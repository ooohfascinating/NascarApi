#!/usr/bin/env python3
"""
NASCAR Track Visualization - Live track overlay with car positions
Shows top drivers moving around the track in real-time
"""
import math
import time
import signal
import sys
import argparse
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from enum import Enum

from nascar_api import NascarAPI, LiveData, Vehicle


class TrackType(Enum):
    OVAL = "oval"
    SUPERSPEEDWAY = "superspeedway"
    SHORT_TRACK = "short_track"
    ROAD_COURSE = "road_course"
    ROVAL = "roval"
    TRI_OVAL = "tri_oval"


@dataclass
class TrackLayout:
    """Defines a track's visual layout"""
    name: str
    track_type: TrackType
    width: int
    height: int
    points: List[Tuple[float, float]]  # Normalized 0-1 coordinates
    start_finish: int  # Index in points where S/F line is
    pit_road: Optional[List[Tuple[float, float]]] = None


# Track layouts for common NASCAR tracks
TRACK_LAYOUTS: Dict[int, TrackLayout] = {
    # Daytona International Speedway (track_id: 105)
    105: TrackLayout(
        name="Daytona",
        track_type=TrackType.TRI_OVAL,
        width=80, height=24,
        points=[
            (0.15, 0.7), (0.10, 0.5), (0.15, 0.3),  # Turn 1-2
            (0.35, 0.2), (0.50, 0.15), (0.65, 0.2),  # Backstretch
            (0.85, 0.3), (0.90, 0.5), (0.85, 0.7),  # Turn 3-4
            (0.65, 0.8), (0.50, 0.85), (0.35, 0.8),  # Frontstretch (tri-oval)
        ],
        start_finish=10,
    ),
    # Bristol Motor Speedway (track_id: 14)
    14: TrackLayout(
        name="Bristol",
        track_type=TrackType.SHORT_TRACK,
        width=60, height=20,
        points=[
            (0.20, 0.70), (0.15, 0.50), (0.20, 0.30),  # Turn 1-2
            (0.50, 0.25),  # Backstretch
            (0.80, 0.30), (0.85, 0.50), (0.80, 0.70),  # Turn 3-4
            (0.50, 0.75),  # Frontstretch
        ],
        start_finish=7,
    ),
    # Bowman Gray Stadium (track_id: 159)
    159: TrackLayout(
        name="Bowman Gray",
        track_type=TrackType.SHORT_TRACK,
        width=50, height=18,
        points=[
            (0.20, 0.65), (0.15, 0.50), (0.20, 0.35),  # Turn 1-2
            (0.50, 0.30),  # Backstretch
            (0.80, 0.35), (0.85, 0.50), (0.80, 0.65),  # Turn 3-4
            (0.50, 0.70),  # Frontstretch
        ],
        start_finish=7,
    ),
    # Atlanta Motor Speedway (track_id: 111)
    111: TrackLayout(
        name="Atlanta",
        track_type=TrackType.SUPERSPEEDWAY,
        width=70, height=22,
        points=[
            (0.18, 0.70), (0.12, 0.50), (0.18, 0.30),
            (0.40, 0.22), (0.60, 0.22),
            (0.82, 0.30), (0.88, 0.50), (0.82, 0.70),
            (0.60, 0.78), (0.40, 0.78),
        ],
        start_finish=9,
    ),
    # Martinsville Speedway (track_id: 22)
    22: TrackLayout(
        name="Martinsville",
        track_type=TrackType.SHORT_TRACK,
        width=55, height=25,
        points=[
            (0.25, 0.75), (0.15, 0.50), (0.25, 0.25),  # Turn 1-2 (tight)
            (0.50, 0.20),  # Backstretch (short)
            (0.75, 0.25), (0.85, 0.50), (0.75, 0.75),  # Turn 3-4 (tight)
            (0.50, 0.80),  # Frontstretch
        ],
        start_finish=7,
    ),
}

# Default oval layout for unknown tracks
DEFAULT_OVAL = TrackLayout(
    name="Oval",
    track_type=TrackType.OVAL,
    width=70, height=22,
    points=[
        (0.18, 0.70), (0.12, 0.50), (0.18, 0.30),
        (0.50, 0.25),
        (0.82, 0.30), (0.88, 0.50), (0.82, 0.70),
        (0.50, 0.75),
    ],
    start_finish=7,
)


