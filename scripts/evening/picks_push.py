#!/usr/bin/env python3
"""저녁판 AI 요약 층 게시 — 게시 전용 폴더에서 data/digest_picks.json 하나만 main에 올린다 (2026-10-09, PC에서만 돈다).

evening_llm.py가 부른다. 여기에는 원문도 모델 호출도 없다 — git · gh와, 올리기 전에 한 번 더 보는 검사뿐이다.
게시 전용 폴더(--repo-dir)는 이 일만 하는 저장소 작업 폴더다: 늘 origin/main의 끝에 가지 없이(detached) 서 있고, 사람이 그 안에서
작업하지 않는다. 작업 중인 폴더를 잘못 줘도 남의 변경을 버리지 않는다 — 요약 파일 말고 바뀐 것이 있으면 아무것도 하지 않고 멈춘다.

  switch    켜는 스위치를 읽는다: gh variable list --json name,value 에서 EVENING_ENABLED가 true인가. 읽지 못하면 Stop("switch") — 닫는 쪽으로.
  sync      작업 폴더를 origin/main의 끝으로: (앞 실행이 남긴 요약 파일만 되돌리고 — 커밋 직전에 끊겨 스테이징만 된 것도 그 한 경로만 풀어서)
            → git fetch origin main → git checkout --detach origin/main
  publish   바뀐 것이 요약 파일 한 줄뿐인지(git status --porcelain) → 파일을 다시 검증(형식 · 꼴 · 금지 낱말 · 다시 쓴 바이트와 같은가 ·
            판 날짜) → 공개 전 검사(scripts/check_blind.py — 통과해야 커밋한다. 걸린 글자가 저장소 기록에 남지 않게) → 작업 폴더가
            origin/main의 끝에 있는지(아니면 커밋을 남기지 않고 멈춘다) → 커밋(실패하면 스테이징을 푼다) → origin/main..HEAD가 커밋 1개이고
            그 커밋이 바꾼 파일이 그 하나인지 → push(인증은 gh 로그인을 빌린다).
            push가 거절됐고 그사이 main이 움직였으면 한 번만 다시: 문장을 다시 만들지 않고 같은 바이트를 새 main 위에 커밋한다 — 다만
            새 main의 판을 다시 본다(_fits): 판 날짜가 같고, 내린 판이 아니고, 숨김에 걸리지 않고, 문장이 모두 그 판의 항목에 화면 규칙대로
            붙을 때만. 아니면 올리지 않고 Stop("moved") — 그사이 내린 판 위에 문장이 다시 올라가지 않게(다음 실행이 새 판으로 다시 만든다).
            push하면 기존 daily.yml(push 실행)이 검사하고 배포한다.
  dispatch  gh workflow run evening.yml --ref main으로 규칙판 실행을 시작하고 끝나기를 기다린다(dispatch_poll_s초마다, dispatch_wait_s초까지).
            GitHub의 예약 실행은 몇 시간씩 늦지만 수동 실행은 늦지 않는다 — 같은 판 날짜면 같은 창에서 다시 계산하므로 겹쳐도 된다.
            언제 시작해도 되는지는 부르는 쪽(evening_llm.due)이 가른다.
멈추는 사유는 Stop(코드)로만 알린다 — 메시지에 경로 · 출력 · 글자를 싣지 않는다(코드는 evening_llm의 로그에 그대로 찍힌다):
  switch 스위치를 읽지 못했다 · dirty 요약 파일 말고 바뀐 것이 있다 · status · fetch · detach · git(실행 자체가 안 됨) ·
  scope 올릴 것에 다른 파일이 섞였다 · file 요약 파일이 검증에 걸렸다 · blind 공개 전 검사에 걸렸거나 검사할 수 없다 ·
  head 작업 폴더가 origin/main의 끝이 아니다 · commit · commits 커밋이 1개가 아니거나 다른 파일이 들었다 ·
  moved 다시 올리려는 사이 판이 내려갔거나 달라졌다 · push
"""
import json
import os
import subprocess
import sys
import time

import digest_picks as K
import digest_schema as S

