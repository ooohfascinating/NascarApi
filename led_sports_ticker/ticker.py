#!/usr/bin/env python3
"""
NASCAR LED Sports Ticker - Main Application
Real-time scrolling leaderboard display for NASCAR races
"""
import argparse
import signal
import sys
import time
import os
from typing import List, Optional
from dataclasses import dataclass
from enum import Enum

from nascar_api import NascarAPI, LiveData, Vehicle
from led_display import (
    TerminalDisplay, TextSegment, Color, ScrollingText,
    TickerRenderer, create_display
)


class DisplayMode(Enum):
    SCROLL = "scroll"           # Scrolling single-line ticker
    LEADERBOARD = "leaderboard" # Full leaderboard view
    COMPACT = "compact"         # Compact multi-line view
    BATTLE = "battle"           # Focus on position battles


@dataclass
class TickerConfig:
    """Configuration for the ticker display"""
    mode: DisplayMode = DisplayMode.SCROLL
    scroll_speed: float = 0.08  # Seconds between scroll updates
    refresh_rate: float = 2.0   # Seconds between data refreshes
    show_positions: int = 20    # Number of positions to show
    show_speed: bool = True     # Show lap speeds
    show_gap: bool = True       # Show gap to leader
    show_laps: bool = True      # Show laps completed
    show_manufacturer: bool = True
    show_flag: bool = True
    compact_rows: int = 5       # Rows for compact mode
    width: int = 120            # Display width (chars for terminal)
    use_emoji: bool = False     # Use emoji symbols
    api_url: Optional[str] = None  # Custom API URL (for replay server)


