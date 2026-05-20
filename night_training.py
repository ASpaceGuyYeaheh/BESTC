import time
import random
import json
import os
from datetime import datetime

import betsc  # your personality file

# =========================
# FILE PATHS
# =========================

STARS_DB_PATH = "stars_database.json"
BRAIN_PATH = "brain.json"
TARGET_PATH = "target_stars.txt"

# =========================
# CONFIG
# =========================

NIGHT_DURATION = 600.0
SCAN_INTERVAL = 0.2

BASELINE_SAMPLES = 50
WAIT_LINE_INTERVAL_MIN = 10
WAIT_LINE_INTERVAL_MAX = 20

DIP_THRESHOLD = 0.003
DIP_END_CONFIRMATION = 5

MIN_FLICKER_DURATION = 0.2
MAX_FLICKER_DURATION = 1.0

MIN_CLOUD_DURATION = 5.0
MAX_CLOUD_DURATION = 20.0

MIN_TRANSIT_DURATION = 120.0
MAX_TRANSIT_DURATION = 180.0

FLICKER_DEPTH = 0.004
CLOUD_DEPTH = 0.015
TRANSIT_DEPTH = 0.01

MIN_PLANET_DEPTH = 0.007
MIN_PLANET_DURATION = 60.0


# =========================
# UTILITIES
# =========================

