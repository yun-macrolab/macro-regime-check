#!/usr/bin/env python3
"""참고 자료 — 국채–OIS 스프레드(par), 2·5·10·30년 (2026-11-15 추가, 운영자 결정 '국채–OIS 공개 카드도').

운영자의 비공개 월간 점검 [수급 구조] 끝 줄(비공개 원본 ois_dtcc.py)을 공개한 것이다. 2026-11-15 운영자가 DTCC 이용 약관을
확인하고 공개하기로 했다 — 그 전에는 비공개 줄이었다. 비공개 원본과 같은 고르는 법·창이다(코드는 가져오지 않고 여기서 따로
쓴다 — 고치면 양쪽을 같이. 비공개 쪽 test_ois_dtcc.PairTest가 형제 폴더가 있을 때 같은 입력으로 견준다). 숫자만 싣는 측정
기록이다 — 문턱이 없고 금리를 예측하지 않는다. 이 사이트의 규칙 점검·공개본·그래프 스크립트는 이 파일의 산출물을 읽지 않는다.

왜: 국채 금리에서 같은 만기 OIS를 빼면 정책금리 기대 경로가 대부분 지워지고 국채만의 몫(공급·딜러가 국채를 들고 있는 비용·
  편의수익)이 남는다. 기간 프리미엄 카드는 사실상 10년 금리 전체의 움직임을 따라 수급 쪽 몫을 따로 보는 칸이 없었다.
  부호: 국채 − OIS = −(시장에서 말하는 '스와프 스프레드').
자료: DTCC Data Repository (U.S.) LLC가 CFTC 규칙(17 CFR Part 43)으로 공개하는 금리 스와프 거래 보고의 하루 파일(URL — 인증
  없음, 압축 약 1.3MB·2만여 행, 주말·휴일에도 작은 파일이 있다, 대략 2년 전까지 — 그보다 오래된 날은 S3가 403으로 답한다).
  출처 표기: CITATION — DTCC 로고·링크는 쓰지 않는다. 국채 금리는 FRED의 재무부 par 곡선(DGS2·DGS5·DGS10·DGS30, 연준 이사회
  H.15 — 'Public Domain: Citation Requested', FRED 권장 인용을 함께).
남기는 것 — 두 파일(둘 다 <out>/, 커밋된다):
  STORE(ois_days.json)  날마다 만기마다 {n: 거래 수, med: 고정금리 중앙값(%), q1, q3} — 셈한 값뿐. 원 행·거래 식별자
                        (Dissemination Identifier)는 쓰지 않는다(zip은 메모리에서만 풀고 버린다). 받을 날(targets — 어제부터
                        TARGET_DAYS일 안의 평일)만 두고 나머지는 지운다. 다시 볼 날의 표(tries)와 마지막 수신 상태(status — 정해 둔
                        사유 코드뿐)도 여기에.
  FILE(ois.json)        화면에 싣는 두 칸(level · ten) — 받아 둔 날과 FRED로 계산한다(DTCC 요청 0번).
고르는 행(하루 파일마다 — 비공개 원본과 같다):
  - 새 거래만: Action type NEWT · Event type TRAD. 같은 파일의 취소(EROR)가 가리키는 거래는 뺀다
  - SOFR OIS: 'UPI Underlier Name'에 USD와 SOFR, 'Notional currency-Leg 1' USD(연방기금 OIS·다른 통화는 빠진다). 사후 가격
    (Post-priced swap indicator TRUE)은 뺀다
  - 고정 다리가 정확히 하나('Fixed rate-Leg 1'·'Leg 2' 중 하나만). 단위: 1보다 작으면 소수(0.0467 = 4.67%), 그 밖은 %. RATE_PCT 밖은 뺀다
  - 현물 시작: 체결일(UTC 날짜)이 파일 날짜와 같고, 시작일이 체결일부터 SPOT_DAYS일 안
  - 만기: (끝 − 시작)/365.25가 2·5·10·30년에서 TENOR_TOL년 안(패키지 거래도 넣는다)
  - 만기마다 {n, 중앙값, 사분위(statistics.quantiles n=4 — 하나뿐이면 셋 다 그 값)}
창(window — 비공개 원본과 같다): 그날 그 만기 거래가 MIN_TRADES건 이상이고 같은 날 FRED DGS가 있는 날만. 스프레드 = (DGS − 그날
  중앙값) × 100, bp. 끝 = 10년 스프레드가 있는 마지막 날(오늘 날짜는 읽지 않는다). 수준 = 끝 이하 마지막 LEVEL_N개의 중앙값(모두
  끝에서 LEVEL_SPAN일 안 — 아니면 없음). 10년 13주 변화 = 수준 − 끝 WEEKS13일 전 이하 LEVEL_N개의 중앙값(같은 규칙). 1년 범위 =
  (끝 − YEAR, 끝] 안 10년 스프레드의 LEVEL_N개 이동 중앙값의 최저~최고와 그 날(같은 값이면 이른 날), 받은 날 = 그 안의 10년
  스프레드 날 수 / 그 YEAR일의 평일 수. 끝이 STALE_DAYS일보다 오래되면 '받지 못함(stale)'. 같은 시각이 아니다 — DGS는 장 마감
  쪽 값, OIS는 하루 동안의 거래. par 기준이라 zero 기준으로 잰 자료와 수준을 그대로 견주지 않는다.
비공개 원본과 다른 곳(공개판의 틀 — cds_fetch와 같다): 받아 둔 날을 날짜별 파일이 아니라 한 저장 파일에 두고, 실패 문구는 정해
  둔 사유 코드뿐(오류 원문을 싣지 않는다), 직전 ois.json의 숫자를 '받지 못함'과 함께 이어 싣는다. 화면에는 끝 날 10년의 사분위 폭
  (iqr10)을 더 싣는다. 하루 파일의 행은 필요한 칸만 남겨 읽는다(같은 행을 고른다 — 메모리를 덜 쓰려고).

수신(sync — 비공개 원본·cds_fetch와 같은 규칙): 빠진 평일만, 새 날부터. DTCC 수신 전체 BUDGET초 굳은 상한(요청 하나를 따로
  스레드에서 돌리고 남은 예산만큼만 기다린다). 파일 하나에 약 1초라 첫 몇 번의 실행은 다 받지 못한다 — 다음 실행이 이어 받는다
  (새 날부터라 첫 실행 뒤에도 수준·13주 변화가 나온다).
  - 연결 실패·시간 초과(요청 하나에 TIMEOUT을 거의 다 준 때) — 멈추고, 같은 날(UTC)의 다음 실행은 건너뛴다(--force면 다시).
  - 예산이 모자라 짧게 준 요청의 시간 초과 — 실패가 아니라 '못 받은 날'(다음 실행 몫).
  - 그날 하나의 문제(HTTP 5xx·깨진 zip·지원하지 않는 압축·너무 큰 파일·필요한 칸이 없는 파일·셈 오류)와 없는 파일(S3 403
    AccessDenied)·보관된 파일(403 InvalidObjectState) — 그날만 건너뛴다. RETRY_DAYS일 안의 '없음'은 아직 안 올라온 것이라
    세지 않는다. 같은 날짜는 하루 한 번만 다시 보고, 서로 다른 GIVE_UP일 실패한 날은 더 받지 않는다.
  - 받은 것 없이 최근 RECENT_ALARM일 안의 날이 ALARM_DAYS번 실패하면 '주소·접근이 바뀌었을 수 있음'으로 멈춘다.
  FRED(DGS 넷 — 10년 먼저): FRED_BUDGET초 안에서 요청마다 min(ai_invest_fetch.TIMEOUT, 남은 예산), 기본 머리글
  (ai_invest_fetch.load_series), 원문 캐시는 <work>/ois/. 온라인에서 받지 못한 만기는 그 만기만 '—'(10년을 못 받으면 창이 없다).

종료코드: 0 수신이 멈추지 않았고 한 칸이라도 지금 값 / 1 그 밖(파일을 쓰지 못함 포함). 워크플로 단계는 continue-on-error, 알림 없음.

사용법: python scripts/ois_fetch.py [--out data] [--work .work] [--budget 70] [--offline] [--force]
"""
import os, io, re, sys, csv, json, time, zlib, zipfile, argparse, datetime, statistics, urllib.request, urllib.error

