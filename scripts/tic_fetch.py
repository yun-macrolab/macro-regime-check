#!/usr/bin/env python3
"""참고 자료 — 미 재무부 TIC 해외 보유 미 국채(월말) (2026-11-19 추가, 운영자 결정 '1번 카드로 꺼내고 TIC도 추가해').

수급 참고 카드의 월간 부분이다(주간 부분은 supply_fetch.py — 뉴욕 연은 딜러 통계·해외 공적 수탁). 규칙이 아니다 — 충족·판정이
없고, 판정·공개본·그래프 스크립트는 이 파일(<out>/tic.json)을 읽지 않는다. 숫자만 싣는 참고 자료이고 예측이 아니다.

자료(미 연방 정부 저작물, 'public domain' — 인증 없음, 2026-11-19 이 환경에서 받아 꼴을 확인했다):
  표 5   TABLE_URL — 'Table 5: Major Foreign Holders of Treasury Securities', 'Holdings at end of time period', 'Billions of
         dollars'. 탭으로 나눈 글자(줄 끝 CRLF). 머리 줄 'Country<TAB>2026-09<TAB>2026-08 … 2025-09'(13개 달, 새 달부터),
         나라 20줄(그 달 보유가 큰 곳 — 달마다 바뀔 수 있다), 'All Other', 'Grand Total', 'Of Which: Foreign Official',
         'Of Which: Foreign Official Treasury Bills', 'Of Which: Foreign Official T-Bonds & Notes', 그 뒤 Notes(보관 기관 소재지
         주석 · SLT·BL2 양식으로 낸 추정치라는 주석). 매달 18일 무렵 두 달 전 월말 자료가 나온다(2026-09 자료는 2026-11-18).
  과거 표 HIST_URL — 해마다 한 덩어리(Dec … Jan 열), 2011년과 그 앞 덩어리는 'Jun'이 두 번인 13열(시리즈 구분), 이름은 따옴표가
         붙기도 하고("China, Mainland"), 합계 줄은 'Grand Total'·'For. Official'(옛 덩어리는 앞에 빈칸), 숫자는 1200 또는 1200.0.
         주석 17/: 2011년 12월부터 모든 달의 이표채 보유가 월간 SLT 보고 기준이다(단기채는 그 주석 밖 — 표 5 주석으로는 BL2 보고로
         추정) — 그 앞은 이표채 집계 방식이 달라(시리즈 구분) 쓰지 않고 그래프도 잇지 않는다(FROM_MONTH). 이름 끝에 주석 표시가
         붙은 나라 줄은 나라 그래프에 쓰지 않는다(표시의 뜻을 하나하나 가리지 않는 보수적 규칙). 그래서 영국 선은 2012-01부터다
         — 2011년 덩어리의 영국 줄만 'United Kingdom 2/'(주석 2/: 채널 제도·맨섬을 함께 묶은 줄, 그 묶음은 2016년 2월 자료 뒤에
         끝났다)이고 2012년부터의 덩어리는 표시 없는 'United Kingdom'이다. 표시 없는 2012~2016년
         2월 값이 새 기준으로 다시 계산된 것인지는 파일에 적혀 있지 않다. 고쳐 나오는 때는 정해져 있지 않다(파일의 개정 기록: 2026년에만
         1·7·9월 — 2026-11-19 받은 파일은 2026-09-16, 마지막 덩어리 2025년). 파일 날짜는 어느 해든 마지막으로 고친 날일 뿐이다 —
         날짜 줄 뒤의 '(2025 revised July 14, 2026)' 같은 줄이 해마다의 개정일이고(2026-09-16은 2024년 개정일, 2025년 덩어리는
         7월 판), 그래프 잇기는 이 해마다의 날짜를 쓴다(아래 chart).
  옛 파일 mfh.txt는 2023년 1월에서 멈췄다 — 쓰지 않는다.

계산(십억 달러, 표의 값 그대로 — 소수 첫째 자리):
  totals    해외 전체(Grand Total)·그중 해외 공적(Of Which: Foreign Official)·공적 중 단기채(T-bill)·공적 중 이표채(T-note · T-bond)의 마지막 달
            수준과 1개월·12개월 변화(그 달 − 전 달 · − 12개월 전 같은 달), 공적의 전체 대비 비중 %, 단기채의 공적 대비 비중 %.
            12개월 전 달이 표 5에 없으면 과거 표에서(표 5가 이긴다). share_pct는 어디서나 해외 전체 대비 — 단기채의 공적 대비
            비중은 bills_share_of_official_pct 한 곳에만(2026-11-19 검토 반영)
  countries 표 5의 나라 20줄을 표의 차례대로 + '그 밖' — 수준·1개월·12개월 변화(표 5의 같은 줄에서만)·전체 대비 비중 %.
            rank = 마지막 달 값의 큰 차례(같으면 표의 차례). 모르는 이름은 name_ko가 null(화면은 영어 이름)
  korea     한국 줄(같은 꼴) — 그 달 표에 없으면 null(상위 20개 밖, '그 밖'에 들어 있다)
  chart     해외 전체·해외 공적의 월말 값, 2011-12부터 마지막 달까지 — 직전 tic.json의 점 위에 과거 표, 그 위에 표 5를 덮는다
            (겹치는 달은 표 5가 이긴다 — 더 새 발표라 개정이 들어 있다). 표 5에서 빠진 달도 그 값이 전에 받은 표 5에서 온 것이고
            (table_asof — 선마다 {달: 그 값을 담은 표 5를 받은 날}) 그 받은 날이 과거 표에서 그 해 덩어리의 날짜(year_asof)보다
            뒤면 과거 표가 덮지 않는다 — 13개 달 창을 벗어난 달이 더 옛 개정치로 돌아가지 않게(2026-11-19 검토 반영). 그 해
            덩어리의 날짜는 그 해의 개정 줄('(YYYY revised …)'), 개정 줄이 없으면 그 덩어리를 처음 본 파일의 날짜(직전 tic.json의
            history.year_asof에서 이어 온다 — 다른 해를 고쳐 파일 날짜만 바뀐 것으로 그 해를 새 판으로 보지 않게), 처음 보면 파일
            날짜다(2026-11-19 2차 검토 반영 — 전엔 파일 날짜 하나로 견줘, 2024년만 고친 9/16/2026 파일이 7월 판인 2025년 덩어리까지
            새 판으로 쳤다). 그 해의 개정 줄이 표 5를 받은 날보다 뒤면 과거 표가 이기고 그 달의 table_asof는 지운다. 표 5 쪽은
            발표일이 아니라 받은 날이다(파일에 발표일이 없다) — 수신이 며칠 끊긴 사이 그 해가 고쳐 나오면 그 뒤에 받은 옛 발표의 표 5가
            이길 수 있다. 과거 표를 이번에 못 받았으면 직전 파일의 점을 그대로 두고, 과거 표의 마지막 달과
            표 5의 첫 달 사이가 비면(과거 표는 정해진 때 없이 고쳐 나온다) 직전 파일의 점으로 채운다. 그래도 빈 달은 null(선이
            끊긴다 — 없는 달을 곧은 선으로 잇지 않는다). 점의 날짜는 그 달 말일(월말 잔액). 덧줄(note)은 그래프의 첫 달이 2011-12일
            때만 '2011년 12월 이후 …', 더 늦게 시작하면(과거 표도 직전 점도 없을 때) 그 첫 달로 적는다
  chart_countries  일본·영국·중국 본토(같은 규칙, 그 나라 줄이 있는 달만 — 없는 달은 null). 영국 선이 2012-01부터이고 다른 선이
                   2011-12부터일 때만 덧줄에 그 까닭(UK_NOTE)
  chart_korea      한국(같은 규칙) — 화면이 쓸지 정한다(값의 크기가 달라 위 그래프와 따로 둔다)
  checks    표 5의 나라 20줄 + '그 밖'의 합 − 전체(열마다, 반올림 오차 SUM_TOL 안이면 맞음)와 공적 = 단기채 + 이표채(PARTS_TOL).
            어긋나도 숫자를 지어내거나 고치지 않는다 — 표 그대로 싣고 note에 적는다(아래 '닫힌 쪽으로 실패하는 것'과 다르다:
            합계 두 줄은 재무부가 발표한 값 그대로이고, 줄 하나가 빠지면 그 줄 자체는 읽기 단계에서 막힌다)

닫힌 쪽으로 실패하는 것(그 파일을 싣지 않고 직전 값을 '받지 못함'으로 이어 싣는다): 머리 줄('Country' 뒤 YYYY-MM 달들)이 없음,
  달이 한 달씩 이어지지 않음, 'All Other'·'Grand Total'·'Of Which: Foreign Official'이 없음(그 밖 줄이 이름만 바뀌면 나라 1위로
  읽혀 순위가 모두 밀리므로 — 2026-11-19 검토 반영), 이름에 other·others·total·rest·remainder 낱말이 든 나라 줄, 숫자가 아닌 칸
  (빈 칸은 어디서나 실패 — 나라·합계 줄은 칸이 모두 비어도 실패하고, 칸이 모두 빈 줄은 'Of which:' 같은 라벨 줄과 주석('Notes')·
  합계 뒤의 글 줄만 넘긴다(2026-11-19 2차 검토 반영 — 전엔 칸이 모두 빈 나라 줄을 라벨로 보고 빼 순위가 밀렸다), '*'만 나라 칸에서
  허용 — '5천만 달러 미만'이라 값 없음으로), 범위 밖의 값(전체 GRAND_BN, 공적
  OFFICIAL_BN이면서 전체 이하, 나라 ROW_BN), 같은 이름 두 번, 나라 줄이 COUNTRY_ROWS 밖, 마지막 달이 오늘 달보다 뒤, 마지막
  달이 직전 tic.json보다 앞(older). 단기채·이표채 줄은 없어도 읽는다(그 칸만 비운다). 과거 표는 2011-12 뒤의 달마다
  전체·공적이 있고 범위 안이며 달이 이어져야 하고, 마지막 달이나 파일 날짜가 직전 tic.json보다 앞이면(older — 옛 사본이 그래프를
  옛 개정치로 되돌리지 않게, 2026-11-19 2차 검토 반영) 받지 않으며, 파일 날짜가 오늘 뒤면 형식 오류다(아니면 과거 표만 실패 —
  직전 그래프 점으로 대신하고 표 5 숫자는 싣는다).

실패·이어 싣기(supply_fetch와 같은 원칙): 표 5를 못 받으면 직전 tic.json의 원표(table — 표 5를 읽은 그대로, 다시 계산의 원천)를
  '받지 못함(stale)'과 못 받기 시작한 날(failed_since)과 함께 다시 계산해 싣는다(직전 값이 없으면 사유만). 직전 파일이 깨졌거나 꼴이
  어긋나면 이어 실을 값이 없는 것으로 본다. 받은 날(retrieved)은 원표가 직전과 같으면 그대로 둔다 — 같은 자료로 매일 파일을 바꾸지
  않게. 같은 내용이면(생성 시각만 다르면) 파일을 다시 쓰지 않는다. 문구는 이 파일에 정해 둔 것뿐(오류 원문·예외 문자열은 공개 파일에
  싣지 않는다 — Actions 로그에는 정해 둔 사유만).

요청: 표 5 → 과거 표, 두 번. 단계 전체 BUDGET초 굳은 상한(요청 하나를 따로 스레드에서 돌리고 남은 예산만큼만 기다린다), 요청마다
  min(TIMEOUT, 남은 예산), 읽는 동안에도 마감을 본다, 응답 하나 MAX_BYTES. https · 같은 호스트만(다른 곳으로 넘겨지면 받지 않는다).
  머리글은 이 프로젝트를 밝히는 User-Agent(credit_fetch.UA — 연락처 없음, 연준 이사회·뉴욕 연은·미 재무부 요청과 같다). 받은 원문은
  <work>/tic/에 둔다(--offline이면 이것만 읽는다 — CI의 .work는 실행마다 사라지므로 과거 표의 대신은 직전 tic.json의 점이다).

종료코드: 0 표 5를 이번에 받음(과거 표만 못 받은 날도 0 — 경고 주석이 남는다) / 1 표 5를 못 받음(또는 파일을 쓰지 못함).
  워크플로 단계는 continue-on-error, 알림 없음. 못 받은 것은 표준 출력의 GitHub Actions 경고 주석(::warning::, 정해 둔 사유만)과
  화면의 '받지 못함' 표시로 본다.

산출: <out>/tic.json (압축 JSON)
사용법: python scripts/tic_fetch.py [--out data] [--work .work] [--budget 45] [--offline]
"""
import os, re, sys, json, time, argparse, calendar, datetime, threading, urllib.request, urllib.parse
from decimal import Decimal, ROUND_HALF_UP

