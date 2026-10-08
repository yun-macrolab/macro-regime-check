#!/usr/bin/env python3
"""저녁판 실행 묶음 — 수집 잡의 다섯 단계를 차례로 돌리고(pipeline), 22:41 감시가 main과 공개 페이지를 견준다(watch) (2026-10-08).

evening.yml과 PC의 시범 실행이 같은 순서·같은 판단을 쓰게 하려는 얇은 묶음이다. 규칙은 여기에 없다 — 단계 스크립트를
계약(digest_schema.py 머리말)의 인자로 부르고 종료코드만 읽는다.

pipeline   tg_collect → digest_cluster → digest_score → digest_build → digest_check(--raw)
  - <out>에는 공개해도 되는 JSON만 생긴다(원문은 <work>에만). 시작할 때 <out>에 남은 저녁판 파일을 지운다.
    검사는 --strict로 돈다 — <out>에 저녁판 파일 말고 다른 것이 있으면 판을 내지 않는다(아티팩트로 올라가는 폴더라서).
  - 조립의 종료코드 2(수집 부족 · 0건 연속 · 채널 바뀜)와 3(형식 바뀜 — 상태만 씀)은 '게시는 하되 실행은 실패로 끝낼 것'이다.
  - 어느 단계든 실패하면(검사에 걸린 판 포함) <out>을 비우고, 판 없이 '실행 실패' 상태만 만들어 그것을 게시하게 한다
    (digest_build --error → digest_check). 화면은 직전 판과 실패 표시를 보여 준다. 그것마저 안 되면 종료코드 1.
  - 결과는 한 줄로 찍고, --github-output을 주면 그 파일에도 쓴다:
      publish  true면 <out>을 게시한다          alert  true면 워크플로가 마지막에 실행을 실패로 끝낸다(메일)
      reason   ok · short · empty_streak · broken · withdrawn · channel(채널 바뀜) · error      stage  done 또는 실패한 단계
  종료코드: 0 <out>에 게시할 것이 있다(publish=true) / 1 없다

watch      수집하지 않는다(텔레그램 요청 0회). main의 data/digest_status.json이 오늘 판을 낸 상태인지 보고,
           공개 페이지의 같은 파일과 견준다 — 요청은 공개 페이지에 한 번뿐이다.
  - main에 오늘 판이 없으면 missing=true, 종료코드 1(실행을 실패로 끝낸다).
  - main에는 있는데 페이지가 다르거나 읽히지 않으면 redeploy=true(배포만 다시), 같으면 false. 종료코드 0.

출력은 공개 Actions 로그에 남는다 — 정해 둔 낱말(true·false·사유·단계 이름)만 찍는다.
사용법: python scripts/evening/evening_run.py pipeline [--work .work/evening] [--out 폴더] [--data data] [--replay] [--now ISO]
        python scripts/evening/evening_run.py watch --page-url https://<소유자>.github.io/<저장소> [--data data] [--now ISO]
"""
import argparse
import datetime
import json
import os
import subprocess
import sys
import urllib.parse
import urllib.request

import digest_check as C
import digest_schema as S

HERE = os.path.dirname(os.path.abspath(__file__))
REASONS = (*S.REASONS, "channel")           # channel = 판은 정상인데 조립이 채널 바뀜으로 실패를 알린 날
STAGES = ("collect", "cluster", "score", "build", "check", "done")
SAME = ("edition", "checked_at", "published")       # 페이지와 main의 상태 파일에서 견주는 칸
TIMEOUT = 20
MAX_BYTES = 200_000


def _emit(path, name, **facts):
    """결과 한 줄. 값은 참·거짓과 정해 둔 낱말뿐이다 — 그 밖의 것이 오면 멈춘다(출력 파일에 다른 줄이 끼어들지 않게)."""
    words = {}
    for k, v in facts.items():
        if type(v) is not bool and v not in REASONS + STAGES:
            raise ValueError("정해 두지 않은 출력 값")
        words[k] = str(v).lower() if type(v) is bool else v
    print(f"[evening_run] {name} " + " ".join(f"{k}={v}" for k, v in words.items()))
    if path:
        with open(path, "a", encoding="utf-8") as f:
            f.write("".join(f"{k}={v}\n" for k, v in words.items()))


# ---------- pipeline ----------

def _commands(a):
    """(단계 이름, 스크립트, 인자) — 계약의 CLI 그대로."""
    src, state = os.path.join(a.data, "sources.json"), os.path.join(a.data, "digest_state.json")
    collect = ["--sources", src, "--state", state, "--work", a.work] + (["--replay"] if a.replay else []) + _now(a)
    return (("collect", "tg_collect.py", collect),
            ("cluster", "digest_cluster.py", ["--work", a.work]),
            ("score", "digest_score.py", ["--work", a.work, "--calendar", os.path.join(a.data, "calendar.json"),
                                          "--korea", os.path.join(a.data, "korea.json"), "--state", state]),
            ("build", "digest_build.py", ["--work", a.work, "--out", a.out, "--data", a.data]),
            ("check", "digest_check.py", ["--public", a.out, "--raw", a.work, "--sources", src, "--strict"]))


def _now(a):
    return ["--now", a.now] if a.now else []


def _call(script, args, run):
    return run([sys.executable, "-X", "utf8", os.path.join(HERE, script), *args]).returncode


