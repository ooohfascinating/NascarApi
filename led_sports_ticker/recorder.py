#!/usr/bin/env python3
"""
NASCAR Race Recorder - Captures live API data for later replay
Records all live feed data at configurable intervals for testing
"""
import json
import gzip
import os
import signal
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
import argparse


@dataclass
class RecordingMetadata:
    """Metadata about a recording session"""
    recording_id: str
    start_time: str
    end_time: Optional[str]
    race_id: int
    series_id: int
    run_name: str
    track_name: str
    run_type: int  # 1=Practice, 2=Qualifying, 3=Race
    interval_ms: int
    total_frames: int
    total_duration_sec: float
    file_size_bytes: int = 0
    compressed: bool = True
    version: str = "1.0"


@dataclass
class RecordedFrame:
    """A single frame of recorded data"""
    timestamp: float  # Unix timestamp
    frame_number: int
    elapsed_ms: int  # MS since recording started
    live_feed: Dict
    flag_data: Optional[List] = None
    pit_data: Optional[List] = None
    points_data: Optional[List] = None
    stage_points: Optional[List] = None


class NASCARRecorder:
    """Records live NASCAR API data to file"""

    API_BASE = "https://cf.nascar.com"
    ENDPOINTS = {
        'live_feed': '/live/feeds/live-feed.json',
        'flag_data': '/live/feeds/live-flag-data.json',
        'pit_data': '/live/feeds/live-pit-data.json',
        'points_data': '/live/feeds/live-points.json',
        'stage_points': '/live/feeds/live-stage-points.json',
    }

    def __init__(self, output_dir: str = "recordings", interval: float = 1.0):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.interval = interval  # Seconds between captures
        self.running = False
        self.frames: List[RecordedFrame] = []
        self.metadata: Optional[RecordingMetadata] = None
        self.start_time: float = 0
        self.frame_count = 0

    def _fetch(self, endpoint: str) -> Optional[Dict]:
        """Fetch JSON from NASCAR API"""
        url = f"{self.API_BASE}{endpoint}"
        try:
            req = urllib.request.Request(url, headers={
                'User-Agent': 'NASCARRecorder/1.0',
                'Accept': 'application/json',
            })
            with urllib.request.urlopen(req, timeout=10) as response:
                return json.loads(response.read().decode('utf-8'))
        except (urllib.error.URLError, json.JSONDecodeError) as e:
            return None

    def _fetch_all_endpoints(self) -> Dict[str, Any]:
        """Fetch data from all endpoints"""
        data = {}
        for name, endpoint in self.ENDPOINTS.items():
            data[name] = self._fetch(endpoint)
        return data

    def _create_recording_id(self, live_feed: Dict) -> str:
        """Create a unique recording ID based on session info"""
        race_id = live_feed.get('race_id', 0)
        series_id = live_feed.get('series_id', 1)
        run_type = live_feed.get('run_type', 1)
        run_types = {1: 'practice', 2: 'qualifying', 3: 'race'}
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        return f"nascar_s{series_id}_r{race_id}_{run_types.get(run_type, 'session')}_{timestamp}"

    def _init_metadata(self, live_feed: Dict) -> RecordingMetadata:
        """Initialize recording metadata from first frame"""
        return RecordingMetadata(
            recording_id=self._create_recording_id(live_feed),
            start_time=datetime.now().isoformat(),
            end_time=None,
            race_id=live_feed.get('race_id', 0),
            series_id=live_feed.get('series_id', 1),
            run_name=live_feed.get('run_name', 'Unknown'),
            track_name=live_feed.get('track_name', 'Unknown'),
            run_type=live_feed.get('run_type', 1),
            interval_ms=int(self.interval * 1000),
            total_frames=0,
            total_duration_sec=0,
        )

    def record_frame(self) -> Optional[RecordedFrame]:
        """Record a single frame of data"""
        data = self._fetch_all_endpoints()
        live_feed = data.get('live_feed')

        if not live_feed:
            return None

        # Initialize metadata on first frame
        if self.metadata is None:
            self.metadata = self._init_metadata(live_feed)
            self.start_time = time.time()

        now = time.time()
        elapsed_ms = int((now - self.start_time) * 1000)

        frame = RecordedFrame(
            timestamp=now,
            frame_number=self.frame_count,
            elapsed_ms=elapsed_ms,
            live_feed=live_feed,
            flag_data=data.get('flag_data'),
            pit_data=data.get('pit_data'),
            points_data=data.get('points_data'),
            stage_points=data.get('stage_points'),
        )

        self.frames.append(frame)
        self.frame_count += 1
        return frame

    def save_recording(self, compress: bool = True) -> str:
        """Save recorded frames to file"""
        if not self.metadata or not self.frames:
            raise ValueError("No data recorded")

        # Update metadata
        self.metadata.end_time = datetime.now().isoformat()
        self.metadata.total_frames = len(self.frames)
        self.metadata.total_duration_sec = (self.frames[-1].timestamp - self.frames[0].timestamp) if self.frames else 0
        self.metadata.compressed = compress

        # Prepare output data
        output = {
            'metadata': asdict(self.metadata),
            'frames': [asdict(f) for f in self.frames],
        }

        # Generate filename
        filename = f"{self.metadata.recording_id}.json"
        if compress:
            filename += ".gz"

        filepath = self.output_dir / filename

        # Write file
        json_data = json.dumps(output, separators=(',', ':'))  # Compact JSON

        if compress:
            with gzip.open(filepath, 'wt', encoding='utf-8') as f:
                f.write(json_data)
        else:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(json_data)

        self.metadata.file_size_bytes = filepath.stat().st_size
        return str(filepath)

    def start_recording(self, duration: Optional[float] = None,
                       max_frames: Optional[int] = None,
                       record_all: bool = True):
        """Start recording live data"""
        self.running = True
        self.frames = []
        self.metadata = None
        self.frame_count = 0

        print(f"\n{'='*60}")
        print(" NASCAR RACE RECORDER")
        print(f"{'='*60}")
        print(f" Interval: {self.interval}s | Output: {self.output_dir}")
        if duration:
            print(f" Duration: {duration}s")
        if max_frames:
            print(f" Max Frames: {max_frames}")
        print(f"{'='*60}\n")

        print(" Waiting for live data...")

        start = time.time()
        last_lap = -1
        last_flag = -1

        try:
            while self.running:
                frame = self.record_frame()

                if frame:
                    # Display progress
                    live = frame.live_feed
                    lap = live.get('lap_number', 0)
                    flag = live.get('flag_state', 0)
                    flag_names = {0: '', 1: 'GRN', 2: 'YEL', 3: 'RED', 4: 'WHT', 5: 'CHK', 8: 'HOT', 9: 'CLD'}

                    # Show session info on first frame
                    if self.frame_count == 1:
                        print(f"\n Recording: {live.get('run_name', 'Unknown')}")
                        print(f" Track: {live.get('track_name', 'Unknown')}")
                        print(f" Race ID: {live.get('race_id', 0)}\n")

                    # Show progress
                    vehicles = live.get('vehicles', [])
                    leader = None
                    for v in vehicles:
                        if v.get('running_position') == 1:
                            leader = v
                            break

                    leader_name = leader['driver']['last_name'] if leader else 'Unknown'
                    leader_num = leader.get('vehicle_number', '?') if leader else '?'

                    elapsed = frame.elapsed_ms / 1000
                    flag_str = flag_names.get(flag, '???')

                    status = f"\r Frame {self.frame_count:5d} | {elapsed:7.1f}s | "
                    status += f"Lap {lap:3d} [{flag_str:3s}] | "
                    status += f"Leader: #{leader_num} {leader_name[:12]:<12s} | "
                    status += f"Cars: {len(vehicles)}"

                    # Highlight lap changes and flag changes
                    if lap != last_lap and last_lap >= 0:
                        status += " [NEW LAP]"
                    if flag != last_flag and last_flag >= 0:
                        status += f" [FLAG: {flag_str}]"

                    print(status, end='', flush=True)
                    last_lap = lap
                    last_flag = flag

                else:
                    print(f"\r Waiting for data... (frame {self.frame_count})", end='', flush=True)

                # Check stop conditions
                if duration and (time.time() - start) >= duration:
                    print(f"\n\n Duration limit reached ({duration}s)")
                    break

                if max_frames and self.frame_count >= max_frames:
                    print(f"\n\n Frame limit reached ({max_frames})")
                    break

                time.sleep(self.interval)

        except KeyboardInterrupt:
            print("\n\n Recording stopped by user")

        self.running = False

    def stop_recording(self):
        """Stop recording"""
        self.running = False


