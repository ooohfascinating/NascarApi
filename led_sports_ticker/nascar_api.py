"""
NASCAR API Client - Fetches live race data from NASCAR's public APIs
"""
import json
import time
import urllib.request
import urllib.error
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from datetime import datetime


@dataclass
class Driver:
    driver_id: int
    full_name: str
    first_name: str
    last_name: str
    short_name: str = ""
    is_in_chase: bool = False

    def __post_init__(self):
        if not self.short_name:
            # Create short name like "K. Larson"
            self.short_name = f"{self.first_name[0]}. {self.last_name}" if self.first_name else self.last_name


@dataclass
class Vehicle:
    number: str
    driver: Driver
    manufacturer: str
    sponsor: str
    running_position: int
    laps_completed: int
    last_lap_time: float
    last_lap_speed: float
    best_lap_time: float
    best_lap_speed: float
    delta: float  # Gap to leader
    status: int
    is_on_track: bool
    laps_led: int = 0
    pit_stops: int = 0
    average_speed: float = 0.0
    passes_made: int = 0
    quality_passes: int = 0
    starting_position: int = 0


@dataclass
class SessionInfo:
    race_id: int
    series_id: int
    track_id: int
    run_name: str
    track_name: str
    track_length: float
    lap_number: int
    laps_in_race: int
    laps_to_go: int
    flag_state: int
    elapsed_time: int
    run_type: int  # 1=Practice, 2=Qualifying, 3=Race
    num_cautions: int
    num_caution_laps: int
    num_lead_changes: int
    num_leaders: int
    stage_num: int = 1
    stage_finish_lap: int = 0


@dataclass
class LiveData:
    session: SessionInfo
    vehicles: List[Vehicle]
    timestamp: datetime = field(default_factory=datetime.now)

    @property
    def leader(self) -> Optional[Vehicle]:
        for v in self.vehicles:
            if v.running_position == 1:
                return v
        return self.vehicles[0] if self.vehicles else None

    def get_top_n(self, n: int = 10) -> List[Vehicle]:
        return sorted(self.vehicles, key=lambda v: v.running_position)[:n]