SCRIPTS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPTS)
import credit_fetch as cf                     # User-Agent(UA — 이 프로젝트를 밝히는 글, 연락처 없음)만 쓴다
import render_public as rp                    # PUBLISHER(관계없음 고지의 이름)

SCHEMA = 1
REPO = os.path.dirname(SCRIPTS)
DEFAULT_OUT = os.path.join(REPO, "data")
DEFAULT_WORK = os.path.join(REPO, ".work")
FILE = "tic.json"
CACHE = "tic"                                 # <work>/tic/<원문 파일 이름>

HOST = "ticdata.treasury.gov"
BASE = f"https://{HOST}/resource-center/data-chart-center/tic/Documents/"
TABLE_URL = BASE + "slt_table5.txt"
HIST_URL = BASE + "mfhhis01.txt"
TABLE_CACHE, HIST_CACHE = "slt_table5.txt", "mfhhis01.txt"
SOURCE_NAME = ("U.S. Department of the Treasury, Treasury International Capital (TIC) System — Major Foreign Holders of "
               "Treasury Securities")
TABLE_TITLE = "Table 5: Major Foreign Holders of Treasury Securities"
_MONTHS = ("January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
           "November", "December")

BUDGET = 45                    # 단계 전체(초) — 두 요청을 합쳐(워크플로 단계 제한 안에서)
TIMEOUT = 20                   # 요청 하나엔 min(이것, 남은 예산) — 2026-11-19 이 환경에서 두 파일 모두 첫 바이트까지 8~11초였다
                               # (서버 루트 주소도 같았다 — 크기가 아니라 응답 시작이 늦다). 10초로는 표 5가 자주 끊겼다
MIN_LEFT = 1                   # 남은 예산이 이보다 적으면 요청하지 않는다
MAX_BYTES = 2_000_000          # 응답 하나(2026-11-19: 표 5 약 4KB, 과거 표 약 100KB)
CHUNK = 65536
FROM_MONTH = "2011-12"         # 과거 표 주석 17/ — 이달부터 모든 달의 이표채 보유가 월간 SLT 보고 기준(그 앞은 시리즈 구분)
GRAND_BN = (1000.0, 30000.0)   # 해외 전체의 그럴듯한 범위(십억 달러) — 밖이면 단위·열을 잘못 읽은 것으로 본다
OFFICIAL_BN = (100.0, 20000.0)
ROW_BN = (0.0, 5000.0)         # 나라 한 줄·공적 단기채·이표채
COUNTRY_ROWS = (5, 60)         # 표 5의 나라 줄 수
MAX_COLS = 24                  # 표 5의 달 수 상한
MIN_HIST_MONTHS = 12           # 과거 표에서 읽은 2011-12 뒤 달이 이보다 적으면 실패
SUM_TOL = 0.5                  # 나라 합 + 그 밖 − 전체(열마다, bn) — 2026-11-19 실자료 13열 최대 0.2
PARTS_TOL = 0.15 + 1e-9        # 공적 − (단기채 + 이표채) — 값 셋의 반올림 오차 상한(0.05 × 3)
KOREA = "Korea, South"
CHART_COUNTRIES = ("Japan", "United Kingdom", "China, Mainland")

MONTH_RE = re.compile(r"\d{4}-(0[1-9]|1[0-2])")
MONTH_ABBR = ("jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec")
FOOTNOTE = re.compile(r"\s+\d{1,2}/$")         # 이름 끝의 주석 표시('United Kingdom 2/', 'Belgium  5/')
# 과거 표 날짜 줄 뒤의 해마다 개정일 줄 — '(2025 revised July 14, 2026)'(따옴표는 _cells가 뗀다)
REVISED = re.compile(r"\((\d{4}) revised ([A-Za-z]{3,9})\.? (\d{1,2}), (\d{4})\)", re.I)
# 나라 줄로 받지 않는 이름 — 합계·나머지 줄이 이름만 바뀐 것('All Others', 'Other Countries', 'Rest of World')을 나라로 읽지 않게
NOT_COUNTRY = re.compile(r"\b(?:others?|totals?|rest|remainder)\b", re.I)