SCRIPTS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPTS)
import cds_fetch as cd                        # 같은 DTCC 버킷 — 실패 종류(FetchError)·굳은 마감(_within)·쓰기·꼴 검사를 그대로 쓴다
import ai_invest_fetch as ai                  # FRED 수신(load_series — 기본 머리글, 읽는 동안에도 마감)·인용의 달 이름
import render_public as rp                    # FRED 시리즈 주소 꼴

REPO = os.path.dirname(SCRIPTS)
DEFAULT_OUT = os.path.join(REPO, "data")
DEFAULT_WORK = os.path.join(REPO, ".work")
SCHEMA = 1
FILE = "ois.json"
STORE = "ois_days.json"
CACHE = "ois"                                 # <work>/ois/<ID>.csv — FRED 원문 캐시(커밋하지 않는다)
D = datetime.date
URL = "https://kgc0418-tdw-data-0.s3.amazonaws.com/cftc/eod/CFTC_CUMULATIVE_RATES_{:%Y_%m_%d}.zip"

BUDGET = 70                  # DTCC 수신 전체(초) — FRED_BUDGET과 합쳐 워크플로 단계 제한(2분) 안에서
FRED_BUDGET = 20             # FRED 네 요청 전체(초)
TIMEOUT = 10                 # 요청 하나엔 min(이것, 남은 예산)
MIN_LEFT = 1                 # 남은 예산이 이보다 적으면 요청하지 않는다
MAX_BYTES = 40 * 1024 * 1024
CHUNK = 65536
TARGET_DAYS = 400            # 받을 날(어제부터, 평일만) — 1년 범위 + 13주 전 + 여유
RETRY_DAYS = 3               # 이보다 최근 날의 '파일 없음'은 아직 안 올라온 것으로 본다(세지 않는다)
GIVE_UP = 3                  # 서로 다른 날 이만큼 실패한 날짜는 더 받지 않는다
RECENT_ALARM = 10            # 받은 것 없이 이 안의 날이 ALARM_DAYS번 실패하면 멈춘다
ALARM_DAYS = 2
TENORS = (2, 5, 10, 30)
TENOR_TOL = 0.03             # 해 — 약 11일
SPOT_DAYS = 5
RATE_PCT = (0.05, 15.0)      # 이 밖의 고정금리(%)는 단위 오기로 본다
MIN_TRADES = 10              # 그날 그 만기 거래가 이보다 적으면 그날은 쓰지 않는다
LEVEL_N = 5                  # 5영업일 중앙값
LEVEL_SPAN = 14              # 최근 LEVEL_N개가 이 날 수 안에 있어야 한다
WEEKS13 = 91
YEAR = 364
STALE_DAYS = 7               # 끝 날이 이보다 오래면 '받지 못함'으로 싣는다
DGS = {2: "DGS2", 5: "DGS5", 10: "DGS10", 30: "DGS30"}
FRED_ORDER = (10, 2, 5, 30)  # 10년 먼저 — 예산이 모자라면 나머지가 빠진다(10년이 없으면 창이 없다)
SPREAD_BP = (-500.0, 500.0)  # 칸 값의 꼴 검사 — 이 밖의 스프레드는 싣지 않는다
QUART = 30.0                 # 받아 둔 사분위의 꼴 검사(|%| 상한 — 거래가 둘뿐이면 사분위가 자료 밖으로 나간다)
COLUMNS = ("Dissemination Identifier", "Original Dissemination Identifier", "Action type", "Event type",
           "Execution Timestamp", "Effective Date", "Expiration Date", "Fixed rate-Leg 1", "Fixed rate-Leg 2",
           "Notional currency-Leg 1", "Post-priced swap indicator", "UPI Underlier Name")   # 없으면 그날은 형식 오류
KEYS = [str(t) for t in TENORS]
DAY_KEYS = {"n", "med", "q1", "q3"}

