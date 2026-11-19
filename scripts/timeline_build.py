#!/usr/bin/env python3
"""판단 연표 (2026-11-19 운영자 결정 '5번도 공개') — 운영자가 공개 기록 저장소에 올린 주간 판정을 옮겨, 정해 둔 방법(판단 연표
약속 1판)으로 그 뒤의 미 금리 변화와 나란히 적는다. 측정 기록이지 채점이 아니다 — 판정이 금리 변화와 같은 쪽이었는지를 매기지
않는다. 표준 라이브러리만.

읽는 것   공개 기록 저장소 yun-macrolab/macro-notes-automation의 records/YYYY-MM-DD.json(스키마 macro-notes-public/1, 그 주 월요일)
          — 커밋 기록째로 읽는다: GitHub REST API(api.github.com — records/를 건드린 커밋 목록, 커밋마다 바뀐 파일)와
          raw.githubusercontent.com(그 커밋의 파일). --records-dir이면 그 저장소의 로컬 git 사본을 git log · git diff · git show로
          (정해 둔 인자만 — 테스트와 손 확인용).
          <data>/charts.json      '금리의 구조' 주간 점 DGS10 · T10Y2Y(ledger_build.load_charts — 기록 장부와 같은 선·같은 읽기)
          <data>/history/         날짜별 공개 기록 — 그 주 일요일 이하 마지막 기록의 핵심 신호 · 국면 후보(ledger_build.load_history)
          <data>/lp.json          판단 격자 L × P의 기준월 기록(history) — 알려진 날(known)이 그 주 일요일 이하인 마지막 달
          <data>/timeline.json    직전 결과 — 처리한 마지막 커밋(source.newest_commit)과 주마다 잠근 판정. 다음 실행은 그 뒤 커밋만 받는다
쓰는 것   <out>/timeline.json

옮기는 것: 주 시작·끝 · 확정 여부 · 듀레이션/커브 합계와 판정 · 사람이 고친 칸 수(edited_n) · 운영자가 시트에 적은 국면(flags.regime —
A · A′ · B · C만. 그 밖의 글은 옮기지 않고 null + regime_flag_other 참 — 빈 칸과 가른다) · 잠근 커밋(sha)과 시각 · 확정 뒤 고친 값 ·
지운 커밋. 뉴스 · 결론 · 메모 · 근거 · 요약 · 하우스 뷰 글은 읽지도 옮기지도 않는다(테스트가 심어 둔 글로 확인). 초안 점수는 공개
기록에 없고 여기서도 만들지 않는다.

판단 연표 약속 1판(PROTOCOL_*, 2026-11-19 고정 — 문장은 protocol_text(), README와 화면에 같은 글)
  판정    records/<주>.json이 state.confirmed == true인 채로 처음 들어간 커밋(커밋 차례 — 오래된 것부터)의 내용. 그 커밋에 적힌 커미터
          시각이 잠근 시각(lock.at, UTC로 적는다) — 운영자의 게시기(macro-notes-automation publish_records.py)는 커밋을 GitHub
          Git Data API로 날짜 없이 만들어 GitHub이 그때의 시각을 적고, PC에서 git으로 만든 커밋에는 그 PC의 시계가 적힌다(검증한 시각이
          아니라 적힌 시각). 그 뒤 커밋이 그 주의 판정·합계(dur · cur)를 바꾸면 changed_after에 마지막으로 바뀐 값과 그 커밋을 적되 셈은
          처음 확정된 판정만 쓴다. 나중 값이 처음 값으로 돌아오면 changed_after는 비운다. lock.first_upload — 그 주의 확정 전 판 없이
          처음 올라온 판이 곧 확정본(확정 시각 = 첫 업로드 시각).
  잠금    한 번 잠근 판정 · 시각은 바꾸지 않는다. 그 주 파일을 지우거나 다른 이름으로 옮기면 removed에 그 커밋을 적고(판정 · 셈 그대로),
          다시 올라오면 removed를 비우고 다른 값만 changed_after로 적는다(다시 잠그지 않는다). 확정 전인 주를 지우면 목록에서 뺀다.
          직전 파일의 마지막 커밋이 공개 기록 저장소의 기록에 없으면(기록을 고쳐 씀) 잠근 주는 그대로 두고(lock.in_history = 그 커밋이
          지금 기록에 있는가, source.rewritten_at = 그 실행의 시각), 잠근 시각 뒤의 커밋만으로 changed_after · removed를 다시 셈한다.
          잠금을 새로 정하는 것은 직전 파일이 없거나 깨졌을 때와 --rebuild뿐이다. 꼴이 어긋난 판(아래 '검사')은 없던 것으로 치고
          source.skipped_versions로 센다.
  출발    그 주(월~일) 안의 마지막 주간 점(대개 금요일 종가). 잠근 시각이 그 주 다음 월요일 OPEN_UTC(13:30 UTC = 22:30 KST — 뉴욕 주식
          현물 시장이 가장 일찍 여는 시각, 서머타임 기간 09:30 EDT. 미 국채는 그 앞 아시아·런던 시간에도 거래되므로 그 앞에 잠근 주도
          월요일 앞부분의 움직임이 1주 변화 안에 든다)보다 늦으면 'late' — 출발 = 잠근 날(UTC 날짜) 이후(그날 포함) START_DAYS(7)일 안의
          첫 주간 점(ledger_build.outcome의 출발 규칙 그대로). 점이 아직 없으면 'pending', 범위 안에 점이 없으면 'missing'. 확정 전인
          주는 출발이 정해지지 않아 'pending'(start null).
  끝      출발 + 7H일에 가장 가까운 주간 점(±TOL_DAYS, 같은 거리면 이른 점), 출발 + 7H + TOL_DAYS가 그 선의 마지막 점보다 뒤면
          'pending' — ledger_build.match · _pending · outcome을 그대로 부른다(H = 1 · 4주).
  짝      듀레이션 판정 ↔ DGS10(charts의 yield10/dgs10), 커브 판정 ↔ T10Y2Y(term/t10y2y). bp = (끝 − 출발) × 100, 소수 한 자리.
  평균    demeaned_bp = change_bp − baseline_bp(H, 선) — ledger_build.baseline(같은 선의 모든 H주 변화의 평균)을 H = 1 · 4로.
  요약    듀레이션 O/W 쪽(O/W · 강한 O/W) · Neutral · U/W 쪽, 커브 Flattening 쪽 · Neutral · Steepening 쪽마다 H별로, 잠근 날(UTC
          날짜) ≥ PROTOCOL_FIXED이고 결과가 'done'인 주만, 출발 점마다 하나로 센다(같은 묶음에서 (출발, 끝)이 같은 주들은 같은
          움직임 — 늦게 확정한 주가 뒤 주와 출발 점을 나눈 경우): n = 주 수, starts = 서로 다른 출발 점 수. starts ≥ N_MIN이면 그
          출발 점들로 mean_demeaned_bp(소수 한 자리)와 up_share(change_bp > 0의 몫, 소수 둘째 자리), 아니면 둘 다 null(화면 '판단
          보류 (starts/10)'). '채점 미완 n/7'과 확정 전인 주는 세지 않는다.
  약속 전 잠근 날(UTC 날짜) < PROTOCOL_FIXED → before_protocol(목록에 결과와 함께 싣되 요약에서 뺀다). 확정 전인 주는 거짓.
  맥락    site = 그 주 일요일 이하 마지막 날짜별 기록(그날 사이트에 실린 그대로)의 핵심 신호(regime.core — 없으면 null) · 충족 규칙
          수(met) · 국면 후보(ledger_build._regime 그대로: A · A′ · B · C, 절은 있는데 후보가 없으면 '판정불가', 절이 없으면 null —
          화면 '—'). lp = lp.json history에서 known(발표일 근사) ≤ 그 주 일요일인 마지막 기준월의 L · P · 칸 이름(lp_fetch.cell(L, P)와
          맞는 행만) — lp_fetch가 갱신마다 그날의 FRED 자료로 다시 재생한 기록이라 그때 사이트에 실린 값이 아니고(판단 격자 카드는
          2026-11-18부터), 지난 값이 개정되면 바뀐다. 칸 이름은 운영자 메모라 화면에서 lp_label(= lp_fetch.LABEL) 아래에 싣는다. 맥락은
          셈에 쓰지 않는다.
  판      약속을 바꾸면 새 판 번호와 날짜를 붙인다. 직전 파일의 판이 다르면 처음부터 다시 셈한다.

검사(쓰는 칸만 — 하나라도 어긋나면 그 판을 쓰지 않는다): schema == 'macro-notes-public/1' · week.start가 파일 이름의 월요일 ·
week.end = start + 6일 · state.confirmed가 참/거짓/null(null은 확정 아님) · dur/cur.verdict가 정해 둔 판정 글(VERDICTS) 또는
'채점 미완 n/7'(n 0~6) · total이 유한한 숫자 또는 null · edited_n이 0 이상의 정수(참거짓 아님) · flags가 객체. 2MB 넘는 파일은 읽지 않는다.

수신(빌드 단계만 — 화면은 다른 곳에 요청하지 않는다): 커밋 목록은 최신부터 쪽마다 100개, 직전 파일의 newest_commit을 만나면 멈춘다
(못 만나면 저장소 기록을 고쳐 쓴 것 — 경고 한 줄, 위 '잠금'. 그때 목록이 비었으면 실패로 친다). 새 커밋마다 GET commits/{sha},
바뀐 records/ 파일마다 raw 한 번(잠근 주의 잠근 시각 앞 판은 받지 않는다). 커밋의 바뀐 파일이 API 한 쪽(300개)을 넘으면(Link
rel="next" 또는 300개) 실패로 친다 — 그 날은 --records-dir로. 머리글: Accept application/vnd.github+json · User-Agent
'macro-regime-check-timeline'(연락처 없음) · 환경 변수 GITHUB_TOKEN이 있으면 api.github.com 요청에만 'Authorization: Bearer …'(raw에는
싣지 않는다). 다른 곳으로 옮기는 응답(3xx)은 따라가지 않는다(머리글이 따라가지 않게). 단계 전체 BUDGET초 굳은 상한 — 요청마다 따로
스레드에서 돌려 min(TIMEOUT, 남은 시간)만 기다린다(이름 풀이 · 여러 주소 연결 · 느린 수신 모두. 넘으면 그 스레드는 버린다), 읽는
동안에도 마감을 본다. 토큰은 출력·파일·오류 문구 어디에도 싣지 않는다(오류는 정해 둔 사유 글만).
--records-dir은 전체 사본만 — 얕은 사본(git clone --depth)은 경계 커밋이 모든 파일을 새로 더한 것처럼 보여 잠금이 늦어지므로 실패로
친다.
전부 아니면 쓰지 않음: 새 커밋을 하나라도 끝까지 처리하지 못하면(요청 실패 · 시간 상한) 판정 쪽(weeks의 잠금·값, source)은 직전
파일 그대로 두고 '::warning::' 한 줄, 종료코드 0 — 그래도 로컬 파일에서 오는 칸(맥락 · 결과 · 평균 · 요약 · 출처의 날짜)은 다시
셈해 달라졌으면 쓴다. 직전 파일이 없으면 아무것도 쓰지 않는다. --offline은 요청 없이 같은 길(경고 없음).
charts.json이 없거나 깨졌거나 두 선 가운데 하나라도 없으면 쓰지 않고 직전 파일을 둔다(경고 한 줄 — ledger_build와 같다).
source.checked_at은 공개 기록을 마지막으로 끝까지 읽은 실행의 시각이다(읽지 못한 날은 그대로). generated_at 말고 같은 내용이면
다시 쓰지 않는다. 쓰기는 임시 파일 → os.replace(ledger_build.write).

종료코드: 0 씀(또는 그대로 둠 · 입력 없음) / 1 쓰지 못함.
사용법: python scripts/timeline_build.py [--data data] [--out data] [--offline] [--budget 40] [--records-dir DIR]
                                         [--records-ref REF] [--rebuild]
"""
import os, re, sys, json, copy, time, bisect, argparse, datetime, threading, subprocess
import urllib.error, urllib.parse, urllib.request
from decimal import Decimal

