#!/usr/bin/env python3
"""
NASCAR Race Replay Server - Serves recorded data as live API
Allows testing ticker features without live race data
"""
import argparse
import gzip
import json
import os
import signal
import sys
import threading
import time
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from typing import Dict, List, Optional, Any
from urllib.parse import urlparse, parse_qs


class ReplayState:
    """Manages playback state for replayed data"""

    def __init__(self, recording_path: str):
        self.recording_path = recording_path
        self.metadata: Dict = {}
        self.frames: List[Dict] = []
        self.current_frame: int = 0
        self.playback_speed: float = 1.0
        self.is_playing: bool = False
        self.is_paused: bool = False
        self.loop: bool = True
        self.last_frame_time: float = 0
        self._lock = threading.Lock()

        self._load_recording()

    def _load_recording(self):
        """Load recording from file"""
        path = Path(self.recording_path)

        if not path.exists():
            raise FileNotFoundError(f"Recording not found: {self.recording_path}")

        print(f" Loading: {path.name}...")

        if path.suffix == '.gz':
            with gzip.open(path, 'rt', encoding='utf-8') as f:
                data = json.load(f)
        else:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)

        self.metadata = data.get('metadata', {})
        self.frames = data.get('frames', [])

        if not self.frames:
            raise ValueError("Recording contains no frames")

        print(f" Loaded {len(self.frames):,} frames")
        print(f" Session: {self.metadata.get('run_name', 'Unknown')}")
        print(f" Track: {self.metadata.get('track_name', 'Unknown')}")
        print(f" Duration: {self.metadata.get('total_duration_sec', 0):.1f}s")

    def start(self):
        """Start playback"""
        self.is_playing = True
        self.is_paused = False
        self.last_frame_time = time.time()

    def pause(self):
        """Pause playback"""
        self.is_paused = True

    def resume(self):
        """Resume playback"""
        self.is_paused = False
        self.last_frame_time = time.time()

    def stop(self):
        """Stop playback"""
        self.is_playing = False

    def seek(self, frame_number: int):
        """Seek to specific frame"""
        with self._lock:
            self.current_frame = max(0, min(frame_number, len(self.frames) - 1))
            self.last_frame_time = time.time()

    def seek_percent(self, percent: float):
        """Seek to percentage of recording"""
        frame = int((percent / 100) * len(self.frames))
        self.seek(frame)

    def seek_lap(self, lap: int):
        """Seek to specific lap number"""
        for i, frame in enumerate(self.frames):
            live_feed = frame.get('live_feed', {})
            if live_feed.get('lap_number', 0) >= lap:
                self.seek(i)
                return True
        return False

    def set_speed(self, speed: float):
        """Set playback speed multiplier"""
        self.playback_speed = max(0.1, min(10.0, speed))

    def get_current_frame(self) -> Optional[Dict]:
        """Get the current frame based on playback timing"""
        if not self.frames or not self.is_playing:
            return None

        with self._lock:
            if self.is_paused:
                return self.frames[self.current_frame]

            # Calculate which frame we should be on based on elapsed time
            now = time.time()
            elapsed = (now - self.last_frame_time) * self.playback_speed

            # Get frame interval from metadata (or default to 1 second)
            interval_ms = self.metadata.get('interval_ms', 1000)
            interval_sec = interval_ms / 1000

            # Advance frames based on elapsed time
            frames_to_advance = int(elapsed / interval_sec)

            if frames_to_advance > 0:
                self.current_frame += frames_to_advance
                self.last_frame_time = now

                # Handle loop or stop at end
                if self.current_frame >= len(self.frames):
                    if self.loop:
                        self.current_frame = 0
                    else:
                        self.current_frame = len(self.frames) - 1
                        self.is_playing = False

            return self.frames[self.current_frame]

    def get_status(self) -> Dict:
        """Get current playback status"""
        current = self.frames[self.current_frame] if self.frames else {}
        live_feed = current.get('live_feed', {})

        return {
            'playing': self.is_playing,
            'paused': self.is_paused,
            'speed': self.playback_speed,
            'loop': self.loop,
            'current_frame': self.current_frame,
            'total_frames': len(self.frames),
            'progress_percent': (self.current_frame / len(self.frames) * 100) if self.frames else 0,
            'current_lap': live_feed.get('lap_number', 0),
            'total_laps': live_feed.get('laps_in_race', 0),
            'flag_state': live_feed.get('flag_state', 0),
            'session': self.metadata.get('run_name', 'Unknown'),
            'track': self.metadata.get('track_name', 'Unknown'),
        }