class Color:
    """ANSI color codes"""
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"

    # Foreground
    BLACK = "\033[30m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"

    # Bright foreground
    BRIGHT_RED = "\033[91m"
    BRIGHT_GREEN = "\033[92m"
    BRIGHT_YELLOW = "\033[93m"
    BRIGHT_BLUE = "\033[94m"
    BRIGHT_CYAN = "\033[96m"
    BRIGHT_WHITE = "\033[97m"

    # Background
    BG_BLACK = "\033[40m"
    BG_RED = "\033[41m"
    BG_GREEN = "\033[42m"
    BG_YELLOW = "\033[43m"
    BG_BLUE = "\033[44m"
    BG_WHITE = "\033[47m"
    BG_GRAY = "\033[100m"

    @staticmethod
    def rgb_fg(r: int, g: int, b: int) -> str:
        return f"\033[38;2;{r};{g};{b}m"

    @staticmethod
    def rgb_bg(r: int, g: int, b: int) -> str:
        return f"\033[48;2;{r};{g};{b}m"


# Manufacturer colors
MFR_COLORS = {
    'Tyt': (Color.rgb_fg(220, 0, 0), Color.rgb_bg(220, 0, 0)),      # Toyota red
    'Chv': (Color.rgb_fg(255, 200, 0), Color.rgb_bg(255, 200, 0)),  # Chevy gold
    'Frd': (Color.rgb_fg(0, 80, 180), Color.rgb_bg(0, 80, 180)),    # Ford blue
}


@dataclass
class CarIcon:
    """A car icon on the track"""
    number: str
    driver_name: str
    position: int
    manufacturer: str
    x: float  # 0-1 position on track
    y: float
    on_track: bool
    laps_completed: int


