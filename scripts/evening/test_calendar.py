#!/usr/bin/env python3
"""일정표(data/calendar.json) 테스트 — 형태, 시각 순서, 항목마다 공식 출처에서 읽은 것인지.

실행:  python -m unittest discover -s scripts/evening   (저장소 루트에서)
네트워크 불필요. 일정표는 사람이 쓰는 파일이다. 계약의 calendar 형태에는 출처 칸이 없어서(공개본의 글자는 사전 낱말·날짜·시각뿐)
"어디서 읽었나"는 아래 LEDGER에 적는다. 일정을 고칠 때는 calendar.json과 LEDGER를 같이 고친다 — 어긋나면 여기서 떨어진다.
  - 공식 출처의 일정 쪽에서 직접 읽은 날짜만 넣는다. 읽지 못한 것은 넣지 않는다(기억으로 채우지 않는다).
  - 날짜·시각은 KST. 미국 발표는 현지 시각(미 동부)을 같이 적고, zoneinfo로 바꾼 값이 적어 둔 KST와 같은지 본다
    (서머타임이 2026-11-01에 끝나 그 뒤로는 한 시간 늦다). 시각이 없는 줄은 출처가 날짜만 밝힌 것이다.
  - 아직 없는 것: 미 CPI · 미 고용 — 2026-10-08에 bls.gov가 자동 요청을 막아(403) 읽지 못했다. 읽으면 SRC에 bls를 보탠다.
"""
import datetime
import os
import sys
import unittest
import urllib.parse
import zoneinfo

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import digest_schema as S

CHECKED = "2026-10-08"                           # 아래 출처를 읽은 날 = calendar.json의 updated
OFFICIAL = ("federalreserve.gov", "bls.gov", "bea.gov", "bok.or.kr", "kostat.go.kr", "mods.go.kr")
SRC = {
    "fed": "https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm",       # 회의 날짜. 성명 14:00(미 동부)은 같은 곳의 행사 달력
    "bea": "https://www.bea.gov/news/schedule",                                     # 개인소득·지출(PCE 물가가 여기 실린다)
    "bok_mpc": "https://www.bok.or.kr/portal/singl/crncyPolicyDrcMtg/listYear.do?mtgSe=A&menuNo=200755",     # 통화정책방향 결정회의
    "bok_stat": "https://www.bok.or.kr/portal/stats/statsPublictSchdul/listCldr.do?menuNo=200775",           # 통계공표일정
    "mods": "https://mods.go.kr/newsPln.es?mid=a10305000000",                       # 국가데이터처 보도계획(kostat.go.kr이 이리로 넘어온다)
}
US = ("fed", "bea", "bls")                       # 현지 시각이 미 동부인 출처
# (KST 날짜, KST 시각 또는 None, 사전 낱말, 출처, 미 동부 현지 시각 또는 None) — 시각순
LEDGER = (
    ("2026-10-22", None, "금통위", "bok_mpc", None),
    ("2026-10-27", "08:00", "한국 GDP", "bok_stat", None),                # 3분기 실질 국내총생산(속보)
    ("2026-10-29", "03:00", "FOMC", "fed", "2026-10-28 14:00"),          # 10월 27~28일 회의
    ("2026-10-29", "21:30", "미 PCE", "bea", "2026-10-29 08:30"),        # 9월분
    ("2026-11-03", "08:00", "한국 CPI", "mods", None),                    # 10월 소비자물가동향
    ("2026-11-25", "22:30", "미 PCE", "bea", "2026-11-25 08:30"),        # 10월분
    ("2026-11-26", None, "금통위", "bok_mpc", None),
    ("2026-12-02", "08:00", "한국 CPI", "mods", None),                    # 11월 소비자물가동향
    ("2026-12-09", "08:00", "한국 GDP", "bok_stat", None),                # 3분기 국민소득(잠정)
    ("2026-12-10", "04:00", "FOMC", "fed", "2026-12-09 14:00"),          # 12월 8~9일 회의 — 직전 회의에서 확정되기 전까지는 잠정
    ("2026-12-23", "22:30", "미 PCE", "bea", "2026-12-23 08:30"),        # 11월분
    ("2026-12-31", "08:00", "한국 CPI", "mods", None),                    # 12월 및 연간 소비자물가동향
)

try:
    NEW_YORK = zoneinfo.ZoneInfo("America/New_York")
except zoneinfo.ZoneInfoNotFoundError:           # 윈도우에는 tz 자료가 없다 — PYTHONTZPATH로 주면 돈다. CI(리눅스)에는 있다
    NEW_YORK = None


def to_kst(local):
    """미 동부 현지 시각 "YYYY-MM-DD HH:MM" → (KST 날짜, KST 시각)."""
    at = datetime.datetime.strptime(local, "%Y-%m-%d %H:%M").replace(tzinfo=NEW_YORK).astimezone(S.KST)
    return at.strftime("%Y-%m-%d"), at.strftime("%H:%M")


class CalendarTest(unittest.TestCase):
    def setUp(self):
        self.cal = S.read_json(os.path.join(S.DATA, "calendar.json"))
        self.events = self.cal["events"]

    def test_shape_is_the_contract(self):
        S.validate_calendar(self.cal)
        self.assertEqual(S.closed_violations(self.cal), [])                  # 낱말은 사전에 있는 것만
        self.assertTrue(self.events)
        self.assertEqual(self.cal["updated"], CHECKED)

    def test_events_are_in_time_order(self):
        keys = [(e["date"], e.get("time") or "") for e in self.events]      # 시각 없는 줄은 그날의 맨 앞
        self.assertEqual(keys, sorted(keys))
        self.assertEqual(len({(e["date"], e["term"]) for e in self.events}), len(self.events))

    def test_every_event_was_read_from_an_official_page(self):
        self.assertEqual([(e["date"], e.get("time"), e["term"]) for e in self.events], [row[:3] for row in LEDGER])
        self.assertEqual({row[3] for row in LEDGER}, set(SRC))               # 안 쓰는 출처를 남기지 않는다
        for name, url in SRC.items():
            u = urllib.parse.urlsplit(url)
            self.assertEqual((u.scheme, u.port, u.username), ("https", None, None), name)
            self.assertTrue(any(u.hostname == d or u.hostname.endswith("." + d) for d in OFFICIAL), name)
        self.assertTrue(all((row[4] is not None) == (row[3] in US) for row in LEDGER))    # 미국 것은 현지 시각을 같이 적는다

    @unittest.skipIf(NEW_YORK is None, "tz 자료 없음 — PYTHONTZPATH를 주고 돌린다")
    def test_us_times_are_converted_by_zoneinfo(self):
        us = [row for row in LEDGER if row[4]]
        self.assertTrue(us)
        for date, time, term, _, local in us:
            self.assertEqual(to_kst(local), (date, time), term)


if __name__ == "__main__":
    unittest.main()