class ReplayRequestHandler(BaseHTTPRequestHandler):
    """HTTP request handler that serves replay data"""

    # Class-level state (shared across all requests)
    replay_state: Optional[ReplayState] = None

    def log_message(self, format, *args):
        """Suppress default logging"""
        pass

    def _send_json(self, data: Any, status: int = 200):
        """Send JSON response"""
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode('utf-8'))

    def _send_error(self, message: str, status: int = 400):
        """Send error response"""
        self._send_json({'error': message}, status)

    def do_GET(self):
        """Handle GET requests"""
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)

        # NASCAR API endpoints
        if path == '/live/feeds/live-feed.json':
            self._handle_live_feed()
        elif path == '/live/feeds/live-flag-data.json':
            self._handle_flag_data()
        elif path == '/live/feeds/live-pit-data.json':
            self._handle_pit_data()
        elif path == '/live/feeds/live-points.json':
            self._handle_points_data()
        elif path == '/live/feeds/live-stage-points.json':
            self._handle_stage_points()

        # Replay control endpoints
        elif path == '/replay/status':
            self._handle_status()
        elif path == '/replay/play':
            self._handle_play()
        elif path == '/replay/pause':
            self._handle_pause()
        elif path == '/replay/stop':
            self._handle_stop()
        elif path == '/replay/seek':
            self._handle_seek(query)
        elif path == '/replay/speed':
            self._handle_speed(query)
        elif path == '/replay/loop':
            self._handle_loop(query)

        # Web UI
        elif path == '/' or path == '/index.html':
            self._handle_web_ui()

        else:
            self._send_error(f"Unknown endpoint: {path}", 404)

    def _handle_live_feed(self):
        """Serve live-feed.json from replay"""
        if not self.replay_state:
            self._send_error("No replay loaded", 500)
            return

        frame = self.replay_state.get_current_frame()
        if frame:
            self._send_json(frame.get('live_feed', {}))
        else:
            self._send_error("No data available", 404)

    def _handle_flag_data(self):
        """Serve live-flag-data.json from replay"""
        if not self.replay_state:
            self._send_error("No replay loaded", 500)
            return

        frame = self.replay_state.get_current_frame()
        if frame:
            self._send_json(frame.get('flag_data') or [])
        else:
            self._send_json([])

    def _handle_pit_data(self):
        """Serve live-pit-data.json from replay"""
        if not self.replay_state:
            self._send_error("No replay loaded", 500)
            return

        frame = self.replay_state.get_current_frame()
        if frame:
            self._send_json(frame.get('pit_data') or [])
        else:
            self._send_json([])

    def _handle_points_data(self):
        """Serve live-points.json from replay"""
        if not self.replay_state:
            self._send_error("No replay loaded", 500)
            return

        frame = self.replay_state.get_current_frame()
        if frame:
            self._send_json(frame.get('points_data') or [])
        else:
            self._send_json([])

    def _handle_stage_points(self):
        """Serve live-stage-points.json from replay"""
        if not self.replay_state:
            self._send_error("No replay loaded", 500)
            return

        frame = self.replay_state.get_current_frame()
        if frame:
            self._send_json(frame.get('stage_points') or [])
        else:
            self._send_json([])

    def _handle_status(self):
        """Return replay status"""
        if self.replay_state:
            self._send_json(self.replay_state.get_status())
        else:
            self._send_error("No replay loaded", 500)

    def _handle_play(self):
        """Start/resume playback"""
        if self.replay_state:
            if self.replay_state.is_paused:
                self.replay_state.resume()
            else:
                self.replay_state.start()
            self._send_json({'status': 'playing'})
        else:
            self._send_error("No replay loaded", 500)

    def _handle_pause(self):
        """Pause playback"""
        if self.replay_state:
            self.replay_state.pause()
            self._send_json({'status': 'paused'})
        else:
            self._send_error("No replay loaded", 500)

    def _handle_stop(self):
        """Stop playback"""
        if self.replay_state:
            self.replay_state.stop()
            self.replay_state.seek(0)
            self._send_json({'status': 'stopped'})
        else:
            self._send_error("No replay loaded", 500)

    def _handle_seek(self, query: Dict):
        """Seek to position"""
        if not self.replay_state:
            self._send_error("No replay loaded", 500)
            return

        if 'frame' in query:
            frame = int(query['frame'][0])
            self.replay_state.seek(frame)
            self._send_json({'status': 'seeked', 'frame': frame})
        elif 'percent' in query:
            percent = float(query['percent'][0])
            self.replay_state.seek_percent(percent)
            self._send_json({'status': 'seeked', 'percent': percent})
        elif 'lap' in query:
            lap = int(query['lap'][0])
            if self.replay_state.seek_lap(lap):
                self._send_json({'status': 'seeked', 'lap': lap})
            else:
                self._send_error(f"Lap {lap} not found", 404)
        else:
            self._send_error("Missing seek parameter (frame, percent, or lap)", 400)

    def _handle_speed(self, query: Dict):
        """Set playback speed"""
        if not self.replay_state:
            self._send_error("No replay loaded", 500)
            return

        if 'value' in query:
            speed = float(query['value'][0])
            self.replay_state.set_speed(speed)
            self._send_json({'status': 'speed_set', 'speed': self.replay_state.playback_speed})
        else:
            self._send_error("Missing speed value", 400)

    def _handle_loop(self, query: Dict):
        """Toggle loop mode"""
        if not self.replay_state:
            self._send_error("No replay loaded", 500)
            return

        if 'value' in query:
            self.replay_state.loop = query['value'][0].lower() in ('true', '1', 'yes')
        else:
            self.replay_state.loop = not self.replay_state.loop

        self._send_json({'status': 'loop_set', 'loop': self.replay_state.loop})

    def _handle_web_ui(self):
        """Serve web control UI"""
        html = """<!DOCTYPE html>
<html>
<head>
    <title>NASCAR Replay Control</title>
    <style>
        body { font-family: Arial, sans-serif; background: #1a1a2e; color: #eee; padding: 20px; }
        .container { max-width: 800px; margin: 0 auto; }
        h1 { color: #ffd700; }
        .status { background: #16213e; padding: 20px; border-radius: 10px; margin: 20px 0; }
        .controls { display: flex; gap: 10px; flex-wrap: wrap; margin: 20px 0; }
        button { background: #e94560; color: white; border: none; padding: 10px 20px;
                 border-radius: 5px; cursor: pointer; font-size: 16px; }
        button:hover { background: #ff6b6b; }
        button.secondary { background: #0f3460; }
        button.secondary:hover { background: #1a4f7a; }
        .progress { background: #0f3460; height: 30px; border-radius: 5px; margin: 20px 0; position: relative; }
        .progress-bar { background: #e94560; height: 100%; border-radius: 5px; transition: width 0.3s; }
        .progress-text { position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); }
        input[type=range] { width: 200px; }
        .info { display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px; }
        .info-item { background: #0f3460; padding: 10px; border-radius: 5px; }
        .label { color: #888; font-size: 12px; }
        .value { font-size: 18px; font-weight: bold; }
    </style>
</head>
<body>
    <div class="container">
        <h1>NASCAR Replay Control</h1>

        <div class="status">
            <div class="info">
                <div class="info-item">
                    <div class="label">Session</div>
                    <div class="value" id="session">-</div>
                </div>
                <div class="info-item">
                    <div class="label">Track</div>
                    <div class="value" id="track">-</div>
                </div>
                <div class="info-item">
                    <div class="label">Current Lap</div>
                    <div class="value" id="lap">-</div>
                </div>
                <div class="info-item">
                    <div class="label">Flag</div>
                    <div class="value" id="flag">-</div>
                </div>
                <div class="info-item">
                    <div class="label">Frame</div>
                    <div class="value" id="frame">-</div>
                </div>
                <div class="info-item">
                    <div class="label">Speed</div>
                    <div class="value" id="speed">-</div>
                </div>
            </div>

            <div class="progress">
                <div class="progress-bar" id="progress-bar"></div>
                <div class="progress-text" id="progress-text">0%</div>
            </div>
        </div>

        <div class="controls">
            <button onclick="play()">Play</button>
            <button onclick="pause()">Pause</button>
            <button onclick="stop()">Stop</button>
            <button class="secondary" onclick="seek(0)">Restart</button>
            <button class="secondary" onclick="toggleLoop()">Toggle Loop</button>
        </div>

        <div class="controls">
            <label>Speed: <input type="range" id="speed-slider" min="0.1" max="5" step="0.1" value="1"
                   onchange="setSpeed(this.value)"></label>
            <label>Seek to Lap: <input type="number" id="lap-input" min="1" style="width:60px">
                   <button class="secondary" onclick="seekLap()">Go</button></label>
        </div>

        <p style="color:#888; margin-top:40px;">
            API Endpoints:<br>
            <code>/live/feeds/live-feed.json</code> - Live feed data<br>
            <code>/replay/status</code> - Playback status<br>
            <code>/replay/play</code> - Start playback<br>
            <code>/replay/pause</code> - Pause playback<br>
            <code>/replay/seek?lap=50</code> - Seek to lap
        </p>
    </div>

    <script>
        const flags = {0:'None',1:'GREEN',2:'CAUTION',3:'RED',4:'WHITE',5:'CHECKERED',8:'HOT',9:'COLD'};

        function updateStatus() {
            fetch('/replay/status')
                .then(r => r.json())
                .then(d => {
                    document.getElementById('session').textContent = d.session;
                    document.getElementById('track').textContent = d.track;
                    document.getElementById('lap').textContent = d.current_lap + '/' + d.total_laps;
                    document.getElementById('flag').textContent = flags[d.flag_state] || 'Unknown';
                    document.getElementById('frame').textContent = d.current_frame + '/' + d.total_frames;
                    document.getElementById('speed').textContent = d.speed + 'x' + (d.loop ? ' (loop)' : '');
                    document.getElementById('progress-bar').style.width = d.progress_percent + '%';
                    document.getElementById('progress-text').textContent = d.progress_percent.toFixed(1) + '%';
                });
        }

        function play() { fetch('/replay/play'); }
        function pause() { fetch('/replay/pause'); }
        function stop() { fetch('/replay/stop'); }
        function seek(frame) { fetch('/replay/seek?frame=' + frame); }
        function seekLap() { fetch('/replay/seek?lap=' + document.getElementById('lap-input').value); }
        function setSpeed(v) { fetch('/replay/speed?value=' + v); }
        function toggleLoop() { fetch('/replay/loop'); }

        setInterval(updateStatus, 500);
        updateStatus();
    </script>
</body>
</html>"""
        self.send_response(200)
        self.send_header('Content-Type', 'text/html')
        self.end_headers()
        self.wfile.write(html.encode('utf-8'))