def _clear(out):
    """<out>의 저녁판 파일만 지운다(다른 것은 두고, 폴더가 없으면 아무것도 하지 않는다)."""
    for name in S.PUBLIC_FILES:
        if os.path.isfile(os.path.join(out, name)):
            os.remove(os.path.join(out, name))
    sub = os.path.join(out, "digest")
    for n in sorted(os.listdir(sub)) if os.path.isdir(sub) else []:
        if C.DAY_FILE.fullmatch(n):
            os.remove(os.path.join(sub, n))


def _reason(out, alert):
    """게시할 상태 파일의 사유. 판은 정상(ok)인데 조립이 실패를 알렸으면 채널 바뀜이다."""
    reason = S.validate_status(S.read_json(os.path.join(out, "digest_status.json")))["reason"]
    return "channel" if alert and reason == "ok" else reason


def _fallback(a, run, stage):
    """어느 단계가 실패한 날 — 반쯤 만든 것을 지우고 '실행 실패' 상태만 만들어 검사한다. 그것도 안 되면 게시할 것이 없다."""
    _clear(a.out)
    ok = _call("digest_build.py", ["--error", "--work", a.work, "--out", a.out, "--data", a.data] + _now(a), run) == 0 \
        and _call("digest_check.py", ["--public", a.out, "--sources", os.path.join(a.data, "sources.json"), "--strict"], run) == 0
    if not ok:
        _clear(a.out)
    _emit(a.github_output, "pipeline", publish=ok, alert=True, reason="error", stage=stage)
    return 0 if ok else 1


def pipeline(a, run=subprocess.run):
    if os.path.abspath(a.out) == os.path.abspath(a.data):
        raise ValueError("--out은 data 폴더와 달라야 한다(data/로 옮기는 일은 digest_publish가 한다)")
    _clear(a.out)
    alert = False
    for stage, script, args in _commands(a):
        code = _call(script, args, run)
        if stage == "build" and code in (2, 3):
            alert = True                         # 게시는 하되 실행은 실패로 끝낼 것
        elif code != 0:
            return _fallback(a, run, stage)
    _emit(a.github_output, "pipeline", publish=True, alert=alert, reason=_reason(a.out, alert), stage="done")
    return 0


# ---------- watch ----------

def _status(doc):
    """상태 파일의 자료 — 계약의 형식이 아니면 None."""
    try:
        return S.validate_status(doc)
    except ValueError:
        return None


def _page_address(page_url, stamp):
    """공개 페이지의 상태 파일 주소. 페이지 주소는 꾸밈없는 https여야 한다(설정이 틀리면 조용히 넘기지 않고 멈춘다)."""
    u = urllib.parse.urlsplit(page_url)
    if u.scheme != "https" or not u.hostname or u.username or u.password or u.query or u.fragment:
        raise ValueError("공개 페이지 주소 꼴이 아님")
    return f"{page_url.rstrip('/')}/data/digest_status.json?t={stamp}"       # 꼬리표는 CDN의 묵은 사본을 피하려는 것


def _fetch(url, opener=None):
    """공개 페이지의 상태 파일 — 못 받거나 못 읽으면 None(그때는 다시 배포한다)."""
    try:
        with (opener or urllib.request.urlopen)(url, timeout=TIMEOUT) as r:
            raw = r.read(MAX_BYTES + 1)
        return json.loads(raw.decode("utf-8")) if len(raw) <= MAX_BYTES else None
    except (OSError, ValueError):
        return None


def watch(a, opener=None):
    now = S.parse_iso(a.now) if a.now else datetime.datetime.now(S.KST)
    url = _page_address(a.page_url, int(now.timestamp()))
    main_st = _status(S.read_json(os.path.join(a.data, "digest_status.json"), None))
    if not (main_st and main_st["edition"] == S.edition_date(now) and main_st["published"]):
        _emit(a.github_output, "watch", redeploy=False, missing=True)
        return 1
    page = _status(_fetch(url, opener))
    same = page is not None and all(page[k] == main_st[k] for k in SAME)
    _emit(a.github_output, "watch", redeploy=not same, missing=False)
    return 0


def main(argv=None, run=subprocess.run, opener=None):
    ap = argparse.ArgumentParser(description="저녁판 실행 묶음 — pipeline(수집 잡의 다섯 단계) · watch(22:41 감시)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("pipeline", help="수집 → 묶기 → 점수 → 조립 → 검사")
    p.add_argument("--work", default=S.WORK, help="작업 폴더 — 원문은 여기에만 (기본: .work/evening, git 제외)")
    p.add_argument("--out", default=os.path.join(S.WORK, "public"),
                   help="공개해도 되는 JSON만 쓰는 폴더 (기본: .work/evening/public — 워크플로는 아티팩트로 올릴 _evening을 준다)")
    p.add_argument("--replay", action="store_true", help="네트워크 없이 <work>/pages/의 저장분으로 (tg_collect --replay)")
    w = sub.add_parser("watch", help="main과 공개 페이지의 판 견주기")
    w.add_argument("--page-url", required=True, help="공개 페이지 주소 (https://<소유자>.github.io/<저장소>)")
    for x in (p, w):
        x.add_argument("--data", default=S.DATA, help="저장소의 data/ 폴더")
        x.add_argument("--now", default=None, help="실행 시각(ISO +09:00, 기본: 지금)")
        x.add_argument("--github-output", default=None, help="결과를 덧붙여 쓸 파일(Actions의 $GITHUB_OUTPUT)")
    a = ap.parse_args(argv)
    return pipeline(a, run) if a.cmd == "pipeline" else watch(a, opener)


if __name__ == "__main__":
    sys.exit(S.run_cli("evening_run", main))
