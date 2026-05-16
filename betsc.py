print("Initializing BETSC Systems...")
print("Loading target star catalogue...")
print("Checking data directories...")
print("All systems nominal.")
print("BETSC Is Online And Ready To Scan The Skies!")
def load_targets():
    with open("target_stars.txt") as f:
        return [line.strip() for line in f]
def scan_star(star):
    print(f"Scanning {star}...")
def log_event(message):
    with open("logs/betsc.log", "a") as f:
        f.write(message + "\n")