class NASCARTicker:
    """Main ticker application"""

    def __init__(self, config: TickerConfig):
        self.config = config
        self.api = NascarAPI(base_url=config.api_url)
        self.display = create_display("terminal", width=config.width, use_emoji=config.use_emoji)
        self.renderer = TickerRenderer(use_emoji=config.use_emoji)
        self.scroller = ScrollingText(self.display, speed=config.scroll_speed)
        self.running = False
        self.last_data: Optional[LiveData] = None
        self.last_refresh = 0

    def build_scroll_content(self, data: LiveData) -> List[TextSegment]:
        """Build scrolling ticker content from live data"""
        segments: List[TextSegment] = []

        # Session header
        series_short = self.api.get_series_name(data.session.series_id, short=True)
        run_type = self.api.get_run_type(data.session.run_type)

        segments.append(TextSegment(f" {series_short} ", Color.NASCAR_YELLOW.value, bold=True))
        segments.append(TextSegment(f"{run_type} ", Color.WHITE.value))
        segments.append(TextSegment(f"@ {data.session.track_name} ", Color.CYAN.value))

        # Flag status
        if self.config.show_flag:
            segments.extend(self.renderer.format_flag(data.session.flag_state))

        # Lap counter
        if data.session.run_type == 3:  # Race
            if self.config.show_laps:
                segments.append(TextSegment(f"Lap {data.session.lap_number}/{data.session.laps_in_race} ", Color.WHITE.value))
                if data.session.laps_to_go <= 10 and data.session.laps_to_go > 0:
                    segments.append(TextSegment(f"({data.session.laps_to_go} TO GO!) ", Color.RED.value, bold=True))
        else:
            # Practice/Qualifying - show elapsed time
            elapsed_min = data.session.elapsed_time // 60
            elapsed_sec = data.session.elapsed_time % 60
            segments.append(TextSegment(f"[{elapsed_min}:{elapsed_sec:02d}] ", Color.GRAY.value))

        segments.append(TextSegment(" | ", Color.GRAY.value))

        # Leader info
        leader = data.leader
        if leader:
            segments.append(TextSegment("LEADER: ", Color.GOLD.value, bold=True))
            segments.append(TextSegment(f"#{leader.number} ", Color.WHITE.value, bold=True))
            segments.append(TextSegment(f"{leader.driver.short_name} ", Color.WHITE.value))
            if self.config.show_manufacturer:
                segments.append(self.renderer.format_manufacturer(leader.manufacturer))
                segments.append(TextSegment(" ", Color.WHITE.value))
            if self.config.show_speed and leader.best_lap_speed > 0:
                segments.append(self.renderer.format_speed(leader.best_lap_speed))
            segments.append(TextSegment(" | ", Color.GRAY.value))

        # Top positions
        for vehicle in data.get_top_n(self.config.show_positions):
            segments.extend(self._format_vehicle_scroll(vehicle, data))
            segments.append(TextSegment("  ", Color.BLACK.value))

        # Stats section
        if data.session.run_type == 3:  # Race only stats
            segments.append(TextSegment(" | ", Color.GRAY.value))
            segments.append(TextSegment(f"Lead Changes: {data.session.num_lead_changes} ", Color.CYAN.value))
            segments.append(TextSegment(f"Cautions: {data.session.num_cautions} ", Color.YELLOW.value))

        return segments

    def _format_vehicle_scroll(self, vehicle: Vehicle, data: LiveData) -> List[TextSegment]:
        """Format a single vehicle for scrolling display"""
        segments: List[TextSegment] = []

        # Position
        segments.append(self.renderer.format_position(vehicle.running_position))
        segments.append(TextSegment(" ", Color.WHITE.value))

        # Car number with manufacturer color
        mfr_colors = {
            'Tyt': Color.TOYOTA_RED.value,
            'Chv': Color.CHEVY_GOLD.value,
            'Frd': Color.FORD_BLUE.value,
        }
        num_color = mfr_colors.get(vehicle.manufacturer, Color.WHITE.value)
        segments.append(TextSegment(f"#{vehicle.number}", num_color, bold=True))
        segments.append(TextSegment(" ", Color.WHITE.value))

        # Driver name
        segments.append(TextSegment(vehicle.driver.short_name, Color.WHITE.value))

        # Gap to leader
        if self.config.show_gap and vehicle.running_position > 1:
            segments.append(TextSegment(" ", Color.WHITE.value))
            leader = data.leader
            leader_laps = leader.laps_completed if leader else vehicle.laps_completed
            segments.append(self.renderer.format_gap(vehicle.delta, vehicle.laps_completed, leader_laps))

        # Best speed (for practice/qualifying)
        if self.config.show_speed and data.session.run_type in (1, 2):
            if vehicle.best_lap_speed > 0:
                segments.append(TextSegment(" ", Color.WHITE.value))
                segments.append(TextSegment(f"{vehicle.best_lap_speed:.2f}", Color.CYAN.value))

        return segments

    def build_leaderboard_content(self, data: LiveData) -> List[str]:
        """Build multi-line leaderboard display"""
        lines = []

        # Header
        series = self.api.get_series_name(data.session.series_id)
        flag_text = self.api.get_flag_text(data.session.flag_state)
        flag_color = self.api.get_flag_color(data.session.flag_state)

        header = f"\033[1;33m{data.session.run_name}\033[0m @ \033[1;36m{data.session.track_name}\033[0m"
        lines.append(header)

        # Flag and lap info
        flag_ansi = {
            'green': '\033[1;32m',
            'yellow': '\033[1;33m',
            'red': '\033[1;31m',
            'white': '\033[1;37m',
        }.get(flag_color, '\033[0m')

        if data.session.run_type == 3:
            status = f"{flag_ansi}[{flag_text}]\033[0m  Lap {data.session.lap_number}/{data.session.laps_in_race}"
            if data.session.laps_to_go <= 10:
                status += f"  \033[1;31m{data.session.laps_to_go} TO GO!\033[0m"
        else:
            elapsed = f"{data.session.elapsed_time // 60}:{data.session.elapsed_time % 60:02d}"
            status = f"{flag_ansi}[{flag_text}]\033[0m  Elapsed: {elapsed}"

        lines.append(status)
        lines.append("")

        # Column headers
        if data.session.run_type == 3:
            header = f"{'Pos':<4} {'#':<4} {'Driver':<18} {'Gap':<10} {'Laps':<6} {'Stops':<5}"
        else:
            header = f"{'Pos':<4} {'#':<4} {'Driver':<18} {'Best Time':<12} {'Speed':<10} {'Laps':<5}"
        lines.append(f"\033[1;4m{header}\033[0m")

        # Positions
        leader = data.leader
        for v in data.get_top_n(self.config.show_positions):
            pos_color = '\033[1;33m' if v.running_position == 1 else (
                '\033[1;32m' if v.running_position <= 3 else (
                    '\033[0m' if v.running_position <= 10 else '\033[2m'
                )
            )

            mfr_color = {
                'Tyt': '\033[31m',
                'Chv': '\033[33m',
                'Frd': '\033[34m',
            }.get(v.manufacturer, '')

            if data.session.run_type == 3:
                # Race format
                if v.running_position == 1:
                    gap = "LEADER"
                elif leader and v.laps_completed < leader.laps_completed:
                    gap = f"-{leader.laps_completed - v.laps_completed}L"
                else:
                    gap = f"+{v.delta:.3f}" if v.delta < 10 else f"+{v.delta:.1f}"

                line = f"{pos_color}P{v.running_position:<3}\033[0m {mfr_color}#{v.number:<3}\033[0m {v.driver.short_name:<18} {gap:<10} {v.laps_completed:<6} {v.pit_stops:<5}"
            else:
                # Practice/Qualifying format
                time_str = f"{v.best_lap_time:.3f}" if v.best_lap_time > 0 else "---"
                speed_str = f"{v.best_lap_speed:.3f}" if v.best_lap_speed > 0 else "---"

                line = f"{pos_color}P{v.running_position:<3}\033[0m {mfr_color}#{v.number:<3}\033[0m {v.driver.short_name:<18} {time_str:<12} {speed_str:<10} {v.laps_completed:<5}"

            lines.append(line)

        # Footer stats
        lines.append("")
        if data.session.run_type == 3:
            stats = f"Lead Changes: {data.session.num_lead_changes} | Leaders: {data.session.num_leaders} | Cautions: {data.session.num_cautions} ({data.session.num_caution_laps} laps)"
        else:
            stats = f"Cars on Track: {sum(1 for v in data.vehicles if v.is_on_track)} | Total Entries: {len(data.vehicles)}"
        lines.append(f"\033[2m{stats}\033[0m")

        return lines

    def build_compact_content(self, data: LiveData) -> List[str]:
        """Build compact multi-row ticker display"""
        lines = []

        # Session info line
        series = self.api.get_series_name(data.session.series_id, short=True)
        flag = self.api.get_flag_text(data.session.flag_state)
        flag_colors = {
            1: '\033[32m', 2: '\033[33m', 3: '\033[31m',
            4: '\033[37m', 5: '\033[37m', 8: '\033[33m', 9: '\033[36m'
        }
        fc = flag_colors.get(data.session.flag_state, '')

        if data.session.run_type == 3:
            info = f"\033[1;33m{series}\033[0m {fc}[{flag}]\033[0m Lap {data.session.lap_number}/{data.session.laps_in_race} @ {data.session.track_name}"
        else:
            info = f"\033[1;33m{series} {self.api.get_run_type(data.session.run_type)}\033[0m {fc}[{flag}]\033[0m @ {data.session.track_name}"
        lines.append(info)

        # Positions in rows
        vehicles = data.get_top_n(self.config.show_positions)
        per_row = len(vehicles) // self.config.compact_rows + 1

        for row in range(self.config.compact_rows):
            start = row * per_row
            end = min(start + per_row, len(vehicles))
            row_vehicles = vehicles[start:end]

            row_text = ""
            for v in row_vehicles:
                mfr_color = {'Tyt': '\033[31m', 'Chv': '\033[33m', 'Frd': '\033[34m'}.get(v.manufacturer, '')
                pos_color = '\033[1;33m' if v.running_position == 1 else '\033[0m'
                row_text += f"{pos_color}P{v.running_position}\033[0m {mfr_color}#{v.number}\033[0m {v.driver.last_name[:10]}  "

            lines.append(row_text.rstrip())

        return lines

    def fetch_data(self) -> Optional[LiveData]:
        """Fetch fresh data from API"""
        now = time.time()
        if now - self.last_refresh >= self.config.refresh_rate:
            self.last_data = self.api.get_live_feed()
            self.last_refresh = now
        return self.last_data

    def run_scroll_mode(self):
        """Run scrolling ticker mode"""
        print("\033[?25l", end='')  # Hide cursor

        try:
            while self.running:
                data = self.fetch_data()
                if data:
                    content = self.build_scroll_content(data)
                    self.scroller.set_content(content)

                    # Scroll through content
                    for _ in range(self.scroller.content_width + self.config.width):
                        if not self.running:
                            break
                        self.display.clear()
                        visible = self.scroller.get_visible_segments(self.config.width)
                        self.display.draw_text(0, 0, visible)
                        self.display.show()
                        self.scroller.step()
                        time.sleep(self.config.scroll_speed)

                        # Check for new data mid-scroll
                        if time.time() - self.last_refresh >= self.config.refresh_rate:
                            break
                else:
                    print("\rWaiting for NASCAR live data...", end='')
                    time.sleep(2)

        finally:
            print("\033[?25h")  # Show cursor
            print()

    def run_leaderboard_mode(self):
        """Run full leaderboard mode"""
        try:
            while self.running:
                data = self.fetch_data()
                if data:
                    lines = self.build_leaderboard_content(data)
                    # Clear screen and print
                    print("\033[2J\033[H", end='')
                    for line in lines:
                        print(line)
                else:
                    print("\033[2J\033[HWaiting for NASCAR live data...")

                time.sleep(self.config.refresh_rate)
        except KeyboardInterrupt:
            pass

    def run_compact_mode(self):
        """Run compact multi-line mode"""
        try:
            while self.running:
                data = self.fetch_data()
                if data:
                    lines = self.build_compact_content(data)
                    print("\033[2J\033[H", end='')
                    for line in lines:
                        print(line)
                else:
                    print("\033[2J\033[HWaiting for NASCAR live data...")

                time.sleep(self.config.refresh_rate)
        except KeyboardInterrupt:
            pass

    def run(self):
        """Main run loop"""
        self.running = True

        def signal_handler(sig, frame):
            self.running = False
            print("\n\033[?25h")  # Restore cursor
            sys.exit(0)

        signal.signal(signal.SIGINT, signal_handler)

        print(f"\n NASCAR LED Ticker - Mode: {self.config.mode.value}")
        print(" Press Ctrl+C to exit\n")
        time.sleep(1)

        if self.config.mode == DisplayMode.SCROLL:
            self.run_scroll_mode()
        elif self.config.mode == DisplayMode.LEADERBOARD:
            self.run_leaderboard_mode()
        elif self.config.mode == DisplayMode.COMPACT:
            self.run_compact_mode()
        else:
            self.run_scroll_mode()

    def stop(self):
        """Stop the ticker"""
        self.running = False


