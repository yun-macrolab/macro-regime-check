#!/usr/bin/env python3
"""저녁판 게시 — 검사를 통과한 공개 폴더를 data/로 옮긴다 (2026-10-08, 1단계 규칙 선별판).

게시 잡에서 돈다. 여기에는 원문이 없다(.work/는 수집 잡의 러너와 함께 사라졌다) — 받은 것은 아티팩트의 공개 JSON뿐이고,
그것도 믿지 않고 옮기기 전에 digest_check로 다시 검사한다(형식 · 닫힌 글자 · 다시 쓴 바이트와 같은가 · 파일끼리 맞는가).

옮기는 것은 계약의 저녁판 파일뿐이다: digest.json · digest_index.json · digest_state.json · digest_status.json · digest/<날짜>.json.
폴더에 다른 것이 있으면 검사에서 떨어지고(stray), 아침 자료(korea.json 등)와 사람이 쓰는 파일(sources.json 등)은 건드리지 않는다.
파일은 읽은 자료를 다시 써서 옮긴다(바이트 복사가 아니다 — 검사한 자료와 나가는 바이트가 같게).
  - 판을 낸 날: 목차(digest_index.json)에 없는 날짜의 digest/<날짜>.json을 지운다(35일이 지난 판, 내린 뒤의 지난 판).
  - 상태만 낸 날(형식 바뀜 · 실행 실패): digest_status.json만 옮긴다 — 직전 판은 그대로 남는다.
  - 이미 올라간 상태보다 앞선 시각의 것은 옮기지 않는다(늦게 끝난 옛 실행이 새 판을 덮지 않게).

사용법: python scripts/evening/digest_publish.py --from <폴더> --data data [--sources data/sources.json]
종료코드: 0 옮김 / 1 검사 위반이나 실패(아무것도 옮기지 않음)
"""
import argparse
import os
import sys

import digest_check as C
import digest_schema as S

LAST = "digest_status.json"                 # 화면이 가장 먼저 읽는 파일 — 마지막에 옮긴다


def _newer_than_published(src, data):
    """받은 상태가 이미 올라간 상태보다 앞선 시각이 아닌가. 올라간 것이 없거나 읽을 수 없으면 옮겨도 된다."""
    try:
        old = S.validate_status(S.read_json(os.path.join(data, LAST)))
    except (OSError, ValueError):
        return True
    new = S.read_json(os.path.join(src, LAST))
    return S.parse_iso(new["checked_at"]) >= S.parse_iso(old["checked_at"])


def _prune(data):
    """목차에 없는 날짜의 판 파일을 지운다 → 지운 수."""
    keep = {e["date"] for e in S.validate_index(S.read_json(os.path.join(data, "digest_index.json")))["editions"]}
    sub, removed = os.path.join(data, "digest"), 0
    for n in sorted(os.listdir(sub)) if os.path.isdir(sub) else []:
        if C.DAY_FILE.fullmatch(n) and n[:-5] not in keep:
            os.remove(os.path.join(sub, n))
            removed += 1
    return removed


def publish(src, data, sources):
    """검사를 통과하면 옮긴다 → (위반 수, 옮긴 파일 수, 지운 파일 수, 검사가 본 사실). 위반이 있으면 아무것도 옮기지 않는다."""
    if os.path.abspath(src) == os.path.abspath(data):
        raise ValueError("--from과 --data가 같은 폴더")
    found, facts = C.check_folder(src, sources, strict=True)       # 받은 폴더에 저녁판 파일 말고 다른 것이 있으면 옮기지 않는다
    if found:
        return len(found), 0, 0, facts
    if not _newer_than_published(src, data):
        raise ValueError("이미 올라간 상태보다 앞선 시각의 것은 옮기지 않음")
    names, _ = C.list_files(src)
    for name in sorted(names, key=lambda n: (n == LAST, not n.startswith("digest/"), n)):
        S.write_json(os.path.join(data, *name.split("/")), S.read_json(os.path.join(src, *name.split("/"))))
    removed = _prune(data) if "digest_index.json" in names else 0
    return 0, len(names), removed, facts


def main(argv=None):
    ap = argparse.ArgumentParser(description="저녁판 게시 — 검사를 통과한 공개 폴더의 저녁판 파일만 data/로 옮긴다")
    ap.add_argument("--from", dest="src", required=True, help="수집 잡이 만든 공개 폴더(아티팩트)")
    ap.add_argument("--data", default=S.DATA, help="옮길 곳 (기본: 저장소의 data/)")
    ap.add_argument("--sources", default=None, help="출처 목록 (기본: <data>/sources.json)")
    a = ap.parse_args(argv)
    src, data = os.path.abspath(a.src), os.path.abspath(a.data)
    sources = S.validate_sources(S.read_json(a.sources or os.path.join(data, "sources.json")))
    bad, files, removed, facts = publish(src, data, sources)
    if bad:
        S.report("digest_publish", violations=bad)
        return 1
    S.report("digest_publish", files=files, removed=removed, edition=facts["edition"], reason=facts["reason"])
    return 0


if __name__ == "__main__":
    sys.exit(S.run_cli("digest_publish", main))