def load_json(path, default):
    if not os.path.exists(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return default

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def load_target_star():
    with open(TARGET_PATH, "r", encoding="utf-8") as f:
        for line in f:
            name = line.strip()
            if name:
                return name
    raise ValueError("target_stars.txt is empty.")

def load_star_info(star_name):
    print("DEBUG:", repr(star_name))

    db = load_json(STARS_DB_PATH, {})

    # Normalize the name
    normalized = star_name.strip().replace("\u00A0", " ")  # remove non-breaking spaces

    return db.get(normalized, {
        "spectral_type": "Unknown",
        "variability": "unknown",
        "known_planets": []
    })

def load_brain():
    return load_json(BRAIN_PATH, {})

def save_brain(brain):
    save_json(BRAIN_PATH, brain)


# =========================
# EVENT MODEL
# =========================

def generate_night_events():
    events = []

    transit_start = random.uniform(60.0, NIGHT_DURATION - MAX_TRANSIT_DURATION - 60.0)
    transit_duration = random.uniform(MIN_TRANSIT_DURATION, MAX_TRANSIT_DURATION)
    events.append({
        "type": "transit",
        "start": transit_start,
        "end": transit_start + transit_duration,
        "depth": TRANSIT_DEPTH
    })

    for _ in range(random.randint(1, 3)):
        start = random.uniform(20.0, NIGHT_DURATION - 20.0)
        dur = random.uniform(MIN_FLICKER_DURATION, MAX_FLICKER_DURATION)
        events.append({
            "type": "flicker",
            "start": start,
            "end": start + dur,
            "depth": FLICKER_DEPTH
        })

    for _ in range(random.randint(0, 2)):
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
        if self.end_time is None:
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

def classify_dip(dip):
    dur = dip.duration
    depth = dip.max_depth
    var = dip.variance

    if dur < MIN_FLICKER_DURATION or depth < FLICKER_DEPTH * 0.5:
        return "flicker"

    if depth >= MIN_PLANET_DEPTH and dur >= MIN_PLANET_DURATION and var < (CLOUD_DEPTH ** 2) * 0.2:
        return "planet"

    if depth >= FLICKER_DEPTH:
        return "cloud"

    return "flicker"


# =========================
# PLANET NAMING (PAUSE MODE)
# =========================

def handle_new_planet_candidate(star_name, dip, star_info, brain, planet_detections):
    betsc.betsc_on_planet(dip)

    star_entry = brain.get(star_name, {})
    discovered = star_entry.get("discovered_planets", [])
    known_from_db = star_info.get("known_planets", [])

    is_first = (len(known_from_db) == 0 and len(discovered) == 0)

    planet_name = None

    if is_first:
        print("\nBETSC: BENJAMIN. BENJAMIN. BENJAMIN.")
        print("BETSC: I THINK THIS IS A NEW PLANET.")
        print("BETSC: I HAVE FROZEN TIME. I AM VIBRATING.")
        print("BETSC: PLEASE. NAME. THE. PLANET.\n")

        suggestion = f"{star_name} b"
        user_input = input(f"Name this planet (Enter = '{suggestion}', or Enter again to skip): ").strip()

        if user_input:
            planet_name = user_input
        else:
            confirm = input(f"Use default name '{suggestion}'? (y/n): ").strip().lower()
            if confirm == "y":
                planet_name = suggestion

        if planet_name:
            print(f"BETSC: WRITING '{planet_name}' INTO MY BRAIN. VERY CAREFULLY.")
            discovered.append(planet_name)
            star_entry["discovered_planets"] = discovered
            brain[star_name] = star_entry
            save_brain(brain)
        else:
            print("BETSC: UNNAMED PLANET CANDIDATE. I WILL REMEMBER IT ANYWAY.")

    planet_detections.append({
        "name": planet_name,
        "depth": dip.max_depth,
        "duration": dip.duration
    })

# =========================
# EMOTIONAL ENGINE + PERSONALITY SYSTEM (SCRIPT 2)
# =========================

def clamp_emotion(value):
    return max(0, min(100, value))

def initialize_emotions(brain, star_name):
    star_entry = brain.get(star_name, {})
    emotions = star_entry.get("emotions")

    if emotions is None:
        emotions = {
            "excited": 40,
            "annoyed": 20,
            "angry_clouds": 30,   # UNCAPPED
            "bored": 10,
            "paranoid": 15,
            "smug": 5,
            "offended": 0,
            "sleepy": 0,
            "determined": 25
        }
        star_entry["emotions"] = emotions
        brain[star_name] = star_entry
        save_brain(brain)

    return emotions


# =========================
# PERSONALITY LINES (SCRIPT 2)
# =========================

def generate_personality_lines(spectral_type, variability):
    spectral_type = spectral_type.upper()
    variability = variability.lower()

    # --- Spectral Type Lines ---
    if spectral_type.startswith("G"):
        spectral_line = "A classic G‑star. Reliable. Warm. I like this one."
    elif spectral_type.startswith("K"):
        spectral_line = "A K‑star… soft, warm, and steady. This feels nice."
    elif spectral_type.startswith("M"):
        spectral_line = "An M‑dwarf. Tiny. Unpredictable. I’m watching you."
    elif spectral_type.startswith("F"):
        spectral_line = "An F‑star! Bright, bold, and full of flair. My kind of chaos."
    elif spectral_type.startswith("A"):
        spectral_line = "An A‑type. Too perfect. Too shiny. Tone it down."
    elif spectral_type.startswith("B"):
        spectral_line = "A B‑star?! That’s a LOT of photons. I’m sweating."
    elif spectral_type.startswith("O"):
        spectral_line = "An O‑star. That’s a cosmic blowtorch. I’m scared."
    else:
        spectral_line = "I don’t know what this star is, but I’m pretending I do."

    # --- Variability Lines ---
    if variability in ["none", "low"]:
        variability_line = "Stable star. Good. I can relax."
    elif variability == "medium":
        variability_line = "Moderate variability. I’ll keep an eye on it."
    elif variability == "high":
        variability_line = "High variability?! It’s flickering on purpose. I KNOW it is."
    elif variability in ["flare", "eruptive"]:
        variability_line = "Flare star detected. I swear it’s trying to kill me."
    else:
        variability_line = "Variability unknown. That’s worse than knowing."

    return spectral_line, variability_line

# =========================
# PERSONALITY EMOTION SHIFTS (SCRIPT 2)
# =========================

def apply_star_personality(spectral_type, variability, emotions, brain, star_name):
    """
    Adjust BETSC's emotional baseline depending on spectral type + variability.
    Save personality lines into the brain.
    """

    spectral_type = spectral_type.upper()
    variability = variability.lower()

    # --- Emotional shifts based on spectral type ---
    if spectral_type.startswith("G"):
        emotions["excited"] += 5
        emotions["bored"] = max(0, emotions["bored"] - 3)

    elif spectral_type.startswith("K"):
        emotions["sleepy"] += 3
        emotions["angry_clouds"] = max(0, emotions["angry_clouds"] - 5)

    elif spectral_type.startswith("M"):
        emotions["annoyed"] += 4
        emotions["excited"] = max(0, emotions["excited"] - 2)

    elif spectral_type.startswith("F"):
        emotions["excited"] += 8
        emotions["angry_clouds"] += 5

    elif spectral_type.startswith("A"):
        emotions["annoyed"] += 2
        emotions["bored"] += 4

    elif spectral_type.startswith("B"):
        emotions["excited"] += 10
        emotions["paranoid"] += 10

    elif spectral_type.startswith("O"):
        emotions["paranoid"] += 20
        emotions["excited"] -= 5

    # --- Variability emotional shifts ---
    if variability in ["none", "low"]:
        emotions["sleepy"] += 2

    elif variability == "medium":
        emotions["annoyed"] += 3

    elif variability == "high":
        emotions["paranoid"] += 10
        emotions["annoyed"] += 5

    elif variability in ["flare", "eruptive"]:
        emotions["paranoid"] += 20
        emotions["angry_clouds"] += 10

    # --- Generate personality lines ---
    spectral_line, variability_line = generate_personality_lines(spectral_type, variability)

    print("BETSC personality:", spectral_line)
    print("BETSC variability:", variability_line)

    # --- Save personality lines into brain ---
    star_entry = brain.get(star_name, {})
    star_entry["spectral_personality_line"] = spectral_line
    star_entry["variability_personality_line"] = variability_line
    brain[star_name] = star_entry
    save_brain(brain)


# =========================
# EMOTION EVENTS
# =========================

def decay_emotions(emotions):
    for key in emotions:
        if key == "angry_clouds":
            continue
        emotions[key] = clamp_emotion(emotions[key] - 5)

def emotion_on_planet(emotions):
    emotions["excited"] = clamp_emotion(emotions["excited"] + 40)
    emotions["smug"] = clamp_emotion(emotions["smug"] + 20)
    emotions["determined"] = clamp_emotion(emotions["determined"] + 10)
    emotions["bored"] = 0
    emotions["annoyed"] = 0
    emotions["angry_clouds"] = max(0, emotions["angry_clouds"] - 1)

def emotion_on_cloud(emotions):
    emotions["angry_clouds"] += 10
    emotions["annoyed"] = clamp_emotion(emotions["annoyed"] + 10)
    emotions["excited"] = clamp_emotion(emotions["excited"] - 10)
    emotions["paranoid"] = clamp_emotion(emotions["paranoid"] + 5)

def emotion_on_flicker(emotions):
    emotions["annoyed"] = clamp_emotion(emotions["annoyed"] + 15)
    emotions["bored"] = clamp_emotion(emotions["bored"] + 5)
    emotions["excited"] = clamp_emotion(emotions["excited"] + 5)

def emotion_on_bored(emotions):
    emotions["bored"] = clamp_emotion(emotions["bored"] + 10)
    emotions["annoyed"] = clamp_emotion(emotions["annoyed"] + 5)

def emotion_on_skip(emotions):
    emotions["offended"] = 100
    emotions["excited"] = clamp_emotion(emotions["excited"] - 20)
    emotions["smug"] = clamp_emotion(emotions["smug"] - 10)

def emotion_on_night_end(emotions):
    emotions["sleepy"] = clamp_emotion(emotions["sleepy"] + 40)
    emotions["excited"] = clamp_emotion(emotions["excited"] - 10)

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
        "notes": "BETSC: Night training run."
    }

    observations.append(obs)
    star_entry["observations"] = observations
    brain[star_name] = star_entry
    save_brain(brain)