# 출처 — DTCC 공개 배포(CFTC Part 43). 이용 조건 표시(sources[].licence) — 2026-11-15 운영자가 DTCC 이용 약관을 확인
CITATION = ("Source: DTCC Data Repository (U.S.) LLC, CFTC swap data public dissemination (17 CFR Part 43); "
            "site calculations")
DATASET = "CFTC_CUMULATIVE_RATES"
_BOARD = "Board of Governors of the Federal Reserve System (US)"
# FRED 권장 인용의 출처·제목(2026-11-15 시리즈 쪽 제목 그대로 — 넷 다 JSON-LD license가 공공 영역)
SOURCES = {sid: (_BOARD, f"Market Yield on U.S. Treasury Securities at {t}-Year Constant Maturity, Quoted on an "
                         "Investment Basis") for t, sid in DGS.items()}
LICENCE = {DATASET: "cftc-part43-public-dissemination", **{sid: "public-domain" for sid in SOURCES}}
NOTICE = ("이 사이트의 규칙 점검에 쓰지 않는 참고 자료다. 공개 거래 보고와 재무부 par 금리로 잰 측정 기록이고, 금리를 "
          "예측하지 않는다.")
COMPUTED_NOTICE = ("스프레드·중앙값·범위는 macro-regime-check가 DTCC 공개 금리 스와프 거래 보고의 하루 파일과 FRED의 재무부 "
                   "par 금리로 계산한 값이다 — 원 행·거래 식별자는 싣지 않고 만기별 중앙값만 남긴다.")
CAVEAT_NOTICE = ("DTCC Data Repository (U.S.)에 보고된 거래만 들어 있다 — 다른 스와프 데이터 저장소에 보고된 거래는 없다. "
                 "체결된 거래의 고정금리라 호가 중간값(mid)이 아니고, 다음 날 이후 취소된 거래는 섞인다.")
STORE_NOTICE = ("날마다 만기마다 SOFR OIS 새 거래 수(n)·고정금리 중앙값(med, %)·사분위(q1·q3)만 — DTCC 공개 금리 스와프 "
                "거래 보고로 센 값이다. 원 행·거래 식별자는 없다.")
ORDER = ["level", "ten"]
TITLE = {"level": f"국채 − OIS (par, {LEVEL_N}영업일 중앙값)", "ten": "10년 국채 − OIS — 13주 변화와 1년 범위"}
# 페이지·파일·로그에 나가는 실패 문구는 이것뿐
REASONS = {
    "fetch": "수신 실패",
    "timeout": "수신 시간 초과",
    "alarm": "최근 날의 파일을 받지 못함 · 주소나 접근 방식이 바뀌었을 수 있음",
    "none": "받아 둔 자료 없음",
    "fred": "국채 금리(FRED)를 받지 못함",
    "old": "새 날 자료가 들어오지 않음",
    "older": "받은 자료가 직전 자료보다 오래됨",
    "format": "계산할 자료가 모자람",
}
_STOP = {"net": "fetch", "timeout": "timeout"}      # FetchError.kind → 멈출 때의 사유 코드


# ---------- 작은 도움 ----------

def _s(v):
    """부호 붙인 정수 bp — 0은 부호 없이(비공개 원본 render_lines와 같은 꼴)."""
    if v is None:
        return "—"
    s = f"{v:+.0f}"
    return "0" if s in ("+0", "-0") else s


def _day(s):
    try:
        return D.fromisoformat(str(s)[:10])
    except ValueError:
        return None


# ---------- 하루 파일 → 만기별 중앙값 (비공개 원본 ois_dtcc와 같은 산식) ----------

def _rate(s):
    try:
        v = float(str(s).replace(",", ""))
    except ValueError:
        return None
    if v < 1:
        v *= 100
    return v if RATE_PCT[0] <= v <= RATE_PCT[1] else None


def is_sofr_ois(row):
    name = (row.get("UPI Underlier Name") or "").upper()
    return "SOFR" in name and "USD" in name and (row.get("Notional currency-Leg 1") or "").upper() == "USD"


def summarize(rows, day):
    """하루 파일의 행(dict) → {"2": {n, med, q1, q3}, …} — 만기마다(거래가 없으면 n 0). 셈한 값뿐이다."""
    rows = list(rows)
    cancelled = set()
    for x in rows:
        if x.get("Action type") == "EROR":
            cancelled.add(x.get("Original Dissemination Identifier") or "")
            cancelled.add(x.get("Dissemination Identifier") or "")
    cancelled.discard("")
    got = {t: [] for t in TENORS}
    for x in rows:
        if x.get("Action type") != "NEWT" or x.get("Event type") != "TRAD" or not is_sofr_ois(x):
            continue
        if (x.get("Dissemination Identifier") or "") in cancelled:
            continue
        if (x.get("Post-priced swap indicator") or "").strip().upper() in ("TRUE", "Y", "YES"):
            continue
        f1, f2 = (x.get("Fixed rate-Leg 1") or "").strip(), (x.get("Fixed rate-Leg 2") or "").strip()
        if bool(f1) == bool(f2):
            continue
        r = _rate(f1 or f2)
        ex, ef, mt = _day(x.get("Execution Timestamp")), _day(x.get("Effective Date")), _day(x.get("Expiration Date"))
        if r is None or ex != day or ef is None or mt is None or not 0 <= (ef - ex).days <= SPOT_DAYS:
            continue
        yrs = (mt - ef).days / 365.25
        t = next((t for t in TENORS if abs(yrs - t) <= TENOR_TOL), None)
        if t is not None:
            got[t].append(r)
    out = {}
    for t, v in got.items():
        if v:
            q = statistics.quantiles(v, n=4) if len(v) >= 2 else [v[0], v[0], v[0]]
            out[str(t)] = {"n": len(v), "med": round(statistics.median(v), 6), "q1": round(q[0], 6), "q3": round(q[2], 6)}
        else:
            out[str(t)] = {"n": 0, "med": None, "q1": None, "q3": None}
    return out


