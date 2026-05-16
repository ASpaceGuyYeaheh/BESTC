import time
import random

# =========================
# CONFIG
# =========================

NIGHT_DURATION = 600.0      # 10 minutes in seconds (you can lower for testing)
SCAN_INTERVAL = 0.05         # seconds between samples

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
# BETSC PERSONALITY
# =========================

def betsc_intro():
    print("BETSC: Initialising… deep breath… okay. One star. One night. Let’s HUNT.")

def betsc_baseline():
    print("BETSC: Building baseline… don’t move the telescope, don’t sneeze, don’t even THINK loud.")

def betsc_night_start():
    print("\nBETSC: Night started. Watching this star for the whole night. No NEXT button. Just me and photons.")

def betsc_on_dip_start():
    print("BETSC: I THINK I SEE SOMETHING!! HOLD ON— HOLD ON— HOLD ON—")

def betsc_on_planet(dip):
    print("BETSC: THAT’S A PLANET. THAT’S A PLANET. THAT’S A PLANET.")
    print(f"BETSC: Duration {dip.duration:.1f}s, depth {dip.max_depth:.5f}. I am a GENIUS.")

def betsc_on_cloud(dip):
    print("BETSC: That was HUGE and MESSY. Cloud. Absolutely a cloud.")
    print("BETSC: Atmosphere, you are my nemesis.")

def betsc_on_flicker(dip):
    print("BETSC: Tiny little twitch. Star flicker. Not impressed.")
    print("BETSC: I’ll keep watching. Could still be something real.")

def betsc_night_end(summary):
    print("\nBETSC: Night over. Shutting down the telescope… gently.")
    print(f"BETSC: Summary: {summary['planets']} planet(s), {summary['clouds']} cloud(s), {summary['flickers']} flicker(s).")
    if summary["planets"] > 0:
        print("BETSC: I FOUND A PLANET. I WILL BE TALKING ABOUT THIS FOR WEEKS.")
    elif summary["clouds"] > 0 or summary["flickers"] > 0:
        print("BETSC: No planets… but I learned a LOT. Training arc continues.")
    else:
        print("BETSC: Nothing. Absolutely nothing. I stared at a star for 10 minutes. I need a snack.")
    print("BETSC: zzzzzzzzzzzzzzzzzzzzzzzzzzzzz…")

# =========================
# MAIN NIGHT LOOP
# =========================

def run_betsc_night():
    betsc_intro()
    betsc_baseline()

    # Simple baseline around 1.0 with noise
    baseline_samples = []
    for _ in range(BASELINE_SAMPLES):
        baseline_samples.append(1.0 + random.uniform(-0.0005, 0.0005))
        time.sleep(SCAN_INTERVAL)
    baseline = sum(baseline_samples) / len(baseline_samples)
    print(f"BETSC: Baseline locked at {baseline:.5f}. I trust this. Mostly.")

    events = generate_night_events()
    betsc_night_start()

    start_time = time.time()
    dip = None
    dip_end_counter = 0

    summary = {"planets": 0, "clouds": 0, "flickers": 0}

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
                betsc_on_dip_start()
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
                    betsc_on_planet(dip)
                    summary["planets"] += 1
                elif classification == "cloud":
                    betsc_on_cloud(dip)
                    summary["clouds"] += 1
                else:
                    betsc_on_flicker(dip)
                    summary["flickers"] += 1

                dip = None
                dip_end_counter = 0

        time.sleep(SCAN_INTERVAL)

    # If a dip was in progress when night ended, classify it once
    if dip is not None:
        dip.end_time = NIGHT_DURATION
        classification = classify_dip(dip)
        if classification == "planet":
            betsc_on_planet(dip)
            summary["planets"] += 1
        elif classification == "cloud":
            betsc_on_cloud(dip)
            summary["clouds"] += 1
        else:
            betsc_on_flicker(dip)
            summary["flickers"] += 1

    betsc_night_end(summary)

# =========================
# ENTRY POINT
# =========================

if __name__ == "__main__":
    run_betsc_night()