# =========================
# MAIN NIGHT LOOP
# =========================

def run_betsc_night():
    star_name = load_target_star()
    star_info = load_star_info(star_name)

    brain = load_brain()
    emotions = initialize_emotions(brain, star_name)

    spectral_type = star_info.get("spectral_type", "unknown")
    variability = star_info.get("variability", "unknown")

    # BETSC intro FIRST
    print(f"Starting night for {star_name}...")
    print(f"Star info: {star_info}")

    # THEN personality
    apply_star_personality(spectral_type, variability, emotions, brain, star_name)

    # Baseline
    next_wait_line = time.time() + random.uniform(WAIT_LINE_INTERVAL_MIN, WAIT_LINE_INTERVAL_MAX)
    baseline_samples = []

    for _ in range(BASELINE_SAMPLES):
        if time.time() >= next_wait_line:
            betsc.betsc_wait_line_once()
            next_wait_line = time.time() + random.uniform(WAIT_LINE_INTERVAL_MIN, WAIT_LINE_INTERVAL_MAX)

        baseline_samples.append(1.0 + random.uniform(-0.0005, 0.0005))
        time.sleep(SCAN_INTERVAL)

    baseline = sum(baseline_samples) / len(baseline_samples)
    print(f"BETSC: Baseline locked at {baseline:.5f}.")

    events = generate_night_events()

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
            if delta >= DIP_THRESHOLD:
                dip = DipEvent(elapsed, baseline)
                dip.add_sample(elapsed, brightness)
                dip_end_counter = 0
                betsc.betsc_on_dip_start()
        else:
            dip.add_sample(elapsed, brightness)

            if abs(brightness - baseline) < DIP_THRESHOLD / 2:
                dip_end_counter += 1
            else:
                dip_end_counter = 0

            if dip_end_counter >= DIP_END_CONFIRMATION:
                dip.end_time = elapsed
                classification = classify_dip(dip)

                if classification == "planet":
                    emotion_on_planet(emotions)
                    summary["planets"] += 1
                    handle_new_planet_candidate(star_name, dip, star_info, brain, planet_detections)
                    print(f"BETSC (emotional log): {emotions}")
                elif classification == "cloud":
                    emotion_on_cloud(emotions)
                    summary["clouds"] += 1
                    betsc.betsc_on_cloud(dip)
                    print(f"BETSC (emotional log): {emotions}")
                else:
                    emotion_on_flicker(emotions)
                    summary["flickers"] += 1
                    betsc.betsc_on_flicker(dip)
                    print(f"BETSC (emotional log): {emotions}")

                dip = None
                dip_end_counter = 0

        time.sleep(SCAN_INTERVAL)

    betsc.betsc_sleep()
    
    emotion_on_night_end(emotions)
    decay_emotions(emotions)

    star_entry = brain.get(star_name, {})
    star_entry["emotions"] = emotions
    brain[star_name] = star_entry
    save_brain(brain)

    write_observation_to_brain(star_name, brain, summary, planet_detections)

if __name__ == "__main__":
    run_betsc_night()
