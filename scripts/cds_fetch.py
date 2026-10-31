#!/usr/bin/env python3
"""참고 자료 — 하이퍼스케일러·AI 칩 업체 12곳의 단일종목 CDS (2026-10-30 추가, 사용자 결정: 비공개 줄 공개).

운영자의 비공개 월간 점검 [AI 투자 참고]의 '단일종목 CDS 5년 호가'·'새 거래 건수' 두 줄을 공개한 것이다(비공개 원본
cds_dtcc.py와 같은 세는 법·창 — 코드는 가져오지 않고 여기서 따로 쓴다. 고치면 양쪽을 같이). 숫자만 싣는 측정 기록이다 —
판정·문턱이 없고 신용 사건이나 금리를 예측하지 않는다. 판정·공개본·그래프 스크립트는 이 파일의 산출물을 읽지 않는다.

자료: DTCC Data Repository (U.S.) LLC가 SEC 규칙(Reg SBSR)으로 공개하는 증권기반 스와프 거래 보고의 하루 파일(URL — 인증
  없음, 약 110KB, 주말·미국 휴일에도 있다, 대략 2년 전까지). 그날 D의 파일은 D+1 00:15 UTC쯤 올라온다. DTCC 쪽 보고만 들어
  있다(ICE Trade Vault 쪽·미국 밖 거래는 없다). 출처 표기: CITATION — DTCC 로고는 쓰지 않는다. Reg SBSR 공개분은 이용을
  제한하지 않는 자료로 본다(2026-10-30 확인).
남기는 것 — 두 파일(둘 다 <out>/, 커밋된다):
  STORE(cds_days.json)  날마다 이름마다 {new: 새 거래 수, q: 5년 호가 수, med: 5년 호가 중앙값(bp)} — 셈한 값뿐. 원 행·거래
                        식별자(Dissemination Identifier)·RED 코드는 쓰지 않는다(zip은 메모리에서만 풀고 버린다). 받을 날
                        (targets — 어제부터 RECENT_DAYS일 · 1년 전 YEAR_DAYS일)과 지금 창이 쓰는 날만 두고 나머지는 지운다.
                        다시 볼 날의 표(tries)와 마지막 수신 상태(status — 정해 둔 사유 코드뿐)도 여기에.
  FILE(cds.json)        화면에 싣는 창 두 칸(quotes · trades) — 받아 둔 날로 계산한다(요청 0번).
세는 법(하루 파일마다 — 비공개 원본과 같다):
  - 새 거래만: Action type NEWT · Event type TRAD, UPI FISN에 'CDS'와 'SN'(단일종목) — 지수·바스켓·수정·정정 행은 세지 않는다
  - 체결일이 파일 날짜와 같거나 LAG_DAYS일 안(옛 거래의 일괄·늦은 보고 제외)
  - 같은 파일의 취소(EROR)가 가리키는 거래 제외 — 다음 날 이후 취소분(새 거래의 약 3%)은 빼지 못한다
  - 묶음 제외: 같은 체결 시각·명목·선지급금이 서로 다른 기준 실체 둘 이상에 찍힌 행과, 같은 체결 시각(초)에 서로 다른 기준 실체
    BUNDLE_NAMES곳 이상이 찍힌 행(대형 포트폴리오 거래). 2~9곳짜리 초는 센다(대개 이 목록의 이름 몇 곳을 함께 사고판 바구니)
  - 이름: 'Underlying Asset Name' + 'UPI Underlier Name'에 정규식(표기가 제각각 — 종목 기호 꼴 'ORCL CDS USD SR 5Y D14'도).
    'Amentum (Amazon Holdco Inc)'는 아마존이 아니다
  - 이름 칸이 빈 행은 그 파일 안에서 이름이 맞은 행의 RED 코드(앞 6자리)로 찾는다(한 코드가 한 이름에만 쓰인 때만 — 메모리에서만)
  - 묶음을 셀 때의 기준 실체는 이름이 먼저다('Underlier ID-Leg 1'에는 수백 곳이 함께 쓰는 '참조 채권 없음' 자리표가 많다)
  - 5년 호가: 'Spread-Leg 1'이 있고 만기가 체결일의 표준 5년(3·9월 20일에 바뀐다)인 거래. 단위: 'Spread notation-Leg 1'이
    4면 bp, 아니면 소수(0.0249 = 249bp) — 다만 1 이상이면 bp로 적은 것으로 본다. QUOTE_BP 밖은 뺀다
  - 선지급금만 있는 거래는 스프레드로 바꾸지 않는다(공개분에 방향 칸이 없어 두 해가 나온다 — 그런 이름은 건수만)
창(window — 비공개 원본과 같다): 끝 = 받아 둔 마지막 날(오늘 날짜의 파일은 읽지 않는다). 호가 = 최근 LEVEL_DAYS일 호가의
  중앙값(날마다 중앙값을 호가 수만큼 무게로 — 원 호가는 남기지 않으므로 근사), 호가가 MIN_QUOTES개보다 적으면 '호가 부족'.
  4주 전 = 끝 PRIOR_GAP일 전까지의 14일, 1년 전 = 끝 YEAR_GAP일 전까지의 14일. 건수 = 최근 COUNT_DAYS일과 1년 전 같은
  28일(1년 전은 28일을 모두 받아 둔 때만). 창마다 받은 날 수(cover)와 끝 날의 나이(age)를 함께 낸다.

수신(sync — 비공개 원본과 같다): 빠진 날만, 새 날부터. 수신 전체 BUDGET초 굳은 상한 — 요청 하나를 따로 스레드에서 돌리고
  남은 예산만큼만 기다린다(주소 찾기·여러 주소 연결·느린 수신 모두). 첫 실행은 다 받지 못할 수 있다 — 다음 실행이 이어 받는다.
  - 연결 실패·시간 초과(요청 하나에 TIMEOUT을 거의 다 준 때) — 멈추고, 같은 날(UTC)의 다음 실행은 건너뛴다(--force면 다시).
  - 예산이 모자라 짧게 준 요청의 시간 초과 — 실패가 아니라 '못 받은 날'(다음 실행 몫).
  - 그날 하나의 문제(HTTP 5xx·깨진 zip·지원하지 않는 압축·너무 큰 파일·필요한 칸이 없는 파일·셈 오류)와 없는 파일(S3 403
    AccessDenied)·보관된 파일(403 InvalidObjectState) — 그날만 건너뛴다. RETRY_DAYS일 안의 '없음'은 아직 안 올라온 것이라
    세지 않는다. 같은 날짜는 하루 한 번만 다시 보고, 서로 다른 GIVE_UP일 실패한 날은 더 받지 않는다.
  - 받은 것 없이 최근 RECENT_ALARM일 안의 날이 ALARM_DAYS번 실패하면 '주소·접근이 바뀌었을 수 있음'으로 멈춘다.

실패·이어 싣기·문구 원칙은 oil_fetch와 같다: 받아 둔 날이 있으면 그것으로 창을 낸다. 끝 날이 STALE_DAYS일보다 오래되면
'받지 못함(stale)'과 그날부터라는 날짜를 함께 싣는다. 받아 둔 날이 하나도 없으면(저장 파일이 깨졌을 때 등) 직전 cds.json의
숫자를 '받지 못함'으로 이어 싣고, 그것도 없으면 사유만. 문구는 이 파일에 정해 둔 것뿐이다(오류 원문·예외 문자열은 파일·로그에
싣지 않는다 — 로그엔 날짜와 정해 둔 사유만). 같은 내용이면(생성 시각만 다르면) 다시 쓰지 않는다.

종료코드: 0 수신이 멈추지 않았고 한 칸이라도 지금 값 / 1 그 밖(파일을 쓰지 못함 포함). 워크플로 단계는 continue-on-error, 알림 없음.

사용법: python scripts/cds_fetch.py [--out data] [--budget 90] [--offline] [--force]
"""
import os, io, re, sys, csv, json, time, zlib, socket, zipfile, argparse, datetime, threading, statistics, urllib.request, \
    urllib.error