# 영어 이름(표의 글자, 따옴표·주석 표시를 뗀 것) → 한국어. 표 5(2026-11-19)와 과거 표(2011-12 뒤)의 모든 나라 + 자주 오르는 곳.
# 모르는 이름은 null(화면은 영어 이름)
NAME_KO = {
    "Japan": "일본", "United Kingdom": "영국", "China, Mainland": "중국 본토", "Belgium": "벨기에",
    "Cayman Islands": "케이맨 제도", "Canada": "캐나다", "Luxembourg": "룩셈부르크", "Ireland": "아일랜드", "France": "프랑스",
    "Taiwan": "대만", "Switzerland": "스위스", "Singapore": "싱가포르", "Hong Kong": "홍콩", "India": "인도",
    "Norway": "노르웨이", "Brazil": "브라질", "Korea, South": "한국", "Saudi Arabia": "사우디아라비아", "Bermuda": "버뮤다",
    "United Arab Emirates": "아랍에미리트", "Germany": "독일", "Netherlands": "네덜란드", "Australia": "호주",
    "Mexico": "멕시코", "Thailand": "태국", "Israel": "이스라엘", "Philippines": "필리핀", "Kuwait": "쿠웨이트",
    "Sweden": "스웨덴", "Poland": "폴란드", "Italy": "이탈리아", "Chile": "칠레", "Colombia": "콜롬비아", "Spain": "스페인",
    "El Salvador": "엘살바도르", "Peru": "페루", "Bahamas": "바하마", "Denmark": "덴마크", "Egypt": "이집트",
    "Finland": "핀란드", "Indonesia": "인도네시아", "Iraq": "이라크", "Kazakhstan": "카자흐스탄", "Malaysia": "말레이시아",
    "Oman": "오만", "Russia": "러시아", "South Africa": "남아프리카공화국", "Turkey": "튀르키예", "Uruguay": "우루과이",
    "Vietnam": "베트남", "Qatar": "카타르", "Austria": "오스트리아", "New Zealand": "뉴질랜드", "Argentina": "아르헨티나",
    "Bahrain": "바레인", "Portugal": "포르투갈", "Greece": "그리스", "Czech Republic": "체코", "Hungary": "헝가리",
    "Nigeria": "나이지리아", "Panama": "파나마", "British Virgin Islands": "영국령 버진아일랜드", "Jersey": "저지섬",
    "Guernsey": "건지섬", "Isle of Man": "맨섬", "Curacao": "퀴라소", "Belgium-Luxembourg": "벨기에·룩셈부르크",
    "China": "중국",
}
# 같은 나라의 다른 표기(글자만 남긴 소문자 키) → 위 표의 영어 이름
ALIASES = {"southkorea": KOREA, "korea": KOREA, "korearepublicof": KOREA, "republicofkorea": KOREA,
           "chinamainland": "China, Mainland", "mainlandchina": "China, Mainland", "uk": "United Kingdom",
           "turkiye": "Turkey", "trkiye": "Turkey", "uae": "United Arab Emirates", "caymanislandsthe": "Cayman Islands"}
OTHER_KO = "그 밖"

# 화면(site/supply.js의 TOTALS)과 같은 이름 — 한 칸에 한 이름(단기채 = T-bill, 이표채 = T-note · T-bond)
TOTAL_NAME = {"grand": "해외 전체 보유", "official": "그중 해외 공적", "official_bills": "공적 중 단기채(T-bill)",
              "official_notes_bonds": "공적 중 이표채(T-note · T-bond)"}

NOTICE = ("이 사이트의 규칙 판정에 쓰지 않는 참고 자료다. 미 재무부가 발표한 월말 보유 잔액과 거기서 계산한 차이·비중만 싣고, "
          "금리나 수요를 예측하지 않는다.")
NOTICES = [                                   # 화면이 그대로 싣는 고지 — 출처(한국어·영어) · 나라의 뜻 · 관계없음
    "값은 미 재무부 TIC(Treasury International Capital) 표 'Major Foreign Holders of Treasury Securities'의 월말 보유 잔액(십억 "
    "달러)을 그대로 옮긴 것이고, 1개월·12개월 변화와 비중은 macro-regime-check가 계산한 값이다. 미 재무부가 발표한 값이 아니다.",
    "Holdings are as published by the U.S. Department of the Treasury (TIC, Major Foreign Holders of Treasury Securities, "
    "billions of dollars, end of period). One- and twelve-month changes and shares are computed by macro-regime-check; they "
    "are not published by the U.S. Treasury.",
    "나라는 미국 안의 보관 기관·브로커딜러가 보고한 보유자(또는 보관 기관)의 소재지다 — 실제 주인의 나라와 다를 수 있다. 다른 나라의 "
    "보관 기관에 맡긴 국채는 그 보관 기관의 나라로 잡힐 수 있다(표의 주석, TIC FAQ 7번).",
    f"{rp.PUBLISHER} is not affiliated with, sponsored by, or endorsed by the U.S. Department of the Treasury.",
]
# 자료 파일을 직접 읽는 사람을 위한 단서(2026-11-19 통합 — 화면은 같은 뜻을 카드의 늘 보이는 한 줄과 접는 설명 '읽는 법'에 따로
# 적으므로 고지 칸에 다시 싣지 않는다). 평가 기준은 1차 출처로 확인하지 못해 양식 이름(표의 주석)까지만 적는다
CAVEATS = [
    "월말 잔액의 변화는 순매입이 아니다 — 가격·평가의 변화(이표채 보유를 보고하는 SLT 양식의 이름에 'Fair Value Changes'가 "
    "들어 있다)와 보관 기관을 옮긴 것도 잔액을 바꿀 수 있다. TIC는 거래 통계를 따로 발표하며 여기에는 싣지 않는다.",
    "추정치다 — 이표채(T-note · T-bond)는 TIC SLT 양식의 월간 보유, 단기채(T-bill)는 BL2 양식 보고로 추정한다(표의 주석). 다음 "
    "발표에서 고쳐질 수 있고, 과거 표도 정해진 때 없이 고쳐 나온다(그 파일의 개정 기록: 2026년에만 1·7·9월).",
    "표의 나라 20곳은 그 달 보유가 큰 곳이라 달마다 바뀔 수 있다. '그 밖'은 나머지 모두다.",
]
# 위 주간 '해외 공적 수탁'(supply.json의 custody — FRED WMTSECL1)과 왜 다른가. 숫자는 날마다 바뀌므로 글에 넣지 않는다.
# 한쪽이 다른 쪽의 일부라고 쓰지 않는다(2026-11-19 검토 반영) — 해외 보관 기관을 거친 공적 보유는 TIC에서 공적으로 잡히지 않을 수
# 있고, WMTSECL1은 해외 공적·국제 기관 몫이라 범위가 다르다. 평가 기준은 1차 출처로 확인하지 못해 '다를 수 있다'까지만
VS_CUSTODY_NOTE = ("TIC의 '해외 공적'은 미국 안의 보관 기관·브로커딜러가 외국 중앙은행·정부 등 공적 기관의 보유로 보고한 값이다(해외 "
                   "보관 기관을 거친 몫은 공적으로 잡히지 않을 수 있다). 주간 '해외 공적 수탁'(연준 H.4.1, WMTSECL1)은 뉴욕 연은이 "
                   "해외 공적·국제 기관을 위해 보관하는 국채라 범위가 다르고, 기준일(월말 · 수요일)과 평가 기준도 다를 수 있다. "
                   "두 숫자를 같은 양으로 보지 않는다.")
RELEASE_NOTE = "매달 18일 무렵 두 달 전 월말 자료"
CHART_NOTE = "2011년 12월 이후 · 월말 · 십억 달러 — 그 앞은 집계 방식이 달라(시리즈 구분) 잇지 않는다"
# 그래프가 2011-12보다 늦게 시작할 때(과거 표도 직전 점도 없을 때) — 그 첫 달로 적는다(2026-11-19 2차 검토 반영)
CHART_NOTE_LATE = ("{y}년 {m}월 이후 · 월말 · 십억 달러 — 그 앞 달은 받아 둔 자료에 없어 싣지 않는다(2011년 12월 앞은 집계 방식이 "
                   "달라 잇지 않는다)")
# 나라 그래프에만 덧붙인다 — 영국 선이 한 달 늦게 시작하는 까닭(과거 표의 주석 표시 줄은 쓰지 않는다)
UK_NOTE = ("영국 선은 2012년 1월부터 — 과거 표의 2011년 영국 줄에는 채널 제도·맨섬을 함께 묶은 줄이라는 주석 표시(2/)가 붙어 있어 "
           "쓰지 않는다(2012년부터의 영국 줄에는 표시가 없다)")
