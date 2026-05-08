#!/usr/bin/env python3
"""
Terminal → Phone Keyboard over ADB (Tailscale)
Usage: python3 phone_keyboard.py [device-ip:port]
"""

import sys
import tty
import termios
import subprocess
import os
import select
import re

KEYEVENT = {
    '\r':     66,   # Enter
    '\n':     66,   # Enter
    '\x7f':   67,   # Backspace
    '\x08':   67,   # Backspace (alt)
    '\x1b':   111,  # Escape
    '\t':     61,   # Tab
    ' ':      62,   # Space
}

KEY_LABEL = {
    '\x1b[A': '↑ swipe', '\x1b[B': '↓ swipe',
    '\x1b[C': '→ swipe', '\x1b[D': '← swipe',
    '\r': 'Enter', '\n': 'Enter', '\x7f': 'Backspace', '\x08': 'Backspace',
    '\x1b': 'Esc', '\t': 'Tab', ' ': 'Space',
}

SWIPE_DURATION_MS = 80


class ADBShell:
    """Persistent adb shell — one process, no spawn overhead per keypress."""

    def __init__(self):
        self.proc = subprocess.Popen(
            ['adb', 'shell'],
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    def send(self, cmd: str):
        try:
            self.proc.stdin.write((cmd + '\n').encode())
            self.proc.stdin.flush()
        except BrokenPipeError:
            raise RuntimeError("ADB shell died — device disconnected?")

    def keyevent(self, code: int):
        self.send(f'input keyevent {code}')

    def text(self, char: str):
        # Escape chars that adb shell interprets: \ " $ ` & ; | < > ( )
        escaped = (char
                   .replace('\\', '\\\\')
                   .replace('"', '\\"')
                   .replace('$', '\\$')
                   .replace('`', '\\`'))
        self.send(f'input text "{escaped}"')

    def swipe(self, x1, y1, x2, y2, duration=SWIPE_DURATION_MS):
        self.send(f'input swipe {x1} {y1} {x2} {y2} {duration}')

    def close(self):
        try:
            self.proc.stdin.close()
            self.proc.wait(timeout=2)
        except Exception:
            self.proc.kill()


def get_screen_size():
    result = subprocess.run(['adb', 'shell', 'wm', 'size'], capture_output=True, text=True)
    match = re.search(r'(\d+)x(\d+)', result.stdout)
    if not match:
        return 1080, 1920  # safe fallback
    return int(match.group(1)), int(match.group(2))


def read_key(fd):
    ch = os.read(fd, 1).decode('utf-8', errors='ignore')
    if ch == '\x1b':
        r, _, _ = select.select([fd], [], [], 0.05)
        if r:
            ch2 = os.read(fd, 1).decode('utf-8', errors='ignore')
            if ch2 == '[':
                r2, _, _ = select.select([fd], [], [], 0.05)
                if r2:
                    ch3 = os.read(fd, 1).decode('utf-8', errors='ignore')
                    return '\x1b[' + ch3
            return ch + ch2
    return ch


def check_devices():
    result = subprocess.run(['adb', 'devices'], capture_output=True, text=True)
    lines = result.stdout.strip().split('\n')
    return [l.split()[0] for l in lines[1:] if l.strip() and '\tdevice' in l]


def connect(ip_port):
    result = subprocess.run(['adb', 'connect', ip_port], capture_output=True, text=True)
    return result.stdout.strip()


def main():
    if len(sys.argv) > 1:
        ip_port = sys.argv[1]
        print(f"Connecting to {ip_port}...")
        print(connect(ip_port))

    devices = check_devices()
    if not devices:
        print("No ADB device found.")
        print("  python3 phone_keyboard.py <tailscale-ip>:5555")
        sys.exit(1)

    print(f"Device: {devices[0]}")

    w, h = get_screen_size()
    cx = w // 2
    cy = int(h * 0.40)
    swipe_top    = int(h * 0.30)
    swipe_bottom = int(h * 0.65)
    swipe_left   = int(w * 0.20)
    swipe_right  = int(w * 0.80)
    print(f"Screen: {w}x{h} — vertical swipe y={swipe_top}↔{swipe_bottom}, horizontal x={swipe_left}↔{swipe_right}")
    print("↑ = scroll up (prev)  ↓ = scroll down (next)  ← → = swipe left/right")
    print("Quit: Ctrl+C\n")
    print("--- sending to phone ---")

    shell = ADBShell()
    stdout_fd = sys.stdout.fileno()

    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)

    try:
        tty.setraw(fd)
        while True:
            key = read_key(fd)

            if key == '\x03':  # Ctrl+C
                break

            if key == '\x1b[A':   # Arrow Up → swipe down (scroll to previous)
                shell.swipe(cx, swipe_top, cx, swipe_bottom)
                os.write(stdout_fd, b'[scroll-prev]')
            elif key == '\x1b[B': # Arrow Down → swipe up (scroll to next)
                shell.swipe(cx, swipe_bottom, cx, swipe_top)
                os.write(stdout_fd, b'[scroll-next]')
            elif key == '\x1b[C': # Arrow Right → swipe right
                shell.swipe(swipe_right, cy, swipe_left, cy)
                os.write(stdout_fd, b'[swipe-left]')
            elif key == '\x1b[D': # Arrow Left → swipe left
                shell.swipe(swipe_left, cy, swipe_right, cy)
                os.write(stdout_fd, b'[swipe-right]')
            elif key in KEYEVENT:
                shell.keyevent(KEYEVENT[key])
                label = KEY_LABEL.get(key, key)
                os.write(stdout_fd, f'[{label}]'.encode())
            elif len(key) == 1 and key.isprintable():
                shell.text(key)
                os.write(stdout_fd, key.encode())

    except RuntimeError as e:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        print(f"\nError: {e}")
        sys.exit(1)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        shell.close()
        print("\n\nDisconnected.")


if __name__ == '__main__':
    main()