SCRIPTS = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(SCRIPTS)
DEFAULT_OUT = os.path.join(REPO, "data")
SCHEMA = 1
FILE = "cds.json"
STORE = "cds_days.json"
D = datetime.date
URL = "https://kgc0418-tdw-data-0.s3.amazonaws.com/sec/eod/SEC_CUMULATIVE_CREDITS_{:%Y_%m_%d}.zip"

BUDGET = 90                  # 수신 전체(초) — 워크플로 단계 제한 안에서
TIMEOUT = 10                 # 요청 하나엔 min(이것, 남은 예산)
MIN_LEFT = 1                 # 남은 예산이 이보다 적으면 요청하지 않는다
MAX_BYTES = 20 * 1024 * 1024
CHUNK = 65536
RECENT_DAYS = 42             # 받을 최근 날 수(어제부터) — 14일 호가 + 4주 전 14일 + 여유
YEAR_DAYS = 29               # 1년 전(364일 전)에서 거슬러 받을 날 수 — 1년 전 28일 건수
RETRY_DAYS = 3               # 이보다 최근 날의 '파일 없음'은 아직 안 올라온 것으로 본다(세지 않는다)
GIVE_UP = 3                  # 서로 다른 날 이만큼 실패한 날짜는 더 받지 않는다
RECENT_ALARM = 10            # 받은 것 없이 이 안의 날이 ALARM_DAYS번 실패하면 멈춘다
ALARM_DAYS = 2
LAG_DAYS = 3                 # 체결일이 파일 날짜보다 이만큼 넘게 앞서면 세지 않는다
LEVEL_DAYS = 14              # 호가 창
COUNT_DAYS = 28              # 건수 창
PRIOR_GAP = 28               # 4주 전 = 끝에서 이만큼 앞
YEAR_GAP = 364               # 1년 전 = 끝에서 이만큼 앞(같은 요일)
MIN_QUOTES = 3
QUOTE_BP = (5.0, 3000.0)     # 이 밖의 호가는 단위 오기로 본다
BUNDLE_NAMES = 10            # 같은 체결 시각(초)에 서로 다른 기준 실체가 이만큼 이상이면 대형 포트폴리오 묶음
STALE_DAYS = 4               # 끝 날이 이보다 오래면 '받지 못함'으로 싣는다
COLUMNS = ("Dissemination Identifier", "Original Dissemination Identifier", "Action type", "Event type",
           "Execution Timestamp", "Expiration Date", "Notional amount-Leg 1", "Spread-Leg 1", "Spread notation-Leg 1",
           "Other payment amount", "Underlying Asset Name", "UPI FISN", "UPI Underlier Name")   # 없으면 그날은 형식 오류