SCRIPTS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPTS)
import ledger_build as lb                              # 주간 점 읽기 · 끝 점 맞추기 · 평균 · 출발 규칙 · 반올림 · 쓰기 — 다시 짜지 않는다
import lp_fetch as lpf                                 # 판단 격자의 칸 이름(cell)과 이름표(LABEL) — 읽기만
import render_public as rp                             # FRED 권장 인용(citation)과 인용 필요 시리즈 목록 — 읽기만

D = datetime.date
UTC = datetime.timezone.utc
REPO = os.path.dirname(SCRIPTS)
DEFAULT_DATA = os.path.join(REPO, "data")
SCHEMA = 1
FILE = "timeline.json"

# ── 판단 연표 약속 1판 (2026-11-19 고정 — 바꾸면 PROTOCOL_VERSION과 PROTOCOL_FIXED를 새로, README '판단 연표' 절도 같이) ──────
PROTOCOL_VERSION = 1
PROTOCOL_FIXED = "2026-11-19"
HORIZONS = (1, 4)                                      # 주
N_MIN = 10
TOL_DAYS = 3                                           # ledger_build.match가 쓰는 값과 같아야 한다(테스트가 견준다)
START_DAYS = 7                                         # 늦게 확정한 주의 출발 — ledger_build.outcome의 START_DAYS와 같아야 한다
OPEN_UTC = (13, 30)                                    # 그 주 다음 월요일 이 시각(UTC)보다 늦게 잠그면 '늦게 확정'
KST_HOURS = 9                                          # 한국 시각(서머타임 없음) — 화면과 약속 문장의 풀이용
PAIRS = (("dur", "dgs10", "DGS10", "미 10년"), ("cur", "t10y2y", "T10Y2Y", "10년−2년"))   # (판정 칸, 그래프 선, 시리즈, 이름)
GROUPS = {"dur": (("ow", ("O/W", "강한 O/W")), ("neutral", ("Neutral",)), ("uw", ("U/W", "강한 U/W"))),
          "cur": (("flat", ("Flattening", "강한 Flattening")), ("neutral", ("Neutral",)),
                  ("steep", ("Steepening", "강한 Steepening")))}
VERDICTS = {b: tuple(v for _, vs in g for v in vs) for b, g in GROUPS.items()}   # 운영자 시트(sheet_v2.verdict)가 내는 판정 글
UNSCORED_RE = re.compile(r"채점 미완 [0-6]/7")          # 7행이 다 채점되지 않은 주 — 판정 아님, 요약에 들지 않는다
REGIMES = ("A", "A′", "B", "C")                          # 운영자 국면 칸(flags.regime) — 그 밖의 글은 옮기지 않는다

# ── 원본 · 수신 ─────────────────────────────────────────────────────────────────────────────────────────────
SOURCE_REPO = "yun-macrolab/macro-notes-automation"
SOURCE_PATH = "records/"
SOURCE_SITE = "https://yun-macrolab.github.io/macro-notes-automation/"
RECORD_SCHEMA = "macro-notes-public/1"
API_HOST, RAW_HOST = "api.github.com", "raw.githubusercontent.com"
API = f"https://{API_HOST}/repos/{SOURCE_REPO}"
LIST_URL = API + "/commits?path=records&per_page={per}&page={page}"
COMMIT_URL = API + "/commits/{sha}"
RAW_URL = f"https://{RAW_HOST}/{SOURCE_REPO}" + "/{sha}/records/{name}"
USER_AGENT = "macro-regime-check-timeline"
API_VERSION = "2022-11-28"
BUDGET = 40.0
TIMEOUT = 15.0
PER_PAGE = 100
MAX_PAGES = 30
MAX_RECORD_BYTES = 2_000_000                            # macro-notes-automation web/build.py의 MAX_RECORD_BYTES와 같다
MAX_API_BYTES = 8_000_000
MAX_COMMIT_FILES = 300                                  # GitHub 'Get a commit'의 files 한 쪽 — 이만큼이면 나머지가 다음 쪽에 있을 수 있다
SHA_RE = re.compile(r"[0-9a-f]{40}")
REF_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._/-]{0,99}")
RECORD_PATH_RE = re.compile(r"records/(\d{4}-\d{2}-\d{2})\.json")
MONTH_RE = re.compile(r"\d{4}-\d{2}")
TOKEN_RE = re.compile(r"[A-Za-z0-9_.\-]{8,255}")