CHART_SOURCE = "자료: U.S. Department of the Treasury, TIC — Major Foreign Holders of Treasury Securities (표 5 · 과거 표) · 십억 달러"
REASONS = {                                   # 페이지·파일·로그에 나가는 실패 문구는 이것뿐
    "fetch": "수신 실패",
    "timeout": "수신 시간 상한",
    "format": "형식이 다름(표를 읽지 못함)",
    "range": "값이 범위 밖(단위나 열을 잘못 읽었을 수 있음)",
    "older": "받은 자료가 직전 자료보다 오래됨",
}
LABEL = {"table": "표 5", "history": "과거 표"}   # Actions 로그용(값은 찍지 않는다)


class TicError(Exception):
    """한 파일의 실패 — code는 REASONS의 키. 메시지는 정해 둔 짧은 글뿐(원격 글을 담지 않는다)."""
    def __init__(self, code):
        super().__init__(code)
        self.code = code


# ---------- 수신 ----------

def fetch_bytes(url, deadline, clock=time.monotonic, opener=None):
    """파일 한 건 — https · HOST만, 다른 곳으로 넘겨지면 받지 않는다(credit_fetch.fetch_bytes와 같은 꼴, 상한은 MAX_BYTES).
    남은 시간을 타임아웃으로 주고(최대 TIMEOUT) 읽는 동안에도 마감을 본다. Content-Length보다 덜 받으면 실패(잘린 표를 싣지 않게)."""
    left = deadline - clock()
    if left <= MIN_LEFT:
        raise TicError("timeout")
    if urllib.parse.urlsplit(url)[:2] != ("https", HOST):
        raise TicError("fetch")
    req = urllib.request.Request(url, headers={"User-Agent": cf.UA})
    chunks, size = [], 0
    with (opener or urllib.request.urlopen)(req, timeout=min(TIMEOUT, left)) as r:
        final = urllib.parse.urlsplit(r.geturl())
        if (final.scheme, final.netloc) != ("https", HOST):
            raise TicError("fetch")
        read = getattr(r, "read1", None) or r.read
        while True:
            if clock() > deadline:
                raise TicError("timeout")
            chunk = read(CHUNK)
            if not chunk:
                break
            size += len(chunk)
            if size > MAX_BYTES:
                raise TicError("fetch")
            chunks.append(chunk)
        rest = getattr(r, "length", None)
        if isinstance(rest, int) and not isinstance(rest, bool) and rest > 0:
            raise TicError("fetch")
    return b"".join(chunks)


def _within(fn, seconds):
    """fn()을 데몬 스레드에서 돌리고 seconds초만 기다린다 — 넘으면 TicError('timeout')(스레드는 버리고 결과를 쓰지 않는다)."""
    box = {}

    def run():
        try:
            box["v"] = fn()
        except BaseException as e:            # 스레드 밖으로 그대로 옮긴다
            box["e"] = e
    t = threading.Thread(target=run, daemon=True)
    t.start()
    t.join(max(0.0, seconds))
    if t.is_alive():
        raise TicError("timeout")
    if "e" in box:
        raise box["e"]
    return box.get("v")


def _decode(blob):
    return blob.decode("utf-8", "replace").lstrip("\ufeff")


def _write_cache(path, blob):
    """받은 원문을 캐시에(--offline용). 못 써도 그대로 — 캐시는 덤이다."""
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path + ".tmp", "wb") as f:
            f.write(blob)
        os.replace(path + ".tmp", path)
    except OSError:
        try:
            os.remove(path + ".tmp")
        except OSError:
            pass


def load(kind, work, today, offline=False, deadline=None, clock=time.monotonic, opener=None):
    """kind 'table'(표 5) 또는 'history'(과거 표) → 읽은 자료. 실패는 TicError(예외를 그대로 내보내지 않는다 — 뜻밖의 오류도
    TicError로 바꾼다). 온라인이면 받아서 읽히면 캐시에 쓴다, --offline이면 캐시만."""
    url, name = (TABLE_URL, TABLE_CACHE) if kind == "table" else (HIST_URL, HIST_CACHE)
    path = os.path.join(work, CACHE, name)
    try:
        if offline:
            try:
                with open(path, "rb") as f:
                    blob = f.read()
            except OSError:
                raise TicError("fetch")
        else:
            left = deadline - clock()
            if left <= MIN_LEFT:
                raise TicError("timeout")
            blob = _within(lambda: fetch_bytes(url, deadline, clock, opener), left)
        text = _decode(blob)
        parsed = parse_table(text, today) if kind == "table" else parse_history(text)
    except TicError:
        raise
    except Exception as e:                    # 연결·HTTP·시간 초과 — 원문은 싣지 않는다(로그엔 예외 이름만)
        timeout = isinstance(e, TimeoutError) or "timed out" in str(e).lower()
        print(f"[tic_fetch] {LABEL[kind]} 수신 오류: {type(e).__name__}", file=sys.stderr)
        raise TicError("timeout" if timeout else "fetch")
    if not offline:
        _write_cache(path, blob)
    return parsed


# ---------- 읽기 ----------

def _cells(line):
    """탭으로 나눈 칸 — 앞뒤 빈칸·따옴표를 떼고 안쪽 빈칸을 하나로."""
    return [re.sub(r"\s+", " ", c.strip().strip('"').strip()) for c in line.split("\t")]