def parse_zip(blob):
    """zip 바이트 → 행(dict, COLUMNS의 칸만) 목록 — 첫 csv 하나. 디스크에 쓰지 않는다. 필요한 칸이 없으면 그날의 형식 오류.
    대소문자·띄어쓰기만 바뀐 머리글은 받아들인다. 빈 줄은 건너뛰고, 칸이 모자란 행의 빈 칸은 None(csv.DictReader와 같다)."""
    try:
        with zipfile.ZipFile(io.BytesIO(blob)) as zf:
            names = [n for n in zf.namelist() if n.lower().endswith(".csv")]
            if not names:
                raise cd.FetchError("day")
            with zf.open(names[0]) as f:
                reader = csv.reader(io.TextIOWrapper(f, encoding="utf-8-sig", newline=""))
                head = next(reader, None) or []
                canon = {" ".join(c.split()).lower(): c for c in COLUMNS}
                head = [canon.get(" ".join(h.split()).lower(), h) for h in head]
                if any(c not in head for c in COLUMNS):
                    raise cd.FetchError("day")                         # 필요한 칸이 없다 — 0건으로 남기지 않는다
                at = [(c, head.index(c)) for c in COLUMNS]
                return [{c: (r[i] if i < len(r) else None) for c, i in at} for r in reader if r]
    except cd.FetchError:
        raise
    except (zipfile.BadZipFile, zlib.error, EOFError, OSError, UnicodeDecodeError, csv.Error, ValueError,
            NotImplementedError, RuntimeError):                   # 지원하지 않는 압축(Deflate64 등)·암호화도 그날만의 문제
        raise cd.FetchError("day")


def fetch(day, timeout, opener=None, deadline=None, clock=time.monotonic):
    """그날 파일 → 행 목록, 파일이 없으면 None(S3 403 AccessDenied·보관됨·404). 그 밖의 실패는 cd.FetchError(kind로 종류).
    deadline(clock 기준)을 주면 덩어리마다 확인한다 — 넘으면 kind 'budget'. cds_fetch.fetch와 같은 규칙."""
    opener = opener or urllib.request.urlopen
    try:
        with opener(URL.format(day), timeout=timeout) as r:
            read = getattr(r, "read1", None) or r.read            # read1: 수신 한 번마다 돌아와 마감을 자주 본다
            chunks, size = [], 0
            while True:
                if deadline is not None and clock() > deadline:
                    raise cd.FetchError("budget")
                chunk = read(CHUNK)
                if not chunk:
                    break
                chunks.append(chunk)
                size += len(chunk)
                if size > MAX_BYTES:
                    raise cd.FetchError("day")
            blob = b"".join(chunks)
    except cd.FetchError:
        raise
    except urllib.error.HTTPError as e:
        body = b""
        try:
            body = e.read(4096) or b""
            e.close()
        except Exception:
            pass
        if e.code == 404 or (e.code == 403 and any(k in body for k in (b"AccessDenied", b"NoSuchKey", b"InvalidObjectState"))):
            return None                                           # 없음 · 보관됨 — 그날만
        raise cd.FetchError("day" if e.code >= 500 else "net")
    except Exception as e:
        raise cd.FetchError("timeout" if cd._is_timeout(e) else "net")
    return parse_zip(blob)


# ---------- 받아 둔 날(STORE) ----------

def _num(v, lo, hi):
    return cd._is_num(v) and lo <= v <= hi


def day_ok(tenors):
    """받아 둔 하루가 꼴에 맞는가 — 네 만기 모두 {n, med, q1, q3}, 거래가 있으면 중앙값이 RATE_PCT 안이고 q1 ≤ med ≤ q3."""
    if not isinstance(tenors, dict) or set(tenors) != set(KEYS):
        return False
    for v in tenors.values():
        if not isinstance(v, dict) or set(v) != DAY_KEYS or not cd._is_int(v["n"]):
            return False
        if v["n"] == 0:
            if (v["med"], v["q1"], v["q3"]) != (None, None, None):
                return False
        elif not (_num(v["med"], *RATE_PCT) and _num(v["q1"], -QUART, QUART) and _num(v["q3"], -QUART, QUART)
                  and v["q1"] <= v["med"] <= v["q3"]):
            return False
    return True


def empty_store():
    return {"days": {}, "tries": {}, "status": {}}


def load_store(out):
    """<out>/ois_days.json → {days, tries, status}. 없거나 깨졌거나 판이 다르면 빈 저장(다시 받는다). 꼴이 어긋난 날은 버린다."""
    try:
        with open(os.path.join(out, STORE), encoding="utf-8") as f:
            js = json.load(f)
    except (OSError, ValueError):
        return empty_store()
    if not isinstance(js, dict) or js.get("schema") != SCHEMA or not isinstance(js.get("days"), dict):
        return empty_store()
    days = {k: v for k, v in js["days"].items() if cd._is_day(k) and day_ok(v)}
    raw = js.get("tries") if isinstance(js.get("tries"), dict) else {}
    tries = {k: {"n": v["n"], "last": v["last"], "why": v["why"]} for k, v in raw.items()
             if cd._is_day(k) and isinstance(v, dict) and cd._is_int(v.get("n"), GIVE_UP) and cd._is_day(v.get("last"))
             and v.get("why") in ("absent", "bad")}
    st = js.get("status") if isinstance(js.get("status"), dict) else {}
    status = {}
    if cd._is_day(st.get("date")) and (st.get("error") is None or st.get("error") in REASONS):
        status = {"date": st["date"], "error": st.get("error")}
    return {"days": days, "tries": tries, "status": status}


def targets(today):
    """받을 날 — 어제부터 TARGET_DAYS일 안의 평일, 새 날부터."""
    days = (today - datetime.timedelta(days=i) for i in range(1, TARGET_DAYS + 1))
    return [d for d in days if d.weekday() < 5]