class ReplayServer:
    """HTTP server for NASCAR replay"""

    def __init__(self, recording_path: str, host: str = '0.0.0.0', port: int = 8080):
        self.host = host
        self.port = port
        self.replay_state = ReplayState(recording_path)
        self.server: Optional[HTTPServer] = None

    def start(self, auto_play: bool = True):
        """Start the replay server"""
        # Set up handler with replay state
        ReplayRequestHandler.replay_state = self.replay_state

        self.server = HTTPServer((self.host, self.port), ReplayRequestHandler)

        if auto_play:
            self.replay_state.start()

        print(f"\n{'='*60}")
        print(" NASCAR REPLAY SERVER")
        print(f"{'='*60}")
        print(f" Server:  http://{self.host}:{self.port}")
        print(f" Control: http://localhost:{self.port}/")
        print(f"{'='*60}")
        print(f"\n Point your ticker at: http://localhost:{self.port}")
        print(f" Example: Set API base URL to http://localhost:{self.port}\n")
        print(" Press Ctrl+C to stop\n")

        try:
            self.server.serve_forever()
        except KeyboardInterrupt:
            print("\n Server stopped")

    def stop(self):
        """Stop the server"""
        if self.server:
            self.server.shutdown()


def list_recordings(directory: str = "recordings") -> List[Dict]:
    """List available recordings"""
    from recorder import list_recordings as list_recs
    return list_recs(directory)


