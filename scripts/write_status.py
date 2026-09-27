#!/usr/bin/env python3
"""갱신 상태 기록 — data/status.json. 사이트 첫 화면의 '마지막 성공 시각'과 실패 배너가 이 파일을 읽는다.

실행:  python scripts/write_status.py --fetch <결과> --render <결과> [--out data]
  <결과>는 GitHub Actions 단계 결과(steps.<id>.outcome): success / failure / cancelled / skipped.
실패한 날에도 쓴다 — 공개본(public.json)은 직전 것이 남고 상태만 실패로 바뀐다.
  마지막 성공 시각(last_success)과 공개본 날짜(data_date)는 직전 값을 지킨다.
문구는 MESSAGES의 것만 — 오류 원문(경로·URL·예외 문자열)은 공개 페이지에 싣지 않는다. 원인은 run_url의 실행 로그에서.
종료코드: 0 기록함(실패를 기록한 경우 포함) / 1 기록 못 함.
"""
import argparse, datetime, json, os, re, sys

SCHEMA = 1
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_OUT = os.path.join(REPO, "data")
MESSAGES = {
    "ok": "정상 갱신",
    "fetch": "자료 수신 실패 — 직전 공개본을 유지한다",
    "render": "공개본 생성 실패 — 직전 공개본을 유지한다",
}
KEYS = ("schema", "checked_at", "ok", "stage", "message", "data_date", "last_success", "run_url")
DATE_RE = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")
TS_RE = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}\+00:00")
REPO_RE = re.compile(r"[A-Za-z0-9-]+/[A-Za-z0-9._-]+")
RUN_ID_RE = re.compile(r"[0-9]+")


def _read_json(path):
    try:
        with open(path, encoding="utf-8") as f:
            js = json.load(f)
    except (OSError, ValueError):
        return {}
    return js if isinstance(js, dict) else {}


def _match(regex, value):
    return value if isinstance(value, str) and regex.fullmatch(value) else None


def run_url(env):
    """GitHub Actions 실행 로그 주소 — 환경 변수가 형식에 맞을 때만."""
    server = env.get("GITHUB_SERVER_URL")
    repo, run_id = env.get("GITHUB_REPOSITORY", ""), env.get("GITHUB_RUN_ID", "")
    if server != "https://github.com" or not REPO_RE.fullmatch(repo) or not RUN_ID_RE.fullmatch(run_id):
        return None
    return f"{server}/{repo}/actions/runs/{run_id}"


def stage_of(fetch, render, data_date):
    """어느 단계에서 멈췄나. 'success'가 아닌 결과(failure·cancelled·skipped·빈 값)는 모두 실패로 본다."""
    if fetch != "success":
        return "fetch"
    if render != "success" or data_date is None:
        return "render"
    return "ok"


def update(out, fetch, render, now=None, env=None):
    now = now or datetime.datetime.now(datetime.timezone.utc)
    env = os.environ if env is None else env
    prev = _read_json(os.path.join(out, "status.json"))
    data_date = _match(DATE_RE, _read_json(os.path.join(out, "public.json")).get("date"))
    stage = stage_of(fetch, render, data_date)
    checked = now.astimezone(datetime.timezone.utc).replace(microsecond=0).isoformat()
    st = {"schema": SCHEMA, "checked_at": checked, "ok": stage == "ok", "stage": stage,
          "message": MESSAGES[stage], "data_date": data_date,
          "last_success": checked if stage == "ok" else _match(TS_RE, prev.get("last_success")),
          "run_url": run_url(env)}
    path = os.path.join(out, "status.json")
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(st, ensure_ascii=False, indent=2) + "\n")
    os.replace(tmp, path)
    return st


def main():
    ap = argparse.ArgumentParser(description="갱신 상태를 data/status.json에 기록")
    ap.add_argument("--out", default=DEFAULT_OUT, help="공개 산출물 폴더(기본 data/)")
    ap.add_argument("--fetch", required=True, help="수집·판정 단계 결과")
    ap.add_argument("--render", required=True, help="공개본 생성 단계 결과")
    a = ap.parse_args()
    try:
        if not os.path.isdir(a.out):
            raise RuntimeError(f"출력 폴더 없음: {a.out}")
        st = update(a.out, a.fetch, a.render)
    except (OSError, RuntimeError) as e:
        print(f"[write_status] {e}", file=sys.stderr)
        return 1
    print(f"[write_status] {st['checked_at']} — {st['message']} (공개본 {st['data_date'] or '없음'})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
