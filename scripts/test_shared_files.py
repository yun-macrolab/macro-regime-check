#!/usr/bin/env python3
"""공유 파일 고정 — fred_fetch.py·regime_rules.py는 비공개 저장소에도 같은 내용으로 있다.

fred_fetch.py는 바이트까지 같고, regime_rules.py는 머리말 7행(6·7행이 저장소마다 다르다)을 뺀 8행부터 같다.
두 저장소의 이 테스트가 같은 고정값을 갖는다 — 한쪽만 고치면 그쪽 테스트가 실패한다.
고칠 때: 두 저장소의 사본을 함께 고치고, 두 저장소의 아래 상수 둘을 함께 새 값으로 바꾼다.
줄 끝은 LF로 맞춰 잰다(Windows 체크아웃의 CRLF 변환에 흔들리지 않게).

실행:  python -m unittest discover -s scripts   (저장소 루트에서) — 네트워크 불필요
"""
import os, hashlib, unittest

SCRIPTS = os.path.dirname(os.path.abspath(__file__))
FRED_FETCH_SHA256 = "ab9d9a555301a89317f49e474fd01941bf78a072ebcc0671a9009e8980345889"
REGIME_RULES_BODY_SHA256 = "bf63177017ddffb92bc5f6106512f89d1e08d82938b268025367265c2e055a5c"    # 8행부터
HEADER_LINES = 7
FIX = ("두 저장소(이 저장소 scripts/ · 비공개 저장소)의 사본을 함께 고치고, "
       "두 저장소 test_shared_files.py의 상수 둘(FRED_FETCH_SHA256 · REGIME_RULES_BODY_SHA256)을 함께 새 값으로 바꿀 것")


def digest(name, skip=0):
    """파일의 sha256(줄 끝 LF로 맞춤). skip행을 앞에서 뺀다."""
    with open(os.path.join(SCRIPTS, name), "rb") as f:
        data = f.read().replace(b"\r\n", b"\n")
    return hashlib.sha256(b"".join(data.splitlines(keepends=True)[skip:])).hexdigest()


class SharedFilesTest(unittest.TestCase):
    def test_fred_fetch_matches_shared_copy(self):
        self.assertEqual(digest("fred_fetch.py"), FRED_FETCH_SHA256,
                         f"fred_fetch.py가 공유 고정값과 다르다(바이트 동일 유지) — {FIX}")

    def test_regime_rules_body_matches_shared_copy(self):
        self.assertEqual(digest("regime_rules.py", HEADER_LINES), REGIME_RULES_BODY_SHA256,
                         f"regime_rules.py 8행부터가 공유 고정값과 다르다(머리말 7행만 저장소마다 다를 수 있다) — {FIX}")

    def test_header_is_seven_lines(self):
        # 머리말 독스트링이 7행에서 끝나야 '8행부터 같다'가 뜻이 있다 — 머리말 줄 수를 바꾸면 두 저장소를 함께
        with open(os.path.join(SCRIPTS, "regime_rules.py"), encoding="utf-8") as f:
            lines = f.read().splitlines()
        self.assertEqual(lines[HEADER_LINES], '"""', FIX)


if __name__ == "__main__":
    unittest.main(verbosity=1)