def main():
    parser = argparse.ArgumentParser(
        description='NASCAR Replay Server - Serve recorded data as live API',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s recording.json.gz        # Start server with recording
  %(prog)s -p 9000 recording.json   # Use custom port
  %(prog)s --list                   # List available recordings
  %(prog)s --speed 2.0 rec.json.gz  # Start at 2x speed

Replay Control (via HTTP):
  GET /replay/status                # Get playback status
  GET /replay/play                  # Start/resume playback
  GET /replay/pause                 # Pause playback
  GET /replay/seek?lap=50           # Seek to lap 50
  GET /replay/speed?value=2.0       # Set 2x playback speed
        """
    )

    parser.add_argument('recording', nargs='?', help='Recording file to replay')
    parser.add_argument('-p', '--port', type=int, default=8080,
                        help='Server port (default: 8080)')
    parser.add_argument('-H', '--host', type=str, default='0.0.0.0',
                        help='Server host (default: 0.0.0.0)')
    parser.add_argument('--speed', type=float, default=1.0,
                        help='Initial playback speed (default: 1.0)')
    parser.add_argument('--no-autoplay', action='store_true',
                        help='Do not auto-start playback')
    parser.add_argument('--no-loop', action='store_true',
                        help='Do not loop at end of recording')
    parser.add_argument('--list', action='store_true',
                        help='List available recordings')
    parser.add_argument('-d', '--directory', type=str, default='recordings',
                        help='Recordings directory (default: recordings)')

    args = parser.parse_args()

    # List recordings
    if args.list:
        try:
            recordings = list_recordings(args.directory)
        except ImportError:
            # Fall back to inline implementation
            recordings = []
            path = Path(args.directory)
            if path.exists():
                for file in path.glob("*.json*"):
                    recordings.append({'filename': file.name, 'filepath': str(file)})

        if not recordings:
            print("No recordings found")
            return

        print(f"\n Available Recordings in '{args.directory}':\n")
        for i, rec in enumerate(recordings, 1):
            print(f" {i}. {rec.get('filename', 'Unknown')}")
            if 'run_name' in rec:
                print(f"    {rec.get('run_name')} @ {rec.get('track_name')}")
        print()
        return

    # Require recording file
    if not args.recording:
        parser.error("Recording file required (or use --list)")

    # Find recording file
    recording_path = args.recording
    if not os.path.exists(recording_path):
        # Try in recordings directory
        alt_path = os.path.join(args.directory, args.recording)
        if os.path.exists(alt_path):
            recording_path = alt_path
        else:
            print(f"Error: Recording not found: {args.recording}")
            sys.exit(1)

    # Start server
    server = ReplayServer(recording_path, host=args.host, port=args.port)

    # Apply settings
    server.replay_state.playback_speed = args.speed
    server.replay_state.loop = not args.no_loop

    def signal_handler(sig, frame):
        server.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)

    server.start(auto_play=not args.no_autoplay)


if __name__ == "__main__":
    main()
