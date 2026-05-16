print("Initializing BETSC Systems...")
print("Loading target star catalogue...")
print("Checking data directories...")
print("All systems nominal.")
print("BETSC Is Online And Ready To Scan The Skies!")
def load_targets():
    with open("target_stars.txt") as f:
        return [line.strip() for line in f]
import random
import time

def scan_star(star):
    print(f"Scanning {star}...")
    search_time = 10  # seconds
    start = time.time()

    while time.time() - start < search_time:
        dip = random.uniform(0, 1)

        # If a planet is detected at ANY moment:
        if dip > 0.92:
            planet_name = generate_planet_name(star)
            print(f"BETSC: Transit dip detected! Possible exoplanet found around {star}!")
            print(f"BETSC: Planet Designation assigned: {planet_name}")
            print("")
            log_event(f"Detected planet {planet_name} around {star}")
            return  # stop searching immediately

        # Small delay so he feels like he's actually scanning
        time.sleep(0.3)

    # If we reach here, no planet was found in 10 seconds
    reactions = [
        "BETSC: No planets here... unless they're hiding from us.",
        "BETSC: Nothing yet. Must be shy then.",
        "BETSC: A bit too quiet, isn't it...",
        "BETSC: I scanned it practically a million times. Still nothing.",
        "BETSC: Nope. Just photons and disappointment."
    ]
    reaction = random.choice(reactions)
    print(reaction)
    print("")
    log_event(f"No planet detected around {star}")

def log_event(message):
    with open("logs/betsc.log", "a") as f:
        f.write(message + "\n")

stars = load_targets()

for star in stars:
    scan_star(star)