class NascarAPI:
    """Client for fetching NASCAR live data"""

    DEFAULT_BASE_URL = "https://cf.nascar.com"
    LIVE_FEED = "/live/feeds/live-feed.json"
    LIVE_FLAG = "/live/feeds/live-flag-data.json"
    LIVE_POINTS = "/live/feeds/live-points.json"
    LIVE_PIT = "/live/feeds/live-pit-data.json"
    LIVE_STAGE_POINTS = "/live/feeds/live-stage-points.json"

    FLAG_STATES = {
        0: ("NONE", "white"),
        1: ("GREEN", "green"),
        2: ("YELLOW", "yellow"),
        3: ("RED", "red"),
        4: ("WHITE", "white"),
        5: ("CHECKERED", "white"),
        6: ("UNKNOWN", "white"),
        7: ("UNKNOWN", "white"),
        8: ("HOT TRACK", "orange"),
        9: ("COLD TRACK", "blue"),
    }

    SERIES_NAMES = {
        1: "NASCAR Cup Series",
        2: "NASCAR Xfinity Series",
        3: "NASCAR Craftsman Truck Series",
    }

    SERIES_SHORT = {
        1: "CUP",
        2: "NXS",
        3: "TRUCK",
    }

    RUN_TYPES = {
        1: "Practice",
        2: "Qualifying",
        3: "Race",
    }

    MFR_COLORS = {
        "Tyt": "red",      # Toyota
        "Chv": "yellow",   # Chevrolet
        "Frd": "blue",     # Ford
    }

    def __init__(self, timeout: int = 10, base_url: Optional[str] = None):
        self.timeout = timeout
        self.base_url = base_url or self.DEFAULT_BASE_URL
        self._cache: Dict[str, Any] = {}
        self._cache_time: Dict[str, float] = {}
        self._cache_ttl = 1.0  # 1 second cache for live data

    def _fetch(self, endpoint: str) -> Optional[Dict]:
        """Fetch JSON data from NASCAR API"""
        url = f"{self.base_url}{endpoint}"

        # Check cache
        now = time.time()
        if endpoint in self._cache:
            if now - self._cache_time.get(endpoint, 0) < self._cache_ttl:
                return self._cache[endpoint]

        try:
            req = urllib.request.Request(url, headers={
                'User-Agent': 'NASCARLEDTicker/1.0',
                'Accept': 'application/json',
            })
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                data = json.loads(response.read().decode('utf-8'))
                self._cache[endpoint] = data
                self._cache_time[endpoint] = now
                return data
        except urllib.error.URLError as e:
            print(f"Error fetching {url}: {e}")
            return None
        except json.JSONDecodeError as e:
            print(f"Error parsing JSON from {url}: {e}")
            return None

    def get_live_feed(self) -> Optional[LiveData]:
        """Get current live feed data"""
        data = self._fetch(self.LIVE_FEED)
        if not data:
            return None

        # Parse session info
        stage = data.get('stage', {})
        session = SessionInfo(
            race_id=data.get('race_id', 0),
            series_id=data.get('series_id', 1),
            track_id=data.get('track_id', 0),
            run_name=data.get('run_name', 'Unknown'),
            track_name=data.get('track_name', 'Unknown'),
            track_length=data.get('track_length', 0),
            lap_number=data.get('lap_number', 0),
            laps_in_race=data.get('laps_in_race', 0),
            laps_to_go=data.get('laps_to_go', 0),
            flag_state=data.get('flag_state', 0),
            elapsed_time=data.get('elapsed_time', 0),
            run_type=data.get('run_type', 1),
            num_cautions=data.get('number_of_caution_segments', 0),
            num_caution_laps=data.get('number_of_caution_laps', 0),
            num_lead_changes=data.get('number_of_lead_changes', 0),
            num_leaders=data.get('number_of_leaders', 0),
            stage_num=stage.get('stage_num', 1),
            stage_finish_lap=stage.get('finish_at_lap', 0),
        )

        # Parse vehicles
        vehicles = []
        for v in data.get('vehicles', []):
            driver_data = v.get('driver', {})
            driver = Driver(
                driver_id=driver_data.get('driver_id', 0),
                full_name=driver_data.get('full_name', 'Unknown'),
                first_name=driver_data.get('first_name', ''),
                last_name=driver_data.get('last_name', 'Unknown'),
                is_in_chase=driver_data.get('is_in_chase', False),
            )

            laps_led = v.get('laps_led', [])
            total_laps_led = sum(lap.get('end_lap', 0) - lap.get('start_lap', 0) + 1
                                 for lap in laps_led) if isinstance(laps_led, list) else 0

            vehicle = Vehicle(
                number=v.get('vehicle_number', ''),
                driver=driver,
                manufacturer=v.get('vehicle_manufacturer', ''),
                sponsor=v.get('sponsor_name', ''),
                running_position=v.get('running_position', 99),
                laps_completed=v.get('laps_completed', 0),
                last_lap_time=v.get('last_lap_time', 0) or 0,
                last_lap_speed=v.get('last_lap_speed', 0) or 0,
                best_lap_time=v.get('best_lap_time', 0) or 0,
                best_lap_speed=v.get('best_lap_speed', 0) or 0,
                delta=v.get('delta', 0) or 0,
                status=v.get('status', 0),
                is_on_track=v.get('is_on_track', False),
                laps_led=total_laps_led,
                pit_stops=len(v.get('pit_stops', [])),
                average_speed=v.get('average_speed', 0) or 0,
                passes_made=v.get('passes_made', 0),
                quality_passes=v.get('quality_passes', 0),
                starting_position=v.get('starting_position', 0),
            )
            vehicles.append(vehicle)

        return LiveData(session=session, vehicles=vehicles)

    def get_flag_data(self) -> Optional[List[Dict]]:
        """Get live flag data"""
        return self._fetch(self.LIVE_FLAG)

    def get_points(self) -> Optional[List[Dict]]:
        """Get live points standings"""
        return self._fetch(self.LIVE_POINTS)

    def get_flag_text(self, flag_state: int) -> str:
        """Get flag state text"""
        return self.FLAG_STATES.get(flag_state, ("UNKNOWN", "white"))[0]

    def get_flag_color(self, flag_state: int) -> str:
        """Get flag state color"""
        return self.FLAG_STATES.get(flag_state, ("UNKNOWN", "white"))[1]

    def get_series_name(self, series_id: int, short: bool = False) -> str:
        """Get series name"""
        if short:
            return self.SERIES_SHORT.get(series_id, "NASCAR")
        return self.SERIES_NAMES.get(series_id, "NASCAR")

    def get_run_type(self, run_type: int) -> str:
        """Get run type name"""
        return self.RUN_TYPES.get(run_type, "Session")


# Demo/test function
if __name__ == "__main__":
    api = NascarAPI()
    data = api.get_live_feed()

    if data:
        print(f"\n{'='*60}")
        print(f"{data.session.run_name} @ {data.session.track_name}")
        print(f"Flag: {api.get_flag_text(data.session.flag_state)}")
        print(f"Lap {data.session.lap_number}/{data.session.laps_in_race}")
        print(f"{'='*60}")

        print(f"\n{'Pos':<4} {'#':<4} {'Driver':<20} {'Best Time':<10} {'Speed':<8}")
        print("-" * 50)

        for v in data.get_top_n(15):
            print(f"{v.running_position:<4} {v.number:<4} {v.driver.short_name:<20} "
                  f"{v.best_lap_time:<10.3f} {v.best_lap_speed:<8.2f}")
    else:
        print("No live data available")