def _rows(text):
    return [_cells(line) for line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n")]


def clean_name(s):
    """표의 이름 → (이름, 주석 표시가 있었나). 'United Kingdom 2/' → ('United Kingdom', True)."""
    s = re.sub(r"\s+", " ", str(s).strip().strip('"').strip())
    m = FOOTNOTE.search(s)
    return (s[:m.start()].strip(), True) if m else (s, False)


def _key(name):
    return re.sub(r"[^a-z]", "", str(name).lower())


_CANON = {_key(k): k for k in NAME_KO}


def canonical(name):
    """표기만 다른 같은 나라를 한 이름으로('South Korea' → 'Korea, South'). 모르는 이름은 그대로."""
    k = _key(name)
    return ALIASES.get(k) or _CANON.get(k) or name


def name_ko(name):
    return NAME_KO.get(canonical(name))


def row_kind(name):
    """합계 줄의 종류 — 'grand' · 'official' · 'bills' · 'notes' · 'other' · 'skip'(라벨) · 'bad'(나라가 아닌 모르는 줄) · None(나라)."""
    k = _key(name)
    if k == "grandtotal":
        return "grand"
    if k in ("forofficial", "foreignofficial", "ofwhichforeignofficial", "ofwhichforofficial"):
        return "official"
    if k.endswith("treasurybills"):
        return "bills"
    if k.endswith("tbondsnotes") or k.endswith("tbondsandnotes"):
        return "notes"
    if k == "allother":
        return "other"
    if k in ("ofwhich", "country", ""):
        return "skip"
    if NOT_COUNTRY.search(str(name)):
        return "bad"                                  # 나라가 아닌 줄의 모르는 이름 — 표를 받지 않는다
    return None


def _val(s):
    """칸 → float · '*'(5천만 달러 미만 — 값 없음) · ''(빈 칸) · None(숫자가 아님)."""
    s = str(s).strip().replace(",", "")
    if s in ("", "*"):
        return s
    if not re.fullmatch(r"-?\d+(?:\.\d+)?", s):
        return None
    x = float(s)
    return x if x == x and abs(x) != float("inf") else None


def _prev_month(m, n=1):
    y, mo = int(m[:4]), int(m[5:7]) - n
    while mo < 1:
        y, mo = y - 1, mo + 12
    return f"{y:04d}-{mo:02d}"


def _next_month(m):
    y, mo = int(m[:4]), int(m[5:7]) + 1
    return f"{y + (mo > 12):04d}-{(mo - 1) % 12 + 1:02d}"


def month_end(m):
    y, mo = int(m[:4]), int(m[5:7])
    return datetime.date(y, mo, calendar.monthrange(y, mo)[1]).isoformat()


def _in(v, rng):
    return isinstance(v, float) and rng[0] <= v <= rng[1]


def check_table(t, today):
    """원표(새로 읽은 것이든 직전 파일의 것이든)를 검사한다 — 어긋나면 TicError('format'|'range'). 고치지 않는다."""
    months = t.get("months") if isinstance(t, dict) else None
    if not (isinstance(months, list) and 2 <= len(months) <= MAX_COLS
            and all(isinstance(m, str) and MONTH_RE.fullmatch(m) for m in months)):
        raise TicError("format")
    if any(months[i + 1] != _prev_month(months[i]) for i in range(len(months) - 1)):
        raise TicError("format")                     # 한 달씩 거꾸로 이어지지 않는다
    if months[0] > f"{today.year:04d}-{today.month:02d}":
        raise TicError("format")
    n = len(months)

    def vec(v, allow_none):
        return (isinstance(v, list) and len(v) == n
                and all((x is None and allow_none) or (type(x) is float and x == x and abs(x) != float("inf"))
                        for x in v))
    for k in ("grand", "official", "other"):
        if not vec(t.get(k), False):
            raise TicError("format")                 # 'All Other'도 꼭 있어야 한다 — 나라 합 검사와 순위의 바탕
    for k in ("official_bills", "official_notes_bonds"):
        if t.get(k) is not None and not vec(t.get(k), False):
            raise TicError("format")
    rows = t.get("countries")
    if not (isinstance(rows, list) and COUNTRY_ROWS[0] <= len(rows) <= COUNTRY_ROWS[1]):
        raise TicError("format")
    names = set()
    for r in rows:
        if not (isinstance(r, list) and len(r) == 2 and isinstance(r[0], str) and r[0] and vec(r[1], True)):
            raise TicError("format")
        if canonical(r[0]) in names or row_kind(r[0]) is not None:
            raise TicError("format")
        names.add(canonical(r[0]))
    for i in range(n):
        g, o = t["grand"][i], t["official"][i]
        if not (_in(g, GRAND_BN) and _in(o, OFFICIAL_BN) and o <= g):
            raise TicError("range")
        if not _in(t["other"][i], (0.0, g)):
            raise TicError("range")
        for k in ("official_bills", "official_notes_bonds"):
            if t.get(k) is not None and not _in(t[k][i], (0.0, o + PARTS_TOL)):
                raise TicError("range")
        if any(r[1][i] is not None and not _in(r[1][i], ROW_BN) for r in rows):
            raise TicError("range")
    return t


def parse_table(text, today):
    """표 5의 글자 → 원표 {months(새 달부터), countries [[이름, 값…]…](표의 차례), other, grand, official, official_bills,
    official_notes_bonds}. 꼴이 어긋나면 TicError — 닫힌 쪽으로('All Other'·'Grand Total'·'Of Which: Foreign Official'은 꼭 있어야
    하고, 빈 칸은 어느 줄에서나 실패 — 나라·합계 줄은 칸이 모두 비어도 실패, '*'는 나라 칸만). 칸이 모두 빈 줄은 라벨 줄('Of which:')과
    주석('Notes')·합계 뒤의 글 줄만 넘긴다."""
    rows = _rows(text)
    hdr = None
    for i, r in enumerate(rows):
        if r and r[0].lower() == "country":
            cols = [(j, c) for j, c in enumerate(r) if j > 0 and c]
            if cols and all(MONTH_RE.fullmatch(c) for _, c in cols):
                hdr = i
                break
    if hdr is None:
        raise TicError("format")
    idx, months = [j for j, _ in cols], [c for _, c in cols]
    t = {"months": months, "countries": [], "other": None, "grand": None, "official": None, "official_bills": None,
         "official_notes_bonds": None}
    for r in rows[hdr + 1:]:
        name = clean_name(r[0])[0] if r else ""
        if not name and not any(r):
            continue                                  # 빈 줄
        raw = [r[j] if j < len(r) else "" for j in idx]
        if not name and set("".join(raw)) <= set("- "):
            continue                                  # 빈 줄 · 줄긋기('------')
        vals = [_val(c) for c in raw]
        if name.lower().startswith("notes"):
            break                                     # 주석 — 표 끝
        if all(v == "" for v in vals):
            # 칸이 모두 빈 줄 — 라벨 줄('Of which:')만 넘기고, 합계 뒤의 다른 글 줄은 표 끝(숫자가 있는 줄과 같은 규칙).
            # 나라·합계 줄이면 실패(2026-11-19 2차 검토 반영 — 전엔 라벨로 보고 빼 순위가 밀리고, 합계 뒤의 빈 단기채 줄은 표를
            # 끝내 이표채 줄까지 잃었다)
            kind = row_kind(name)
            if kind == "skip":
                continue
            if kind in (None, "bad") and (t["grand"] is not None or t["other"] is not None):
                break                                 # 합계 뒤의 글 줄('Totals may not add …' 같은 것도) — 표 끝
            raise TicError("format")
        if any(v is None or v == "" for v in vals):
            raise TicError("format")                  # 숫자가 아닌 칸·일부만 빈 줄
        kind = row_kind(name)
        if kind in ("skip", "bad") or not name:
            raise TicError("format")
        nums = [None if v == "*" else v for v in vals]
        if kind is None:
            if t["grand"] is not None or t["other"] is not None:
                break                                 # 합계 뒤에 나온 다른 줄 — 표 끝으로 본다
            t["countries"].append([name, nums])
            continue
        key = {"grand": "grand", "official": "official", "bills": "official_bills", "notes": "official_notes_bonds",
               "other": "other"}[kind]
        if t[key] is not None or None in nums:
            raise TicError("format")                  # 같은 합계 줄 두 번 · 합계 칸의 '*'
        t[key] = nums
    if t["grand"] is None or t["official"] is None or t["other"] is None:
        raise TicError("format")
    return check_table(t, today)


def _revised(m):
    """'(2025 revised July 14, 2026)'의 짝 → 'YYYY-MM-DD' 또는 None(달 이름·날짜가 어긋나면)."""
    mon = m.group(2)[:3].lower()
    if mon not in MONTH_ABBR:
        return None
    try:
        return datetime.date(int(m.group(4)), MONTH_ABBR.index(mon) + 1, int(m.group(3))).isoformat()
    except ValueError:
        return None


def parse_history(text):
    """과거 표 → {"months": {YYYY-MM: {"grand", "official", "countries": {영어 이름: 값}}}, "file_date": "YYYY-MM-DD"|None,
    "revised": {"YYYY": "YYYY-MM-DD"}} — revised는 날짜 줄 뒤의 해마다 개정일 줄(파일 날짜는 어느 해든 마지막으로 고친 날이라
    해마다 다르다). FROM_MONTH 앞 달·한 덩어리에 두 번 나온 달(시리즈 구분)·주석 표시가 붙은 나라 줄은 쓰지 않는다. 꼴이 어긋나면
    TicError(개정일 줄은 읽을 수 없으면 그 줄만 넘긴다)."""
    months, file_date, revised = {}, None, {}
    pending, cols = None, None
    for r in _rows(text):
        if not r:
            continue
        mon = [(j, c.lower()) for j, c in enumerate(r) if j > 0 and c]
        if not r[0] and len(mon) >= 6 and all(m in MONTH_ABBR for _, m in mon):
            pending, cols = mon, None                 # 달 이름 줄 — 다음 'Country' 줄의 해와 짝
            continue
        if r[0].lower() == "country":
            years = {j: c for j, c in enumerate(r) if j > 0 and c}
            if pending is None or set(years) != {j for j, _ in pending} or \
                    not all(re.fullmatch(r"\d{4}", y) for y in years.values()):
                pending, cols = None, None            # 읽을 수 없는 덩어리 — 그 달들은 빠진다(아래 이음 검사가 잡는다)
                continue
            keys = [(j, f"{years[j]}-{MONTH_ABBR.index(m) + 1:02d}") for j, m in pending]
            seen = {}
            for _, k in keys:
                seen[k] = seen.get(k, 0) + 1
            cols = [(j, k) for j, k in keys if seen[k] == 1 and k >= FROM_MONTH]
            for _, k in cols:
                if k in months:
                    raise TicError("format")          # 같은 달이 두 덩어리에
                months[k] = {"grand": None, "official": None, "countries": {}}
            pending = None
            continue
        if file_date is None and re.fullmatch(r"\d{1,2}/\d{1,2}/\d{4}", r[0]):
            mo, d, y = (int(x) for x in r[0].split("/"))
            try:
                file_date = datetime.date(y, mo, d).isoformat()
            except ValueError:
                pass
            cols = None                               # 날짜 줄 뒤는 주석
            continue
        rv = REVISED.fullmatch(r[0])
        if rv:
            d = _revised(rv)
            if d is not None and d > revised.get(rv.group(1), ""):
                revised[rv.group(1)] = d              # 같은 해가 두 번이면 늦은 날
            continue
        if not cols or set(r[0]) <= set("- "):
            continue
        name, marked = clean_name(r[0])
        kind = row_kind(name)
        if kind in ("skip", "other", "bills", "notes", "bad"):
            continue
        for j, k in cols:
            v = _val(r[j] if j < len(r) else "")
            if kind in ("grand", "official"):
                if not isinstance(v, float) or months[k][kind] is not None:
                    raise TicError("format")
                months[k][kind] = v
            elif isinstance(v, float) and not marked:
                months[k]["countries"][canonical(name)] = v
    if len(months) < MIN_HIST_MONTHS:
        raise TicError("format")
    keys = sorted(months)
    if any(keys[i + 1] != _next_month(keys[i]) for i in range(len(keys) - 1)):
        raise TicError("format")                      # 빈 달
    for k in keys:
        g, o = months[k]["grand"], months[k]["official"]
        if g is None or o is None:
            raise TicError("format")
        if not (_in(g, GRAND_BN) and _in(o, OFFICIAL_BN) and o <= g):
            raise TicError("range")
        if any(not _in(v, ROW_BN) for v in months[k]["countries"].values()):
            raise TicError("range")
    return {"months": months, "file_date": file_date, "revised": revised}


def year_asof(hres, prev_years, today):
    """과거 표의 해마다 덩어리의 날짜 {"YYYY": "YYYY-MM-DD"|None} — 그 해의 개정일 줄, 없으면 직전 tic.json이 적어 둔 그 해의 날짜
    (그 덩어리를 처음 본 파일의 날짜 — 다른 해를 고쳐 파일 날짜만 바뀐 것으로 그 해를 새 판으로 보지 않게), 그것도 없으면 파일
    날짜. 파일 날짜(없으면 오늘)보다 뒤의 날짜는 쓰지 않는다. merged가 표 5에서 온 점과 견주는 날짜다."""
    fd = hres.get("file_date")
    cap = fd or today.isoformat()
    out = {}
    for y in sorted({k[:4] for k in hres["months"]}):
        d = hres.get("revised", {}).get(y)
        if d is None or d > cap:
            p = (prev_years or {}).get(y)
            d = p if p is not None and p <= cap else fd
        out[y] = d
    return out


# ---------- 계산 ----------

def _r(v, nd=1):
    return None if v is None else round(v, nd) + 0.0     # + 0.0: -0.0을 0.0으로


def _chg(a, b):
    return None if a is None or b is None else _r(a - b)


def _int(v):
    """소수 첫째 자리 값을 정수로 — 0.5는 0에서 먼 쪽으로(표기 반올림). 부동소수 찌꺼기를 먼저 떼어 낸다."""
    return int(Decimal(repr(round(v, 1))).quantize(Decimal(1), rounding=ROUND_HALF_UP))


def _level(v):
    return "—" if v is None else f"{_int(v):,d}"


def _signed(v):
    """정수로 반올림한 부호 붙은 수(천 단위 쉼표). 0은 부호 없이, 없으면 '—'."""
    if v is None:
        return "—"
    r = _int(v)
    return "0" if r == 0 else f"{r:+,d}"


def _share(a, b):
    return None if a is None or not b else _r(a / b * 100)


def checks_of(t):
    """나라 합 + 그 밖 = 전체, 공적 = 단기채 + 이표채 — 열마다의 가장 큰 차(bn). 어긋나도 값은 그대로(note만)."""
    n = len(t["months"])
    gap = None
    if t.get("other") is not None:
        gap = max(abs(sum(r[1][i] or 0.0 for r in t["countries"]) + t["other"][i] - t["grand"][i]) for i in range(n))
    parts = None
    if t.get("official_bills") is not None and t.get("official_notes_bonds") is not None:
        parts = max(abs(t["official_bills"][i] + t["official_notes_bonds"][i] - t["official"][i]) for i in range(n))
    sum_ok = gap is None or gap <= SUM_TOL + 1e-9
    parts_ok = parts is None or parts <= PARTS_TOL
    notes = []
    if not sum_ok:
        notes.append(f"표의 나라별 값과 '그 밖'의 합이 전체와 최대 {gap:.1f}bn 어긋난다(반올림 오차보다 크다) — 표 그대로 싣는다.")
    if not parts_ok:
        notes.append(f"공적 보유가 단기채와 이표채의 합과 최대 {parts:.1f}bn 어긋난다 — 표 그대로 싣는다.")
    return {"sum_gap_bn": _r(gap), "sum_ok": sum_ok, "parts_gap_bn": _r(parts), "parts_ok": parts_ok,
            "note": " ".join(notes) or None}


def merged(table_vals, months, hist, prev, field, asof=None, hist_asof=None, retrieved=None):
    """({YYYY-MM: 값}, {YYYY-MM: 받은 날}) — 직전 파일의 점 < 과거 표 < 표 5 차례로 덮는다. field는 'grand' · 'official' 또는 나라
    영어 이름. asof는 직전 파일의 점 가운데 표 5에서 온 것의 받은 날(table_asof의 그 선) — 그 날이 과거 표에서 그 달이 든 해
    덩어리의 날짜(hist_asof — {"YYYY": 날짜|None}, year_asof)보다 뒤면(또는 그 해의 날짜를 모르면) 과거 표가 그 점을 덮지 않는다(더
    나중에 받은 표 5의 개정치 — 파일 날짜 하나로 견주면 다른 해를 고친 파일이 그 해까지 새 판으로 친다). 과거 표가 덮은 달은 받은
    날을 지우고, 표 5가 덮은 달은 retrieved로 적는다. 두 번째 값은 다음 파일의 table_asof가 된다."""
    out = {k: v for k, v in (prev or {}).items() if v is not None}
    when = {k: d for k, d in (asof or {}).items() if k in out}
    for k, e in (hist or {}).items():
        v = e.get(field) if field in ("grand", "official") else e["countries"].get(field)
        if v is None:
            continue
        d, hd = when.get(k), (hist_asof or {}).get(k[:4])
        if d is not None and (hd is None or d > hd):
            continue                                  # 직전 파일의 점이 과거 표의 그 해 덩어리보다 나중에 받은 표 5의 값
        out[k] = v
        when.pop(k, None)
    for k, v in zip(months, table_vals or []):
        if v is not None:
            out[k] = v
            when[k] = retrieved
    return out, when


def _points(series, last):
    """2011-12(또는 첫 값의 달)부터 last까지 달마다 [그 달 말일, 값|None] — 빈 달은 None(선이 끊긴다)."""
    have = sorted(k for k in series if FROM_MONTH <= k <= last)
    if not have:
        return []
    out, k = [], have[0]
    while k <= last:
        v = series.get(k)
        out.append([month_end(k), None if v is None else _r(v)])
        k = _next_month(k)
    return out


def _first(spec):
    """그래프의 첫 달(선마다의 첫 점 가운데 가장 이른 달) 또는 None."""
    starts = [x["points"][0][0][:7] for x in spec["lines"] if x["points"]]
    return min(starts) if starts else None


def _chart(key, title, lines, last):
    spec = {"key": key, "title": title, "unit": "bn", "years": None, "zero": False, "threshold": None, "note": CHART_NOTE,
            "source_note": CHART_SOURCE, "notices": [],
            "lines": [{"key": k, "label": label, "role": "series", "series": [series], "derived": False,
                       "points": _points(s, last)} for k, label, series, s in lines]}
    first = _first(spec)
    if first is not None and first > FROM_MONTH:              # 과거 표도 직전 점도 없어 늦게 시작한다 — 덧줄도 그 첫 달로
        spec["note"] = CHART_NOTE_LATE.format(y=int(first[:4]), m=int(first[5:7]))
    return spec


def _total(name, level, prev, year_ago, share=None):
    out = {"name": name, "level_bn": _r(level), "chg_1m_bn": _chg(level, prev), "chg_12m_bn": _chg(level, year_ago)}
    if share is not None:
        out["share_pct"] = share
    return out


def _line(t, share_text=None):
    parts = [f"{_level(t['level_bn'])}bn"]
    if share_text:
        parts.append(share_text)
    parts += [f"1개월 {_signed(t['chg_1m_bn'])}", f"12개월 {_signed(t['chg_12m_bn'])}"]
    return " · ".join(parts)


def citation(retrieved):
    """권장 인용 꼴(FRED 권장 인용과 같은 차례) — 날짜는 지금 원표를 처음 받은 날(retrieved). 달 이름은 지역 설정에 기대지 않는다."""
    d = datetime.date.fromisoformat(retrieved)
    return (f"U.S. Department of the Treasury, Treasury International Capital (TIC) System, {TABLE_TITLE} and historical "
            f"table, retrieved from {TABLE_URL} and {HIST_URL}, {_MONTHS[d.month - 1]} {d.day}, {d.year}.")


def present(t, hist, prev_pts, hist_meta, retrieved, prev_asof=None):
    """원표 t(+ 과거 표 · 직전 그래프 점과 그 점의 받은 날) → 화면에 싣는 숫자·문구·그래프. 이어 실을 때도 이걸로 다시 만든다."""
    months = t["months"]
    m0 = months[0]
    p1, p12 = _prev_month(m0), _prev_month(m0, 12)
    prev_asof = prev_asof or {}
    meta = hist_meta or {}
    years = meta.get("year_asof") if isinstance(meta.get("year_asof"), dict) else {}
    # 과거 표의 해마다 덩어리의 날짜 — year_asof가 없는 해는 파일 날짜로
    hist_asof = {y: years.get(y, meta.get("file_date")) for y in {k[:4] for k in hist}} if hist is not None else None
    asof = {}

    def ser(vals, key, field):
        out, when = merged(vals, months, hist, prev_pts.get(key), field, prev_asof.get(key), hist_asof, retrieved)
        keep = {k: d for k, d in when.items() if FROM_MONTH <= k <= m0}
        if keep:
            asof[key] = dict(sorted(keep.items()))
        return out
    g_ser = ser(t["grand"], "grand", "grand")
    o_ser = ser(t["official"], "official", "official")
    at = lambda vals, k: vals[months.index(k)] if vals is not None and k in months else None
    grand = g_ser[m0]
    totals = {
        "grand": _total(TOTAL_NAME["grand"], grand, g_ser.get(p1), g_ser.get(p12)),
        "official": _total(TOTAL_NAME["official"], o_ser[m0], o_ser.get(p1), o_ser.get(p12), _share(o_ser[m0], grand)),
        "official_bills": None, "official_notes_bonds": None, "bills_share_of_official_pct": None}
    for k in ("official_bills", "official_notes_bonds"):
        if t.get(k) is not None:
            totals[k] = _total(TOTAL_NAME[k], at(t[k], m0), at(t[k], p1), at(t[k], p12))
    if totals["official_bills"] is not None:
        totals["bills_share_of_official_pct"] = _share(totals["official_bills"]["level_bn"], o_ser[m0])

    latest = [(i, r[1][0]) for i, r in enumerate(t["countries"])]
    order = sorted((x for x in latest if x[1] is not None), key=lambda x: -x[1])
    rank = {i: n + 1 for n, (i, _) in enumerate(order)}

    def row(i, name, vals, ko):
        lv = vals[0]
        out = {"rank": rank.get(i), "name_en": name, "name_ko": ko, "level_bn": _r(lv),
               "chg_1m_bn": _chg(lv, at(vals, p1)), "chg_12m_bn": _chg(lv, at(vals, p12)), "share_pct": _share(lv, grand)}
        share = f"전체의 {out['share_pct']:.1f}%" if out["share_pct"] is not None else None
        out["line"] = _line(out, share)
        return out
    countries = [row(i, r[0], r[1], name_ko(r[0])) for i, r in enumerate(t["countries"])]
    if t.get("other") is not None:
        countries.append({**row(None, "All Other", t["other"], OTHER_KO), "rank": None})
    korea = next((c for c in countries if c["rank"] is not None and canonical(c["name_en"]) == KOREA), None)

    o = totals["official"]
    lines = {"grand": _line(totals["grand"]),
             "official": _line(o, f"전체의 {o['share_pct']:.1f}%" if o.get("share_pct") is not None else None),
             "official_bills": None, "official_notes_bonds": None,
             "korea": (_line(korea, f"{korea['rank']}위 · 전체의 {korea['share_pct']:.1f}%") if korea
                       else "이번 달 표(보유 상위 나라)에 없음 — '그 밖'에 들어 있음")}
    if totals["official_bills"] is not None:
        lines["official_bills"] = _line(totals["official_bills"], f"공적의 {totals['bills_share_of_official_pct']:.1f}%")
    if totals["official_notes_bonds"] is not None:
        lines["official_notes_bonds"] = _line(totals["official_notes_bonds"])

    rows = {canonical(r[0]): r[1] for r in t["countries"]}
    chart = _chart("tic_totals", "해외 보유 미 국채(월말)",
                   [("grand", TOTAL_NAME["grand"], "Grand Total", g_ser),
                    ("official", TOTAL_NAME["official"], "Foreign Official", o_ser)], m0)
    chart_countries = _chart("tic_countries", "주요 보유 나라(월말)",
                             [(c, NAME_KO[c], c, ser(rows.get(c), c, c)) for c in CHART_COUNTRIES], m0)
    uk = next((x for x in chart_countries["lines"] if x["key"] == "United Kingdom"), None)
    # 영국 선만 2012-01부터이고 다른 선이 2011-12부터일 때만(과거 표의 2011년 영국 줄이 주석 표시 줄이라) — 모든 선이 늦게 시작하면 아니다
    if uk and uk["points"] and uk["points"][0][0][:7] == _next_month(FROM_MONTH) and _first(chart_countries) == FROM_MONTH:
        chart_countries["note"] = CHART_NOTE + " · " + UK_NOTE
    chart_korea = _chart("tic_korea", "한국 보유(월말)", [(KOREA, NAME_KO[KOREA], KOREA, ser(rows.get(KOREA), KOREA, KOREA))], m0)
    return {"month": m0, "month_end": month_end(m0), "prev_month": p1, "year_ago": p12, "retrieved": retrieved,
            "totals": totals, "countries": countries, "korea": korea, "lines": lines, "checks": checks_of(t),
            "chart": chart, "chart_countries": chart_countries, "chart_korea": chart_korea, "history": hist_meta,
            "table_asof": asof,
            "table": {k: t[k] for k in ("months", "countries", "other", "grand", "official", "official_bills",
                                        "official_notes_bonds")},
            "source": {"table": TABLE_URL, "history": HIST_URL, "name": SOURCE_NAME, "citation": citation(retrieved)},
            "notices": list(NOTICES), "caveats": list(CAVEATS), "vs_custody_note": VS_CUSTODY_NOTE,
            "release_note": RELEASE_NOTE}


# ---------- 직전 파일 ----------

def _is_day(v):
    try:
        return isinstance(v, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", v) is not None and \
            datetime.date.fromisoformat(v) is not None
    except ValueError:
        return False


def previous(out):
    """직전 tic.json → dict. 없거나 못 읽거나 판이 다르면 {}."""
    try:
        with open(os.path.join(out, FILE), encoding="utf-8") as f:
            js = json.load(f)
    except (OSError, ValueError):
        return {}
    return js if isinstance(js, dict) and js.get("schema") == SCHEMA else {}


def prev_table(prev, today):
    """직전 파일의 원표와 받은 날 → (원표, retrieved) 또는 None(없거나 꼴이 어긋남 — 이어 실을 값이 없는 것으로 본다)."""
    t = prev.get("table")
    if not isinstance(t, dict) or not _is_day(prev.get("retrieved")):
        return None
    t = {k: t.get(k) for k in ("months", "countries", "other", "grand", "official", "official_bills",
                               "official_notes_bonds")}
    if isinstance(t["countries"], list):
        t["countries"] = [list(r) if isinstance(r, list) else r for r in t["countries"]]
    fl = lambda v: [float(x) if type(x) is int else x for x in v] if isinstance(v, list) else v
    for k in ("grand", "official", "other", "official_bills", "official_notes_bonds"):
        t[k] = fl(t[k])                                   # JSON이 1200.0을 1200으로 써도(다른 도구) 같은 값
    if isinstance(t["countries"], list):
        t["countries"] = [[r[0], fl(r[1])] if isinstance(r, list) and len(r) == 2 else r for r in t["countries"]]
    try:
        return check_table(t, today), prev["retrieved"]
    except TicError:
        return None


def prev_points(prev):
    """직전 파일의 그래프 점 → {선 키: {YYYY-MM: 값}} — 'grand' · 'official' · 나라 영어 이름. 꼴이 어긋난 점은 버린다."""
    out = {}
    for ck in ("chart", "chart_countries", "chart_korea"):
        c = prev.get(ck)
        for line in (c.get("lines") if isinstance(c, dict) and isinstance(c.get("lines"), list) else []):
            if not isinstance(line, dict) or not isinstance(line.get("key"), str) or \
                    not isinstance(line.get("points"), list):
                continue
            pts = {}
            for p in line["points"]:
                if (isinstance(p, list) and len(p) == 2 and _is_day(p[0]) and p[0] == month_end(p[0][:7])
                        and p[0][:7] >= FROM_MONTH and type(p[1]) in (int, float) and p[1] == p[1]
                        and _in(float(p[1]), GRAND_BN if line["key"] == "grand" else
                                OFFICIAL_BN if line["key"] == "official" else ROW_BN)):
                    pts[p[0][:7]] = float(p[1])
            out[line["key"]] = pts
    return out


def prev_asof(prev, old):
    """직전 파일의 그래프 점 가운데 표 5에서 온 것의 받은 날 → {선 키: {YYYY-MM: YYYY-MM-DD}}. 직전 파일의 table_asof(꼴이 맞는
    칸만)에 더해, 직전 원표(old — 이미 검사를 거친 것)의 달은 그 원표를 받은 날로 적는다 — table_asof가 없던 옛 파일도 바로 앞
    발표의 개정치를 잃지 않게. 늦은 날이 이긴다."""
    out = {}
    ta = prev.get("table_asof")
    for key, by in (ta.items() if isinstance(ta, dict) else []):
        if isinstance(key, str) and isinstance(by, dict):
            ok = {m: d for m, d in by.items() if isinstance(m, str) and MONTH_RE.fullmatch(m) and _is_day(d)}
            if ok:
                out[key] = ok
    if old:
        t, got = old
        lines = [("grand", t["grand"]), ("official", t["official"])] + [(canonical(r[0]), r[1]) for r in t["countries"]]
        for key, vals in lines:
            for m, v in zip(t["months"], vals):
                if v is not None and (out.get(key, {}).get(m) or "") < got:
                    out.setdefault(key, {})[m] = got
    return out


def prev_hist_meta(prev, today):
    """직전 파일의 과거 표 정보 — 꼴이 어긋난 칸과 오늘 뒤의 날짜는 버린다(깨진 날짜가 뒤의 과거 표를 모두 'older'로 막지 않게)."""
    h = prev.get("history")
    if not isinstance(h, dict):
        return {}
    day = lambda v: v if _is_day(v) and v <= today.isoformat() else None
    ya = h.get("year_asof")
    return {"file_date": day(h.get("file_date")),
            "last_month": h["last_month"] if isinstance(h.get("last_month"), str) and MONTH_RE.fullmatch(h["last_month"])
            else None,
            "failed_since": h["failed_since"] if _is_day(h.get("failed_since")) else None,
            "year_asof": {y: day(d) for y, d in ya.items() if isinstance(y, str) and re.fullmatch(r"\d{4}", y)}
            if isinstance(ya, dict) else {}}


# ---------- 산출물 ----------

def build(tres, hres, prev, now):
    """tres(원표 또는 TicError) · hres(과거 표 또는 TicError) · 직전 파일 → 산출물 dict."""
    today = now.date()
    head = {"schema": SCHEMA, "generated_at": now.isoformat(timespec="seconds"), "notice": NOTICE}
    old = prev_table(prev, today)
    pmeta = prev_hist_meta(prev, today)
    pts = prev_points(prev)
    when = prev_asof(prev, old)

    if not isinstance(hres, TicError):
        last, fd, pfd = max(hres["months"]), hres.get("file_date"), pmeta.get("file_date")
        if fd is not None and fd > today.isoformat():
            hres = TicError("format")                 # 오늘 뒤의 파일 날짜 — 날짜 줄을 잘못 읽은 것
        elif (pmeta.get("last_month") and last < pmeta["last_month"]) or (fd and pfd and fd < pfd):
            hres = TicError("older")                  # 마지막 달이나 파일 날짜가 직전보다 앞 — 옛 사본(2026-11-19 2차 검토 반영)
    if isinstance(hres, TicError):
        hist = None
        hist_meta = {"ok": False, "stale": bool(pts.get("grand")), "error": REASONS[hres.code],
                     "failed_since": pmeta.get("failed_since") or today.isoformat(),
                     "file_date": pmeta.get("file_date"), "last_month": pmeta.get("last_month"),
                     "year_asof": pmeta.get("year_asof") or {}}
    else:
        hist = hres["months"]
        hist_meta = {"ok": True, "stale": False, "error": None, "failed_since": None, "file_date": hres.get("file_date"),
                     "last_month": max(hist), "year_asof": year_asof(hres, pmeta.get("year_asof"), today)}

    table = None if isinstance(tres, TicError) else tres
    code = tres.code if isinstance(tres, TicError) else None
    if table is not None and old and table["months"][0] < old[0]["months"][0]:
        table, code = None, "older"
    if table is not None:
        retrieved = old[1] if old and old[0] == table else today.isoformat()
        return {**head, "ok": True, "stale": False, "error": None, "failed_since": None,
                **present(table, hist, pts, hist_meta, retrieved, when)}
    since = prev.get("failed_since") if prev.get("ok") is False and _is_day(prev.get("failed_since")) else today.isoformat()
    if old:
        return {**head, "ok": False, "stale": True, "error": REASONS[code], "failed_since": since,
                **present(old[0], hist, pts, hist_meta, old[1], when)}
    return {**head, "ok": False, "stale": False, "error": REASONS[code], "failed_since": since, "history": hist_meta,
            "source": {"table": TABLE_URL, "history": HIST_URL, "name": SOURCE_NAME}, "notices": list(NOTICES),
            "caveats": list(CAVEATS), "release_note": RELEASE_NOTE}


def differs(out, data):
    """저장 파일과 내용이 다른가(생성 시각은 빼고). 없거나 못 읽으면 다르다."""
    try:
        with open(os.path.join(out, FILE), encoding="utf-8") as f:
            old = json.load(f)
    except (OSError, ValueError):
        return True
    strip = lambda d: {k: v for k, v in d.items() if k != "generated_at"} if isinstance(d, dict) else d
    return strip(old) != strip(json.loads(json.dumps(data)))


def write(out, data):
    """같은 폴더의 임시 파일을 다 쓴 뒤 바꿔 넣는다. 실패하면 임시 파일을 지우고 예외를 그대로(data/에 .tmp가 남지 않게)."""
    os.makedirs(out, exist_ok=True)
    path = os.path.join(out, FILE)
    tmp = path + ".tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(json.dumps(data, ensure_ascii=False, separators=(",", ":")))
        os.replace(tmp, path)
    except OSError:
        try:
            os.remove(tmp)
        except OSError:
            pass
        raise


def annotate(text):
    """GitHub Actions 경고 주석 한 줄(표준 출력). 명령 글자는 규약대로 바꾼다."""
    print("::warning::" + text.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A"), flush=True)


def main(argv=None, opener=None, now=None, clock=time.monotonic):
    ap = argparse.ArgumentParser(description="미 재무부 TIC 해외 보유 미 국채(표 5 · 과거 표) → <out>/tic.json")
    ap.add_argument("--out", default=DEFAULT_OUT, help="사이트 데이터 폴더 (기본: 저장소의 data/)")
    ap.add_argument("--work", default=DEFAULT_WORK, help="작업 폴더 — 원문 캐시는 <work>/tic/ (기본: 저장소의 .work/)")
    ap.add_argument("--budget", type=float, default=BUDGET, help=f"수신 전체 상한(초, 기본 {BUDGET})")
    ap.add_argument("--offline", action="store_true", help="요청하지 않고 <work>/tic/의 캐시만 읽는다(로컬 확인용)")
    a = ap.parse_args(argv)
    out, work = os.path.abspath(a.out), os.path.abspath(a.work)
    now = now or datetime.datetime.now(datetime.timezone.utc)
    today = now.date()
    deadline = clock() + a.budget
    res = {}
    for kind in ("table", "history"):
        try:
            res[kind] = load(kind, work, today, a.offline, deadline, clock, opener)
        except TicError as e:
            res[kind] = e
    data = build(res["table"], res["history"], previous(out), now)
    # 공개 저장소의 Actions 로그 — 달과 정해 둔 사유만 찍고 값은 찍지 않는다
    if data["ok"]:
        print(f"[tic_fetch] 표 5 {data['month']} 월말까지")
    else:
        kept = f" — 직전 값({data['month']} 월말) 유지" if data["stale"] else ""
        annotate(f"TIC 해외 보유 표 5 받지 못함: {data['error']}{kept}")
    h = data["history"]
    if h["ok"]:
        print(f"[tic_fetch] 과거 표 {h['last_month']}까지")
    else:
        annotate(f"TIC 과거 표 받지 못함: {h['error']}" + (" — 직전 그래프 점 유지" if h["stale"] else ""))
    if data.get("checks") and data["ok"] and data["checks"]["note"]:
        annotate("TIC 표 5 확인: 합계가 어긋남(표 그대로 실음)")
    try:
        if differs(out, data):
            write(out, data)
    except OSError as e:
        print(f"[tic_fetch] {FILE}를 쓰지 못함: {type(e).__name__}", file=sys.stderr)
        return 1
    return 0 if data["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