def sync(store, today, budget=BUDGET, opener=None, clock=time.monotonic, force=False):
    """빠진 평일만 받아 store(dict)를 고친다 — {fetched, absent, bad, missing, gave_up, error(사유 코드), skipped}.
    어떤 실패도 예외로 내보내지 않는다. 연결 실패·시간 초과(요청에 TIMEOUT을 다 준 때)는 멈추고 같은 날의 다음 실행은
    건너뛴다(force면 다시). 그날 하나의 문제·없는 파일은 그날만 건너뛰고 tries에 적는다."""
    out = {"fetched": 0, "absent": 0, "bad": 0, "missing": 0, "gave_up": 0, "error": None, "skipped": False}
    iso = today.isoformat()
    try:
        st = store.get("status") or {}
        if not force and st.get("date") == iso and st.get("error"):
            return {**out, "error": st["error"], "skipped": True}
        days = store["days"]
        want = targets(today)
        keep = {d.isoformat() for d in want}
        tries = {k: v for k, v in (store.get("tries") or {}).items() if k in keep}
        todo = []
        for d in want:
            if d.isoformat() in days:
                continue
            t = tries.get(d.isoformat()) or {}
            if int(t.get("n") or 0) >= GIVE_UP:
                out["gave_up"] += 1
                continue
            if t.get("last") == iso:                       # 오늘 이미 본 날짜 — 다음 날 다시
                continue
            todo.append(d)
        deadline, alarm = clock() + budget, 0

        def mark(d, why):
            t = tries.get(d.isoformat()) or {}
            tries[d.isoformat()] = {"n": int(t.get("n") or 0) + 1, "last": iso, "why": why}
        for i, d in enumerate(todo):
            left = deadline - clock()
            if left < MIN_LEFT:
                out["missing"] = len(todo) - i
                break
            give = min(TIMEOUT, left)
            failed = None
            try:
                rows = cd._within(lambda: fetch(d, give, opener, deadline=deadline, clock=clock), left)
            except cd.FetchError as e:
                if e.kind == "budget" or (e.kind == "timeout" and give < TIMEOUT - 1):
                    out["missing"] = len(todo) - i             # 예산이 모자라 짧게 준 요청 — 실패가 아니다
                    break
                if e.kind in _STOP:
                    out["error"] = _STOP[e.kind]
                    out["missing"] = len(todo) - i
                    break
                failed, rows = "bad", None
            if rows is None:
                failed = failed or ("absent" if (today - d).days > RETRY_DAYS else None)
                if failed:
                    out[failed] += 1
                    mark(d, failed)
                    if (today - d).days <= RECENT_ALARM:
                        alarm += 1
                    if alarm >= ALARM_DAYS and not out["fetched"]:
                        out["error"] = "alarm"
                        out["missing"] = len(todo) - i - 1
                        break
                continue
            try:
                tenors = summarize(rows, d)
            except Exception:                                    # 셈이 깨지는 꼴의 파일 — 그날만의 문제로
                out["bad"] += 1
                mark(d, "bad")
                continue
            days[d.isoformat()] = tenors
            tries.pop(d.isoformat(), None)
            out["fetched"] += 1
        store["tries"] = tries
        store["status"] = {"date": iso, "error": out["error"]}
    except Exception:
        out["error"] = out["error"] or "fetch"
        try:
            store["status"] = {"date": iso, "error": out["error"]}
        except Exception:
            pass
    return out


def prune(store, today):
    """받을 날(targets)만 남긴다."""
    keep = {d.isoformat() for d in targets(today)}
    store["days"] = {k: v for k, v in store["days"].items() if k in keep}
    store["tries"] = {k: v for k, v in store["tries"].items() if k in keep}


def store_text(store):
    """저장 파일 글 — 하루가 한 줄(커밋 차이가 그날 줄로만 보이게). 날짜 차례."""
    head = {"schema": SCHEMA, "notice": STORE_NOTICE, "source": CITATION, "tenors": KEYS}
    lines = [json.dumps(k, ensure_ascii=False) + ":" + json.dumps({t: store["days"][k][t] for t in KEYS},
                                                                  ensure_ascii=False, separators=(",", ":"))
             for k in sorted(store["days"])]
    tries = {k: store["tries"][k] for k in sorted(store["tries"])}
    return ("{" + json.dumps(head, ensure_ascii=False, separators=(",", ":"))[1:-1] + ',\n"days":{\n' + ",\n".join(lines)
            + "\n},\n\"tries\":" + json.dumps(tries, ensure_ascii=False, separators=(",", ":"))
            + ",\n\"status\":" + json.dumps(store["status"], ensure_ascii=False, separators=(",", ":")) + "}\n")


# ---------- FRED ----------

def load_fred(work, offline=False, fred_load=None, clock=time.monotonic, budget=FRED_BUDGET, opener=None):
    """{만기: [(date, %)]}와 {ID: 실패 코드}. 온라인에서 캐시로 대신한 것은 실패('fetch')로 센다(fred_load를 준 경우 — 테스트)."""
    cache = os.path.join(work, CACHE)
    dgs, errors = {}, {}
    deadline = clock() + budget
    for t in FRED_ORDER:
        sid = DGS[t]
        left = deadline - clock()
        if not offline and left <= MIN_LEFT:
            errors[sid] = "fetch"
            continue
        try:
            if fred_load:
                series, src = fred_load(sid, cache, offline=offline, timeout=min(ai.TIMEOUT, max(1.0, left)))
            else:
                series, src = ai.load_series(sid, cache, offline, deadline, clock, opener)
        except Exception:
            errors[sid] = "fetch"
            continue
        if src != "net" and not offline:
            errors[sid] = "fetch"
            continue
        if not series:
            errors[sid] = "format"
            continue
        dgs[t] = series
    return dgs, errors


# ---------- 창 (비공개 원본 ois_dtcc.window와 같은 산식) ----------

def _held(days, today):
    """받아 둔 날(오늘 날짜는 빼고) — [(date, 만기 dict)] 날짜 차례."""
    out = []
    for k in sorted(days):
        d = D.fromisoformat(k) if cd._is_day(k) else None
        if d is not None and d < today:
            out.append((d, days[k]))
    return out


def spreads(days, today, dgs):
    """{만기: [(날짜, bp)]} — 거래가 MIN_TRADES건 이상인 날, 같은 날 DGS가 있을 때만. dgs = {만기: [(date, %)]}."""
    out = {t: [] for t in TENORS}
    yields = {t: dict(x for x in (dgs.get(t) or []) if x[0] <= today) for t in TENORS}
    for d, js in _held(days, today):
        for t in TENORS:
            e = js.get(str(t)) or {}
            if (e.get("n") or 0) >= MIN_TRADES and e.get("med") is not None and d in yields[t]:
                out[t].append((d, (yields[t][d] - e["med"]) * 100))
    return out


