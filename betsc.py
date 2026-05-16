import time
import random

# =========================
# CONFIG
# =========================

SCAN_INTERVAL = 0.1
BASELINE_SAMPLES = 50
DIP_THRESHOLD = 0.003
MIN_DIP_DURATION = 5.0
MAX_FLICKER_DEPTH = 0.005
MAX_CLOUD_VARIANCE = 0.0008
MIN_PLANET_DEPTH = 0.005

WAIT_TIME = 10.0  # seconds BETSC waits per star

# =========================
# LOAD STAR LIST
# =========================

def load_target_stars():
    try:
        with open("target_stars.txt", "r") as f:
            stars = [line.strip() for line in f.readlines() if line.strip()]
        return stars
    except FileNotFoundError:
        print("BETSC: target_stars.txt missing!! I can’t scan NOTHING!!")
        return []

# =========================
# MOCK BRIGHTNESS SOURCE
# =========================

def get_brightness():
    base = 1.0
    noise = random.uniform(-0.0005, 0.0005)
    return base + noise

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

def classify_dip(dip: DipEvent):
    dur = dip.duration
    depth = dip.max_depth
    var = dip.variance

    if dur < MIN_DIP_DURATION or depth < MAX_FLICKER_DEPTH:
        return "flicker"

    if depth >= MIN_PLANET_DEPTH:
        if var <= MAX_CLOUD_VARIANCE:
            return "planet"
        else:
            return "cloud"

    return "cloud"

# =========================
# BETSC PERSONALITY LINES
# =========================

def betsc_announce_star(star):
    print(f"\nBETSC: Now scanning **{star}**!")
    print("BETSC: OOO I hope this one has a planet… I’m READY!")

def betsc_wait_line_once():
    print("BETSC: Holding my breath… I love exoplanets more than oxyge—")

def betsc_disappointed():
    print("BETSC: Awwwwwwww… nothing. Not even a tiny dip.")
    print("BETSC: It’s okay. I’ll find one. I’m the BEST. I think.")

def betsc_on_dip_start():
    print("BETSC: I THINK I SEE SOMETHING!! HOLD ON—HOLD ON—HOLD ON—")

def betsc_on_planet(dip):
    print("BETSC: YES!! YES!! IT’S REAL!! I KNEW IT!!")
    print(f"BETSC: Transit complete! Duration {dip.duration:.1f}s, depth {dip.max_depth:.5f}!")
    print("BETSC: LOGGING THIS BEFORE I EXPLODE WITH JOY.")

def betsc_on_cloud(dip):
    print("BETSC: Wow, that’s a big exopla— oh no wait it’s a stupid cloud.")
    print("BETSC: Clouds are banned from space. Effective immediately.")

def betsc_on_flicker(dip):
    print("BETSC: That dip was… microscopic.")
    print("BETSC: Star flicker. Fake. Fraud. NEXT.")

def betsc_sleep():
    print("\nBETSC: All stars done! I’m getting a bit tire— SNORE.")
    print("BETSC: zzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzz…")

# =========================
# MAIN SCAN LOOP
# =========================

def run_betsc():
    print("BETSC: Initialising BEST— I mean BETS— I mean— I AM the BEST.")
    print("BETSC: Building baseline…")

    baseline_samples = []
    for _ in range(BASELINE_SAMPLES):
        baseline_samples.append(get_brightness())
        time.sleep(SCAN_INTERVAL)

    baseline = sum(baseline_samples) / len(baseline_samples)
    print(f"BETSC: Baseline locked at {baseline:.5f}. LET’S GOOOOO.")

    stars = load_target_stars()
    if not stars:
        return

    for star in stars:

        betsc_announce_star(star)
        betsc_wait_line_once()  # ONLY ONCE

        start_time = time.time()
        dip = None

        while time.time() - start_time < WAIT_TIME:
            brightness = get_brightness()
            delta = baseline - brightness

            if dip is None:
                if delta >= DIP_THRESHOLD:
                    dip = DipEvent(time.time(), baseline)
                    dip.add_sample(time.time(), brightness)
                    betsc_on_dip_start()
            else:
                dip.add_sample(time.time(), brightness)

                if abs(brightness - baseline) < DIP_THRESHOLD / 2:
                    dip.end_time = time.time()
                    classification = classify_dip(dip)

                    if classification == "planet":
                        betsc_on_planet(dip)
                    elif classification == "cloud":
                        betsc_on_cloud(dip)
                    else:
                        betsc_on_flicker(dip)

                    dip = None
                    break

            time.sleep(SCAN_INTERVAL)

        if dip is None:
            betsc_disappointed()

    betsc_sleep()

# =========================
# ENTRY POINT
# =========================

if __name__ == "__main__":
    run_betsc()