def list_recordings(directory: str = "recordings") -> List[Dict]:
    """List available recordings"""
    recordings = []
    path = Path(directory)

    if not path.exists():
        return recordings

    for file in path.glob("*.json*"):
        try:
            if file.suffix == '.gz':
                with gzip.open(file, 'rt', encoding='utf-8') as f:
                    data = json.load(f)
            else:
                with open(file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

            meta = data.get('metadata', {})
            meta['filename'] = file.name
            meta['filepath'] = str(file)
            recordings.append(meta)
        except Exception as e:
            print(f"Error reading {file}: {e}")

    return sorted(recordings, key=lambda x: x.get('start_time', ''), reverse=True)


def main():
    parser = argparse.ArgumentParser(
        description='NASCAR Race Recorder - Capture live data for replay',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                          # Record until Ctrl+C
  %(prog)s -d 3600                  # Record for 1 hour
  %(prog)s -i 0.5                   # Record every 0.5 seconds
  %(prog)s -f 1000                  # Record 1000 frames
  %(prog)s --list                   # List existing recordings
        """
    )

    parser.add_argument('-o', '--output', type=str, default='recordings',
                        help='Output directory (default: recordings)')
    parser.add_argument('-i', '--interval', type=float, default=1.0,
                        help='Capture interval in seconds (default: 1.0)')
    parser.add_argument('-d', '--duration', type=float, default=None,
                        help='Recording duration in seconds')
    parser.add_argument('-f', '--frames', type=int, default=None,
                        help='Maximum number of frames to record')
    parser.add_argument('--no-compress', action='store_true',
                        help='Save uncompressed JSON')
    parser.add_argument('--list', action='store_true',
                        help='List existing recordings')

    args = parser.parse_args()

    # List recordings
    if args.list:
        recordings = list_recordings(args.output)
        if not recordings:
            print("No recordings found")
            return

        print(f"\n{'='*80}")
        print(" Available Recordings")
        print(f"{'='*80}\n")

        for rec in recordings:
            run_types = {1: 'Practice', 2: 'Qualifying', 3: 'Race'}
            run_type = run_types.get(rec.get('run_type', 1), 'Session')

            print(f" {rec.get('filename', 'Unknown')}")
            print(f"   Session: {rec.get('run_name', 'Unknown')} ({run_type})")
            print(f"   Track:   {rec.get('track_name', 'Unknown')}")
            print(f"   Date:    {rec.get('start_time', 'Unknown')[:19]}")
            print(f"   Frames:  {rec.get('total_frames', 0):,} ({rec.get('total_duration_sec', 0):.1f}s)")
            size_mb = rec.get('file_size_bytes', 0) / 1024 / 1024
            print(f"   Size:    {size_mb:.2f} MB")
            print()

        return

    # Start recording
    recorder = NASCARRecorder(output_dir=args.output, interval=args.interval)

    def signal_handler(sig, frame):
        recorder.stop_recording()

    signal.signal(signal.SIGINT, signal_handler)

    recorder.start_recording(duration=args.duration, max_frames=args.frames)

    # Save recording
    if recorder.frames:
        print("\n Saving recording...")
        filepath = recorder.save_recording(compress=not args.no_compress)
        size_mb = os.path.getsize(filepath) / 1024 / 1024

        print(f"\n{'='*60}")
        print(" RECORDING SAVED")
        print(f"{'='*60}")
        print(f" File: {filepath}")
        print(f" Frames: {recorder.metadata.total_frames:,}")
        print(f" Duration: {recorder.metadata.total_duration_sec:.1f}s")
        print(f" Size: {size_mb:.2f} MB")
        print(f"{'='*60}\n")
    else:
        print("\n No data recorded")


if __name__ == "__main__":
    main()
