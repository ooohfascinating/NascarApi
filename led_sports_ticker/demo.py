#!/usr/bin/env python3
"""
Demo mode for NASCAR LED Ticker - Shows sample data when no live session available
"""
import sys
import time
import random
from typing import List

from led_display import TextSegment, Color, TerminalDisplay, ScrollingText, TickerRenderer


class DemoTicker:
    """Demo ticker with sample NASCAR data"""

    SAMPLE_DRIVERS = [
        ("5", "Kyle Larson", "Chv"),
        ("24", "William Byron", "Chv"),
        ("54", "Ty Gibbs", "Tyt"),
        ("19", "Chase Briscoe", "Frd"),
        ("20", "Christopher Bell", "Tyt"),
        ("11", "Denny Hamlin", "Tyt"),
        ("23", "Bubba Wallace", "Tyt"),
        ("17", "Chris Buescher", "Frd"),
        ("1", "Ross Chastain", "Chv"),
        ("45", "Tyler Reddick", "Tyt"),
        ("9", "Chase Elliott", "Chv"),
        ("77", "Carson Hocevar", "Chv"),
        ("8", "Kyle Busch", "Chv"),
        ("22", "Joey Logano", "Frd"),
        ("3", "Austin Dillon", "Chv"),
        ("12", "Ryan Blaney", "Frd"),
        ("14", "Chase Briscoe", "Frd"),
        ("48", "Alex Bowman", "Chv"),
        ("4", "Josh Berry", "Frd"),
        ("21", "Harrison Burton", "Frd"),
    ]

    def __init__(self):
        self.display = TerminalDisplay(width=120)
        self.renderer = TickerRenderer()
        self.scroller = ScrollingText(self.display, speed=0.08)
        self.lap = 1
        self.flag_state = 1  # Green

    def build_demo_content(self) -> List[TextSegment]:
        """Build demo scrolling content"""
        segments: List[TextSegment] = []

        # Header
        segments.append(TextSegment(" CUP ", Color.NASCAR_YELLOW.value, bold=True))
        segments.append(TextSegment("Race ", Color.WHITE.value))
        segments.append(TextSegment("@ Bowman Gray Stadium ", Color.CYAN.value))

        # Flag
        flag_colors = {1: Color.GREEN.value, 2: Color.NASCAR_YELLOW.value}
        flag_names = {1: "GREEN", 2: "CAUTION"}
        segments.append(TextSegment(" [", Color.GRAY.value))
        segments.append(TextSegment(flag_names.get(self.flag_state, "GREEN"),
                                   flag_colors.get(self.flag_state, Color.GREEN.value), bold=True))
        segments.append(TextSegment("] ", Color.GRAY.value))

        # Lap counter
        segments.append(TextSegment(f"Lap {self.lap}/200 ", Color.WHITE.value))
        segments.append(TextSegment(" | ", Color.GRAY.value))

        # Shuffle positions slightly for realism
        positions = list(range(len(self.SAMPLE_DRIVERS)))
        if random.random() > 0.7:
            # Occasionally swap adjacent positions
            i = random.randint(0, len(positions) - 2)
            positions[i], positions[i + 1] = positions[i + 1], positions[i]

        # Leader
        leader_idx = positions[0]
        num, name, mfr = self.SAMPLE_DRIVERS[leader_idx]
        segments.append(TextSegment("LEADER: ", Color.GOLD.value, bold=True))
        segments.append(TextSegment(f"#{num} ", Color.WHITE.value, bold=True))
        short_name = f"{name.split()[0][0]}. {name.split()[-1]}"
        segments.append(TextSegment(f"{short_name} ", Color.WHITE.value))
        segments.append(TextSegment(" | ", Color.GRAY.value))

        # Top 15 positions
        mfr_colors = {
            'Tyt': Color.TOYOTA_RED.value,
            'Chv': Color.CHEVY_GOLD.value,
            'Frd': Color.FORD_BLUE.value,
        }

        gaps = [0, 0.234, 0.567, 1.123, 2.456, 3.789, 5.012, 6.345, 8.234, 10.567,
                12.890, 15.123, 18.456, 22.789, 27.012]

        for pos, driver_idx in enumerate(positions[:15], 1):
            num, name, mfr = self.SAMPLE_DRIVERS[driver_idx]
            short_name = f"{name.split()[0][0]}. {name.split()[-1]}"

            # Position
            if pos == 1:
                segments.append(TextSegment(f"P{pos}", Color.GOLD.value, bold=True))
            elif pos <= 3:
                segments.append(TextSegment(f"P{pos}", Color.GREEN.value, bold=True))
            elif pos <= 10:
                segments.append(TextSegment(f"P{pos}", Color.WHITE.value))
            else:
                segments.append(TextSegment(f"P{pos}", Color.GRAY.value))

            segments.append(TextSegment(" ", Color.WHITE.value))

            # Car number
            segments.append(TextSegment(f"#{num}", mfr_colors.get(mfr, Color.WHITE.value), bold=True))
            segments.append(TextSegment(" ", Color.WHITE.value))

            # Driver name
            segments.append(TextSegment(short_name, Color.WHITE.value))

            # Gap
            if pos > 1:
                gap = gaps[pos - 1] + random.uniform(-0.1, 0.1)
                segments.append(TextSegment(" ", Color.WHITE.value))
                if gap < 1:
                    segments.append(TextSegment(f"+{gap:.3f}", Color.GREEN.value))
                elif gap < 5:
                    segments.append(TextSegment(f"+{gap:.2f}", Color.YELLOW.value))
                else:
                    segments.append(TextSegment(f"+{gap:.1f}", Color.ORANGE.value))

            segments.append(TextSegment("  ", Color.BLACK.value))

        # Stats
        segments.append(TextSegment(" | ", Color.GRAY.value))
        segments.append(TextSegment(f"Lead Changes: {random.randint(5, 25)} ", Color.CYAN.value))
        segments.append(TextSegment(f"Cautions: {random.randint(2, 8)} ", Color.YELLOW.value))

        return segments

    def run(self):
        """Run demo ticker"""
        print("\033[?25l", end='')  # Hide cursor
        print("\n NASCAR LED Ticker - DEMO MODE")
        print(" Press Ctrl+C to exit\n")
        time.sleep(1)

        try:
            while True:
                content = self.build_demo_content()
                self.scroller.set_content(content)

                # Scroll through content
                for _ in range(self.scroller.content_width + 120):
                    self.display.clear()
                    visible = self.scroller.get_visible_segments(120)
                    self.display.draw_text(0, 0, visible)
                    self.display.show()
                    self.scroller.step()
                    time.sleep(0.08)

                # Update lap and occasionally flag
                self.lap += 1
                if self.lap > 200:
                    self.lap = 1
                if random.random() > 0.9:
                    self.flag_state = 2 if self.flag_state == 1 else 1

        except KeyboardInterrupt:
            pass
        finally:
            print("\033[?25h")  # Show cursor
            print()


def main():
    print("""
    ╔═══════════════════════════════════════════════════════════╗
    ║           NASCAR LED SPORTS TICKER - DEMO                 ║
    ╠═══════════════════════════════════════════════════════════╣
    ║  This demo shows sample data to preview the ticker        ║
    ║  when no live NASCAR session is active.                   ║
    ║                                                           ║
    ║  For live data, run: python ticker.py                     ║
    ╚═══════════════════════════════════════════════════════════╝
    """)

    time.sleep(2)
    demo = DemoTicker()
    demo.run()


if __name__ == "__main__":
    main()
