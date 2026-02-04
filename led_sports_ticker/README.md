# NASCAR LED Sports Ticker

Real-time scrolling leaderboard display for NASCAR races, practice sessions, and qualifying.

```
 CUP Race @ Bowman Gray Stadium [GREEN] Lap 45/200 | LEADER: #5 K. Larson | P1 #5 K. Larson  P2 #24 W. Byron +0.234  P3 #54 T. Gibbs +0.567 ...
```

## Features

- **Live Data**: Pulls real-time data from NASCAR's official APIs
- **Multiple Display Modes**:
  - `scroll` - Single-line scrolling ticker (default)
  - `leaderboard` - Full multi-line leaderboard view
  - `compact` - Compact multi-row display
- **Manufacturer Colors**: Toyota (red), Chevrolet (gold), Ford (blue)
- **Flag Status**: Green, Yellow (Caution), Red, White, Checkered
- **Position Highlighting**: Gold for leader, green for podium
- **Gap Display**: Time gap to leader or laps down
- **Session Support**: Race, Practice, and Qualifying sessions

## Quick Start

```bash
# Run with live NASCAR data
cd led_sports_ticker
python ticker.py

# Run demo mode (sample data)
python demo.py

# Full leaderboard view
python ticker.py -m leaderboard

# Compact multi-row view
python ticker.py -m compact

# Faster scroll, top 10 only
python ticker.py -s 0.05 -n 10
```

## Command Line Options

```
usage: ticker.py [-h] [-m {scroll,leaderboard,compact,battle}]
                 [-n POSITIONS] [-s SPEED] [-r REFRESH] [-w WIDTH]
                 [--no-speed] [--no-gap] [--no-mfr] [--emoji] [--rows ROWS]

Options:
  -m, --mode        Display mode (scroll, leaderboard, compact)
  -n, --positions   Number of positions to show (default: 20)
  -s, --speed       Scroll speed in seconds (default: 0.08)
  -r, --refresh     Data refresh rate in seconds (default: 2.0)
  -w, --width       Display width in characters (default: 120)
  --no-speed        Hide speed/lap time info
  --no-gap          Hide gap to leader
  --no-mfr          Hide manufacturer info
  --emoji           Use emoji symbols
  --rows            Rows for compact mode (default: 5)
```

## Display Modes

### Scroll Mode (Default)
Single-line scrolling ticker, perfect for LED matrix displays:
```
CUP Race @ Bristol [GREEN] Lap 250/500 | LEADER: #11 D. Hamlin | P1 #11 D. Hamlin  P2 #19 M. Truex Jr +1.083  P3 #6 B. Keselowski +2.456 ...
```

### Leaderboard Mode
Full multi-line standings display:
```
Food City 500 @ Bristol Motor Speedway
[GREEN]  Lap 250/500

Pos  #    Driver              Gap        Laps   Stops
P1   #11  D. Hamlin           LEADER     250    3
P2   #19  M. Truex Jr         +1.083     250    3
P3   #6   B. Keselowski       +2.456     250    3
...
```

### Compact Mode
Multi-row compact display:
```
CUP Race [GREEN] Lap 250/500 @ Bristol Motor Speedway
P1 #11 Hamlin  P2 #19 Truex  P3 #6 Keselowski  P4 #24 Elliott
P5 #9 Byron  P6 #5 Larson  P7 #20 Bell  P8 #54 Gibbs
...
```

## Data Available

The ticker uses NASCAR's live API endpoints to display:

| Data | Description |
|------|-------------|
| Position | Current running position |
| Car Number | With manufacturer color coding |
| Driver Name | Short format (K. Larson) |
| Gap to Leader | Time delta or laps down |
| Best Lap Speed | Fastest lap (practice/qualifying) |
| Lap Times | Best and last lap times |
| Flag Status | Current flag state |
| Pit Stops | Number of pit stops |
| Laps Led | Laps in the lead |

## Color Coding

### Positions
- **Gold**: Leader (P1)
- **Green**: Podium (P2-P3)
- **White**: Top 10 (P4-P10)
- **Gray**: Outside top 10

### Manufacturers
- **Red**: Toyota
- **Gold/Yellow**: Chevrolet
- **Blue**: Ford

### Flags
- **Green**: Green flag racing
- **Yellow**: Caution/Yellow flag
- **Red**: Red flag (stopped)
- **White**: White flag (final lap)

## Python API Usage

```python
from led_sports_ticker import NascarAPI, NASCARTicker, TickerConfig, DisplayMode

# Fetch live data directly
api = NascarAPI()
data = api.get_live_feed()

if data:
    print(f"Session: {data.session.run_name}")
    print(f"Leader: {data.leader.driver.full_name}")

    for v in data.get_top_n(10):
        print(f"P{v.running_position} #{v.number} {v.driver.short_name}")

# Run ticker programmatically
config = TickerConfig(
    mode=DisplayMode.SCROLL,
    show_positions=15,
    scroll_speed=0.06,
)
ticker = NASCARTicker(config)
ticker.run()
```

## Hardware Support

Currently supports terminal output. Future versions will support:
- RGB LED Matrix (via rpi-rgb-led-matrix)
- Adafruit LED displays
- Serial LED panels
- WLED integration

## Requirements

- Python 3.7+
- No external dependencies (uses only standard library)

## Files

```
led_sports_ticker/
├── __init__.py       # Package exports
├── nascar_api.py     # NASCAR API client
├── led_display.py    # Display rendering
├── ticker.py         # Main application
├── demo.py           # Demo mode
└── README.md         # This file
```

## License

MIT License - See LICENSE file