_PLACEHOLDER = re.compile(r"REFOBL", re.I)     # ID에 REFOBL이 든 것 — 여러 실체가 함께 쓰는 '참조 채권 없음' 자리표
_NO_NAME = {"", "NO NAME OBTAINABLE", "SR NT", "NT", "SUB NT"}
NAMES = [                    # (키, 표시, 정규식) — 차례 = 표시 차례(하이퍼스케일러 → 칩). 비공개 원본과 같다
    ("oracle", "오라클", r"\bORACLE\b|^ORCL CDS\b"),
    ("meta", "메타", r"META PLATFORMS|FACEBOOK|^META CDS\b"),
    ("amazon", "아마존", r"\bAMAZON\b(?!\s+HOLDCO)|^AMZN CDS\b"),     # 'Amentum (Amazon Holdco Inc)'는 다른 회사
    ("alphabet", "알파벳", r"ALPHABET|GOOGLE|^GOOGL? CDS\b"),
    ("microsoft", "MS", r"MICROSOFT|^MSFT CDS\b"),
    ("coreweave", "코어위브", r"COREWEAVE|^CRWV CDS\b"),
    ("broadcom", "브로드컴", r"BROADCOM|^AVGO CDS\b"),
    ("nvidia", "엔비디아", r"NVIDIA|^NVDA CDS\b"),
    ("amd", "AMD", r"ADVANCED MICRO|^(?:AMD|ADVANCED) CDS\b"),
    ("intel", "인텔", r"\bINTEL\b|^INTC CDS\b"),
    ("micron", "마이크론", r"\bMICRON\b|^MU CDS\b"),
    ("tsmc", "TSMC", r"TAIWAN SEMI|\bTSMC|^TSM CDS\b"),
]
_RX = [(k, re.compile(p)) for k, _, p in NAMES]
KEYS = [k for k, _, _ in NAMES]
LABEL = {k: lab for k, lab, _ in NAMES}

# 출처 — DTCC 공개 배포(Reg SBSR). 이용 조건 표시(sources[].licence)
CITATION = ("Source: DTCC Data Repository (U.S.) LLC, SEC security-based swap public dissemination (Reg SBSR); "
            "site calculations")
DATASET = "SEC_CUMULATIVE_CREDITS"
LICENCE = {DATASET: "sec-reg-sbsr-public-dissemination"}
NOTICE = ("이 사이트의 규칙 점검에 쓰지 않는 참고 자료다. 공개 거래 보고를 센 측정 기록이고, 신용 사건이나 금리를 "
          "예측하지 않는다.")
COMPUTED_NOTICE = ("중앙값·건수는 macro-regime-check가 DTCC 공개 거래 보고의 하루 파일로 계산한 값이다 — 원 행·거래 "
                   "식별자·RED 코드는 싣지 않고 이름별 셈만 남긴다.")
CAVEAT_NOTICE = ("DTCC 쪽 보고만 들어 있다 — ICE Trade Vault 쪽 보고와 미국 밖 거래는 없다. 체결된 거래의 스프레드라 "
                 "중간값(mid)이 아니고, 일부 거래는 나중에 취소된다.")
STORE_NOTICE = ("날마다 이름마다 새 거래 수(new)·표준 5년 만기 호가 수(q)·그 중앙값(med, bp)만 — DTCC 공개 거래 보고로 "
                "센 값이다. 원 행·거래 식별자·RED 코드는 없다.")
ORDER = ["quotes", "trades"]
TITLE = {"quotes": "단일종목 CDS 5년 호가 (최근 14일 중앙값)", "trades": "단일종목 CDS 새 거래 건수 (28일)"}
# 페이지·파일·로그에 나가는 실패 문구는 이것뿐
REASONS = {
    "fetch": "수신 실패",
    "timeout": "수신 시간 초과",
    "alarm": "최근 날의 파일을 받지 못함 · 주소나 접근 방식이 바뀌었을 수 있음",
    "none": "받아 둔 자료 없음",
    "old": "새 날 자료가 들어오지 않음",
    "older": "받은 자료가 직전 자료보다 오래됨",
    "format": "계산할 자료가 모자람",
}
_STOP = {"net": "fetch", "timeout": "timeout"}      # FetchError.kind → 멈출 때의 사유 코드


class FetchError(Exception):
    """받지 못함 — kind: 'net'(연결 실패 — 멈춘다) · 'timeout'(시간 초과) · 'budget'(예산 마감) · 'day'(그날 하나의 문제).
    메시지는 정해 둔 짧은 글뿐이다(원격 글을 담지 않는다). 받을 파일이 없는 것(403 AccessDenied)은 예외가 아니라 None."""
    def __init__(self, kind="day"):
        super().__init__(kind)
        self.kind = kind


# ---------- 작은 도움 ----------

def _f(v, nd=0, sign=False, unit=""):
    if v is None:
        return "—"
    s = f"{v:+.{nd}f}" if sign else f"{v:.{nd}f}"
    if float(s) == 0:
        s = f"{0:.{nd}f}"
    return s + unit