TH = S.TH
PATH = "data/" + K.FILE
WORKFLOW = "evening.yml"
MESSAGE = "data: {date} 저녁판 AI 요약"
# 인증은 gh 로그인을 빌린다 — 앞의 빈 값이 다른 credential helper(저장된 토큰)를 지운다. 토큰을 파일에 두지 않는다
PUSH = ("-c", "credential.helper=", "-c", "credential.helper=!gh auth git-credential", "push", "origin", "HEAD:main")
STATUS = ("-c", "core.quotePath=false", "status", "--porcelain", "--untracked-files=all")
CHANGED = (f" M {PATH}", f"?? {PATH}")                 # 고쳐진 파일 · 처음 생긴 파일 — 올릴 수 있는 변경은 이 한 줄뿐이다
STAGED = tuple(f"{xy} {PATH}" for xy in ("A ", "M ", "AM", "MM"))     # 앞 실행이 커밋 직전에 끊겨 스테이징만 된 요약 파일 — sync가 푼다
UNSTAGE = ("reset", "--quiet", "--", PATH)             # 그 한 경로의 스테이징만 푼다(파일과 커밋은 건드리지 않는다)
SWITCH = "EVENING_ENABLED"                             # 켜는 스위치 — 저장소 변수(evening.yml이 보는 것과 같은 것)
NO_HOLD = {"schema": S.SCHEMA, "withdraw": False, "hide_ids": [], "hide_channels": []}
GIT_S, CHECK_S, GH_S = 120, 600, 60                    # 명령 하나의 시간 제한(초)


class Stop(Exception):
    """게시를 멈춘 사유 — 코드만 들고 다닌다."""

    def __init__(self, code):
        super().__init__(code)
        self.code = code


def _call(run, cmd, repo, limit):
    """명령 하나 → (종료코드, 출력). 실행 자체가 안 되면(없는 프로그램 · 시간 초과) (None, "")."""
    try:
        r = run(list(cmd), cwd=repo, capture_output=True, timeout=limit)
    except (OSError, subprocess.SubprocessError):
        return None, ""
    return r.returncode, (r.stdout or b"").decode("utf-8", "replace")


def _git(run, repo, code, *args):
    """git 명령 하나 → 출력. 실패하면 Stop(code), git을 부르지도 못했으면 Stop("git")."""
    rc, out = _call(run, ("git", *args), repo, GIT_S)
    if rc is None:
        raise Stop("git")
    if rc != 0:
        raise Stop(code)
    return out


def _lines(run, repo):
    return [x for x in _git(run, repo, "status", *STATUS).split("\n") if x]


def _undo(run, repo, line):
    """요약 파일의 변경을 되돌린다 — 고쳐진 것이면 HEAD의 것으로, 처음 생긴 것이면 지운다."""
    if line.startswith("??"):
        os.remove(os.path.join(repo, *PATH.split("/")))
    else:
        _git(run, repo, "status", "checkout", "--quiet", "--", PATH)


def sync(repo, run=subprocess.run):
    """작업 폴더를 origin/main의 끝으로 옮긴다. 요약 파일 말고 바뀐 것이 있으면 Stop("dirty") — 아무것도 버리지 않는다."""
    lines = _lines(run, repo)
    if any(x not in CHANGED + STAGED for x in lines):
        raise Stop("dirty")
    if any(x in STAGED for x in lines):                # 커밋 직전에 끊긴 실행의 잔재 — 스테이징을 풀면 아래의 두 꼴 가운데 하나가 된다
        _git(run, repo, "status", *UNSTAGE)
        lines = _lines(run, repo)
        if any(x not in CHANGED for x in lines):
            raise Stop("dirty")
    for x in lines:                                    # 앞 실행이 올리지 못하고 남긴 요약 파일
        _undo(run, repo, x)
    _git(run, repo, "fetch", "fetch", "--quiet", "origin", "main")
    _git(run, repo, "detach", "checkout", "--quiet", "--detach", "origin/main")


def _only_picks(run, repo):
    """바뀐 것이 요약 파일 한 줄뿐인가 → 그 줄(바뀐 것이 없으면 None). 다른 것이 섞였으면 Stop("scope")."""
    lines = _lines(run, repo)
    if not lines:
        return None
    if len(lines) != 1 or lines[0] not in CHANGED:
        raise Stop("scope")
    return lines[0]


