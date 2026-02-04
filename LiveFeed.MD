# Live Feed
`https://cf.nascar.com/live/feeds/live-feed.json`

Thanks to Gus_theAnt:
This feed is updated every second during every race/practice/qualifying session.

## Top-Level Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `lap_number` | int | Current lap number |
| `elapsed_time` | int | Session elapsed time (seconds) |
| `flag_state` | int | Current flag state (see FlagState.MD) |
| `race_id` | int | Unique race identifier |
| `laps_in_race` | int | Total laps (999 for practice) |
| `laps_to_go` | int | Remaining laps |
| `run_id` | int | Session run identifier |
| `run_name` | string | Session name (e.g., "NCS Final Practice") |
| `series_id` | int | Series (1=Cup, 2=Xfinity, 3=Trucks) |
| `time_of_day` | int | Time of day in seconds |
| `time_of_day_os` | string | ISO timestamp with timezone |
| `track_id` | int | Track identifier |
| `track_length` | float | Track length in miles |
| `track_name` | string | Track name |
| `run_type` | int | Session type (1=Practice, 2=Qualifying, 3=Race) |
| `number_of_caution_segments` | int | Total cautions |
| `number_of_caution_laps` | int | Total caution laps |
| `number_of_lead_changes` | int | Lead changes |
| `number_of_leaders` | int | Different leaders |
| `avg_diff_1to3` | float | Average gap between P1-P3 |
| `stage` | object | Stage information |
| `vehicles` | array | Array of vehicle objects |

## Stage Object

| Field | Type | Description |
|-------|------|-------------|
| `stage_num` | int | Current stage number |
| `finish_at_lap` | int | Lap stage ends |
| `laps_in_stage` | int | Total laps in stage |

## Vehicle Object Fields

| Field | Type | Description |
|-------|------|-------------|
| `average_restart_speed` | float | Average speed on restarts |
| `average_running_position` | float | Average position |
| `average_speed` | float | Overall average speed |
| `best_lap` | int | Lap number of best lap |
| `best_lap_speed` | float | Best lap speed (MPH) |
| `best_lap_time` | float | Best lap time (seconds) |
| `vehicle_manufacturer` | string | Manufacturer code (Tyt, Chv, Frd) |
| `vehicle_number` | string | Car number |
| `driver` | object | Driver information |
| `vehicle_elapsed_time` | float | Total time on track |
| `fastest_laps_run` | int | Number of fastest laps set |
| `laps_position_improved` | int | Positions gained |
| `laps_completed` | int | Total laps completed |
| `laps_led` | array | Array of laps led |
| `last_lap_speed` | float | Most recent lap speed |
| `last_lap_time` | float | Most recent lap time |
| `passes_made` | int | Total passes made |
| `passing_differential` | int | Net passes (+/-) |
| `position_differential_last_10_percent` | int | Position change in final 10% |
| `pit_stops` | array | Array of pit stop objects |
| `qualifying_status` | int | Qualifying status code |
| `running_position` | int | Current position |
| `status` | int | Vehicle status (1=Running) |
| `delta` | float | Time gap to leader (seconds) |
| `sponsor_name` | string | Primary sponsor |
| `starting_position` | int | Grid/starting position |
| `times_passed` | int | Times passed by others |
| `quality_passes` | int | Quality passes made |
| `is_on_track` | bool | Currently on track |
| `is_on_dvp` | bool | Damaged vehicle policy |

## Driver Object (nested in vehicle)

| Field | Type | Description |
|-------|------|-------------|
| `driver_id` | int | NASCAR driver ID |
| `full_name` | string | Full driver name |
| `first_name` | string | First name |
| `last_name` | string | Last name |
| `is_in_chase` | bool | Playoff eligible |

## Example Response (Practice Session)

```json
{
  "lap_number": 16,
  "elapsed_time": 2093,
  "flag_state": 1,
  "race_id": 5593,
  "laps_in_race": 999,
  "laps_to_go": 983,
  "run_id": 1,
  "run_name": "NCS Final Practice",
  "series_id": 1,
  "track_id": 159,
  "track_length": 0.25,
  "track_name": "Bowman Gray Stadium",
  "run_type": 1,
  "number_of_caution_segments": 5,
  "number_of_caution_laps": 0,
  "stage": {
    "stage_num": 1,
    "finish_at_lap": 999,
    "laps_in_stage": 999
  },
  "vehicles": [...]
}
```
