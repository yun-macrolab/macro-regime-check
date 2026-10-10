"""저녁 묶음에도 화면 폴더 검사를 싣는 얇은 문 — 저녁 배포도 site/를 통째로 싣는다. 검사 본체는 scripts/ 바로 아래에 있다.

실행:  python -m unittest discover -s scripts/evening   (저장소 루트에서)
"""
import os
import sys
import unittest

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))    # 뒤에 붙인다 — 저녁 쪽 모듈 이름을 가리지 않게
from test_site_origin import *   # noqa: E402,F401,F403 — TestCase를 이 모듈 이름으로 다시 실어 discover가 줍게 한다

if __name__ == "__main__":
    unittest.main()