def _med_upto(series, end, span=LEVEL_SPAN):
    """end 이하 마지막 LEVEL_N개 — 모두 end에서 span일 안이어야 한다. 중앙값 또는 None."""
    pick = [v for d, v in series if d <= end][-LEVEL_N:]
    ds = [d for d, _ in series if d <= end][-LEVEL_N:]
    if len(pick) < LEVEL_N or (end - ds[0]).days > span:
        return None
    return statistics.median(pick)


def window(days, today, dgs):
    """받아 둔 날 + DGS로 창(DTCC 요청 0번) — {end, level: {만기: bp}, chg13, range1y, cover, n10, iqr10, age, stale} 또는
    None(10년 스프레드가 하나도 없음)."""
    s = spreads(days, today, dgs)
    ten = s[10]
    if not ten:
        return None
    end = ten[-1][0]
    level = {str(t): (None if (v := _med_upto(s[t], end)) is None else round(v, 4)) for t in TENORS}
    prior = _med_upto(ten, end - datetime.timedelta(days=WEEKS13))
    chg = None if prior is None or level["10"] is None else round(level["10"] - prior, 4)
    span = [(d, v) for d, v in ten if d > end - datetime.timedelta(days=YEAR)]
    roll = [(span[i][0], statistics.median(v for _, v in span[i - LEVEL_N + 1:i + 1]))
            for i in range(LEVEL_N - 1, len(span))]
    rng = None
    if roll:
        lo, hi = min(roll, key=lambda x: x[1]), max(roll, key=lambda x: x[1])
        rng = {"lo": round(lo[1], 4), "lo_day": lo[0].isoformat(), "hi": round(hi[1], 4), "hi_day": hi[0].isoformat()}
    weekdays = sum(1 for i in range(YEAR) if (end - datetime.timedelta(days=i)).weekday() < 5)
    last = days[end.isoformat()]["10"]
    iqr = round((last["q3"] - last["q1"]) * 100, 4)
    age = (today - end).days
    return {"end": end.isoformat(), "level": level, "chg13": chg, "range1y": rng,
            "cover": {"days": len(span), "weekdays": weekdays}, "n10": last["n"], "iqr10": iqr,
            "age": age, "stale": age > STALE_DAYS}


def why_none(days, today, dgs):
    """창이 없을 때의 사유 코드 — 받아 둔 날이 없음 · 10년 국채 금리를 받지 못함 · 셀 수 있는 날이 없음."""
    if not _held(days, today):
        return "none"
    if not dgs.get(10):
        return "fred"
    return "format"


# ---------- 칸 ----------

VALUE_KEYS = {"end", "level", "chg13", "range1y", "cover", "n10", "iqr10", "fred_missing", "last_error"}
RANGE_KEYS = {"lo", "lo_day", "hi", "hi_day"}


def _bp(v):
    return _num(v, *SPREAD_BP)


def values_ok(v):
    """칸 값의 꼴과 지킴 — 네 만기의 수준은 SPREAD_BP 안의 숫자 또는 없음, 13주 변화는 10년 수준이 있을 때만, 1년 범위는
    최저 ≤ 최고이고 그 날이 끝 날 YEAR일 안, 받은 날은 평일 수 안의 정수, 끝 날 거래 수는 MIN_TRADES 이상. 다른 값(원 행의 글·
    식별자 같은 것)이 섞여 들어오면 싣지 않는다 — 새로 계산한 값과 직전 파일 모두."""
    try:
        if not isinstance(v, dict) or set(v) != VALUE_KEYS or not cd._is_day(v["end"]):
            return False
        if not (v["last_error"] is None or v["last_error"] in REASONS):
            return False
        lv = v["level"]
        if not isinstance(lv, dict) or list(lv) != KEYS or not all(x is None or _bp(x) for x in lv.values()):
            return False
        if v["chg13"] is not None and not (_num(v["chg13"], -2 * SPREAD_BP[1], 2 * SPREAD_BP[1]) and lv["10"] is not None):
            return False
        end = D.fromisoformat(v["end"])
        first = (end - datetime.timedelta(days=YEAR - 1)).isoformat()
        r = v["range1y"]
        if r is not None:
            if not isinstance(r, dict) or set(r) != RANGE_KEYS or not (_bp(r["lo"]) and _bp(r["hi"]) and r["lo"] <= r["hi"]):
                return False
            if not all(cd._is_day(r[k]) and first <= r[k] <= v["end"] for k in ("lo_day", "hi_day")):
                return False
        c = v["cover"]
        if not isinstance(c, dict) or set(c) != {"days", "weekdays"} or not cd._is_int(c["weekdays"], YEAR):
            return False
        if not cd._is_int(c["days"], c["weekdays"]):
            return False
        if not (cd._is_int(v["n10"]) and v["n10"] >= MIN_TRADES):
            return False
        if v["iqr10"] is not None and not _num(v["iqr10"], 0, 2 * QUART * 100):
            return False
        fm = v["fred_missing"]
        if not isinstance(fm, list) or fm != [t for t in TENORS if t in fm] or not all(type(t) is int for t in fm):
            return False
        return 10 not in fm
    except (KeyError, TypeError, ValueError):
        return False


def core_from(W, run_error, fred_missing=()):
    return {"date": W["end"], "values": {"end": W["end"], "level": W["level"], "chg13": W["chg13"], "range1y": W["range1y"],
                                         "cover": W["cover"], "n10": W["n10"], "iqr10": W["iqr10"],
                                         "fred_missing": [t for t in TENORS if t in fred_missing],
                                         "last_error": run_error}}