LABEL = "운영자 주간 판정(공개 기록에서 옮김) — 투자 판단·권유 아님 · 측정 기록"
NOTICE = ("운영자가 공개 기록(macro-notes-automation 저장소의 records/)에 올린 주간 판정을 옮겨, 정해 둔 방법(판단 연표 약속)으로 "
          "그 뒤의 미 금리 변화와 나란히 적은 측정 기록이다. 예측이 아니고 투자 판단이나 권유가 아니다.")
COMPUTED_NOTICE = ("1주·4주 변화 · 평균을 뺀 값 · 평균(기준) · 요약은 macro-regime-check가 그래프 자료(data/charts.json)의 주간 점으로 "
                   "계산한 값이다. 연준 이사회 · 세인트루이스 연은 · FRED가 발표한 값이 아니다.")
COMPUTED_NOTICE_EN = ("The 1- and 4-week changes, demeaned values, baselines and summaries are computed by macro-regime-check "
                      "from the weekly points in data/charts.json; they are not published by the Federal Reserve Board, "
                      "the Federal Reserve Bank of St. Louis or FRED.")
REASONS = {"budget": "시간 상한", "timeout": "요청 시간 초과", "net": "연결 실패", "http": "HTTP 오류",
           "blocked": "요청 한도 또는 거절", "format": "응답 꼴이 다름", "redirect": "다른 주소로 옮김(따라가지 않음)",
           "git": "로컬 git 읽기 실패", "shallow": "얕은 사본 — 전체 사본(git clone, --depth 없이)이 필요함",
           "too_big": "응답이 너무 큼", "too_many_files": "커밋의 바뀐 파일이 API 한 쪽보다 많음 — --records-dir로",
           "empty": "커밋 목록이 비었음"}


def open_kst():
    """OPEN_UTC를 한국 시각으로 'HH:MM'."""
    hh, mm = OPEN_UTC
    return f"{(hh + KST_HOURS) % 24:02d}:{mm:02d}"


def protocol_text():
    """화면 · README에 같은 글로 싣는 판단 연표 약속 문장(한다체). 숫자는 모두 위 상수에서."""
    h = "·".join(f"{x}주" for x in HORIZONS)
    hh, mm = OPEN_UTC
    g = lambda b: " · ".join(f"{name}({'·'.join(vs)})" if len(vs) > 1 else name
                             for name, vs in ((_GROUP_WORD[k], vs) for k, vs in GROUPS[b]))
    return [
        f"판단 연표 약속 {PROTOCOL_VERSION}판 — {PROTOCOL_FIXED}에 정했다.",
        f"판정: 공개 기록 저장소({SOURCE_REPO})의 {SOURCE_PATH}<그 주 월요일>.json이 확정(state.confirmed = true)인 채로 처음 "
        "들어간 커밋의 내용을 그 주의 판정으로 적는다. 그 커밋에 적힌 커미터 시각이 잠근 시각이다 — 운영자의 게시기는 커밋을 GitHub "
        "API로 날짜 없이 만들므로 GitHub이 그 커밋을 만든 때의 시각이 적히고, PC에서 git으로 만든 커밋에는 그 PC의 시계가 적힌다. "
        "커밋을 만드는 쪽이 날짜를 정할 수도 있어 검증한 시각이 아니라 적힌 시각이다. 그 뒤 커밋이 판정이나 합계를 바꾸면 '확정 뒤 "
        "고침'으로 새 값을 함께 적되, 모든 셈은 처음 확정된 판정만 쓴다.",
        "한 번 잠근 판정과 시각은 바꾸지 않는다. 공개 기록에서 그 주 파일을 지우거나 이름을 바꾸면 '공개 기록에서 지움'으로 적되 "
        "판정과 셈은 그대로 두고, 다시 올라오면 다시 잠그지 않고 처음 판정과 다른 값만 '확정 뒤 고침'으로 적는다. 공개 기록 저장소의 "
        "기록을 고쳐 써 잠근 커밋이 기록에서 사라져도 잠근 판정과 시각을 그대로 두고 '잠근 커밋이 지금 기록에 없음'으로 적는다. "
        "잠금을 새로 정하는 것은 직전 파일이 없거나 깨졌을 때와 처음부터 다시 셀 때(--rebuild)뿐이다. 정해 둔 꼴에 맞지 않는 판은 "
        "쓰지 않는다.",
        f"출발 점: 그 주(월~일) 안의 마지막 주간 점(대개 금요일 종가 — 운영자가 확정 전에 볼 수 있던 값)이다. 잠근 시각이 그 주 다음 "
        f"월요일 {hh:02d}:{mm:02d} UTC(한국 시각 {open_kst()} — 뉴욕 주식 현물 시장이 가장 일찍 여는 시각, 서머타임 기간 "
        f"{(hh - 4) % 24:02d}:{mm:02d} EDT)보다 늦으면 '늦게 확정'으로 적고, 출발 점은 잠근 날(UTC 날짜) 이후(그날 포함) {START_DAYS}일 "
        f"안의 첫 주간 점이다. 그 점이 아직 없으면 '기다리는 중', {START_DAYS}일 안에 점이 없으면 '자료 없음'이다. 확정 전인 주는 출발 "
        "점을 정하지 않는다.",
        "미 국채 현물은 그 시각보다 앞서 아시아·런던 시간에도 거래된다 — 그 시각 앞에 잠근 주도 그 월요일 앞부분의 움직임이 확정 "
        "전에 보였을 수 있고, 그 움직임은 1주 변화 안에 든다.",
        f"기간: 출발 점에서 {h} 뒤까지의 변화를 bp로 적는다. 끝 점은 출발 점 날짜에 7×주 수 일을 더한 날에 가장 가까운 주간 점"
        f"(±{TOL_DAYS}일 안, 같은 거리면 이른 점)이다. 그 범위 끝이 그 선의 마지막 점보다 뒤면 '기다리는 중', 범위 안에 점이 없으면 "
        "'자료 없음'으로 둔다.",
        "짝: " + " · ".join(f"{'듀레이션' if b == 'dur' else '커브'} 판정은 {label}({sid})" for b, _, sid, label in PAIRS)
        + "의 변화와 짝짓는다 — 사이트 '금리의 구조' 그래프(data/charts.json)와 같은 주간 점(주마다 마지막 관측)이다.",
        f"평균 빼기: 같은 그래프 선의 모든 주간 점에서 같은 규칙으로 잰 {h} 변화의 평균을 빼서 '평균을 뺀 값'으로도 적는다. 평균은 "
        "갱신마다 그날 그래프가 싣는 최근 기간(창)으로 다시 잰다 — 창이 옮겨 가면 FRED가 값을 고치지 않아도 조금씩 달라진다.",
        f"요약: 듀레이션은 {g('dur')}, 커브는 {g('cur')}으로 묶어, 잠근 날(UTC 날짜)이 {PROTOCOL_FIXED} 이후이고 결과가 나온 "
        "('기다리는 중'·'자료 없음' 제외) 주를 출발 점마다 하나로 센다 — 같은 묶음에서 출발 점이 같은 주들(늦게 확정한 주가 뒤 주와 "
        f"출발 점을 나눈 경우)은 같은 움직임이라 한 번만 센다. 그렇게 센 출발 점이 {N_MIN}개 이상일 때만 그 출발 점들의 평균을 뺀 "
        "값의 평균과 오른 비율(변화가 0보다 큰 몫)을 낸다 — 그 전에는 판단 보류다. '채점 미완' 판정과 확정 전인 주는 세지 않는다.",
        f"약속 전: 잠근 날(UTC 날짜)이 {PROTOCOL_FIXED} 앞인 주는 결과와 함께 목록에 '약속 전'으로 적되 요약에서 뺀다 — 약속을 정할 "
        "때 그 뒤의 금리 변화가 이미 보였다.",
        "측정 기록이다(예측 아님) — 판정이 금리 변화와 같은 쪽이었는지를 매기지 않는다. 판정은 자동화가 쓴 초안 점수에서 시작하므로 "
        "주마다 운영자 시트가 잡은 사람이 고친 칸 수(edited_n)를 함께 적는다. 시트는 자동 실행 때만 고친 칸을 잡아 그 주 마지막 자동 "
        "실행 뒤(주말 등)에 고친 칸은 세지 못한다 — 0이 초안 그대로라는 보장은 아니다.",
        "맥락: 그 주 일요일 이하의 마지막 날짜별 기록(data/history — 그날 이 사이트에 실린 그대로)의 핵심 신호(없으면 충족 규칙 수)와 "
        "국면 후보, 운영자가 시트에 적은 국면, 판단 격자 L × P의 칸을 함께 적는다. L × P는 그때 사이트에 실린 값이 아니라 갱신마다 그날의 "
        "FRED 자료로 다시 재생한 기록(data/lp.json)에서 알려진 날(발표일 근사)이 그 주 일요일 이하인 마지막 기준월이라, 지난 값이 "
        "개정되면 바뀐다. 맥락은 셈에 쓰지 않는다.",
        "charts.json의 주간 점은 FRED가 값을 고치면 바뀐다 — 결과와 평균은 이 파일을 만든 날의 charts.json으로 잰다.",
        "약속을 바꾸면 새 판 번호와 날짜를 붙이고, 판을 바꾸지 않고는 정의를 고치지 않는다 — 지난 판으로 낸 파일은 저장소 기록(git)에 "
        "남는다. 이 파일의 판 번호가 쓴 약속이다.",
    ]