def _checked(repo, date):
    """올릴 파일을 다시 검증한다 → 그 바이트. 형식 · 꼴 · 금지 낱말 · 읽힌 글의 채널 · 판 날짜 · 다시 쓴 바이트와 같은가."""
    path = os.path.join(repo, *PATH.split("/"))
    try:
        with open(path, "rb") as f:
            raw = f.read()
        sources = S.validate_sources(S.read_json(os.path.join(repo, "data", "sources.json")))
        doc = K.validate_picks(json.loads(raw.decode("utf-8")), sources)
    except (OSError, ValueError, TypeError, KeyError, AttributeError, RecursionError):
        raise Stop("file") from None
    if doc["date"] != date or S.dump(doc).encode("utf-8") != raw:
        raise Stop("file")
    return raw


def _commit(run, repo, date):
    """요약 파일만 커밋하고, 올릴 것이 그 커밋 하나 · 그 파일 하나인지 다시 본다. 커밋하지 못했으면 스테이징을 풀고 멈춘다
    (스테이징된 채 남으면 다음 실행부터 모두 dirty로 막힌다)."""
    try:
        _git(run, repo, "commit", "add", "--", PATH)
        _git(run, repo, "commit", "commit", "--quiet", "-m", MESSAGE.format(date=date), "--", PATH)
    except Stop:
        _call(run, ("git", *UNSTAGE), repo, GIT_S)
        raise
    count = _git(run, repo, "commits", "rev-list", "--count", "origin/main..HEAD").strip()
    names = _git(run, repo, "commits", "-c", "core.quotePath=false", "diff", "--name-only", "origin/main", "HEAD").split("\n")
    if count != "1" or [n for n in names if n] != [PATH]:
        raise Stop("commits")


def _push(run, repo):
    rc, _ = _call(run, ("git", *PUSH), repo, GIT_S)
    return rc == 0


def _fits(repo, date):
    """작업 폴더(방금 옮긴 새 main)의 판에 이 요약 파일을 올려도 되는가 — 판 날짜가 같고, 내린 판이 아니고, 숨긴 항목 · 채널에 걸리지
    않고, 문장이 모두 그 판의 항목에 화면 규칙(attach)대로 붙는다. 하나라도 어긋나거나 자료를 읽을 수 없으면 거짓."""
    data = os.path.join(repo, "data")
    try:
        sources = S.validate_sources(S.read_json(os.path.join(data, "sources.json")))
        digest = S.validate_digest(S.read_json(os.path.join(data, "digest.json")), sources)
        hold = S.validate_overrides(S.read_json(os.path.join(data, "digest_overrides.json"), NO_HOLD))
        doc = K.validate_picks(S.read_json(os.path.join(data, K.FILE)), sources)
    except (OSError, ValueError, TypeError, KeyError, AttributeError, RecursionError):
        return False
    if digest["date"] != date or digest["status"] == "withdrawn" or hold["withdraw"]:
        return False
    keys = {p["key"] for p in doc["items"]}
    hidden = any(x["id"] in hold["hide_ids"] for x in K.items_of(digest) if x["key"] in keys) \
        or any(ch in hold["hide_channels"] for p in doc["items"] for ch, _ in p["src"])
    return not hidden and set(K.attach(digest, doc, sources)) == keys


def switch(repo, run=subprocess.run):
    """켜는 스위치(저장소 변수 EVENING_ENABLED)를 읽는다 → "on"(값이 true) · "off"(그 밖의 값 · 변수가 없다). 읽지 못하면
    Stop("switch") — 닫는 쪽으로: 꺼져 있을지 모르는 날에는 규칙판 실행도, 채널 읽기도, 모델 호출도 하지 않는다."""
    rc, out = _call(run, ("gh", "variable", "list", "--json", "name,value"), repo, GH_S)
    try:
        rows = json.loads(out) if rc == 0 else None
    except ValueError:
        rows = None
    if type(rows) is not list or any(type(r) is not dict for r in rows):
        raise Stop("switch")
    return "on" if any(r.get("name") == SWITCH and r.get("value") == "true" for r in rows) else "off"


