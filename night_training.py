import time
import random
import json
import os
from datetime import datetime

import betsc  # uses betsc.py as-is

# =========================
# FILE PATHS
# =========================

STARS_DB_PATH = "stars_database.json"
BRAIN_PATH = "brain.json"
TARGET_PATH = "target_stars.txt"

# =========================
# CONFIG
# =========================

NIGHT_DURATION = 600.0      # 10 minutes in seconds (lower for testing if you want)
SCAN_INTERVAL = 0.2         # seconds between samples

BASELINE_SAMPLES = 50
DIP_THRESHOLD = 0.003       # how far below baseline counts as a dip
DIP_END_CONFIRMATION = 5    # samples near baseline to confirm dip ended

MIN_FLICKER_DURATION = 0.2
MAX_FLICKER_DURATION = 1.0

MIN_CLOUD_DURATION = 5.0
MAX_CLOUD_DURATION = 20.0

MIN_TRANSIT_DURATION = 120.0   # 2 minutes
MAX_TRANSIT_DURATION = 180.0   # 3 minutes

FLICKER_DEPTH = 0.004
CLOUD_DEPTH = 0.015
TRANSIT_DEPTH = 0.01

MIN_PLANET_DEPTH = 0.007
MIN_PLANET_DURATION = 60.0     # at least 1 minute to count as planet

# =========================
# UTILITIES
# =========================

