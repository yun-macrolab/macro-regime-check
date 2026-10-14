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
    ok, failed = False, None
    if state in ("success", "failure"):
        # 수집기 종료코드는 묶음 하나만 실패해도 1이다. 이번 실행이 새 스냅샷을 썼는지는 자료로 판정한다:
        # 새 스냅샷 + 8개 묶음 모두 성공 = success, 새 스냅샷 + 일부 실패 = partial(ok는 False — 실패 묶음만 표시),
        # 새 스냅샷이 아니면(시간 초과·스냅샷 미교체) failure.
        data = read(out/"korea.json"); checked = timestamp(data.get("checked_at"))
        feeds = data.get("feeds")
        fresh = bool(prev.get("state") == "running" and data.get("schema") == 1 and
                     start and checked and start <= checked <= now and isinstance(feeds, dict) and
                     FEEDS.issubset(feeds) and all(isinstance(feeds[k], dict) for k in FEEDS))
        if fresh:
            failed = sorted(k for k in FEEDS if feeds[k].get("ok") is not True)
            ok = not failed
    last = now if ok else timestamp(prev.get("last_success"))
    final = "running" if state == "started" else "success" if ok else "partial" if failed else "failure"
    result = {"schema": 1, "state": final, "ok": ok, "started_at": start.isoformat() if start else None, "checked_at": now.isoformat(),
              "last_success": last.isoformat() if last else None, "run_url": run_url(env)}
    if failed:
        result["failed"] = failed
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