def publish(repo, date, run=subprocess.run, python=sys.executable):
    """작업 폴더의 요약 파일을 main에 올린다 → "pushed" · "same"(바뀐 것이 없다). 올리지 않고 멈출 때는 Stop(코드)."""
    line = _only_picks(run, repo)
    if line is None:
        return "same"
    raw = _checked(repo, date)
    rc, _ = _call(run, (python, "-X", "utf8", os.path.join("scripts", "check_blind.py")), repo, CHECK_S)
    if rc != 0:                                        # 걸렸거나(1) 검사할 수 없거나(2 — 검사어 없음 등). 어느 쪽도 통과가 아니다
        _undo(run, repo, line)
        raise Stop("blind")
    here = _git(run, repo, "commits", "rev-parse", "HEAD", "origin/main").split()
    if len(here) != 2 or here[0] != here[1]:           # 가지 위나 올리지 않은 커밋 위에서 불렸다 — 거기에 커밋을 남기지 않는다(run은 늘 sync 뒤다)
        _undo(run, repo, line)
        raise Stop("head")
    base = here[1]
    _commit(run, repo, date)
    if _push(run, repo):
        return "pushed"
    _git(run, repo, "fetch", "fetch", "--quiet", "origin", "main")
    if _git(run, repo, "commits", "rev-parse", "origin/main").strip() == base:
        raise Stop("push")                             # main은 그대로인데 거절됐다(인증 · 훅 · 네트워크) — 다시 해도 같다
    _git(run, repo, "detach", "checkout", "--quiet", "--detach", "origin/main")       # 방금 커밋은 두고 새 main의 끝으로
    with open(os.path.join(repo, *PATH.split("/")), "wb") as f:
        f.write(raw)                                   # 다시 만들지 않는다 — 같은 바이트를 새 main 위에
    again = _only_picks(run, repo)
    if again is None:
        return "same"
    if not _fits(repo, date):                          # 그사이 판이 내려갔거나 다시 계산됐다 — 옛 판의 문장을 새 main에 올리지 않는다
        _undo(run, repo, again)
        raise Stop("moved")
    _commit(run, repo, date)
    if _push(run, repo):
        return "pushed"
    raise Stop("push")


# ---------- 규칙판 실행을 시작하고 기다리기 ----------

def _runs(run, repo):
    """수동으로 시작한 저녁 실행들(최근 5개) → [{databaseId, status, conclusion}]. 못 읽으면 None."""
    rc, out = _call(run, ("gh", "run", "list", "--workflow", WORKFLOW, "--event", "workflow_dispatch", "--branch", "main",
                          "--limit", "5", "--json", "databaseId,status,conclusion"), repo, GH_S)
    try:
        rows = json.loads(out) if rc == 0 else None
    except ValueError:
        return None
    ok = type(rows) is list and all(type(r) is dict and type(r.get("databaseId")) is int for r in rows)
    return rows if ok else None


def dispatch(repo, run=subprocess.run, sleep=time.sleep, clock=time.monotonic):
    """규칙판 실행을 시작하고 끝나기를 기다린다 → "ok" · "failed"(실행이 실패로 끝남) · "timeout" · "error"(시작하지 못함).
    어느 쪽이든 부른 쪽은 이미 올라와 있는 판으로 계속한다. 우리 실행 = 시작하기 전에 본 것보다 번호가 큰 것 가운데 가장 먼저 생긴 것."""
    before = _runs(run, repo)
    if before is None:
        return "error"
    last = max((r["databaseId"] for r in before), default=0)
    rc, _ = _call(run, ("gh", "workflow", "run", WORKFLOW, "--ref", "main"), repo, GH_S)
    if rc != 0:
        return "error"
    t0 = clock()
    while clock() - t0 < TH["dispatch_wait_s"]:
        sleep(TH["dispatch_poll_s"])
        mine = sorted((r for r in _runs(run, repo) or [] if r["databaseId"] > last), key=lambda r: r["databaseId"])
        if mine and mine[0].get("status") == "completed":
            return "ok" if mine[0].get("conclusion") == "success" else "failed"
    return "timeout"