class TrackRenderer:
    """Renders the track and car positions to terminal"""

    TRACK_CHAR = "░"
    TRACK_BORDER = "█"
    START_FINISH = "═"
    PIT_ROAD = "·"
    GRASS = " "

    def __init__(self, layout: TrackLayout, show_sidebar: bool = True):
        self.layout = layout
        self.show_sidebar = show_sidebar
        self.sidebar_width = 28 if show_sidebar else 0
        self.total_width = layout.width + self.sidebar_width + 4
        self.total_height = layout.height + 4

        # Pre-calculate track pixels
        self._track_pixels = self._calculate_track_pixels()

    def _calculate_track_pixels(self) -> set:
        """Calculate which pixels are part of the track surface"""
        pixels = set()
        points = self.layout.points

        # Interpolate between points to draw track
        for i in range(len(points)):
            p1 = points[i]
            p2 = points[(i + 1) % len(points)]

            # Number of steps based on distance
            dist = math.sqrt((p2[0] - p1[0])**2 + (p2[1] - p1[1])**2)
            steps = max(int(dist * 100), 10)

            for step in range(steps):
                t = step / steps
                x = p1[0] + t * (p2[0] - p1[0])
                y = p1[1] + t * (p2[1] - p1[1])

                # Convert to screen coordinates
                sx = int(x * self.layout.width) + 2
                sy = int(y * self.layout.height) + 2

                # Add track width (multiple pixels)
                for dx in range(-1, 2):
                    for dy in range(-1, 2):
                        pixels.add((sx + dx, sy + dy))

        return pixels

    def _get_position_on_track(self, progress: float) -> Tuple[float, float]:
        """Get x,y position on track for a given progress (0-1)"""
        points = self.layout.points
        num_segments = len(points)

        # Find which segment we're on
        segment_progress = progress * num_segments
        segment_idx = int(segment_progress) % num_segments
        segment_t = segment_progress - int(segment_progress)

        # Interpolate between points
        p1 = points[segment_idx]
        p2 = points[(segment_idx + 1) % num_segments]

        x = p1[0] + segment_t * (p2[0] - p1[0])
        y = p1[1] + segment_t * (p2[1] - p1[1])

        return x, y

    def _draw_car(self, buffer: List[List[str]], car: CarIcon, rank: int):
        """Draw a car number at its position"""
        # Convert normalized position to screen coordinates
        sx = int(car.x * self.layout.width) + 2
        sy = int(car.y * self.layout.height) + 2

        # Get manufacturer color
        mfr_fg, mfr_bg = MFR_COLORS.get(car.manufacturer, (Color.WHITE, Color.BG_GRAY))

        # Format car number (max 2 chars)
        num = car.number[:2] if len(car.number) > 2 else car.number.rjust(2)

        # Position color (gold for P1, green for podium)
        if rank == 1:
            pos_color = Color.BRIGHT_YELLOW
        elif rank <= 3:
            pos_color = Color.BRIGHT_GREEN
        elif rank <= 10:
            pos_color = Color.WHITE
        else:
            pos_color = Color.DIM

        # Draw the car icon
        if 0 <= sy < len(buffer) and 0 <= sx < len(buffer[0]) - 2:
            # Use manufacturer background color with white text
            car_str = f"{mfr_bg}{Color.WHITE}{Color.BOLD}{num}{Color.RESET}"
            buffer[sy][sx] = car_str[0:30]  # Truncate ANSI if needed
            # Actually we need to handle this differently since buffer is char-based

    def render(self, cars: List[CarIcon], session_info: dict) -> str:
        """Render the full display"""
        lines = []

        # Initialize buffer
        buffer = [[' ' for _ in range(self.layout.width + 4)] for _ in range(self.layout.height + 4)]

        # Draw track surface
        for (x, y) in self._track_pixels:
            if 0 <= y < len(buffer) and 0 <= x < len(buffer[0]):
                buffer[y][x] = self.TRACK_CHAR

        # Draw start/finish line
        sf_point = self.layout.points[self.layout.start_finish]
        sf_x = int(sf_point[0] * self.layout.width) + 2
        sf_y = int(sf_point[1] * self.layout.height) + 2
        if 0 <= sf_y < len(buffer) and 0 <= sf_x < len(buffer[0]):
            buffer[sf_y][sf_x] = '▌'

        # Convert buffer to string with track coloring
        track_lines = []
        for row in buffer:
            line = ""
            for char in row:
                if char == self.TRACK_CHAR:
                    line += f"{Color.DIM}{Color.rgb_fg(80,80,80)}{char}{Color.RESET}"
                elif char == '▌':
                    line += f"{Color.BRIGHT_WHITE}{Color.BOLD}▌{Color.RESET}"
                else:
                    line += f"{Color.rgb_fg(30,50,30)}.{Color.RESET}"  # Grass
            track_lines.append(line)

        # Draw cars on track
        car_positions = {}  # Track pixel positions for cars
        for i, car in enumerate(cars[:10]):  # Top 10 only
            sx = int(car.x * self.layout.width) + 2
            sy = int(car.y * self.layout.height) + 2
            car_positions[(sx, sy)] = (car, i + 1)

        # Rebuild lines with cars overlaid
        final_lines = []
        for y, row in enumerate(buffer):
            line = ""
            x = 0
            while x < len(row):
                if (x, y) in car_positions:
                    car, rank = car_positions[(x, y)]
                    mfr_fg, mfr_bg = MFR_COLORS.get(car.manufacturer, (Color.WHITE, Color.BG_GRAY))

                    # Position indicator
                    if rank == 1:
                        pos_color = Color.BRIGHT_YELLOW
                    elif rank <= 3:
                        pos_color = Color.BRIGHT_GREEN
                    else:
                        pos_color = Color.WHITE

                    num = car.number[:2].rjust(2)
                    line += f"{mfr_bg}{Color.WHITE}{Color.BOLD}{num}{Color.RESET}"
                    x += 2
                else:
                    char = row[x]
                    if char == self.TRACK_CHAR:
                        line += f"{Color.rgb_fg(60,60,60)}{char}{Color.RESET}"
                    elif char == '▌':
                        line += f"{Color.BRIGHT_WHITE}{Color.BOLD}▌{Color.RESET}"
                    else:
                        line += f"{Color.rgb_fg(25,40,25)}.{Color.RESET}"
                    x += 1
            final_lines.append(line)

        # Build header
        flag_colors = {
            0: ('', Color.WHITE),
            1: ('GREEN', Color.BRIGHT_GREEN),
            2: ('CAUTION', Color.BRIGHT_YELLOW),
            3: ('RED', Color.BRIGHT_RED),
            4: ('WHITE', Color.BRIGHT_WHITE),
            5: ('CHECKERED', Color.BRIGHT_WHITE),
            8: ('HOT', Color.YELLOW),
            9: ('COLD', Color.CYAN),
        }
        flag_name, flag_color = flag_colors.get(session_info.get('flag_state', 0), ('', Color.WHITE))

        header = f"{Color.BOLD}{Color.BRIGHT_YELLOW}{session_info.get('run_name', 'NASCAR')}{Color.RESET}"
        header += f" @ {Color.CYAN}{self.layout.name}{Color.RESET}"
        if flag_name:
            header += f"  {flag_color}[{flag_name}]{Color.RESET}"

        lap_info = f"Lap {session_info.get('lap_number', 0)}"
        if session_info.get('laps_in_race', 0) < 900:  # Not practice
            lap_info += f"/{session_info.get('laps_in_race', 0)}"

        lines.append("")
        lines.append(f" {header}")
        lines.append(f" {lap_info}")
        lines.append("")

        # Combine track and sidebar
        if self.show_sidebar:
            sidebar = self._render_sidebar(cars, session_info)
            for i, track_line in enumerate(final_lines):
                if i < len(sidebar):
                    lines.append(f" {track_line}  │ {sidebar[i]}")
                else:
                    lines.append(f" {track_line}  │")
        else:
            for track_line in final_lines:
                lines.append(f" {track_line}")

        # Legend
        lines.append("")
        legend = f" {Color.rgb_bg(220,0,0)}{Color.WHITE} TYT {Color.RESET}"
        legend += f" {Color.rgb_bg(255,200,0)}{Color.BLACK} CHV {Color.RESET}"
        legend += f" {Color.rgb_bg(0,80,180)}{Color.WHITE} FRD {Color.RESET}"
        legend += f"  {Color.BRIGHT_WHITE}▌{Color.RESET}=S/F"
        lines.append(legend)

        return "\n".join(lines)

    def _render_sidebar(self, cars: List[CarIcon], session_info: dict) -> List[str]:
        """Render the leaderboard sidebar"""
        lines = []
        lines.append(f"{Color.BOLD}{Color.BRIGHT_WHITE}  LEADERBOARD{Color.RESET}")
        lines.append(f"  {'─' * 22}")

        for i, car in enumerate(cars[:15], 1):
            mfr_fg, _ = MFR_COLORS.get(car.manufacturer, (Color.WHITE, Color.BG_GRAY))

            if i == 1:
                pos_color = Color.BRIGHT_YELLOW
            elif i <= 3:
                pos_color = Color.BRIGHT_GREEN
            elif i <= 10:
                pos_color = Color.WHITE
            else:
                pos_color = Color.DIM

            # Truncate driver name
            name = car.driver_name[:12]
            num = car.number.rjust(2)

            line = f"  {pos_color}P{i:<2}{Color.RESET} "
            line += f"{mfr_fg}#{num}{Color.RESET} "
            line += f"{pos_color}{name}{Color.RESET}"
            lines.append(line)

        # Pad to track height
        while len(lines) < self.layout.height:
            lines.append("")

        return lines