def texts(key, v, date):
    """칸 → (숫자 줄, 덧붙이는 줄 목록). 정해 둔 문구에 숫자만 넣는다."""
    note = ([f"이번 갱신에서 받지 못한 날이 있다 · {REASONS[v['last_error']]} — 다음 갱신에 이어 받는다."]
            if v["last_error"] else [])
    if key == "level":
        lv = v["level"]
        parts = " · ".join(f"{t}년 {_s(lv[str(t)])}" for t in TENORS)
        miss = ([f"이번 갱신에서 국채 금리(FRED)를 받지 못한 만기: {' · '.join(f'{t}년' for t in v['fred_missing'])} — 그 "
                 "만기는 '—'."] if v["fred_missing"] else [])
        iqr = f" · 그날 10년 사분위 폭 {v['iqr10']:.1f}bp" if v["iqr10"] is not None else ""
        return (f"~{date} {LEVEL_N}영업일 중앙값: {parts}bp",
                ["국채 − OIS = 같은 날 재무부 par 금리(FRED DGS2·DGS5·DGS10·DGS30) − SOFR OIS 새 거래 고정금리의 그날 중앙값, "
                 "bp. 시장에서 흔히 말하는 '스와프 스프레드'의 부호를 뒤집은 값이다 — 국채 − OIS = −(스와프 스프레드).",
                 f"그날 그 만기 거래가 {MIN_TRADES}건 이상인 날만 쓰고 최근 {LEVEL_N}개 날의 중앙값을 싣는다. 최근 {LEVEL_N}개가 "
                 f"끝 날부터 {LEVEL_SPAN}일 안에 모두 있지 않은 만기는 '—'. 끝 날 10년 거래 {v['n10']}건{iqr}.",
                 "같은 시각의 값이 아니다 — DGS는 장 마감 무렵의 값, OIS는 하루 동안 체결된 거래다. par 기준이라 zero(현물) "
                 "기준으로 잰 수준과 그대로 견주지 않는다.", *miss, *note])
    if key == "ten":
        cv, r = v["cover"], v["range1y"]
        chg = f"{_s(v['chg13'])}bp" if v["chg13"] is not None else "— (13주 전 자료 모자람)"
        rng = (f"{_s(r['lo'])}~{_s(r['hi'])}bp (최저 {r['lo_day']} · 최고 {r['hi_day']})" if r else "— (자료 모자람)")
        return (f"~{date} 10년: 13주 변화 {chg} · 1년 범위 {rng} · 받은 날 {cv['days']}/{cv['weekdays']}",
                [f"13주 변화 = 지금의 10년 {LEVEL_N}영업일 중앙값 − 끝 날 {WEEKS13}일 전까지의 {LEVEL_N}영업일 중앙값. 1년 범위 = "
                 f"끝 날까지 {YEAR}일 안에서 {LEVEL_N}개씩 옮겨 가며 낸 중앙값의 최저~최고.",
                 f"받은 날 = 그 {YEAR}일의 평일 가운데 10년 스프레드를 셀 수 있었던 날 — 하루 파일을 받았고, 10년 거래가 "
                 f"{MIN_TRADES}건 이상이고, 같은 날 DGS10이 있는 날. 하루 파일은 새 날부터 이어 받아 처음 몇 번의 갱신 동안은 "
                 "받은 날이 적다.", *note])
    raise KeyError(key)


def citation(sid, retrieved):
    d = D.fromisoformat(retrieved)
    src, title = SOURCES[sid]
    return (f"{src}, {title} [{sid}], retrieved from FRED, Federal Reserve Bank of St. Louis; "
            f"{rp.FRED_URL.format(sid)}, {ai._MONTHS[d.month - 1]} {d.day}, {d.year}.")


def sources_of(retrieved=None):
    out = [{"series": DATASET, "name": "DTCC Data Repository (U.S.) LLC", "licence": LICENCE[DATASET], "citation": CITATION}]
    for t in TENORS:
        sid = DGS[t]
        s = {"series": sid, "name": SOURCES[sid][0], "url": rp.FRED_URL.format(sid), "licence": LICENCE[sid]}
        if retrieved:
            s["citation"] = citation(sid, retrieved)
        out.append(s)
    return out


def notices():
    return [COMPUTED_NOTICE, CAVEAT_NOTICE]


def present(key, core, retrieved):
    line, extra = texts(key, core["values"], core["date"])
    return {"key": key, "name": TITLE[key], "date": core["date"], "values": core["values"], "retrieved": retrieved,
            "line": line, "extra": extra, "notices": notices(), "sources": sources_of(retrieved)}


# ---------- 직전 파일 ----------

def core_of(item, key):
    """직전 파일의 칸 → (core, 받은 날) 또는 None(없거나 꼴이 어긋남)."""
    try:
        vals = item["values"]
        ok = (cd._is_day(item["date"]) and cd._is_day(item["retrieved"]) and values_ok(vals) and vals["end"] == item["date"])
        if ok:
            texts(key, vals, item["date"])
    except (KeyError, TypeError, IndexError, AttributeError, ValueError):
        return None
    if not ok:
        return None
    return {"date": item["date"], "values": json.loads(json.dumps(vals))}, item["retrieved"]


def previous(out):
    try:
        with open(os.path.join(out, FILE), encoding="utf-8") as f:
            js = json.load(f)
    except (OSError, ValueError):
        return {}
    if not isinstance(js, dict) or js.get("schema") != SCHEMA or not isinstance(js.get("items"), dict):
        return {}
    return {k: v for k, v in js["items"].items() if k in ORDER and isinstance(v, dict)}


def _since(prev, today):
    return prev.get("failed_since") if prev and prev.get("ok") is not True and cd._is_day(prev.get("failed_since")) \
        else today.isoformat()


def _retrieved(old, core, today):
    """숫자가 같으면 처음 받은 날을 지킨다. 이번 갱신의 실패 사유(last_error)는 받은 숫자가 아니라 견주지 않는다."""
    def bare(c):
        c = json.loads(json.dumps(c))
        c["values"].pop("last_error", None)
        return c
    same = old and bare(old[0]) == bare(core)
    return old[1] if same else today.isoformat()


def item_ok(key, core, prev, today):
    if not values_ok(core["values"]):
        raise ValueError("values")
    old = core_of(prev, key) if prev else None
    if old and core["date"] < old[0]["date"]:
        return item_failed(key, "older", prev, today)
    return {"ok": True, "stale": False, "error": None, "failed_since": None,
            **present(key, core, _retrieved(old, core, today))}


