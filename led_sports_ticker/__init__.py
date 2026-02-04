"""
NASCAR LED Sports Ticker
Real-time scrolling leaderboard display for NASCAR races
"""

from .nascar_api import NascarAPI, LiveData, Vehicle, Driver, SessionInfo
from .led_display import (
    LEDDisplay, TerminalDisplay, TextSegment, Color,
    ScrollingText, TickerRenderer, create_display
)
from .ticker import NASCARTicker, TickerConfig, DisplayMode

__version__ = "1.0.0"
__all__ = [
    'NascarAPI', 'LiveData', 'Vehicle', 'Driver', 'SessionInfo',
    'LEDDisplay', 'TerminalDisplay', 'TextSegment', 'Color',
    'ScrollingText', 'TickerRenderer', 'create_display',
    'NASCARTicker', 'TickerConfig', 'DisplayMode',
]