_GROUP_WORD = {"ow": "O/W 쪽", "uw": "U/W 쪽", "neutral": "Neutral", "flat": "Flattening 쪽", "steep": "Steepening 쪽"}


# ── 작은 도우미 ──────────────────────────────────────────────────────────────────────────────────────────────
def _date(s):
    return lb._date(s)


def _dt(s):
    """ISO 시각 글 → UTC datetime(오프셋 필수, 'Z' 허용), 아니면 None."""
    if not isinstance(s, str) or not 19 <= len(s) <= 40:
        return None
    t = s[:-1] + "+00:00" if s.endswith("Z") else s
    try:
        v = datetime.datetime.fromisoformat(t)
    except ValueError:
        return None
    return v.astimezone(UTC) if v.tzinfo is not None else None


def _iso(v):
    return v.astimezone(UTC).isoformat(timespec="seconds")


def _num(v):
    """유한한 숫자(참거짓 아님) → float(−0.0은 0.0), null → None, 그 밖은 False."""
    if v is None:
        return None
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        return False
    if isinstance(v, float) and (v != v or v in (float("inf"), float("-inf"))):
        return False
    if abs(v) > 1000:
        return False
    v = float(v)
    return 0.0 if v == 0 else v


def record_week(path):
    """'records/YYYY-MM-DD.json' → 'YYYY-MM-DD'(날짜로 읽히는 것만), 아니면 None."""
    m = RECORD_PATH_RE.fullmatch(path) if isinstance(path, str) else None
    return m.group(1) if m and _date(m.group(1)) else None


def _block(b, x):
    """{total, verdict} 검사 → 정리한 사본, 어긋나면 None."""
    if not isinstance(x, dict):
        return None
    total, verdict = _num(x.get("total")), x.get("verdict")
    if total is False or not isinstance(verdict, str) or not (verdict in VERDICTS[b] or UNSCORED_RE.fullmatch(verdict)):
        return None
    return {"total": total, "verdict": verdict}


def _edited(v):
    return v if isinstance(v, int) and not isinstance(v, bool) and 0 <= v <= 10_000 else None


def regime_of(v):
    """시트의 국면 칸 → (옮길 값, 정해 둔 값 밖인가). A · A′ · B · C는 그대로, 비었으면(null · 빈 글) (None, False),
    그 밖의 값은 옮기지 않고 (None, True) — 화면이 '비어 있음'과 '정해 둔 값 밖'을 가른다(글 자체는 싣지 않는다)."""
    if v in REGIMES:
        return v, False
    if v is None or (isinstance(v, str) and not v.strip()):
        return None, False
    return None, True


def read_record(raw, week):
    """공개본 한 판(바이트) → 쓰는 칸만 {confirmed, dur, cur, edited_n, regime_flag, regime_flag_other}. 검사(머리말)에 어긋나면
    None."""
    if not isinstance(raw, (bytes, bytearray)) or len(raw) > MAX_RECORD_BYTES:
        return None
    try:
        rec = json.loads(bytes(raw).decode("utf-8-sig"))
    except (UnicodeDecodeError, ValueError, RecursionError):
        return None
    if not isinstance(rec, dict) or rec.get("schema") != RECORD_SCHEMA:
        return None
    wk, st = rec.get("week"), rec.get("state")
    if not isinstance(wk, dict) or not isinstance(st, dict):
        return None
    start, end = _date(wk.get("start")), _date(wk.get("end"))
    if start is None or start.isoformat() != week or start.weekday() != 0 or end != start + datetime.timedelta(days=6):
        return None
    confirmed = st.get("confirmed")
    if confirmed is not None and not isinstance(confirmed, bool):
        return None
    dur, cur, edited, flags = _block("dur", st.get("dur")), _block("cur", st.get("cur")), _edited(st.get("edited_n")), st.get("flags")
    if dur is None or cur is None or edited is None or not isinstance(flags, dict):
        return None
    regime, other = regime_of(flags.get("regime"))
    return {"confirmed": confirmed is True, "dur": dur, "cur": cur, "edited_n": edited,
            "regime_flag": regime, "regime_flag_other": other}


def is_late(week_end, at):
    """잠근 시각(UTC datetime)이 그 주 다음 월요일 OPEN_UTC보다 늦은가(같으면 늦지 않음)."""
    hh, mm = OPEN_UTC
    return at > datetime.datetime.combine(week_end + datetime.timedelta(days=1), datetime.time(hh, mm), tzinfo=UTC)


# ── 커밋 처리(원본에 무관한 한 길) ───────────────────────────────────────────────────────────────────────────
def apply_version(weeks, week, rec, sha, at):
    """한 커밋의 한 주 판 → weeks(주 → 상태) 갱신. at은 UTC ISO 글. 잠근 주는 다시 잠그지 않는다 — 처음 판정과 다른 값만
    changed_after로."""
    vals = {"dur": rec["dur"], "cur": rec["cur"], "edited_n": rec["edited_n"], "regime_flag": rec["regime_flag"],
            "regime_flag_other": rec["regime_flag_other"]}
    w = weeks.get(week)
    if w is None or w["lock"] is None:
        end = (D.fromisoformat(week) + datetime.timedelta(days=6)).isoformat()
        lock = {"sha": sha, "at": at, "first_upload": w is None, "in_history": True} if rec["confirmed"] else None
        weeks[week] = {"week": week, "end": end, "lock": lock, **vals, "changed_after": None, "removed": None}
        return
    now = (vals["dur"], vals["cur"])
    if now == (w["dur"], w["cur"]):
        w["changed_after"] = None
    elif w["changed_after"] is None or (w["changed_after"]["dur"], w["changed_after"]["cur"]) != now:
        w["changed_after"] = {"at": at, "sha": sha, "dur": vals["dur"], "cur": vals["cur"], "edited_n": vals["edited_n"]}