def item_stale(key, code, core, prev, today):
    """창을 냈지만 끝 날이 오래됨 — 숫자는 싣고 '받지 못함'과 그날부터."""
    if not values_ok(core["values"]):
        raise ValueError("values")
    old = core_of(prev, key) if prev else None
    if old and core["date"] < old[0]["date"]:
        return item_failed(key, "older", prev, today)
    return {"ok": False, "stale": True, "error": REASONS[code], "failed_since": _since(prev, today),
            **present(key, core, _retrieved(old, core, today))}


def item_failed(key, code, prev, today):
    since = _since(prev, today)
    old = core_of(prev, key) if prev else None
    if old:
        return {"ok": False, "stale": True, "error": REASONS[code], "failed_since": since, **present(key, *old)}
    return {"ok": False, "stale": False, "error": REASONS[code], "failed_since": since, "key": key, "name": TITLE[key],
            "notices": notices(), "sources": sources_of()}


def build(W, run_error, why, prev, now, fred_missing=()):
    """창(W 또는 None)·이번 수신의 사유 코드·창이 없는 까닭(why)·FRED에서 받지 못한 만기 → 산출물 dict."""
    today = now.date()
    if W is None:
        code = run_error if why == "none" and run_error else why or "none"
    items = {}
    for key in ORDER:
        p = prev.get(key)
        try:
            if W is None:
                items[key] = item_failed(key, code, p, today)
            else:
                core = core_from(W, run_error, fred_missing)
                if W["stale"]:
                    items[key] = item_stale(key, run_error or "old", core, p, today)
                else:
                    items[key] = item_ok(key, core, p, today)
        except Exception as e:                        # 꼴이 어긋난 계산 — 그 칸만 실패로
            print(f"[ois_fetch] {key} 계산 오류: {type(e).__name__}", file=sys.stderr)
            items[key] = item_failed(key, "format" if W is not None else code, p, today)
    return {"schema": SCHEMA, "generated_at": now.isoformat(timespec="seconds"), "notice": NOTICE, "order": list(ORDER),
            "items": items}


# ---------- 쓰기 ----------

def summary_text(data):
    return json.dumps(data, ensure_ascii=False, separators=(",", ":"))


def summary_differs(out, data):
    try:
        with open(os.path.join(out, FILE), encoding="utf-8") as f:
            old = json.load(f)
    except (OSError, ValueError):
        return True
    strip = lambda d: {k: v for k, v in d.items() if k != "generated_at"} if isinstance(d, dict) else d
    return strip(old) != strip(json.loads(json.dumps(data)))


def main(argv=None, opener=None, now=None, clock=time.monotonic, fred_load=None, fred_opener=None):
    ap = argparse.ArgumentParser(description="DTCC 공개 금리 스와프 거래 보고 + FRED 국채 par 금리 → 국채–OIS 참고 자료"
                                             "(<out>/ois.json · ois_days.json)")
    ap.add_argument("--out", default=DEFAULT_OUT, help="사이트 데이터 폴더 (기본: 저장소의 data/)")
    ap.add_argument("--work", default=DEFAULT_WORK, help="작업 폴더 — FRED 원문 캐시는 <work>/ois/ (기본: 저장소의 .work/)")
    ap.add_argument("--budget", type=float, default=BUDGET, help=f"DTCC 수신 전체 상한(초, 기본 {BUDGET})")
    ap.add_argument("--offline", action="store_true", help="받지 않고 받아 둔 날과 FRED 캐시로 창만")
    ap.add_argument("--force", action="store_true", help="같은 날 앞선 실행이 멈췄어도 다시 받는다")
    a = ap.parse_args(argv)
    out, work = os.path.abspath(a.out), os.path.abspath(a.work)
    now = now or datetime.datetime.now(datetime.timezone.utc)
    today = now.date()
    store = load_store(out)
    r = {"fetched": 0, "absent": 0, "bad": 0, "missing": 0, "error": None, "skipped": False}
    if not a.offline:
        r = sync(store, today, budget=a.budget, opener=opener, clock=clock, force=a.force)
    prune(store, today)
    dgs, ferr = load_fred(work, a.offline, fred_load, clock, opener=fred_opener)
    W = window(store["days"], today, dgs)
    missing = [t for t in TENORS if t not in dgs]
    data = build(W, r["error"], None if W else why_none(store["days"], today, dgs), previous(out), now, missing)
    # Actions 로그 — 날짜·셈·정해 둔 사유만(값·원격 글은 찍지 않는다)
    print(f"[ois_fetch] 받음 {r['fetched']}일 · 없음 {r['absent']}일 · 그날 오류 {r['bad']}일 · 못 받은 날 {r['missing']}일 · "
          f"받아 둔 날 {len(store['days'])}일 · FRED {len(dgs)}/{len(DGS)}"
          + (f" · 끝 {W['end']}" if W else ""))
    if r["error"]:
        annotate_reason = REASONS[r["error"]] + (" — 같은 날 앞선 실행이 멈춰 건너뜀" if r["skipped"] else "")
        cd.annotate(f"국채–OIS 참고: {annotate_reason}")
    if ferr:
        cd.annotate("국채–OIS 참고: 국채 금리(FRED)를 받지 못한 시리즈 " + " · ".join(sorted(ferr)))
    for key in ORDER:
        it = data["items"][key]
        if not it["ok"]:
            kept = f" — 받아 둔 값({it['date']} 기준)을 싣는다" if it["stale"] else ""
            cd.annotate(f"국채–OIS 참고 {key}: {it['error']}{kept}")
    try:
        os.makedirs(out, exist_ok=True)
        text = store_text(store)
        if not a.offline and cd.differs(os.path.join(out, STORE), text):
            cd._atomic_write(os.path.join(out, STORE), text)
        if summary_differs(out, data):
            cd._atomic_write(os.path.join(out, FILE), summary_text(data))
    except OSError as e:
        print(f"[ois_fetch] 파일을 쓰지 못함: {type(e).__name__}", file=sys.stderr)
        return 1
    return 0 if not r["error"] and any(it["ok"] for it in data["items"].values()) else 1


if __name__ == "__main__":
    sys.exit(main())