def _is_day(v):
    try:
        return isinstance(v, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", v) is not None and D.fromisoformat(v) is not None
    except ValueError:
        return False


def _is_num(v):
    return type(v) in (int, float) and v == v and abs(v) != float("inf")


def _is_int(v, hi=None):
    return type(v) is int and v >= 0 and (hi is None or v <= hi)


def _iso(d):
    return d.isoformat()


def _day(s):
    try:
        return D.fromisoformat(str(s)[:10])
    except ValueError:
        return None


def annotate(text):
    print("::warning::" + text.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A"), flush=True)


def _atomic_write(path, text):
    tmp = path + ".tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(text)
        os.replace(tmp, path)
    except OSError:
        try:
            os.remove(tmp)
        except OSError:
            pass
        raise


# ---------- 하루 파일 → 이름별 셈 (비공개 원본 cds_dtcc와 같은 산식) ----------

def five_year(d):
    """체결일의 표준 5년 만기 — 3·9월 20일에 바뀐다."""
    y = d.year
    if d >= D(y, 9, 20):
        return D(y + 5, 12, 20)
    if d >= D(y, 3, 20):
        return D(y + 5, 6, 20)
    return D(y + 4, 12, 20)


def name_of(row):
    text = f"{row.get('Underlying Asset Name') or ''} | {row.get('UPI Underlier Name') or ''}".upper()
    return next((k for k, rx in _RX if rx.search(text)), None)


def entity_of(row):
    """묶음을 셀 때의 기준 실체 — 이 목록의 이름 → 정리한 'Underlying Asset Name' → 'UPI Underlier Name' → 자리표가 아닌
    'Underlier ID-Leg 1' 순. 메모리에서만 쓴다."""
    k = name_of(row)
    if k:
        return k
    for f in ("Underlying Asset Name", "UPI Underlier Name"):
        v = (row.get(f) or "").upper()
        v = re.sub(r"\s+CDS\b.*$", "", v)
        v = re.sub(r"\s+\d+(?:\.\d+)?\s+\d{1,2}[A-Z]{3}\d{2}$", "", v)
        v = " ".join(re.sub(r"[;,.]", " ", v).split())
        if v not in _NO_NAME:
            return v
    i = (row.get("Underlier ID-Leg 1") or "").strip()
    return "" if _PLACEHOLDER.search(i) else i


def _quote_bp(s, notation=""):
    """공개 호가 → bp. 표기 4 = bp, 그 밖은 소수(1 이상이면 bp로 적은 것으로 본다). QUOTE_BP 밖은 None."""
    try:
        v = float(str(s).replace(",", ""))
    except ValueError:
        return None
    if str(notation).strip() != "4" and v < 1:
        v *= 1e4
    return round(v, 4) if QUOTE_BP[0] <= v <= QUOTE_BP[1] else None


_REDCODE = re.compile(r"[0-9A-Z]{6}(?:[0-9A-Z]{3})?")


def _red6(row):
    i = (row.get("Underlier ID-Leg 1") or "").strip().upper()
    src = (row.get("Underlier ID source-Leg 1") or "").upper()
    return i[:6] if "REDID" in src and _REDCODE.fullmatch(i) else None


def summarize(rows, day):
    """하루 파일의 행(dict) → {키: {new, q, med}} — 이름마다(0건도). 셈한 값뿐이다."""
    rows = list(rows)
    seen = {}
    for x in rows:                                               # RED 코드 → 이름(그 파일 안에서 한 이름에만 쓰인 코드만)
        k, r = name_of(x), _red6(x)
        if k and r:
            seen.setdefault(r, set()).add(k)
    red = {r: ks.pop() for r, ks in seen.items() if len(ks) == 1}
    name = lambda x: name_of(x) or red.get(_red6(x))
    cancelled = set()
    for x in rows:
        if x.get("Action type") == "EROR":
            cancelled.add(x.get("Original Dissemination Identifier") or "")
            cancelled.add(x.get("Dissemination Identifier") or "")
    cancelled.discard("")
    new = []
    for x in rows:
        fisn = x.get("UPI FISN") or ""
        if x.get("Action type") != "NEWT" or x.get("Event type") != "TRAD" or "CDS" not in fisn or "SN" not in fisn.split():
            continue
        if (x.get("Dissemination Identifier") or "") in cancelled:
            continue
        d = _day(x.get("Execution Timestamp"))
        if d is None or not 0 <= (day - d).days <= LAG_DAYS:
            continue
        new.append((x, d))
    groups, seconds = {}, {}
    entity = lambda x: name(x) or entity_of(x)
    for x, _ in new:
        g = (x.get("Execution Timestamp"), x.get("Other payment amount") or "", x.get("Notional amount-Leg 1"))
        groups.setdefault(g, set()).add(entity(x))
        seconds.setdefault(x.get("Execution Timestamp"), set()).add(entity(x))
    out = {k: {"new": 0, "q": 0, "quotes": []} for k in KEYS}
    for x, d in new:
        k = name(x)
        if not k:
            continue
        g = (x.get("Execution Timestamp"), x.get("Other payment amount") or "", x.get("Notional amount-Leg 1"))
        if len(groups[g]) > 1 or len(seconds[x.get("Execution Timestamp")]) >= BUNDLE_NAMES:
            continue
        out[k]["new"] += 1
        if (x.get("Expiration Date") or "") == five_year(d).isoformat():
            q = _quote_bp(x.get("Spread-Leg 1") or "", x.get("Spread notation-Leg 1") or "")
            if q is not None:
                out[k]["quotes"].append(q)
    for v in out.values():
        qs = v.pop("quotes")
        v["q"] = len(qs)
        v["med"] = round(statistics.median(qs), 4) if qs else None
    return out


def parse_zip(blob):
    """zip 바이트 → 행(dict) 목록 — 첫 csv 하나. 디스크에 쓰지 않는다."""
    try:
        with zipfile.ZipFile(io.BytesIO(blob)) as zf:
            names = [n for n in zf.namelist() if n.lower().endswith(".csv")]
            if not names:
                raise FetchError("day")
            with zf.open(names[0]) as f:
                reader = csv.DictReader(io.TextIOWrapper(f, encoding="utf-8-sig", newline=""))
                canon = {" ".join(c.split()).lower(): c for c in COLUMNS}   # 대소문자·띄어쓰기만 바뀐 머리글은 받아들인다
                reader.fieldnames = [canon.get(" ".join(h.split()).lower(), h) for h in (reader.fieldnames or [])]
                if any(c not in reader.fieldnames for c in COLUMNS):
                    raise FetchError("day")                             # 필요한 칸이 없다 — 0건으로 남기지 않는다
                return list(reader)
    except FetchError:
        raise
    except (zipfile.BadZipFile, zlib.error, EOFError, OSError, UnicodeDecodeError, csv.Error, ValueError,
            NotImplementedError, RuntimeError):                   # 지원하지 않는 압축(Deflate64 등)·암호화도 그날만의 문제
        raise FetchError("day")


def _is_timeout(e):
    return isinstance(e, (socket.timeout, TimeoutError)) or \
        (isinstance(e, urllib.error.URLError) and isinstance(getattr(e, "reason", None), (socket.timeout, TimeoutError)))


def fetch(day, timeout, opener=None, deadline=None, clock=time.monotonic):
    """그날 파일 → 행 목록, 파일이 없으면 None(S3 403 AccessDenied·보관됨). 그 밖의 실패는 FetchError(kind로 종류).
    deadline(clock 기준)을 주면 덩어리마다 확인한다 — 넘으면 kind 'budget'."""
    opener = opener or urllib.request.urlopen
    try:
        with opener(URL.format(day), timeout=timeout) as r:
            read = getattr(r, "read1", None) or r.read            # read1: 수신 한 번마다 돌아와 마감을 자주 본다
            chunks, size = [], 0
            while True:
                if deadline is not None and clock() > deadline:
                    raise FetchError("budget")
                chunk = read(CHUNK)
                if not chunk:
                    break
                chunks.append(chunk)
                size += len(chunk)
                if size > MAX_BYTES:
                    raise FetchError("day")
            blob = b"".join(chunks)
    except FetchError:
        raise
    except urllib.error.HTTPError as e:
        body = b""
        try:
            body = e.read(4096) or b""
            e.close()
        except Exception:
            pass
        if e.code == 404 or (e.code == 403 and any(k in body for k in (b"AccessDenied", b"NoSuchKey", b"InvalidObjectState"))):
            return None                                           # 없음 · 보관됨(DEEP_ARCHIVE) — 그날만
        raise FetchError("day" if e.code >= 500 else "net")
    except Exception as e:
        raise FetchError("timeout" if _is_timeout(e) else "net")
    return parse_zip(blob)


def _within(fn, seconds):
    """fn()을 데몬 스레드에서 돌리고 seconds초만 기다린다 — 넘으면 FetchError('timeout')(스레드는 버린다, 결과를 쓰지 않는다)."""
    box = {}

    def run():
        try:
            box["v"] = fn()
        except BaseException as e:                               # 스레드 밖으로 그대로 옮긴다
            box["e"] = e
    t = threading.Thread(target=run, daemon=True)
    t.start()
    t.join(max(0.0, seconds))
    if t.is_alive():
        raise FetchError("timeout")
    if "e" in box:
        raise box["e"]
    return box.get("v")


# ---------- 받아 둔 날(STORE) ----------

def day_ok(names):
    """받아 둔 하루가 꼴에 맞는가 — 열두 이름 모두 {new, q, med}, 호가가 있으면 중앙값이 QUOTE_BP 안."""
    if not isinstance(names, dict) or set(names) != set(KEYS):
        return False
    for v in names.values():
        if not isinstance(v, dict) or set(v) != {"new", "q", "med"} or not _is_int(v["new"]) or not _is_int(v["q"]):
            return False
        if v["q"] > v["new"]:
            return False
        if v["q"] == 0:
            if v["med"] is not None:
                return False
        elif not (_is_num(v["med"]) and QUOTE_BP[0] <= v["med"] <= QUOTE_BP[1]):
            return False
    return True


def empty_store():
    return {"days": {}, "tries": {}, "status": {}}


def load_store(out):
    """<out>/cds_days.json → {days, tries, status}. 없거나 깨졌거나 판이 다르면 빈 저장(다시 받는다). 꼴이 어긋난 날은 버린다."""
    try:
        with open(os.path.join(out, STORE), encoding="utf-8") as f:
            js = json.load(f)
    except (OSError, ValueError):
        return empty_store()
    if not isinstance(js, dict) or js.get("schema") != SCHEMA or not isinstance(js.get("days"), dict):
        return empty_store()
    days = {k: v for k, v in js["days"].items() if _is_day(k) and day_ok(v)}
    raw = js.get("tries") if isinstance(js.get("tries"), dict) else {}
    tries = {k: {"n": v["n"], "last": v["last"], "why": v["why"]} for k, v in raw.items()
             if _is_day(k) and isinstance(v, dict) and _is_int(v.get("n"), GIVE_UP) and _is_day(v.get("last"))
             and v.get("why") in ("absent", "bad")}
    st = js.get("status") if isinstance(js.get("status"), dict) else {}
    status = {}
    if _is_day(st.get("date")) and (st.get("error") is None or st.get("error") in REASONS):
        status = {"date": st["date"], "error": st.get("error")}
    return {"days": days, "tries": tries, "status": status}


def targets(today):
    """받을 날 — 어제부터 RECENT_DAYS일, 그다음 1년 전(YEAR_GAP일 전)부터 YEAR_DAYS일. 새 날부터."""
    recent = [today - datetime.timedelta(days=i) for i in range(1, RECENT_DAYS + 1)]
    year = [today - datetime.timedelta(days=YEAR_GAP + i) for i in range(YEAR_DAYS)]
    return recent + year


def sync(store, today, budget=BUDGET, opener=None, clock=time.monotonic, force=False):
    """빠진 날만 받아 store(dict)를 고친다 — {fetched, absent, bad, missing, gave_up, error(사유 코드), skipped}.
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
                rows = _within(lambda: fetch(d, give, opener, deadline=deadline, clock=clock), left)
            except FetchError as e:
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
                names = summarize(rows, d)
            except Exception:                                    # 셈이 깨지는 꼴의 파일 — 그날만의 문제로
                out["bad"] += 1
                mark(d, "bad")
                continue
            days[d.isoformat()] = names
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


# ---------- 창 ----------

def _span(end, days, gap=0):
    hi = end - datetime.timedelta(days=gap)
    return [hi - datetime.timedelta(days=i) for i in range(days)]


def spans(end):
    return {"level": _span(end, LEVEL_DAYS), "prior": _span(end, LEVEL_DAYS, PRIOR_GAP),
            "level_1y": _span(end, LEVEL_DAYS, YEAR_GAP), "count": _span(end, COUNT_DAYS),
            "count_1y": _span(end, COUNT_DAYS, YEAR_GAP)}


def _weighted_median(pairs):
    """[(중앙값, 호가 수)] → 호가 수만큼 무게를 준 중앙값."""
    vals = sorted(v for v, n in pairs for _ in range(n))
    return round(statistics.median(vals), 4) if vals else None


def _stats(days_js, key):
    data = [js for js in days_js if js is not None]
    pairs = [(js[key]["med"], js[key]["q"]) for js in data]
    pairs = [(m, n) for m, n in pairs if m is not None and n > 0]
    return {"q": sum(n for _, n in pairs), "level": _weighted_median(pairs), "new": sum(js[key]["new"] for js in data)}


def end_of(days, today):
    """받아 둔 마지막 날(오늘 날짜는 빼고) 또는 None."""
    ds = [D.fromisoformat(k) for k in days if _is_day(k)]
    ds = [d for d in ds if d < today]
    return max(ds) if ds else None


def window(days, today):
    """받아 둔 날로 창 계산(요청 0번) — {end, from, names, cover, age, stale} 또는 None(받아 둔 날 없음)."""
    end = end_of(days, today)
    if end is None:
        return None
    sp = spans(end)
    loaded = {k: [days.get(d.isoformat()) for d in ds] for k, ds in sp.items()}
    cover = {k: sum(js is not None for js in v) for k, v in loaded.items()}
    names = []
    for key, label, _ in NAMES:
        st = {k: _stats(v, key) for k, v in loaded.items()}
        lv = lambda s: s["level"] if s["q"] >= MIN_QUOTES else None
        names.append({"key": key, "label": label, "level": lv(st["level"]), "q": st["level"]["q"],
                      "prior": lv(st["prior"]), "prior_q": st["prior"]["q"], "level_1y": lv(st["level_1y"]),
                      "q_1y": st["level_1y"]["q"], "new": st["count"]["new"],
                      "new_1y": st["count_1y"]["new"] if cover["count_1y"] == COUNT_DAYS else None})
    age = (today - end).days
    return {"end": end.isoformat(), "from": sp["count"][-1].isoformat(), "names": names, "cover": cover, "age": age,
            "stale": age > STALE_DAYS}


def prune(store, today):
    """받을 날(targets)과 지금 창이 쓰는 날만 남긴다 — 수신이 멈춰 끝 날이 오래돼도 창의 날은 지우지 않는다."""
    keep = {d.isoformat() for d in targets(today)}
    end = end_of(store["days"], today)
    if end is not None:
        keep |= {d.isoformat() for ds in spans(end).values() for d in ds}
    store["days"] = {k: v for k, v in store["days"].items() if k in keep}
    store["tries"] = {k: v for k, v in store["tries"].items() if k in keep}


def store_text(store):
    """저장 파일 글 — 하루가 한 줄(커밋 차이가 그날 줄로만 보이게). 날짜 차례."""
    head = {"schema": SCHEMA, "notice": STORE_NOTICE, "source": CITATION, "names": KEYS}
    lines = [json.dumps(k, ensure_ascii=False) + ":" + json.dumps({n: store["days"][k][n] for n in KEYS},
                                                                  ensure_ascii=False, separators=(",", ":"))
             for k in sorted(store["days"])]
    tries = {k: store["tries"][k] for k in sorted(store["tries"])}
    return ("{" + json.dumps(head, ensure_ascii=False, separators=(",", ":"))[1:-1] + ',\n"days":{\n' + ",\n".join(lines)
            + "\n},\n\"tries\":" + json.dumps(tries, ensure_ascii=False, separators=(",", ":"))
            + ",\n\"status\":" + json.dumps(store["status"], ensure_ascii=False, separators=(",", ":")) + "}\n")


# ---------- 칸 ----------

VALUE_KEYS = {"end", "from", "names", "cover", "last_error"}
NAME_KEYS = ("key", "label", "level", "q", "prior", "prior_q", "level_1y", "q_1y", "new", "new_1y")
COVER_MAX = {"level": LEVEL_DAYS, "prior": LEVEL_DAYS, "level_1y": LEVEL_DAYS, "count": COUNT_DAYS, "count_1y": COUNT_DAYS}


def _bp_ok(v):
    return v is None or (_is_num(v) and QUOTE_BP[0] <= v <= QUOTE_BP[1])


def values_ok(v):
    """칸 값의 꼴과 지킴 — 열두 이름이 정해 둔 차례·표시로, 호가는 QUOTE_BP 안, 건수·받은 날은 0 이상의 정수(받은 날은 창 길이
    안). 다른 값(원 행의 글·식별자 같은 것)이 섞여 들어오면 싣지 않는다 — 새로 계산한 값과 직전 파일 모두."""
    try:
        if not isinstance(v, dict) or set(v) != VALUE_KEYS:
            return False
        if not (_is_day(v["end"]) and _is_day(v["from"]) and v["from"] <= v["end"]):
            return False
        if not (v["last_error"] is None or v["last_error"] in REASONS):
            return False
        c = v["cover"]
        if not isinstance(c, dict) or set(c) != set(COVER_MAX) or not all(_is_int(c[k], m) for k, m in COVER_MAX.items()):
            return False
        ns = v["names"]
        if not isinstance(ns, list) or len(ns) != len(NAMES):
            return False
        for n, (key, label, _) in zip(ns, NAMES):
            if not isinstance(n, dict) or tuple(sorted(n)) != tuple(sorted(NAME_KEYS)):
                return False
            if n["key"] != key or n["label"] != label:
                return False
            if not all(_is_int(n[k]) for k in ("q", "prior_q", "q_1y", "new")):
                return False
            if not (n["new_1y"] is None or _is_int(n["new_1y"])):
                return False
            for lv, q in (("level", "q"), ("prior", "prior_q"), ("level_1y", "q_1y")):
                if not _bp_ok(n[lv]) or (n[lv] is not None and n[q] < MIN_QUOTES):
                    return False
        return True
    except (KeyError, TypeError):
        return False


def core_from(W, run_error):
    return {"date": W["end"], "values": {"end": W["end"], "from": W["from"], "names": W["names"], "cover": W["cover"],
                                         "last_error": run_error}}


def texts(key, v, date):
    """칸 → (숫자 줄, 덧붙이는 줄 목록). 정해 둔 문구에 숫자만 넣는다."""
    cv = v["cover"]
    note = ([f"이번 갱신에서 받지 못한 날이 있다 · {REASONS[v['last_error']]} — 다음 갱신에 이어 받는다."]
            if v["last_error"] else [])
    if key == "quotes":
        parts, none = [], []
        for n in v["names"]:
            if n["level"] is None and not n["q"]:
                none.append(n["label"])                       # 호가가 하나도 없다(선지급 거래뿐인 이름)
                continue
            if n["level"] is None:
                parts.append(f"{n['label']} 호가 부족 {n['q']}개")
                continue
            chg = (_f(n["level"] - n["prior"], 0, True) if n["prior"] is not None else
                   "4주 전 미수신" if not cv["prior"] else "4주 전 호가 부족")
            yr = f" · 1년 전 {_f(n['level_1y'], 0)}" if n["level_1y"] is not None else ""
            parts.append(f"{n['label']} {_f(n['level'], 0, unit='bp')} ({chg}{yr})")
        gap = f" · 받은 날 {cv['level']}/{LEVEL_DAYS}" if cv["level"] < LEVEL_DAYS else ""
        segs = parts + ([f"호가 없음: {'·'.join(none)}"] if none else [])
        line = (f"~{date} 최근 {LEVEL_DAYS}일 중앙값{gap}" + (" — 괄호는 4주 전 대비 · 1년 전" if any("(" in p for p in parts)
                                                          else "") + ": " + " · ".join(segs))
        return (line,
                [f"5년 호가 = 'Spread-Leg 1'에 스프레드가 찍힌 표준 5년 만기 새 거래(만기는 3·9월 20일에 바뀐다)의 최근 "
                 f"{LEVEL_DAYS}일 중앙값, bp. 날마다 중앙값을 호가 수만큼 무게로 모은다 — 원 호가는 남기지 않는다. 호가가 "
                 f"{MIN_QUOTES}개보다 적으면 '호가 부족', 하나도 없으면 '호가 없음'.",
                 "선지급금만 있는 거래는 공개분에 방향 칸이 없어 스프레드로 바꾸지 않는다 — 그런 거래뿐인 이름은 건수 칸에만 있다.",
                 "체결된 거래의 스프레드라 장중 값이 섞이고, 언론이 인용하는 마크와 같은 날에도 몇 bp씩 다를 수 있다.",
                 f"받은 날: 최근 {cv['level']}/{LEVEL_DAYS} · 4주 전 {cv['prior']}/{LEVEL_DAYS} · 1년 전 "
                 f"{cv['level_1y']}/{LEVEL_DAYS}.", *note])
    if key == "trades":
        parts = [f"{n['label']} {n['new']}" + (f" ({n['new_1y']})" if n["new_1y"] is not None else "") for n in v["names"]]
        gap = f" · 받은 날 {cv['count']}/{COUNT_DAYS}, 받은 날만 셈" if cv["count"] < COUNT_DAYS else ""
        yago = (f" — 괄호는 1년 전 같은 {COUNT_DAYS}일" if any(n["new_1y"] is not None for n in v["names"]) else "")
        return (f"{v['from']}~{date} {COUNT_DAYS}일{gap}{yago}: " + " · ".join(parts),
                [f"새 거래 = 새로 체결된 단일종목 CDS(모든 만기·순위). 같은 파일 안의 취소, 같은 시각·명목·선지급금이 여러 기준 "
                 f"실체에 찍힌 묶음 행, 같은 초에 {BUNDLE_NAMES}곳 이상이 찍힌 대형 포트폴리오 거래는 뺀다 — 2~"
                 f"{BUNDLE_NAMES - 1}곳 바구니는 센다. 체결일이 파일 날짜 {LAG_DAYS}일 안인 것만.",
                 "다음 날 이후 취소된 거래(새 거래의 약 3%)는 섞인다. 명목 500만 달러 이상은 '5,000,000+'로 가려져 거래 크기는 "
                 "보지 않는다 — 건수는 헤지·투기 수요의 대략이다.",
                 f"받은 날: 최근 {cv['count']}/{COUNT_DAYS} · 1년 전 {cv['count_1y']}/{COUNT_DAYS} — 1년 전 건수는 그 "
                 f"{COUNT_DAYS}일을 모두 받아 둔 경우만 싣는다.", *note])
    raise KeyError(key)


def table_of(key, v):
    """이름마다 한 줄의 표 — 정해 둔 머리글 + 숫자."""
    cv = v["cover"]
    if key == "quotes":
        rows = []
        for n in v["names"]:
            if n["level"] is None:
                lv, chg = ("호가 없음" if not n["q"] else "호가 부족"), "—"
            else:
                lv = _f(n["level"], 0)
                chg = (_f(n["level"] - n["prior"], 0, True) if n["prior"] is not None else
                       "4주 전 미수신" if not cv["prior"] else "4주 전 호가 부족")
            rows.append([n["label"], lv, chg, _f(n["level_1y"], 0), str(n["q"])])
        return {"caption": f"5년 호가, bp — 최근 {LEVEL_DAYS}일 중앙값", "columns": ["이름", "5년 호가", "4주 전 대비",
                                                                             "1년 전", "호가 수"], "rows": rows}
    if key == "trades":
        return {"caption": f"새 거래 건수 — {v['from']}~{v['end']}", "columns": ["이름", f"최근 {COUNT_DAYS}일",
                                                                             f"1년 전 같은 {COUNT_DAYS}일"],
                "rows": [[n["label"], str(n["new"]), "—" if n["new_1y"] is None else str(n["new_1y"])]
                         for n in v["names"]]}
    raise KeyError(key)


def citation():
    return CITATION


def sources_of():
    return [{"series": DATASET, "name": "DTCC Data Repository (U.S.) LLC", "licence": LICENCE[DATASET],
             "citation": citation()}]


def notices():
    return [COMPUTED_NOTICE, CAVEAT_NOTICE]


def present(key, core, retrieved):
    line, extra = texts(key, core["values"], core["date"])
    return {"key": key, "name": TITLE[key], "date": core["date"], "values": core["values"], "retrieved": retrieved,
            "line": line, "extra": extra, "table": table_of(key, core["values"]), "notices": notices(),
            "sources": sources_of()}


# ---------- 직전 파일 ----------

def core_of(item, key):
    """직전 파일의 칸 → (core, 받은 날) 또는 None(없거나 꼴이 어긋남)."""
    try:
        vals = item["values"]
        ok = (_is_day(item["date"]) and _is_day(item["retrieved"]) and values_ok(vals) and vals["end"] == item["date"])
        if ok:
            texts(key, vals, item["date"])
            table_of(key, vals)
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
    return prev.get("failed_since") if prev and prev.get("ok") is not True and _is_day(prev.get("failed_since")) \
        else today.isoformat()


def _retrieved(old, core, today):
    same = old and json.loads(json.dumps(old[0])) == json.loads(json.dumps(core))
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
    """받아 둔 날로 창을 냈지만 끝 날이 오래됨 — 숫자는 싣고 '받지 못함'과 그날부터."""
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


def build(W, run_error, prev, now):
    """창(W 또는 None)·이번 수신의 사유 코드 → 산출물 dict."""
    today = now.date()
    items = {}
    for key in ORDER:
        p = prev.get(key)
        try:
            if W is None:
                items[key] = item_failed(key, run_error or "none", p, today)
            else:
                core = core_from(W, run_error)
                if W["stale"]:
                    items[key] = item_stale(key, run_error or "old", core, p, today)
                else:
                    items[key] = item_ok(key, core, p, today)
        except Exception as e:                        # 꼴이 어긋난 계산 — 그 칸만 실패로
            print(f"[cds_fetch] {key} 계산 오류: {type(e).__name__}", file=sys.stderr)
            items[key] = item_failed(key, "format" if W is not None else run_error or "none", p, today)
    return {"schema": SCHEMA, "generated_at": now.isoformat(timespec="seconds"), "notice": NOTICE, "order": list(ORDER),
            "items": items}


# ---------- 쓰기 ----------

def differs(path, text):
    try:
        with open(path, encoding="utf-8") as f:
            old = f.read()
    except OSError:
        return True
    return old != text


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


def main(argv=None, opener=None, now=None, clock=time.monotonic):
    ap = argparse.ArgumentParser(description="DTCC 공개 CDS 거래 보고 → 단일종목 CDS 참고 자료(<out>/cds.json · cds_days.json)")
    ap.add_argument("--out", default=DEFAULT_OUT, help="사이트 데이터 폴더 (기본: 저장소의 data/)")
    ap.add_argument("--budget", type=float, default=BUDGET, help=f"수신 전체 상한(초, 기본 {BUDGET})")
    ap.add_argument("--offline", action="store_true", help="받지 않고 받아 둔 날로 창만")
    ap.add_argument("--force", action="store_true", help="같은 날 앞선 실행이 멈췄어도 다시 받는다")
    a = ap.parse_args(argv)
    out = os.path.abspath(a.out)
    now = now or datetime.datetime.now(datetime.timezone.utc)
    today = now.date()
    store = load_store(out)
    r = {"fetched": 0, "absent": 0, "bad": 0, "missing": 0, "error": None, "skipped": False}
    if not a.offline:
        r = sync(store, today, budget=a.budget, opener=opener, clock=clock, force=a.force)
    prune(store, today)
    W = window(store["days"], today)
    data = build(W, r["error"], previous(out), now)
    # Actions 로그 — 날짜·셈·정해 둔 사유만(값·원격 글은 찍지 않는다)
    print(f"[cds_fetch] 받음 {r['fetched']}일 · 없음 {r['absent']}일 · 그날 오류 {r['bad']}일 · 못 받은 날 {r['missing']}일 · "
          f"받아 둔 날 {len(store['days'])}일"
          + (f" · 끝 {W['end']}" if W else ""))
    if r["error"]:
        annotate(f"단일종목 CDS 참고: {REASONS[r['error']]}" + (" — 같은 날 앞선 실행이 멈춰 건너뜀" if r["skipped"] else ""))
    for key in ORDER:
        it = data["items"][key]
        if not it["ok"]:
            kept = f" — 받아 둔 값({it['date']} 기준)을 싣는다" if it["stale"] else ""
            annotate(f"단일종목 CDS 참고 {key}: {it['error']}{kept}")
    try:
        os.makedirs(out, exist_ok=True)
        text = store_text(store)
        if not a.offline and differs(os.path.join(out, STORE), text):
            _atomic_write(os.path.join(out, STORE), text)
        if summary_differs(out, data):
            _atomic_write(os.path.join(out, FILE), summary_text(data))
    except OSError as e:
        print(f"[cds_fetch] 파일을 쓰지 못함: {type(e).__name__}", file=sys.stderr)
        return 1
    return 0 if not r["error"] and any(it["ok"] for it in data["items"].values()) else 1


if __name__ == "__main__":
    sys.exit(main())
