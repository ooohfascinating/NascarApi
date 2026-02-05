"""
LED Display Module - Handles rendering and scrolling for LED matrix displays
Supports both terminal simulation and RGB LED Matrix hardware
"""
import sys
import time
from typing import List, Tuple, Optional, Callable
from dataclasses import dataclass
from enum import Enum


class Color(Enum):
    """Standard colors for LED display"""
    BLACK = (0, 0, 0)
    WHITE = (255, 255, 255)
    RED = (255, 0, 0)
    GREEN = (0, 255, 0)
    BLUE = (0, 0, 255)
    YELLOW = (255, 255, 0)
    ORANGE = (255, 165, 0)
    CYAN = (0, 255, 255)
    MAGENTA = (255, 0, 255)
    PURPLE = (128, 0, 128)
    GRAY = (128, 128, 128)
    DARK_RED = (139, 0, 0)
    DARK_GREEN = (0, 100, 0)
    GOLD = (255, 215, 0)

    # NASCAR specific
    NASCAR_YELLOW = (255, 200, 0)
    TOYOTA_RED = (235, 0, 0)
    CHEVY_GOLD = (255, 204, 0)
    FORD_BLUE = (0, 60, 150)


@dataclass
class TextSegment:
    """A segment of colored text"""
    text: str
    color: Tuple[int, int, int] = Color.WHITE.value
    bold: bool = False


class ScrollDirection(Enum):
    LEFT = "left"
    RIGHT = "right"
    UP = "up"
    DOWN = "down"


class LEDDisplay:
    """Base class for LED display output"""

    def __init__(self, width: int = 128, height: int = 32):
        self.width = width
        self.height = height
        self.scroll_position = 0
        self.scroll_speed = 1

    def clear(self):
        """Clear the display"""
        raise NotImplementedError

    def draw_text(self, x: int, y: int, segments: List[TextSegment]):
        """Draw colored text segments at position"""
        raise NotImplementedError

    def draw_line(self, x1: int, y1: int, x2: int, y2: int, color: Tuple[int, int, int]):
        """Draw a line"""
        raise NotImplementedError

    def draw_rect(self, x: int, y: int, w: int, h: int, color: Tuple[int, int, int], fill: bool = False):
        """Draw a rectangle"""
        raise NotImplementedError

    def show(self):
        """Update the display"""
        raise NotImplementedError


class TerminalDisplay(LEDDisplay):
    """Terminal-based display simulation using ANSI colors"""

    ANSI_RESET = "\033[0m"
    ANSI_BOLD = "\033[1m"
    ANSI_CLEAR = "\033[2J\033[H"
    ANSI_HIDE_CURSOR = "\033[?25l"
    ANSI_SHOW_CURSOR = "\033[?25h"

    def __init__(self, width: int = 100, height: int = 1, use_emoji: bool = False):
        super().__init__(width, height)
        self.buffer = ""
        self.use_emoji = use_emoji
        self._last_line_len = 0

    def _rgb_to_ansi(self, r: int, g: int, b: int) -> str:
        """Convert RGB to ANSI 256 color code"""
        # Use true color if supported
        return f"\033[38;2;{r};{g};{b}m"

    def _bg_rgb_to_ansi(self, r: int, g: int, b: int) -> str:
        """Convert RGB to ANSI background color"""
        return f"\033[48;2;{r};{g};{b}m"

    def clear(self):
        self.buffer = ""

    def draw_text(self, x: int, y: int, segments: List[TextSegment]):
        """Append colored text segments to buffer"""
        for seg in segments:
            r, g, b = seg.color
            color_code = self._rgb_to_ansi(r, g, b)
            bold_code = self.ANSI_BOLD if seg.bold else ""
            self.buffer += f"{color_code}{bold_code}{seg.text}{self.ANSI_RESET}"

    def draw_line(self, x1: int, y1: int, x2: int, y2: int, color: Tuple[int, int, int]):
        pass  # Not applicable for terminal

    def draw_rect(self, x: int, y: int, w: int, h: int, color: Tuple[int, int, int], fill: bool = False):
        pass  # Not applicable for terminal

    def show(self):
        """Output to terminal with carriage return for single-line scrolling"""
        # Clear previous line and print new one
        clear_str = '\r' + ' ' * self._last_line_len + '\r'
        sys.stdout.write(clear_str + self.buffer)
        sys.stdout.flush()
        self._last_line_len = len(self.buffer.encode('utf-8'))  # Approximate visible length

    def show_multiline(self, lines: List[str]):
        """Output multiple lines"""
        sys.stdout.write(self.ANSI_CLEAR)
        for line in lines:
            sys.stdout.write(line + "\n")
        sys.stdout.flush()