def remove_week(weeks, week, sha, at):
    """그 주 파일이 지워지거나 다른 이름으로 옮겨짐 — 확정 전인 주는 목록에서 빼고, 잠근 주는 판정 · 셈을 그대로 두고 지운 커밋만 적는다."""
    w = weeks.get(week)
    if w is None:
        return
    if w["lock"] is None:
        weeks.pop(week)
    else:
        w["removed"] = {"at": at, "sha": sha}


def process(weeks, commits, src, kept=None):
    """commits — 오래된 것부터 [(sha, at)]. src.changed(sha) → [(상태, 경로, 옛 경로)], src.content(sha, 경로) → 바이트.
    kept — {주: 잠근 시각(datetime)}: 고쳐 쓴 기록을 다시 셀 때 잠근 채로 넘겨받은 주. 그 주의 잠근 시각 이하 커밋은 보지도 받지도
    않는다(확정 전의 판이 '확정 뒤 고침'으로 보이지 않게). weeks를 고치고 → 쓰지 않은(꼴이 어긋난) 판 수. 수신 실패는 FetchError로
    그대로 올린다(부르는 쪽이 통째로 버린다)."""
    kept = kept or {}
    skipped = 0
    for sha, at in commits:
        t = _dt(at)
        early = lambda wk: wk in kept and t <= kept[wk]
        for status, path, prev in src.changed(sha):
            if prev and prev != path:
                pw = record_week(prev)
                if pw and not early(pw):
                    remove_week(weeks, pw, sha, at)
            week = record_week(path)
            if week is None or early(week):
                continue
            if status == "removed":
                remove_week(weeks, week, sha, at)
                continue
            w = weeks.get(week)
            if w is not None and w["lock"] is not None:
                w["removed"] = None                   # 다시 올라옴(꼴이 어긋난 판이어도 파일은 있다) — 잠금은 그대로
            rec = read_record(src.content(sha, path), week)
            if rec is None:
                skipped += 1
                continue
            apply_version(weeks, week, rec, sha, at)
    return skipped


# ── 수신: GitHub API ─────────────────────────────────────────────────────────────────────────────────────────
class FetchError(Exception):
    def __init__(self, kind, code=None):
        super().__init__(kind)
        self.kind, self.code = kind, code

    def reason(self):
        return REASONS.get(self.kind, "알 수 없음") + (f" {self.code}" if self.kind == "http" and self.code else "")


_HOST = re.compile(r"([a-z0-9-]+(?:\.[a-z0-9-]+)*)(?::443)?")


def host_of(url):
    """https 주소가 urllib이 실제로 붙는 호스트(Request.host)로 API_HOST · RAW_HOST 가운데 하나이면 그 이름, 아니면 None.
    사용자 정보('@') · 역슬래시 · 공백 · 제어 문자 · 다른 포트는 받지 않는다(sec_fetch._sec_https와 같은 생각)."""
    if not isinstance(url, str) or any(ord(ch) <= 32 or ord(ch) == 127 for ch in url):
        return None
    try:
        p = urllib.parse.urlsplit(url)
        req = urllib.request.Request(url)
        port = p.port
    except (ValueError, TypeError):
        return None
    if p.scheme != "https" or req.type != "https" or "@" in p.netloc or "\\" in p.netloc or port not in (None, 443):
        return None
    m = _HOST.fullmatch((req.host or "").lower())
    host = m.group(1) if m else None
    return host if host in (API_HOST, RAW_HOST) and (p.hostname or "") == host else None


def gh_request(url, token=None):
    """머리글을 단 요청 — 토큰은 api.github.com에만. 그 밖의 주소는 ValueError."""
    host = host_of(url)
    if host is None:
        raise ValueError("허용하지 않는 주소")
    headers = {"User-Agent": USER_AGENT}
    if host == API_HOST:
        headers["Accept"] = "application/vnd.github+json"
        headers["X-GitHub-Api-Version"] = API_VERSION
        if token:
            headers["Authorization"] = "Bearer " + token
    return urllib.request.Request(url, headers=headers)


class NoRedirect(urllib.request.HTTPRedirectHandler):
    """옮기는 응답은 따라가지 않는다(Authorization이 다른 곳으로 따라가지 않게)."""
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise urllib.error.HTTPError(req.full_url, code, "redirect refused", headers, fp)


def _default_opener():
    return urllib.request.build_opener(NoRedirect()).open


def token_from(env):
    """환경 변수 GITHUB_TOKEN — 꼴이 맞을 때만(공백·제어 문자가 섞이면 쓰지 않는다)."""
    t = (env or {}).get("GITHUB_TOKEN")
    return t if isinstance(t, str) and TOKEN_RE.fullmatch(t) else None


class ApiSource:
    via = "api"

    def __init__(self, deadline, clock=time.monotonic, opener=None, token=None):
        self.deadline, self.clock, self.opener, self.token = deadline, clock, opener or _default_opener(), token
        self.requests = 0

    def _get(self, url, limit, with_link=False):
        """요청 하나를 따로 스레드에서 돌려 min(TIMEOUT, 남은 시간)만 기다린다(굳은 상한 — 이름 풀이 · 여러 주소 연결 · 느린 수신
        모두). 넘으면 그 스레드는 버리고 FetchError('budget' · 남은 시간이 걸렸으면, 아니면 'timeout'). → 바이트(with_link면 (바이트,
        Link 머리글 글 또는 None))."""
        left = self.deadline - self.clock()
        if left <= 1:
            raise FetchError("budget")
        req = gh_request(url, self.token)
        self.requests += 1
        wait = min(TIMEOUT, left)
        box = {}

        def run():
            try:
                box["v"] = self._fetch(req, wait, limit)
            except BaseException as e:                 # 스레드 밖으로 그대로 옮긴다
                box["e"] = e
        t = threading.Thread(target=run, daemon=True)
        t.start()
        t.join(wait)
        if t.is_alive():
            raise FetchError("budget" if left <= TIMEOUT else "timeout")
        if "e" in box:
            e = box["e"]
            raise e if isinstance(e, FetchError) else FetchError("net")
        body, link = box["v"]
        return (body, link) if with_link else body

    def _fetch(self, req, wait, limit):
        try:
            r = self.opener(req, timeout=wait)
        except urllib.error.HTTPError as e:
            try:
                e.close()
            except Exception:
                pass
            if 300 <= e.code < 400:
                raise FetchError("redirect") from None
            if e.code in (403, 429):
                raise FetchError("blocked", e.code) from None
            raise FetchError("http", e.code) from None
        except Exception:
            raise FetchError("net") from None
        chunks, size = [], 0
        try:
            headers = getattr(r, "headers", None)
            link = headers.get("Link") if headers is not None and hasattr(headers, "get") else None
            with r:
                read = getattr(r, "read1", None) or r.read
                while True:
                    if self.clock() > self.deadline:
                        raise FetchError("budget")
                    chunk = read(65536)
                    if not chunk:
                        break
                    size += len(chunk)
                    if size > limit:
                        raise FetchError("too_big")
                    chunks.append(chunk)
        except FetchError:
            raise
        except Exception:
            raise FetchError("net") from None
        return b"".join(chunks), link if isinstance(link, str) else None

    def _json(self, url, with_link=False):
        body, link = self._get(url, MAX_API_BYTES, with_link=True)
        try:
            data = json.loads(body.decode("utf-8"))
        except (UnicodeDecodeError, ValueError, RecursionError):
            raise FetchError("format") from None
        return (data, link) if with_link else data

    def list_commits(self, stop=None):
        """records/를 건드린 커밋, 최신부터 [(sha, at)] — stop(직전 파일의 newest_commit)을 만나면 그 앞에서 멈춘다.
        → (목록, stop을 만났는가)."""
        out = []
        for page in range(1, MAX_PAGES + 1):
            data = self._json(LIST_URL.format(per=PER_PAGE, page=page))
            if not isinstance(data, list):
                raise FetchError("format")
            for c in data:
                sha = c.get("sha") if isinstance(c, dict) else None
                com = c.get("commit") if isinstance(c, dict) else None
                who = com.get("committer") if isinstance(com, dict) else None
                at = _dt(who.get("date")) if isinstance(who, dict) else None
                if not isinstance(sha, str) or not SHA_RE.fullmatch(sha) or at is None:
                    raise FetchError("format")
                if sha == stop:
                    return out, True
                out.append((sha, _iso(at)))
            if len(data) < PER_PAGE:
                return out, False
        raise FetchError("format")                     # 쪽이 너무 많다 — 끝까지 읽지 못한 목록은 쓰지 않는다

    def changed(self, sha):
        data, link = self._json(COMMIT_URL.format(sha=sha), with_link=True)
        files = data.get("files") if isinstance(data, dict) else None
        if not isinstance(files, list):
            raise FetchError("format")
        if len(files) >= MAX_COMMIT_FILES or (link and re.search(r'rel="?next"?', link)):
            raise FetchError("too_many_files")         # 나머지 파일이 다음 쪽에 있을 수 있다 — 반쯤 읽은 커밋은 쓰지 않는다
        out = []
        for f in files:
            if not isinstance(f, dict) or not isinstance(f.get("filename"), str):
                raise FetchError("format")
            st = f.get("status")
            prev = f.get("previous_filename") if st == "renamed" and isinstance(f.get("previous_filename"), str) else None
            out.append(("removed" if st == "removed" else "renamed" if prev else "modified", f["filename"], prev))
        return out

    def content(self, sha, path):
        week = record_week(path)
        if week is None or not SHA_RE.fullmatch(sha):
            raise FetchError("format")
        try:
            return self._get(RAW_URL.format(sha=sha, name=week + ".json"), MAX_RECORD_BYTES)
        except FetchError as e:
            if e.kind == "too_big":
                return b""                             # 2MB 넘는 판 — 꼴이 어긋난 판으로 센다(read_record가 None)
            raise


