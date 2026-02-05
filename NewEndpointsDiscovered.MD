# NASCAR API - New Endpoints Discovered

Discovered during live NCS Final Practice at Bowman Gray Stadium (2026-02-04)

## NEW ENDPOINTS FOUND

### 1. Live Stage Points
```
https://cf.nascar.com/live/feeds/live-stage-points.json
```
Returns stage points for each stage of the race.

**Response Fields:**
- `race_id` - Race identifier
- `run_id` - Run/session identifier
- `stage_number` - Which stage (1, 2, 3)
- `results[]` - Array of stage results
  - `position` - Stage finish position
  - `vehicle_number` - Car number
  - `driver_id` - NASCAR driver ID
  - `full_name` - Driver name
  - `stage_points` - Points earned in this stage

---

### 2. Live Points
```
https://cf.nascar.com/live/feeds/live-points.json
```
Real-time championship points standings during a race.

**Response Fields:**
- `bonus_points` - Bonus points earned
- `car_number` - Vehicle number
- `delta_leader` - Points behind leader
- `delta_next` - Points behind next position
- `first_name` / `last_name` - Driver name
- `driver_id` - NASCAR driver ID
- `is_in_chase` - Boolean for playoff eligibility
- `is_points_eligible` - Boolean for points eligibility
- `is_fastest_lap_point` - Boolean if fastest lap bonus earned
- `is_rookie` - Rookie status
- `membership_id` - NASCAR membership ID
- `points` - Total championship points
- `points_position` - Current points standing
- `points_earned_this_race` - Points from current race
- `stage_1_points` / `stage_2_points` / `stage_3_points` - Stage points
- `stage_1_winner` / `stage_2_winner` / `stage_3_winner` - Stage win flags
- `wins` / `top_5` / `top_10` / `poles` - Season stats
- `series_id` / `race_id` / `run_id` - Identifiers

---

### 3. Live Pit Data
```
https://cf.nascar.com/live/feeds/live-pit-data.json
```
Real-time pit stop information (returns empty array `[]` during practice).

---

### 4. Drivers Database
```
https://cf.nascar.com/cacher/drivers.json
```
Complete database of 908+ NASCAR drivers across all series.

**Response Structure:**
```json
{
  "status": 200,
  "message": "Successfully invoked feed: drivers",
  "response": [...]
}
```

**Driver Object Fields:**
- `Nascar_Driver_ID` - Primary NASCAR ID
- `Driver_ID` - Secondary driver ID
- `Driver_Series` - Series association
- `First_Name` / `Last_Name` / `Full_Name` - Name fields
- `Series_Logo` - URL to series logo
- `Short_Name` / `Description` - Additional name info
- `DOB` / `DOD` - Date of birth / death
- `Hometown_City` / `Hometown_State` / `Hometown_Country` - Hometown
- `Crew_Chief` - Current crew chief
- `Rookie_Year_Series_1/2/3` - Rookie years by series
- `Hobbies` / `Children` - Personal info
- `Twitter_Handle` - Social media
- `Residing_City` / `Residing_State` / `Residing_Country` - Current residence
- `Badge` / `Badge_Image` - Badge info and URL
- `Manufacturer` / `Manufacturer_Small` - Manufacturer info
- `Team` - Team association
- `Image` / `Image_Small` / `Image_Transparent` / `SecondaryImage` - Photos
- `Firesuit_Image` / `Firesuit_Image_Small` - Firesuit photos
- `Career_Stats` - Career statistics link
- `Driver_Page` - NASCAR.com profile link
- `Age` / `Rank` / `Points` / `Points_Behind` - Current stats
- `No_Wins` / `Poles` / `Top5` / `Top10` - Performance stats
- `Laps_Led` / `Stage_Wins` - Race stats
- `Playoff_Points` / `Playoff_Rank` - Playoff info
- `Integrated_Sponsor_Name` / `Integrated_Sponsor` / `Integrated_Sponsor_URL` - Sponsor
- `Silly_Season_Change` / `Silly_Season_Change_Description` - Team changes
- `Driver_Post_Status` - Active/draft status
- `Driver_Part_Time` - Part-time indicator

---

### 5. Tracks Database
```
https://cf.nascar.com/cacher/tracks.json
```
Complete database of 49 NASCAR tracks.

**Response Structure:**
```json
{
  "items": [...]
}
```

**Track Object Fields:**
- `track_id` - Track identifier
- `track_name` - Full track name
- `track_surface` - Surface type (Asphalt, Concrete, Dirt)
- `track_type` - Category (Short Track, Intermediate, Superspeedway, Road Course)
- `track_banking` - Banking degrees for turns and straights
- `year_built` - Year track was constructed
- `track_description` - Detailed description
- `city` / `state` - Location
- `frontstretch_length` / `backstretch_length` - Straight lengths
- `seating_capacity` / `capacity` - Fan capacity
- `track_owner` - Track ownership
- `races` - Associated races
- `length` - Track length in miles
- `zip` / `address` - Physical address
- `caution_car_speed` - Caution pace car speed
- `track_image` / `track_image_thumbnail` / `track_logo` - Images
- `track_major_events` - Major annual events
- `track_num_turns` - Number of turns
- `tickets_url` / `tickets_url_new_window` - Ticket info
- `track_url` / `track_url_new_window` - Track website
- `hide_track_from_site` - Display flag

---

## ENHANCED LIVE FEED DATA

### Live Feed Structure
```
https://cf.nascar.com/live/feeds/live-feed.json
```