class TrackOverlay:
    """Main track overlay application"""

    def __init__(self, api_url: Optional[str] = None, show_sidebar: bool = True,
                 num_cars: int = 10, refresh_rate: float = 0.5):
        self.api = NascarAPI(base_url=api_url)
        self.show_sidebar = show_sidebar
        self.num_cars = num_cars
        self.refresh_rate = refresh_rate
        self.running = False
        self.renderer: Optional[TrackRenderer] = None
        self.current_layout: Optional[TrackLayout] = None

    def _get_layout_for_track(self, track_id: int, track_name: str) -> TrackLayout:
        """Get track layout, or create a default one"""
        if track_id in TRACK_LAYOUTS:
            return TRACK_LAYOUTS[track_id]

        # Create default layout with track name
        layout = TrackLayout(
            name=track_name[:15] if track_name else "Track",
            track_type=TrackType.OVAL,
            width=DEFAULT_OVAL.width,
            height=DEFAULT_OVAL.height,
            points=DEFAULT_OVAL.points,
            start_finish=DEFAULT_OVAL.start_finish,
        )
        return layout

    def _calculate_car_positions(self, data: LiveData) -> List[CarIcon]:
        """Calculate positions for all cars on track"""
        cars = []

        # Get top N cars
        sorted_vehicles = sorted(data.vehicles, key=lambda v: v.running_position)[:self.num_cars]

        # Get leader's laps for reference
        leader_laps = sorted_vehicles[0].laps_completed if sorted_vehicles else 0

        for vehicle in sorted_vehicles:
            # Calculate progress around track based on position and delta
            # Spread cars out based on their running position
            base_progress = 0.0

            if vehicle.running_position == 1:
                # Leader is at the "front" of the pack
                base_progress = 0.95
            else:
                # Other cars are spread behind based on their gap
                # Use a simple spread based on position
                gap_factor = (vehicle.running_position - 1) * 0.06
                base_progress = max(0.1, 0.95 - gap_factor)

                # If lapped, show them further back
                if vehicle.laps_completed < leader_laps:
                    base_progress = max(0.05, base_progress - 0.3)

            # Get x,y position on track
            if self.renderer:
                x, y = self.renderer._get_position_on_track(base_progress)
            else:
                x, y = 0.5, 0.5

            car = CarIcon(
                number=vehicle.number,
                driver_name=vehicle.driver.short_name,
                position=vehicle.running_position,
                manufacturer=vehicle.manufacturer,
                x=x,
                y=y,
                on_track=vehicle.is_on_track,
                laps_completed=vehicle.laps_completed,
            )
            cars.append(car)

        return cars

    def run(self):
        """Main run loop"""
        self.running = True

        def signal_handler(sig, frame):
            self.running = False
            print("\033[?25h")  # Show cursor
            sys.exit(0)

        signal.signal(signal.SIGINT, signal_handler)

        print("\033[?25l")  # Hide cursor
        print("\033[2J")    # Clear screen

        last_track_id = None

        try:
            while self.running:
                data = self.api.get_live_feed()

                if data:
                    # Check if track changed
                    track_id = data.session.track_id
                    if track_id != last_track_id:
                        layout = self._get_layout_for_track(track_id, data.session.track_name)
                        self.renderer = TrackRenderer(layout, show_sidebar=self.show_sidebar)
                        self.current_layout = layout
                        last_track_id = track_id

                    # Calculate car positions
                    cars = self._calculate_car_positions(data)

                    # Session info for display
                    session_info = {
                        'run_name': data.session.run_name,
                        'track_name': data.session.track_name,
                        'lap_number': data.session.lap_number,
                        'laps_in_race': data.session.laps_in_race,
                        'flag_state': data.session.flag_state,
                    }

                    # Render and display
                    if self.renderer:
                        output = self.renderer.render(cars, session_info)
                        print("\033[H")  # Move cursor to top
                        print(output)

                else:
                    print("\033[H")
                    print(" Waiting for NASCAR live data...")

                time.sleep(self.refresh_rate)

        finally:
            print("\033[?25h")  # Show cursor