# ── 수신: 로컬 git 사본(--records-dir) ──────────────────────────────────────────────────────────────────────
class GitSource:
    via = "git"

    def __init__(self, repo_dir, ref, deadline, clock=time.monotonic):
        if not REF_RE.fullmatch(ref or "") or ".." in ref:
            raise FetchError("git")
        self.dir, self.ref, self.deadline, self.clock = os.path.abspath(repo_dir), ref, deadline, clock
        self.requests = 0

    def _git(self, *args):
        left = self.deadline - self.clock()
        if left <= 1:
            raise FetchError("budget")
        self.requests += 1
        try:
            env = {k: v for k, v in os.environ.items() if k not in ("GITHUB_TOKEN", "GH_TOKEN")}
            p = subprocess.run(["git", "-C", self.dir, *args], capture_output=True, timeout=min(TIMEOUT, left),
                               env={**env, "GIT_PAGER": "cat", "LC_ALL": "C"})
        except (OSError, subprocess.SubprocessError):
            raise FetchError("git") from None
        if p.returncode != 0:
            raise FetchError("git")
        return p.stdout

    def list_commits(self, stop=None):
        # 얕은 사본은 경계 커밋에 부모가 없어 그때 있던 파일을 모두 새로 더한 것처럼 보인다 — 잠금이 늦어지므로 받지 않는다
        if self._git("rev-parse", "--is-shallow-repository").strip() == b"true":
            raise FetchError("shallow")
        out = []
        for line in self._git("log", "--format=%H%x09%cI", self.ref, "--", "records").decode("utf-8", "replace").splitlines():
            sha, _, when = line.partition("\t")
            at = _dt(when)
            if not SHA_RE.fullmatch(sha) or at is None:
                raise FetchError("format")
            if sha == stop:
                return out, True
            out.append((sha, _iso(at)))
        return out, False

    def changed(self, sha):
        if not SHA_RE.fullmatch(sha):
            raise FetchError("format")
        parents = self._git("rev-list", "--parents", "-n", "1", sha).decode().split()[1:]
        if parents:                                   # 첫 부모와 견준다(GitHub의 커밋 응답과 같게)
            text = self._git("diff", "--name-status", "-M", parents[0], sha, "--", "records")
        else:
            text = self._git("diff-tree", "--no-commit-id", "-r", "--root", "--name-status", "-M", sha, "--", "records")
        out = []
        for line in text.decode("utf-8", "replace").splitlines():
            parts = line.split("\t")
            if len(parts) == 3 and parts[0][:1] in "RC":
                out.append(("renamed" if parts[0][0] == "R" else "modified", parts[2], parts[1] if parts[0][0] == "R" else None))
            elif len(parts) == 2:
                out.append(("removed" if parts[0] == "D" else "modified", parts[1], None))
            elif line.strip():
                raise FetchError("format")
        return out

    def content(self, sha, path):
        if record_week(path) is None or not SHA_RE.fullmatch(sha):
            raise FetchError("format")
        data = self._git("show", f"{sha}:{path}")
        return data if len(data) <= MAX_RECORD_BYTES else b""


# ── 직전 파일 ─────────────────────────────────────────────────────────────────────────────────────────────────
def _commit_in(x):
    """{sha, at} → 정리한 사본, null → None, 어긋나면 False."""
    if x is None:
        return None
    if not isinstance(x, dict) or not isinstance(x.get("sha"), str) or not SHA_RE.fullmatch(x["sha"]):
        return False
    at = _dt(x.get("at"))
    return False if at is None else {"sha": x["sha"], "at": _iso(at)}


def _lock_in(x):
    c = _commit_in(x)
    if not c:
        return c
    fu, ih = x.get("first_upload"), x.get("in_history")
    if not isinstance(fu, bool) or not isinstance(ih, bool):
        return False
    return {**c, "first_upload": fu, "in_history": ih}


def _week_in(e):
    """직전 파일의 주 한 칸 → 처리 상태, 어긋나면 None."""
    if not isinstance(e, dict):
        return None
    wd = _date(e.get("week"))
    if wd is None or wd.weekday() != 0 or e.get("end") != (wd + datetime.timedelta(days=6)).isoformat():
        return None
    lock = _lock_in(e.get("lock"))
    dur, cur, edited = _block("dur", e.get("dur")), _block("cur", e.get("cur")), _edited(e.get("edited_n"))
    reg, other = e.get("regime_flag"), e.get("regime_flag_other")
    if lock is False or dur is None or cur is None or edited is None or (reg is not None and reg not in REGIMES) \
            or not isinstance(other, bool) or (other and reg is not None):
        return None
    if e.get("state") != ("confirmed" if lock else "in_progress"):
        return None
    removed = _commit_in(e.get("removed"))
    if removed is False or (removed and not lock):
        return None
    ca = e.get("changed_after")
    if ca is not None:
        cl = _commit_in(ca if isinstance(ca, dict) else None)
        cd, cc, ce = (_block("dur", ca.get("dur")), _block("cur", ca.get("cur")), _edited(ca.get("edited_n"))) \
            if isinstance(ca, dict) else (None, None, None)
        if not lock or not cl or cd is None or cc is None or ce is None:
            return None
        ca = {"at": cl["at"], "sha": cl["sha"], "dur": cd, "cur": cc, "edited_n": ce}
    return {"week": wd.isoformat(), "end": e["end"], "lock": lock, "dur": dur, "cur": cur, "edited_n": edited,
            "regime_flag": reg, "regime_flag_other": other, "changed_after": ca, "removed": removed}