def load_json(path, default):
    if not os.path.exists(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def load_target_star():
    if not os.path.exists(TARGET_PATH):
        raise FileNotFoundError(f"{TARGET_PATH} not found.")
    with open(TARGET_PATH, "r", encoding="utf-8") as f:
        for line in f:
            name = line.strip()
            if name:
                return name
    raise ValueError("target_stars.txt is empty or only whitespace.")

def load_star_info(star_name):
    db = load_json(STARS_DB_PATH, {})
    info = db.get(star_name, None)
    if info is None:
        info = {
            "spectral_type": "Unknown",
            "temperature": None,
            "radius_solar": None,
            "mass_solar": None,
            "distance_ly": None,
            "variability": "unknown",
            "metallicity_fe_h": None,
            "known_planets": [],
            "notes": "Star not found in database; using minimal info."
        }
    return info

def load_brain():
    return load_json(BRAIN_PATH, {})

def save_brain(brain):
    save_json(BRAIN_PATH, brain)

# =========================
# EVENT MODEL
# =========================

def generate_night_events():
    """
    Generate:
    - 1 flat-bottom transit
    - 1–3 flickers
    - 0–2 clouds
    All within the 10-minute night.
    """
    events = []

    # Transit: one clean flat-bottom event
    transit_start = random.uniform(60.0, NIGHT_DURATION - MAX_TRANSIT_DURATION - 60.0)
    transit_duration = random.uniform(MIN_TRANSIT_DURATION, MAX_TRANSIT_DURATION)
    transit_end = transit_start + transit_duration
    events.append({
        "type": "transit",
        "start": transit_start,
        "end": transit_end,
        "depth": TRANSIT_DEPTH
    })

    # Flickers: short, shallow dips
    n_flickers = random.randint(1, 3)
    for _ in range(n_flickers):
        start = random.uniform(20.0, NIGHT_DURATION - 20.0)
        dur = random.uniform(MIN_FLICKER_DURATION, MAX_FLICKER_DURATION)
        events.append({
            "type": "flicker",
            "start": start,
            "end": start + dur,
            "depth": FLICKER_DEPTH
        })

    # Clouds: messy, deeper dips
    n_clouds = random.randint(0, 2)
    for _ in range(n_clouds):
        start = random.uniform(30.0, NIGHT_DURATION - MAX_CLOUD_DURATION - 30.0)
        dur = random.uniform(MIN_CLOUD_DURATION, MAX_CLOUD_DURATION)
        events.append({
            "type": "cloud",
            "start": start,
            "end": start + dur,
            "depth": CLOUD_DEPTH
        })

    return events

def get_brightness(elapsed, events):
    """
    Base brightness ~1.0 with noise.
    Events subtract depth when active.
    If multiple overlap, we take the deepest.
    """
    base = 1.0
    noise = random.uniform(-0.0005, 0.0005)

    active_depth = 0.0
    for ev in events:
        if ev["start"] <= elapsed <= ev["end"]:
            active_depth = max(active_depth, ev["depth"])

    return base - active_depth + noise

# =========================
# DIP EVENT CLASS
# =========================

class DipEvent:
    def __init__(self, start_time, baseline):
        self.start_time = start_time
        self.end_time = None
        self.samples = []
        self.baseline = baseline

    def add_sample(self, t, brightness):
        self.samples.append((t, brightness))

    @property
    def duration(self):
        if self.end_time is None or not self.samples:
            return 0.0
        return self.end_time - self.start_time

    @property
    def depths(self):
        return [self.baseline - b for _, b in self.samples]

    @property
    def max_depth(self):
        return max(self.depths) if self.samples else 0.0

    @property
    def variance(self):
        vals = self.depths
        if not vals:
            return 0.0
        mean = sum(vals) / len(vals)
        return sum((v - mean) ** 2 for v in vals) / len(vals)

# =========================
# CLASSIFICATION
# =========================

def classify_dip(dip: DipEvent):
    dur = dip.duration
    depth = dip.max_depth
    var = dip.variance

    # Very short, shallow = flicker
    if dur < MIN_FLICKER_DURATION or depth < FLICKER_DEPTH * 0.5:
        return "flicker"

    # Deep and long and relatively stable = planet
    if depth >= MIN_PLANET_DEPTH and dur >= MIN_PLANET_DURATION and var < (CLOUD_DEPTH ** 2) * 0.2:
        return "planet"

    # Deep but messy = cloud
    if depth >= FLICKER_DEPTH:
        return "cloud"

    return "flicker"

# =========================
# PLANET NAMING (APPROVAL MODE)
# =========================

def handle_new_planet_candidate(star_name, dip, star_info, brain, planet_detections):
    """
    Called when a dip is classified as a planet.
    - Calls BETSC's planet reaction
    - Checks if this is a 'new' planet for this star
    - Pauses and asks you for a name (excited rambling mode)
    - Updates brain structure
    """
    # Let BETSC react first (personality from betsc.py)
    betsc.betsc_on_planet(dip)

    star_entry = brain.get(star_name, {})
    discovered = star_entry.get("discovered_planets", [])

    # If star_database already has known planets, we treat this as another detection,
    # not a brand new planet to name.
    known_from_db = star_info.get("known_planets", []) or []

    is_first_for_star = (len(known_from_db) == 0 and len(discovered) == 0)

    planet_name = None

    if is_first_for_star:
        # Excited rambling pause
        print()
        print("BETSC: BENJAMIN. BENJAMIN. BENJAMIN.")
        print("BETSC: I THINK THIS IS A *NEW* PLANET.")
        print("BETSC: I HAVE FROZEN TIME. I AM VIBRATING.")
        print("BETSC: PLEASE. NAME. THE. PLANET.")
        print()
        suggestion = f"{star_name} b"
        user_input = input(f"Name this planet (press Enter to use '{suggestion}', or type your own, or just Enter again to skip): ").strip()

        if user_input:
            planet_name = user_input
        else:
            # Ask once more if they want the default or to skip
            confirm = input(f"Use default name '{suggestion}'? (y/n): ").strip().lower()
            if confirm == "y":
                planet_name = suggestion
            else:
                planet_name = None  # unnamed candidate

        if planet_name:
            print(f"BETSC: OKAY. OKAY. WRITING '{planet_name}' INTO MY BRAIN. VERY CAREFULLY.")
            discovered.append(planet_name)
            star_entry["discovered_planets"] = discovered
            brain[star_name] = star_entry
            save_brain(brain)
        else:
            print("BETSC: UNNAMED PLANET CANDIDATE. I WILL STILL REMEMBER THE DIP. I AM MILDLY OFFENDED BUT I UNDERSTAND.")
    else:
        # Not the first planet for this star; just log detection
        print("BETSC: Another planet-like dip for this star. I’ll log it with the others.")

    # Record this detection for tonight's observation summary
    planet_detections.append({
        "name": planet_name,
        "depth": dip.max_depth,
        "duration": dip.duration
    })

# =========================
# MEMORY WRITING
# =========================

def write_observation_to_brain(star_name, brain, summary, planet_detections):
    star_entry = brain.get(star_name, {})
    observations = star_entry.get("observations", [])

    obs = {
        "date": datetime.utcnow().isoformat() + "Z",
        "planets_detected": planet_detections,
        "clouds": summary["clouds"],
        "flickers": summary["flickers"],
        "notes": "BETSC: Night training run. I watched. I classified. I screamed."
    }

    observations.append(obs)
    star_entry["observations"] = observations
    brain[star_name] = star_entry
    save_brain(brain)

# =========================
# MAIN NIGHT LOOP
# =========================

def run_betsc_night():
    # Load target star
    star_name = load_target_star()
    star_info = load_star_info(star_name)
    brain = load_brain()

    # Intro with personality
    betsc.betsc_intro()
    print(f"BETSC: Tonight's target: {star_name}.")
    print(f"BETSC: Spectral type: {star_info.get('spectral_type', 'Unknown')}, variability: {star_info.get('variability', 'unknown')}.")
    if star_name in brain:
        print("BETSC: I REMEMBER THIS STAR. I HAVE SEEN IT BEFORE. I AM OPENING MY BRAIN.")
        past_obs = brain[star_name].get("observations", [])
        print(f"BETSC: I have {len(past_obs)} past observation(s) of this star.")
    else:
        print("BETSC: I HAVE NEVER SEEN THIS STAR BEFORE. FRESH PHOTONS. FRESH CHAOS.")

    betsc.betsc_baseline()

    # Simple baseline around 1.0 with noise
    baseline_samples = []
    for _ in range(BASELINE_SAMPLES):
        baseline_samples.append(1.0 + random.uniform(-0.0005, 0.0005))
        time.sleep(SCAN_INTERVAL)
    baseline = sum(baseline_samples) / len(baseline_samples)
    print(f"BETSC: Baseline locked at {baseline:.5f}. I trust this. Mostly.")

    events = generate_night_events()
    betsc.betsc_night_start()

    start_time = time.time()
    dip = None
    dip_end_counter = 0

    summary = {"planets": 0, "clouds": 0, "flickers": 0}
    planet_detections = []

    while True:
        now = time.time()
        elapsed = now - start_time
        if elapsed >= NIGHT_DURATION:
            break

        brightness = get_brightness(elapsed, events)
        delta = baseline - brightness

        if dip is None:
            # Look for start of dip
            if delta >= DIP_THRESHOLD:
                dip = DipEvent(elapsed, baseline)
                dip.add_sample(elapsed, brightness)
                dip_end_counter = 0
                betsc.betsc_on_dip_start()
        else:
            # Continue dip
            dip.add_sample(elapsed, brightness)

            if abs(brightness - baseline) < DIP_THRESHOLD / 2:
                dip_end_counter += 1
            else:
                dip_end_counter = 0

            if dip_end_counter >= DIP_END_CONFIRMATION:
                dip.end_time = elapsed
                classification = classify_dip(dip)

                if classification == "planet":
                    summary["planets"] += 1
                    handle_new_planet_candidate(
                        star_name,
                        dip,
                        star_info,
                        brain,
                        planet_detections
                    )
                elif classification == "cloud":
                    betsc.betsc_on_cloud(dip)
                    summary["clouds"] += 1
                else:
                    betsc.betsc_on_flicker(dip)
                    summary["flickers"] += 1

                dip = None
                dip_end_counter = 0

        time.sleep(SCAN_INTERVAL)

    # If a dip was in progress when night ended, classify it once
    if dip is not None:
        dip.end_time = NIGHT_DURATION
        classification = classify_dip(dip)
        if classification == "planet":
            summary["planets"] += 1
            handle_new_planet_candidate(
                star_name,
                dip,
                star_info,
                brain,
                planet_detections
            )
        elif classification == "cloud":
            betsc.betsc_on_cloud(dip)
            summary["clouds"] += 1
        else:
            betsc.betsc_on_flicker(dip)
            summary["flickers"] += 1

    betsc.betsc_night_end(summary)
    write_observation_to_brain(star_name, brain, summary, planet_detections)

# =========================
# ENTRY POINT
# =========================

if __name__ == "__main__":
    run_betsc_night()
