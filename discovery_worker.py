"""Independent MED Discovery scheduling worker."""
import json
import os
import sys
import time
from discovery import discover

def interval_hours():
    raw = os.environ.get("MED_DISCOVERY_INTERVAL_HOURS", "24")
    hours = int(raw)
    if not 1 <= hours <= 168:
        raise ValueError("MED_DISCOVERY_INTERVAL_HOURS must be between 1 and 168")
    return hours

def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1 or argv[0] not in ("once", "serve"):
        print("Usage: python discovery_worker.py once|serve", file=sys.stderr)
        return 2
    while True:
        rows = discover()
        print(json.dumps(rows, ensure_ascii=False), flush=True)
        if argv[0] == "once":
            return 1 if any(row["status"] != "ok" for row in rows) else 0
        time.sleep(interval_hours() * 3600)

if __name__ == "__main__":
    raise SystemExit(main())
