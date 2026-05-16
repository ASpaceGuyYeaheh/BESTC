import time
import random

# =========================
# CONFIG
# =========================

SCAN_INTERVAL = 0.1          # seconds between scans
BASELINE_SAMPLES = 50        # how many samples to build baseline
DIP_THRESHOLD = 0.003        # fractional drop to count as "dip start"
MIN_DIP_DURATION = 5.0       # seconds, below this = flicker
MAX_FLICKER_DEPTH = 0.005    # shallow dips more likely flicker
MAX_CLOUD_VARIANCE = 0.0008  # how "messy" a dip can be before it's a cloud
MIN_PLANET_DEPTH = 0.005     # minimum depth for a "real" transit candidate

# =========================
# MOCK BRIGHTNESS SOURCE
# =========================

def get_brightness():
    """
    Replace this with your real brightness sampling.
    For now: returns ~1.0 with tiny noise.
    """
    base = 1.0
    noise = random.uniform(-0.0005, 0.0005)
    return base + noise

# =========================
# DIP DATA STRUCTURE
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
        if not self.samples:
            return 0.0
        return max(self.depths)

    @property
    def variance(self):
        if not self.samples:
            return 0.0
        vals = self.depths
        mean = sum(vals) / len(vals)
        return sum((v - mean) ** 2 for v in vals) / len(vals)

# =========================
# CLASSIFICATION
# =========================

def classify_dip(dip: DipEvent):
    """
    Returns: "planet", "cloud", or "flicker"
    based on duration, depth, and variance.
    """
    dur = dip.duration
    depth = dip.max_depth
    var = dip.variance

    # Very short + shallow → flicker
    if dur < MIN_DIP_DURATION or depth < MAX_FLICKER_DEPTH:
        return "flicker"

    # Deep enough to be interesting
    if depth >= MIN_PLANET_DEPTH:
        # Smooth → planet
        if var <= MAX_CLOUD_VARIANCE:
            return "planet"
        # Messy → cloud
        else:
            return "cloud"

    # Default: cloud / junk
    return "cloud"

# =========================
# BETSC REACTIONS
# =========================

def betsc_on_dip_start():
    print("BETSC: I THINK I SEE SOMETHING!! HOLD ON—HOLD ON—HOLD ON—")

def betsc_on_planet(dip: DipEvent):
    print("BETSC: YES!! YES!! IT’S REAL!! I KNEW IT!!")
    print(f"BETSC: Transit complete! Duration: {dip.duration:.1f}s, depth: {dip.max_depth:.5f}")
    print("BETSC: Logging this IMMEDIATELY before I explode.")

def betsc_on_cloud(dip: DipEvent):
    print("BETSC: Wow, that’s a big exopla— oh no wait it’s a stupid cloud.")
    print("BETSC: Clouds are my mortal enemy. I was ROOTING for that dip.")

def betsc_on_flicker(dip: DipEvent):
    print("BETSC: That dip was… microscopic.")
    print("BETSC: Star flicker. Fake. Fraud. I’m moving on.")

def betsc_idle_line():
    # Optional: little flavour while scanning
    if random.random() < 0.02:
        print("BETSC: Scanning… I love exoplanets more than oxyge—")
        # You can cut to grave in your visual layer :)

# =========================
# LOGGING HOOKS
# =========================

def log_discovery(dip: DipEvent, classification: str):
    """
    Replace this with your real logging system.
    """
    print(f"[LOG] Dip classified as {classification.upper()}: "
          f"duration={dip.duration:.2f}s, depth={dip.max_depth:.5f}, variance={dip.variance:.6f}")

# =========================
# MAIN SCAN LOOP
# =========================

def run_betsc():
    print("BETSC: Initialising BEST— I mean BETS— I mean… I’m the BEST, okay?")
    print("BETSC: Building baseline brightness…")

    # Build baseline
    baseline_samples = []
    for _ in range(BASELINE_SAMPLES):
        b = get_brightness()
        baseline_samples.append(b)
        time.sleep(SCAN_INTERVAL)

    baseline = sum(baseline_samples) / len(baseline_samples)
    print(f"BETSC: Baseline locked at {baseline:.5f}. Time to hunt some planets!")

    current_dip = None

    while True:
        t = time.time()
        brightness = get_brightness()
        delta = baseline - brightness  # positive if brightness dropped

        # No active dip yet
        if current_dip is None:
            # Check for dip start
            if delta >= DIP_THRESHOLD:
                current_dip = DipEvent(start_time=t, baseline=baseline)
                current_dip.add_sample(t, brightness)
                betsc_on_dip_start()
            else:
                betsc_idle_line()
        else:
            # We are inside a dip: keep tracking
            current_dip.add_sample(t, brightness)

            # Check if dip has ended (brightness back near baseline)
            if abs(brightness - baseline) < DIP_THRESHOLD / 2:
                current_dip.end_time = t

                # Classify
                classification = classify_dip(current_dip)
                log_discovery(current_dip, classification)

                if classification == "planet":
                    betsc_on_planet(current_dip)
                elif classification == "cloud":
                    betsc_on_cloud(current_dip)
                else:
                    betsc_on_flicker(current_dip)

                # Reset for next dip
                current_dip = None

        time.sleep(SCAN_INTERVAL)

# =========================
# ENTRY POINT
# =========================

if __name__ == "__main__":
    run_betsc()