def load_previous(path):
    """직전 timeline.json → {"source": {...}, "weeks": {주: 상태}} — 없거나 깨졌거나 판이 다르면 None(처음부터 다시 셈)."""
    try:
        with open(path, encoding="utf-8") as f:
            raw = json.load(f)
    except (OSError, ValueError, RecursionError):
        return None
    if not isinstance(raw, dict) or raw.get("schema") != SCHEMA:
        return None
    p, s = raw.get("protocol"), raw.get("source")
    if not isinstance(p, dict) or p.get("version") != PROTOCOL_VERSION or not isinstance(s, dict):
        return None
    newest = s.get("newest_commit")
    if newest is not None and (not isinstance(newest, str) or not SHA_RE.fullmatch(newest)):
        return None
    checked, rewritten = s.get("checked_at"), s.get("rewritten_at")
    skipped = _edited(s.get("skipped_versions"))
    if (checked is not None and _dt(checked) is None) or (rewritten is not None and _dt(rewritten) is None) \
            or skipped is None or s.get("via") not in ("api", "git") or not isinstance(raw.get("weeks"), list):
        return None
    weeks = {}
    for e in raw["weeks"]:
        w = _week_in(e)
        if w is None or w["week"] in weeks:
            return None
        weeks[w["week"]] = w
    return {"source": {"newest_commit": newest, "checked_at": checked, "via": s["via"], "skipped_versions": skipped,
                       "rewritten_at": rewritten}, "weeks": weeks}


# ── 로컬 자료 ────────────────────────────────────────────────────────────────────────────────────────────────
def load_lp(path):
    """lp.json → [(기준월, 알려진 날, L, P, 칸)] 기준월 순 — 칸이 lp_fetch.cell(L, P)와 맞는 행만. 없거나 깨졌으면 []."""
    try:
        with open(path, encoding="utf-8") as f:
            raw = json.load(f)
    except (OSError, ValueError, RecursionError):
        return []
    if not isinstance(raw, dict) or raw.get("schema") != SCHEMA or not isinstance(raw.get("history"), list):
        return []
    rows, seen = [], set()
    ls, ps = lpf.GRID_L + (lpf.UNKNOWN,), lpf.GRID_P + (lpf.UNKNOWN,)
    for h in raw["history"]:
        if not isinstance(h, dict):
            continue
        month, known, L, P, cell = h.get("month"), _date(h.get("known")), h.get("L"), h.get("P"), h.get("cell")
        if not isinstance(month, str) or not MONTH_RE.fullmatch(month) or month in seen or known is None \
                or L not in ls or P not in ps or cell != lpf.cell(L, P)[0]:
            continue
        seen.add(month)
        rows.append((month, known, L, P, cell))
    rows.sort()
    return rows


def lp_at(rows, sunday):
    got = None
    for month, known, L, P, cell in rows:                 # 기준월 순 — 마지막으로 맞는 것이 가장 새 달
        if known <= sunday:
            got = {"month": month, "L": L, "P": P, "cell": cell}
    return got


def site_at(snaps, sunday):
    """그 주 일요일 이하 마지막 날짜별 기록 → {snapshot, core, met, candidate}."""
    dates = [s["date"] for s in snaps]
    i = bisect.bisect_right(dates, sunday) - 1
    if i < 0:
        return {"snapshot": None, "core": None, "met": None, "candidate": None}
    s = snaps[i]
    reg = s["regime"] or {}
    return {"snapshot": s["date"].isoformat(), "core": reg.get("core"),
            "met": f"{sum(1 for r in s['rules'] if r['status'] == 'met')}/{len(s['rules'])}",
            "candidate": reg.get("candidate")}


# ── 셈 ─────────────────────────────────────────────────────────────────────────────────────────────────────
EMPTY = {"state": "pending", "start": None, "end": None, "change_bp": None, "demeaned_bp": None}


def outcome(points, w, late, h, base_bp):
    """한 주 · 한 선 · H주의 결과 — 출발만 정하고 나머지는 ledger_build.outcome."""
    if w["lock"] is None:
        return dict(EMPTY)                              # 확정 전 — 출발 점이 정해지지 않는다
    if late:
        return lb.outcome(points, _dt(w["lock"]["at"]).date(), h, base_bp)
    if not points:
        return {**EMPTY, "state": "missing"}
    dates = [d for d, _ in points]
    start, end = D.fromisoformat(w["week"]), D.fromisoformat(w["end"])
    i = bisect.bisect_right(dates, end) - 1
    if i < 0 or dates[i] < start:
        return dict(EMPTY) if dates[-1] < start else {**EMPTY, "state": "missing"}
    return lb.outcome(points, dates[i], h, base_bp)


def week_out(w, lines, base_bp, snaps, lp_rows):
    lock = None
    late = False
    if w["lock"]:
        late = is_late(D.fromisoformat(w["end"]), _dt(w["lock"]["at"]))
        lock = {"sha": w["lock"]["sha"], "at": w["lock"]["at"], "late": late, "first_upload": w["lock"]["first_upload"],
                "in_history": w["lock"]["in_history"]}
    sunday = D.fromisoformat(w["end"])
    return {"week": w["week"], "end": w["end"], "state": "confirmed" if lock else "in_progress", "lock": lock,
            "before_protocol": bool(lock) and lock["at"][:10] < PROTOCOL_FIXED,
            "dur": w["dur"], "cur": w["cur"], "edited_n": w["edited_n"], "regime_flag": w["regime_flag"],
            "regime_flag_other": w["regime_flag_other"], "changed_after": w["changed_after"], "removed": w["removed"],
            "site": site_at(snaps, sunday), "lp": lp_at(lp_rows, sunday),
            "outcomes": {str(h): {b: outcome(lines.get(key), w, late, h, base_bp[(h, key)]) for b, key, _, _ in PAIRS}
                         for h in HORIZONS}}


def summarize(weeks):
    """판정 묶음 × H — 약속 뒤(잠근 날 ≥ PROTOCOL_FIXED) · 확정 · 'done'만. 같은 묶음에서 (출발, 끝)이 같은 주는 같은 움직임이라
    한 번만 센다(starts) — starts ≥ N_MIN일 때만 그 출발 점들로 평균(평균을 뺀 값)과 오른 몫. n은 센 주 수."""
    out = {}
    for b, _, _, _ in PAIRS:
        out[b] = {}
        for name, verdicts in GROUPS[b]:
            out[b][name] = {}
            for h in HORIZONS:
                done = [w["outcomes"][str(h)][b] for w in weeks if w["state"] == "confirmed" and not w["before_protocol"]
                        and w[b]["verdict"] in verdicts and w["outcomes"][str(h)][b]["state"] == "done"]
                uniq = list({(o["start"], o["end"]): o for o in reversed(done)}.values())   # 같은 움직임은 하나(값이 같다)
                n, k, mean, up = len(done), len(uniq), None, None
                if k >= N_MIN:
                    dm = [Decimal(repr(o["demeaned_bp"])) for o in uniq if o["demeaned_bp"] is not None]
                    mean = lb._q(sum(dm) / k) if len(dm) == k else None
                    up = lb._q(Decimal(sum(1 for o in uniq if o["change_bp"] > 0)) / k, lb.Q2)
                out[b][name][str(h)] = {"n": n, "starts": k, "mean_demeaned_bp": mean, "up_share": up}
    return out


def sources(charts_date):
    return [{"series": sid, "url": rp.FRED_URL.format(sid),
             "citation": rp.citation(sid, charts_date) if charts_date else None,
             "citation_required": sid in rp.CITATION_REQUIRED} for _, _, sid, _ in PAIRS]


def chart_gaps(charts_date, lines):
    return ([] if charts_date else ["charts.json"]) + [key for _, key, _, _ in PAIRS if not lines.get(key)]