**Top-Level Fields:**
- `lap_number` - Current lap
- `elapsed_time` - Session elapsed time in seconds
- `flag_state` - Current flag (1=Green, 2=Yellow, etc.)
- `race_id` - Race identifier
- `laps_in_race` - Total laps (999 for practice)
- `laps_to_go` - Remaining laps
- `run_id` - Session run ID
- `run_name` - Session name (e.g., "NCS Final Practice")
- `series_id` - Series (1=Cup, 2=Xfinity, 3=Trucks)
- `time_of_day` - Time of day in seconds
- `time_of_day_os` - ISO timestamp with timezone
- `track_id` - Track identifier
- `track_length` - Track length in miles
- `track_name` - Track name
- `run_type` - Session type (1=Practice, 2=Qualifying, 3=Race)
- `number_of_caution_segments` - Total cautions
- `number_of_caution_laps` - Total caution laps
- `number_of_lead_changes` - Lead changes
- `number_of_leaders` - Number of different leaders
- `avg_diff_1to3` - Average gap top 1-3
- `stage` - Stage information object
  - `stage_num` - Current stage number
  - `finish_at_lap` - Stage end lap
  - `laps_in_stage` - Laps in current stage

**Vehicle Object Fields:**
- `average_restart_speed` - Avg speed on restarts
- `average_running_position` - Avg position
- `average_speed` - Overall average speed
- `best_lap` - Best lap number
- `best_lap_speed` - Best lap speed (MPH)
- `best_lap_time` - Best lap time (seconds)
- `vehicle_manufacturer` - Mfr code (Tyt, Chv, Frd)
- `vehicle_number` - Car number
- `driver` - Driver object (driver_id, full_name, first_name, last_name, is_in_chase)
- `vehicle_elapsed_time` - Total time on track
- `fastest_laps_run` - Number of fastest laps
- `laps_position_improved` - Positions gained
- `laps_completed` - Total laps run
- `laps_led` - Array of laps led
- `last_lap_speed` - Most recent lap speed
- `last_lap_time` - Most recent lap time
- `passes_made` - Total passes made
- `passing_differential` - Net passes (+/-)
- `position_differential_last_10_percent` - Position change late
- `pit_stops` - Array of pit stop data
- `qualifying_status` - Qualifying status code
- `running_position` - Current position
- `status` - Vehicle status (1=Running)
- `delta` - Time gap to leader
- `sponsor_name` - Primary sponsor
- `starting_position` - Grid position
- `times_passed` - Times passed by others
- `quality_passes` - High-quality passes
- `is_on_track` - Currently on track flag
- `is_on_dvp` - Damaged vehicle policy flag

---

## LOOP STATS STRUCTURE

```
https://cf.nascar.com/loopstats/prod/{year}/{series_id}/{race_id}.json
```

**Fields per Driver:**
- `driver_id` - NASCAR driver ID
- `start_ps` - Starting position
- `mid_ps` - Mid-race position
- `ps` - Final position
- `closing_ps` - Position in closing laps
- `closing_laps_diff` - Position change in closing
- `best_ps` / `worst_ps` - Best/worst positions
- `avg_ps` - Average running position
- `passes_gf` - Green flag passes made
- `passing_diff` - Net passes (+/-)
- `passed_gf` - Times passed (green flag)
- `quality_passes` - Quality/significant passes
- `fast_laps` - Fastest laps run
- `top15_laps` - Laps running in top 15
- `lead_laps` - Laps in the lead
- `laps` - Total laps completed
- `rating` - Driver rating for race

---

## LIVE PRACTICE DATA SAMPLE

**Bowman Gray Stadium - NCS Final Practice (2026-02-04)**

| Pos | # | Driver | Best Time | Speed | Laps |
|-----|---|--------|-----------|-------|------|
| 1 | 5 | Kyle Larson | 14.137 | 63.663 | 14 |
| 2 | 24 | William Byron | 14.141 | 63.645 | 14 |
| 3 | 54 | Ty Gibbs | 14.146 | 63.622 | 16 |
| 4 | 19 | Chase Briscoe | 14.147 | 63.618 | 14 |
| 5 | 20 | Christopher Bell | 14.150 | 63.604 | 13 |
| 6 | 11 | Denny Hamlin | 14.151 | 63.600 | 13 |
| 7 | 23 | Bubba Wallace | 14.153 | 63.591 | 15 |
| 8 | 17 | Chris Buescher | 14.167 | 63.528 | 18 |

Track: 0.25 miles (shortest track on schedule!)
32+ cars participating

---

## API ENDPOINTS SUMMARY

### Live Data (Real-time)
| Endpoint | URL |
|----------|-----|
| Live Feed | `https://cf.nascar.com/live/feeds/live-feed.json` |
| Live Flag Data | `https://cf.nascar.com/live/feeds/live-flag-data.json` |
| Live Pit Data | `https://cf.nascar.com/live/feeds/live-pit-data.json` |
| Live Points | `https://cf.nascar.com/live/feeds/live-points.json` |
| Live Stage Points | `https://cf.nascar.com/live/feeds/live-stage-points.json` |

### Static/Cached Data
| Endpoint | URL Pattern |
|----------|-------------|
| Race List | `https://cf.nascar.com/cacher/{year}/race_list_basic.json` |
| Drivers | `https://cf.nascar.com/cacher/drivers.json` |
| Tracks | `https://cf.nascar.com/cacher/tracks.json` |
| Weekend Feed | `https://cf.nascar.com/cacher/{year}/{series}/{race_id}/weekend-feed.json` |
| Lap Times | `https://cf.nascar.com/cacher/{year}/{series}/{race_id}/lap-times.json` |
| Lap Notes | `https://cf.nascar.com/cacher/{year}/{series}/{race_id}/lap-notes.json` |
| Loop Stats | `https://cf.nascar.com/loopstats/prod/{year}/{series}/{race_id}.json` |
