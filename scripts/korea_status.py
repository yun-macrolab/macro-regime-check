"""Record collector start/end separately so a timeout cannot leave an old green status."""
import argparse
import datetime as dt
import json
import os
from pathlib import Path

from korea_market import UTC, atomic_json
from write_status import run_url

FEEDS = {"credit", "money", "rates", "foreign3", "foreign10", "calendar", "auctions", "offerings"}


def read(path):
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except (OSError, ValueError):
        return {}


def timestamp(value):
    try:
        date = dt.datetime.fromisoformat(value)
        return date if date.tzinfo is not None else None
    except (TypeError, ValueError):
        return None


def update(out, state, now=None, env=None):
    out = Path(out); out.mkdir(parents=True, exist_ok=True)
    now = (now or dt.datetime.now(UTC)).astimezone(UTC).replace(microsecond=0)
    env = os.environ if env is None else env
    path = out/"korea-status.json"; prev = read(path)
    start = now if state == "started" else timestamp(prev.get("started_at"))
    ok = False
    if state == "success":
        data = read(out/"korea.json"); checked = timestamp(data.get("checked_at"))
        feeds = data.get("feeds")
        ok = bool(prev.get("state") == "running" and data.get("schema") == 1 and
                  start and checked and start <= checked <= now and isinstance(feeds, dict) and
                  FEEDS.issubset(feeds) and all(isinstance(feeds[k], dict) and feeds[k].get("ok") is True for k in FEEDS))
    last = now if ok else timestamp(prev.get("last_success"))
    result = {"schema": 1, "state": "running" if state == "started" else "success" if ok else "failure",
              "ok": ok, "started_at": start.isoformat() if start else None, "checked_at": now.isoformat(),
              "last_success": last.isoformat() if last else None, "run_url": run_url(env)}
    atomic_json(path, result)
    return result


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(Path(__file__).resolve().parents[1]/"data"))
    ap.add_argument("--state", required=True, choices=["started", "success", "failure", "cancelled", "skipped"])
    args = ap.parse_args()
    try:
        result = update(args.out, args.state)
        if os.environ.get("GITHUB_OUTPUT"):
            with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as f:
                f.write("ok=" + str(result["ok"]).lower() + "\n")
        print("[korea_status] " + result["state"])
        return 0
    except Exception as exc:
        print(f"[korea_status] status not replaced: {type(exc).__name__}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