def main():
    parser = argparse.ArgumentParser(
        description='NASCAR LED Sports Ticker - Real-time race leaderboard display',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Display Modes:
  scroll      - Single-line scrolling ticker (default)
  leaderboard - Full multi-line leaderboard view
  compact     - Compact multi-row display

Examples:
  %(prog)s                          # Default scrolling ticker
  %(prog)s -m leaderboard           # Full leaderboard view
  %(prog)s -m compact -n 15         # Compact view, top 15
  %(prog)s -s 0.05 --no-speed       # Faster scroll, no speeds

Replay Mode (use with replay.py server):
  %(prog)s --api-url http://localhost:8080   # Connect to replay server
  %(prog)s --api-url http://localhost:8080 -m leaderboard
        """
    )

    parser.add_argument('-m', '--mode', type=str, default='scroll',
                        choices=['scroll', 'leaderboard', 'compact', 'battle'],
                        help='Display mode (default: scroll)')
    parser.add_argument('-n', '--positions', type=int, default=20,
                        help='Number of positions to show (default: 20)')
    parser.add_argument('-s', '--speed', type=float, default=0.08,
                        help='Scroll speed in seconds (default: 0.08)')
    parser.add_argument('-r', '--refresh', type=float, default=2.0,
                        help='Data refresh rate in seconds (default: 2.0)')
    parser.add_argument('-w', '--width', type=int, default=120,
                        help='Display width in characters (default: 120)')
    parser.add_argument('--no-speed', action='store_true',
                        help='Hide speed/lap time info')
    parser.add_argument('--no-gap', action='store_true',
                        help='Hide gap to leader')
    parser.add_argument('--no-mfr', action='store_true',
                        help='Hide manufacturer info')
    parser.add_argument('--emoji', action='store_true',
                        help='Use emoji symbols')
    parser.add_argument('--rows', type=int, default=5,
                        help='Rows for compact mode (default: 5)')
    parser.add_argument('--api-url', type=str, default=None,
                        help='Custom API URL (for replay server, e.g., http://localhost:8080)')

    args = parser.parse_args()

    config = TickerConfig(
        mode=DisplayMode(args.mode),
        scroll_speed=args.speed,
        refresh_rate=args.refresh,
        show_positions=args.positions,
        show_speed=not args.no_speed,
        show_gap=not args.no_gap,
        show_manufacturer=not args.no_mfr,
        width=args.width,
        use_emoji=args.emoji,
        compact_rows=args.rows,
        api_url=args.api_url,
    )

    ticker = NASCARTicker(config)
    ticker.run()


if __name__ == "__main__":
    main()