class ScrollingText:
    """Manages scrolling text animation"""

    def __init__(self, display: LEDDisplay, speed: float = 0.05):
        self.display = display
        self.speed = speed  # Seconds between scroll steps
        self.position = 0
        self.content_width = 0
        self._segments: List[TextSegment] = []
        self._total_len = 0

    def set_content(self, segments: List[TextSegment]):
        """Set the content to scroll"""
        self._segments = segments
        self._total_len = sum(len(s.text) for s in segments)
        self.content_width = self._total_len
        # Add padding for smooth loop
        self.position = 0

    def get_visible_segments(self, width: int) -> List[TextSegment]:
        """Get the currently visible portion of segments"""
        if not self._segments:
            return []

        # Calculate visible range
        start = self.position % (self._total_len + width)
        visible = []
        current_pos = 0

        # Handle wraparound by duplicating content
        all_segments = self._segments + [TextSegment("   |   ", Color.GRAY.value)] + self._segments

        for seg in all_segments:
            seg_start = current_pos
            seg_end = current_pos + len(seg.text)

            if seg_end > start and seg_start < start + width:
                # This segment is at least partially visible
                visible_start = max(0, start - seg_start)
                visible_end = min(len(seg.text), start + width - seg_start)
                visible_text = seg.text[visible_start:visible_end]
                if visible_text:
                    visible.append(TextSegment(visible_text, seg.color, seg.bold))

            current_pos = seg_end
            if current_pos > start + width:
                break

        return visible

    def step(self):
        """Advance scroll position"""
        self.position += 1
        if self.position > self._total_len + self.display.width:
            self.position = 0


class TickerRenderer:
    """Renders NASCAR data as scrolling ticker content"""

    # Symbols for terminal display
    FLAG_SYMBOLS = {
        'green': '🟢',
        'yellow': '🟡',
        'red': '🔴',
        'white': '⚪',
        'checkered': '🏁',
    }

    POS_SYMBOLS = {
        1: '🥇',
        2: '🥈',
        3: '🥉',
    }

    MFR_SYMBOLS = {
        'Tyt': '🔴',  # Toyota red
        'Chv': '🟡',  # Chevy gold
        'Frd': '🔵',  # Ford blue
    }

    def __init__(self, use_emoji: bool = True):
        self.use_emoji = use_emoji

    def format_position(self, pos: int) -> TextSegment:
        """Format position with color coding"""
        if pos == 1:
            return TextSegment(f"P{pos}", Color.GOLD.value, bold=True)
        elif pos <= 3:
            return TextSegment(f"P{pos}", Color.GREEN.value, bold=True)
        elif pos <= 10:
            return TextSegment(f"P{pos}", Color.WHITE.value)
        else:
            return TextSegment(f"P{pos}", Color.GRAY.value)

    def format_gap(self, delta: float, laps_completed: int, leader_laps: int) -> TextSegment:
        """Format gap to leader"""
        if delta == 0:
            return TextSegment("LEADER", Color.GOLD.value, bold=True)
        elif laps_completed < leader_laps:
            laps_down = leader_laps - laps_completed
            return TextSegment(f"-{laps_down}L", Color.RED.value)
        elif delta < 1:
            return TextSegment(f"+{delta:.3f}", Color.GREEN.value)
        elif delta < 5:
            return TextSegment(f"+{delta:.2f}", Color.YELLOW.value)
        else:
            return TextSegment(f"+{delta:.1f}", Color.ORANGE.value)

    def format_manufacturer(self, mfr: str) -> TextSegment:
        """Format manufacturer with brand colors"""
        colors = {
            'Tyt': Color.TOYOTA_RED.value,
            'Chv': Color.CHEVY_GOLD.value,
            'Frd': Color.FORD_BLUE.value,
        }
        return TextSegment(mfr, colors.get(mfr, Color.WHITE.value))

    def format_flag(self, flag_state: int) -> List[TextSegment]:
        """Format flag state indicator"""
        flag_info = {
            0: ("", Color.WHITE.value),
            1: ("GREEN", Color.GREEN.value),
            2: ("CAUTION", Color.NASCAR_YELLOW.value),
            3: ("RED FLAG", Color.RED.value),
            4: ("WHITE FLAG", Color.WHITE.value),
            5: ("CHECKERED", Color.WHITE.value),
            8: ("HOT TRACK", Color.ORANGE.value),
            9: ("COLD TRACK", Color.CYAN.value),
        }
        text, color = flag_info.get(flag_state, ("", Color.WHITE.value))
        if not text:
            return []
        return [
            TextSegment(" [", Color.GRAY.value),
            TextSegment(text, color, bold=True),
            TextSegment("] ", Color.GRAY.value),
        ]

    def format_speed(self, speed: float) -> TextSegment:
        """Format speed value"""
        if speed > 0:
            return TextSegment(f"{speed:.2f}mph", Color.CYAN.value)
        return TextSegment("--.-mph", Color.GRAY.value)

    def format_time(self, time_sec: float) -> TextSegment:
        """Format lap time"""
        if time_sec > 0:
            if time_sec >= 60:
                mins = int(time_sec // 60)
                secs = time_sec % 60
                return TextSegment(f"{mins}:{secs:06.3f}", Color.WHITE.value)
            return TextSegment(f"{time_sec:.3f}s", Color.WHITE.value)
        return TextSegment("---.---", Color.GRAY.value)


def create_display(display_type: str = "terminal", **kwargs) -> LEDDisplay:
    """Factory function to create appropriate display"""
    if display_type == "terminal":
        return TerminalDisplay(**kwargs)
    # Future: Add support for actual LED matrix hardware
    # elif display_type == "rgb_matrix":
    #     return RGBMatrixDisplay(**kwargs)
    else:
        return TerminalDisplay(**kwargs)
