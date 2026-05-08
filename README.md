# ttytok 📱

> Control TikTok and social media scroll from your terminal — for when your phone is on a holder and your hands are doing something else.

## What it does

Terminal keyboard → ADB → phone. Arrow keys become swipes. No touch needed.

Built for phone-holder setups. Scroll TikTok, Reels, Shorts without picking up your phone.

## Requirements

- Python 3.6+
- `adb` installed (`android-tools-adb`)
- Tailscale on both PC and phone (or same WiFi)
- Android phone with Wireless Debugging enabled

## Setup

### 1. Enable Wireless Debugging on phone
Settings → Developer Options → Wireless Debugging → ON

### 2. Connect ADB
```bash
adb connect <phone-tailscale-ip>:5555
```

### 3. Run
```bash
ttytok
# or with auto-connect:
ttytok 100.x.x.x:5555
```

## Keys

| Key | Action |
|-----|--------|
| `↓` | Next video (swipe up) |
| `↑` | Previous video (swipe down) |
| `←` `→` | Left / Right |
| `Enter` | Like / confirm |
| `Backspace` | Delete |
| `Space` | Pause / play |
| `a-z 0-9` | Type text |
| `Ctrl+C` | Quit |

## How it works

Detects screen size on startup → calculates swipe coordinates → keeps one persistent `adb shell` open (no per-keypress process spawn = no dropped inputs).

## Network

Works over Tailscale — phone on mobile data, PC on WiFi, zero config after initial setup.