def main():
    parser = argparse.ArgumentParser(
        description='NASCAR Track Overlay - Live visualization with car positions',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Shows a live track view with car number icons moving around the track.
Cars are color-coded by manufacturer (Toyota=red, Chevy=gold, Ford=blue).

Examples:
  %(prog)s                          # Show track with leaderboard
  %(prog)s --no-sidebar             # Track only, no leaderboard
  %(prog)s -n 15                    # Show top 15 cars
  %(prog)s --api-url http://localhost:8080  # Use replay server
        """
    )

    parser.add_argument('-n', '--num-cars', type=int, default=10,
                        help='Number of cars to show (default: 10)')
    parser.add_argument('--no-sidebar', action='store_true',
                        help='Hide leaderboard sidebar')
    parser.add_argument('-r', '--refresh', type=float, default=0.5,
                        help='Refresh rate in seconds (default: 0.5)')
    parser.add_argument('--api-url', type=str, default=None,
                        help='Custom API URL (for replay server)')

    args = parser.parse_args()

    overlay = TrackOverlay(
        api_url=args.api_url,
        show_sidebar=not args.no_sidebar,
        num_cars=args.num_cars,
        refresh_rate=args.refresh,
    )

    print(f"\n{Color.BOLD} NASCAR Track Overlay{Color.RESET}")
    print(" Press Ctrl+C to exit\n")
    time.sleep(1)

    overlay.run()


if __name__ == "__main__":
    main()