def build(weeks, source, charts_date, lines, snaps, lp_rows, now):
    """처리 상태 + 로컬 자료 → timeline.json 객체(같은 입력이면 generated_at 말고 같다)."""
    base_bp, bases, detail = {}, {}, {}
    for h in HORIZONS:
        bases[str(h)], detail[str(h)] = {}, {}
        for _, key, _, _ in PAIRS:
            b = lb.baseline(lines.get(key), h)
            base_bp[(h, key)] = None if b is None else lb._q(b[0])
            bases[str(h)][key] = base_bp[(h, key)]
            detail[str(h)][key] = None if b is None else {"n": b[1], "from": b[2].isoformat(), "to": b[3].isoformat()}
    used = [d for _, key, _, _ in PAIRS for d, _ in (lines.get(key) or [])]
    rows = [week_out(weeks[k], lines, base_bp, snaps, lp_rows) for k in sorted(weeks, reverse=True)]
    return {"schema": SCHEMA, "generated_at": now, "notice": NOTICE, "label": LABEL, "lp_label": lpf.LABEL,
            "source": {"repo": SOURCE_REPO, "path": SOURCE_PATH, "site": SOURCE_SITE, **source},
            "protocol": {"version": PROTOCOL_VERSION, "fixed": PROTOCOL_FIXED, "horizons_weeks": list(HORIZONS),
                         "pairs": [{"verdict": b, "series": sid, "label": label, "line": key} for b, key, sid, label in PAIRS],
                         "groups": {b: {name: list(vs) for name, vs in GROUPS[b]} for b in GROUPS},
                         "n_min": N_MIN, "tolerance_days": TOL_DAYS, "start_days": START_DAYS,
                         "open_utc": f"{OPEN_UTC[0]:02d}:{OPEN_UTC[1]:02d}", "open_kst": open_kst(), "text": protocol_text()},
            "charts": {"date": charts_date,
                       "window": {"from": min(used).isoformat() if used else None, "to": max(used).isoformat() if used else None},
                       "last": {key: lines[key][-1][0].isoformat() if lines.get(key) else None for _, key, _, _ in PAIRS},
                       "baseline": bases, "baseline_detail": detail},
            "weeks": rows, "summary": summarize(rows),
            "sources": sources(charts_date), "notices": [COMPUTED_NOTICE, COMPUTED_NOTICE_EN]}


# ── 실행 ─────────────────────────────────────────────────────────────────────────────────────────────────────
def update(prev, src, now=None):
    """직전 상태 + 새 커밋 → (weeks, source 일부, 새 커밋 수, 기록을 고쳐 썼는가). 실패는 FetchError — prev는 고치지 않는다.
    기록을 고쳐 썼으면(직전의 마지막 커밋이 목록에 없음) 잠근 주는 판정 · 시각 · first_upload를 그대로 넘겨받고(in_history = 잠근
    커밋이 지금 목록에 있는가), changed_after · removed는 잠근 시각 뒤의 커밋만으로 다시 센다. 확정 전인 주는 새 기록에서 다시."""
    stop = prev["source"]["newest_commit"] if prev else None
    commits, found = src.list_commits(stop)
    rebuilt = bool(stop) and not found
    if rebuilt and not commits:
        raise FetchError("empty")                       # 직전엔 커밋이 있었는데 목록이 비었다 — 잠금을 지우는 셈이 되지 않게 실패로
    kept = {}
    rewritten = prev["source"].get("rewritten_at") if prev else None
    if prev is None:
        weeks, skipped, newest = {}, 0, None
    elif rebuilt:
        shas = {s for s, _ in commits}
        weeks, skipped, newest, rewritten = {}, 0, None, now
        for k, w in prev["weeks"].items():
            if w["lock"]:
                nw = copy.deepcopy(w)
                nw["lock"]["in_history"] = nw["lock"]["sha"] in shas
                nw["changed_after"], nw["removed"] = None, None
                weeks[k] = nw
                kept[k] = _dt(nw["lock"]["at"])
    else:
        weeks, skipped, newest = copy.deepcopy(prev["weeks"]), prev["source"]["skipped_versions"], stop
    skipped += process(weeks, list(reversed(commits)), src, kept)
    return weeks, {"newest_commit": commits[0][0] if commits else newest, "skipped_versions": skipped,
                   "rewritten_at": rewritten}, len(commits), rebuilt


def main(argv=None, now=None, clock=time.monotonic, opener=None, env=None):
    ap = argparse.ArgumentParser(description="공개 기록 저장소의 주간 판정 + 그래프 자료 → 판단 연표(timeline.json)")
    ap.add_argument("--data", default=DEFAULT_DATA, help="읽을 사이트 데이터 폴더 — charts.json · history/ · lp.json · 직전 timeline.json")
    ap.add_argument("--out", default=None, help="쓸 폴더 (기본: --data와 같은 폴더)")
    ap.add_argument("--offline", action="store_true", help="요청 없이 직전 판정 기록으로 맥락·결과만 다시 셈")
    ap.add_argument("--budget", type=float, default=BUDGET, help=f"수신 전체 상한(초, 기본 {BUDGET:g})")
    ap.add_argument("--records-dir", default=None, help="API 대신 읽을 macro-notes-automation의 로컬 git 사본(테스트 · 손 확인)")
    ap.add_argument("--records-ref", default="HEAD", help="--records-dir에서 읽을 커밋 이름(기본 HEAD)")
    ap.add_argument("--rebuild", action="store_true", help="직전 파일의 처리 상태를 쓰지 않고 커밋 기록 전체를 다시 읽음")
    a = ap.parse_args(argv)
    env = os.environ if env is None else env
    now = now or datetime.datetime.now(UTC).isoformat(timespec="seconds")
    data = os.path.abspath(a.data)
    out = os.path.abspath(a.out) if a.out else data
    prev = None if a.rebuild else load_previous(os.path.join(data, FILE))
    charts_date, lines = lb.load_charts(os.path.join(data, "charts.json"))
    gaps = chart_gaps(charts_date, lines)

    src, weeks, source, note = None, None, None, ""
    if not a.offline:
        deadline = clock() + max(0.0, a.budget)
        try:
            src = GitSource(a.records_dir, a.records_ref, deadline, clock) if a.records_dir \
                else ApiSource(deadline, clock, opener, token_from(env))
            weeks, part, n_new, rebuilt = update(prev, src, now)
            source = {"newest_commit": part["newest_commit"], "checked_at": now, "via": src.via,
                      "skipped_versions": part["skipped_versions"], "rewritten_at": part["rewritten_at"]}
            note = f"새 커밋 {n_new}개"
            if rebuilt:
                gone = sum(1 for w in weeks.values() if w["lock"] and not w["lock"]["in_history"])
                print("::warning::[timeline_build] 직전 파일의 마지막 커밋이 공개 기록 저장소의 기록에 없다(기록을 고쳐 씀) — 잠근 "
                      f"판정은 그대로 두고 그 뒤 기록만 다시 셈(잠근 커밋이 지금 기록에 없는 주 {gone}개)", flush=True)
        except FetchError as e:
            weeks = None
            note = f"공개 기록을 읽지 못함({e.reason()})"
            print(f"::warning::[timeline_build] 공개 기록 저장소를 끝까지 읽지 못했다({e.reason()}) — 판정 기록은 직전 파일 그대로, "
                  "맥락·결과만 다시 셈", flush=True)
    if weeks is None:
        if prev is None:
            print(f"[timeline_build] {note or '오프라인'} · 직전 파일이 없다 — 아무것도 쓰지 않음")
            return 0
        weeks, source = prev["weeks"], dict(prev["source"])
        note = note or "오프라인 — 직전 판정 기록으로"
    if gaps:
        print(f"::warning::[timeline_build] 그래프 자료가 모자란다({', '.join(gaps)}) — timeline.json은 쓰지 않고 직전 파일을 그대로 둠",
              flush=True)
        return 0
    snaps, _ = lb.load_history(os.path.join(data, "history"))
    obj = build(weeks, source, charts_date, lines, snaps, load_lp(os.path.join(data, "lp.json")), now)
    try:
        wrote = lb.write(out, FILE, obj)
    except (OSError, ValueError) as e:
        print(f"[timeline_build] 쓰지 못함: {type(e).__name__}", file=sys.stderr)
        return 1
    rows = obj["weeks"]
    n_conf = sum(1 for w in rows if w["state"] == "confirmed")
    print(f"[timeline_build] {note} · 요청 {src.requests if src else 0}번 · 주 {len(rows)}개(확정 {n_conf} · 진행 중 "
          f"{len(rows) - n_conf}) · 마지막 커밋 {(obj['source']['newest_commit'] or '없음')[:7]} · 그래프 {charts_date} · "
          + ("씀: " + FILE if wrote else "내용 그대로 — 다시 쓰지 않음"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
