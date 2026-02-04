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
- **Race Recording**: Record live race data for replay testing
- **Replay Server**: Replay recorded races anytime for development
- **Manufacturer Colors**: Toyota (red), Chevrolet (gold), Ford (blue)
- **Flag Status**: Green, Yellow (Caution), Red, White, Checkered
- **Position Highlighting**: Gold for leader, green for podium
- **Gap Display**: Time gap to leader or laps down
- **Session Support**: Race, Practice, and Qualifying sessions

## Quick Start

```bash
cd led_sports_ticker

# Run with live NASCAR data
python ticker.py

# Full leaderboard view
python ticker.py -m leaderboard

# Run demo mode (sample data, no live race needed)
python demo.py
```

## Recording & Replay

Record live race data to replay later for testing your LED display:

### Recording a Race

```bash
# Record until you press Ctrl+C
python recorder.py

# Record for 1 hour
python recorder.py -d 3600

# Record with faster capture rate (every 0.5 seconds)
python recorder.py -i 0.5

# Record 1000 frames
python recorder.py -f 1000

# List existing recordings
python recorder.py --list
```

### Playing Back a Recording

```bash
# Start replay server
python replay.py recordings/nascar_s1_r5593_race_20260204.json.gz

# Start at 2x speed
python replay.py --speed 2.0 recording.json.gz

# Use custom port
python replay.py -p 9000 recording.json.gz
```

### Connecting Ticker to Replay

```bash
# In terminal 1: Start replay server
python replay.py recordings/my_recording.json.gz

# In terminal 2: Connect ticker to replay server
python ticker.py --api-url http://localhost:8080
python ticker.py --api-url http://localhost:8080 -m leaderboard
```

### Web Control Interface

Open http://localhost:8080 in your browser to control playback:
- Play/Pause/Stop
- Seek to specific lap
- Adjust playback speed (0.1x - 5x)
- Toggle loop mode

### Replay API Endpoints

| Endpoint | Description |
|----------|-------------|
| `/live/feeds/live-feed.json` | Current frame data (same as NASCAR API) |
| `/replay/status` | Playback status (frame, lap, speed, etc.) |
| `/replay/play` | Start/resume playback |
| `/replay/pause` | Pause playback |
| `/replay/stop` | Stop and reset to beginning |
| `/replay/seek?lap=50` | Seek to lap 50 |
| `/replay/seek?frame=100` | Seek to frame 100 |
| `/replay/seek?percent=50` | Seek to 50% |
| `/replay/speed?value=2.0` | Set 2x playback speed |
| `/replay/loop` | Toggle loop mode |

## Command Line Options

### ticker.py

```
Options:
  -m, --mode        Display mode (scroll, leaderboard, compact)
  -n, --positions   Number of positions to show (default: 20)
  -s, --speed       Scroll speed in seconds (default: 0.08)
  -r, --refresh     Data refresh rate in seconds (default: 2.0)
  -w, --width       Display width in characters (default: 120)
  --api-url         Custom API URL (for replay server)
  --no-speed        Hide speed/lap time info
  --no-gap          Hide gap to leader
  --no-mfr          Hide manufacturer info
  --emoji           Use emoji symbols
  --rows            Rows for compact mode (default: 5)
```

### recorder.py

```
Options:
  -o, --output      Output directory (default: recordings)
  -i, --interval    Capture interval in seconds (default: 1.0)
  -d, --duration    Recording duration in seconds
  -f, --frames      Maximum frames to record
  --no-compress     Save uncompressed JSON
  --list            List existing recordings
```

### replay.py

```
Options:
  -p, --port        Server port (default: 8080)
  -H, --host        Server host (default: 0.0.0.0)
  --speed           Initial playback speed (default: 1.0)
  --no-autoplay     Don't auto-start playback
  --no-loop         Don't loop at end
  --list            List available recordings
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

# Connect to replay server instead of live API
api = NascarAPI(base_url="http://localhost:8080")
data = api.get_live_feed()

# Run ticker with replay server
config = TickerConfig(
    mode=DisplayMode.SCROLL,
    show_positions=15,
    api_url="http://localhost:8080",
)
ticker = NASCARTicker(config)
ticker.run()
```

## Recording File Format

Recordings are stored as gzip-compressed JSON with this structure:

```json
{
  "metadata": {
    "recording_id": "nascar_s1_r5593_race_20260204_153000",
    "start_time": "2026-02-04T15:30:00",
    "end_time": "2026-02-04T19:00:00",
    "race_id": 5593,
    "series_id": 1,
    "run_name": "Daytona 500",
    "track_name": "Daytona International Speedway",
    "run_type": 3,
    "interval_ms": 1000,
    "total_frames": 12600,
    "total_duration_sec": 12600.0
  },
  "frames": [
    {
      "timestamp": 1707061800.0,
      "frame_number": 0,
      "elapsed_ms": 0,
      "live_feed": { ... },
      "flag_data": [ ... ],
      "pit_data": [ ... ],
      "points_data": [ ... ]
    },
    ...
  ]
}
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
├── ticker.py         # Main ticker application
├── recorder.py       # Race data recorder
├── replay.py         # Replay server
├── demo.py           # Demo mode
├── recordings/       # Saved recordings
└── README.md         # This file
```

## License

MIT License - See LICENSE file
