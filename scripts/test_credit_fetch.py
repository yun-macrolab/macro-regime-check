#!/usr/bin/env python3
"""신용 긴축 참고 자료(credit_fetch) 테스트 — 규칙 C의 경계·3값 논리·반올림 전 판정, 분위·묵음, AI 투자 칸, 주가 낙폭
(정수 낙폭 % 하나만 — 지수 값·12개월 고점·수익률 비노출, 소수 둘째 자리 먼저·반올림 경계), 신용 스트레스(공개 자료) EBP·CMDI
(파일 읽기·줄 끝·꼴 검사(깨진 CSV·설명 시트·날짜 머리글·일련번호 범위·없는 공유 문자열은 'layout')·변화·분위·고지·User-Agent·
넘겨짐·5MB 상한), sec.json 옮겨 싣기, 칸마다 실패·직전 값, 이용 조건 목록, 문구 원칙, 화면·워크플로 연결.
비공개 원본 credit_block의 테스트 사례를 옮겼다(숫자는 그쪽처럼 손으로 셀 수 있게 지어낸 것).

실행:  python -m unittest discover -s scripts   (저장소 루트에서)
네트워크 불필요 — FRED는 가짜 loader, 연준 이사회·뉴욕 연은은 가짜 opener(지어낸 CSV·zipfile로 지은 xlsx), SEC는 가짜 응답.
이 모듈이 도는 동안 urllib.request.urlopen은 막아 둔다(실수로 나가는 요청은 실패). 숫자는 모두 지어낸 것이다.
"""
import os, sys, io, re, json, math, shutil, zipfile, datetime, tempfile, unittest, contextlib
from unittest import mock
from xml.sax.saxutils import escape, quoteattr

SCRIPTS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPTS)
import credit_fetch as cf
import fred_fetch as ff
import sec_fetch as sf
import ai_invest_fetch as ai
import render_public as rp
import test_sec_fetch as tsf
from test_render_public import FORBIDDEN_TEXT

REPO = os.path.dirname(SCRIPTS)
D = datetime.date
TODAY = D(2026, 10, 30)
NOW = datetime.datetime(2026, 10, 30, 1, 30, tzinfo=datetime.timezone.utc)
PRICE = 87654.321                     # 지수 값(재배포 제한) — 파일·문구 어디에도 나오면 안 된다
NF_END = D(2026, 10, 16)              # 지어낸 마지막 NFCI 관측(금) — TODAY에서 14일(묵음 문턱 바로 안)
VERDICT = ("판정", "충족", "신호", "경보", "전망", "매수", "매도", "⚠", "강세", "약세", "호재", "악재", "우려", "부담",
           "상승", "하락", "→")
EST_PROB = 0.4321987                  # 지어낸 침체 확률 열 값 — 파일·로그 어디에도 나오면 안 된다
_NET = None


def setUpModule():                    # 실수로 나가는 요청을 막는다(가짜 opener를 주지 않은 경로는 실패로)
    global _NET
    _NET = mock.patch("urllib.request.urlopen", side_effect=AssertionError("network in test"))
    _NET.start()


def tearDownModule():
    _NET.stop()


def quarters(y0, q0, y1, q1):
    out, y, q = [], y0, q0
    while (y, q) <= (y1, q1):
        out.append(D(y, 3 * q - 2, 1))
        y, q = (y + 1, 1) if q == 4 else (y, q + 1)
    return out


def fridays(start, end):
    out, d = [], start
    while d <= end:
        out.append(d)
        d += datetime.timedelta(days=7)
    return out


def bdays(end, n):
    out, d = [], end
    while len(out) < n:
        if d.weekday() < 5:
            out.append(d)
        d -= datetime.timedelta(days=1)
    return out[::-1]


def sloos_world(end=D(2026, 7, 1)):
    """1990Q2부터 −10·0·10·20·30이 돌고, 마지막(2026Q3 조사)은 0."""
    qs = [q for q in quarters(1990, 2, 2030, 4) if q <= end]
    return [(q, (-10.0, 0.0, 10.0, 20.0, 30.0)[(i + 1) % 5]) for i, q in enumerate(qs)]


def nfci_world(end=NF_END, last=-0.031, back=-0.071):
    """1989-10-06(금)부터 0.1·sin — 마지막과 13주 전만 정해 둔다(13주 변화 +0.040)."""
    ds = fridays(D(1989, 10, 6), end)
    s = [(d, round(0.1 * math.sin(i / 7), 3)) for i, d in enumerate(ds)]
    s[-14] = (s[-14][0], back)
    s[-1] = (s[-1][0], last)
    return s


def index_world(end=D(2026, 10, 28), n=600, drop=None):
    """영업일 n개, PRICE에서 하루 0.01%씩 오르다 drop = [(뒤에서 몇째 날부터, 고점 대비 비율)]이면 그날부터 그 비율로."""
    ds = bdays(end, n)
    px = [PRICE * (1.0001 ** i) for i in range(n)]
    for k, f in drop or ():
        top = px[n - k - 1]
        for i in range(n - k, n):
            px[i] = top * f
    return list(zip(ds, px))


def world():
    S = {"DRTSCILM": sloos_world(), "NFCICREDIT": nfci_world()}
    qs = quarters(2018, 1, 2026, 3)
    S["GDP"] = [(q, 20000.0 + 100 * i) for i, q in enumerate(qs)]
    S["A679RC1Q027SBEA"] = [(q, g * (4.0 + 0.05 * i) / 100) for i, (q, g) in enumerate(S["GDP"])]   # 비중 4분기 +0.20%p
    zq = quarters(1984, 1, 2026, 2)
    S["BOGZ1FA106000135Q"] = [(q, 100.0) for q in zq]
    S["BOGZ1FA105050005Q"] = [(q, 90.0 if i >= len(zq) - 4 else 100.0 + 20 * math.sin(i / 3)) for i, q in enumerate(zq)]
    S["NASDAQ100"] = index_world()
    S["NASDAQNQINTEL"] = index_world(drop=[(30, 0.8613)])                     # 30영업일 전부터 고점 대비 약 −14%
    return S


# ---------- 연준 이사회 EBP · 뉴욕 연은 CMDI (지어낸 파일) ----------

def months(y0, m0, y1, m1):
    out, y, m = [], y0, m0
    while (y, m) <= (y1, m1):
        out.append(D(y, m, 1))
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return out


EBP_LAST = D(2026, 9, 1)


def ebp_rows(end=EBP_LAST):
    """1973-01부터 end까지 — EBP는 0.1·sin, GZ는 1.5 + 0.3·cos(퍼센트포인트). 마지막·3개월 전·마지막 GZ만 정해 둔다."""
    ms = months(1973, 1, end.year, end.month)
    rows = [[m, round(0.1 * math.sin(i / 5), 4), round(1.5 + 0.3 * math.cos(i / 4), 4), EST_PROB] for i, m in enumerate(ms)]
    rows[-1][1], rows[-1][2] = 0.1234, 1.8765                    # → EBP +12.3bp · GZ 187.7bp
    rows[-4][1] = 0.0567                                          # 3개월 전 → 변화 +6.7bp
    return rows


def ebp_csv(rows=None, header="date,gz_spread,ebp,est_prob", fmt=lambda d: d.isoformat(), bom=False):
    rows = ebp_rows() if rows is None else rows
    lines = [header] + [f"{fmt(d)},{'' if g is None else g},{'' if e is None else e},{p}" for d, e, g, p in rows]
    return (("\ufeff" if bom else "") + "\n".join(lines) + "\n").encode("utf-8")


MAIN_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
STRICT_NS = "http://purl.oclc.org/ooxml/spreadsheetml/main"
REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"


def serial(d):
    return float((d - D(1899, 12, 30)).days)


def _colname(j):
    s = ""
    j += 1
    while j:
        j, r = divmod(j - 1, 26)
        s = chr(65 + r) + s
    return s


def make_xlsx(sheets, ns=MAIN_NS, inline=False, rich=(), abs_target=False, extra=None, no_refs=False, fstr=()):
    """[(시트 이름, 행 목록)] → xlsx 바이트(zipfile로 짓는다). 행의 칸: 글 → 공유 문자열(inline이면 인라인), 수 → 수, None → 빈 칸.
    rich의 글은 <r> 둘로 쪼개고 발음 표기(<rPh>)를 붙인다. fstr의 글은 수식 결과 글(t="str")로 둔다."""
    shared, idx = [], {}
    def sidx(t):
        if t not in idx:
            idx[t] = len(shared)
            shared.append(t)
        return idx[t]
    parts = {}
    for n, (name, rows) in enumerate(sheets, 1):
        xs = []
        for i, row in enumerate(rows, 1):
            cells = []
            for j, v in enumerate(row):
                if v is None:
                    continue
                ref = "" if no_refs else f' r="{_colname(j)}{i}"'
                if isinstance(v, str) and v in fstr:
                    cells.append(f'<c{ref} t="str"><f>CONCAT("x")</f><v>{escape(v)}</v></c>')
                elif isinstance(v, str) and inline:
                    cells.append(f'<c{ref} t="inlineStr"><is><t>{escape(v)}</t></is></c>')
                elif isinstance(v, str):
                    cells.append(f'<c{ref} t="s"><v>{sidx(v)}</v></c>')
                else:
                    cells.append(f"<c{ref}><v>{v!r}</v></c>")
            xs.append(f'<row r="{i}">{"".join(cells)}</row>')
            if no_refs:                                           # 빈 칸을 건너뛰면 열이 밀리므로 이 꼴은 빈 칸 없이만 쓴다
                assert None not in row
        parts[f"xl/worksheets/sheet{n}.xml"] = (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                                                 f'<worksheet xmlns="{ns}"><sheetData>{"".join(xs)}</sheetData></worksheet>')
    sis = []
    for t in shared:
        if t in rich:
            a, b = t[:len(t) // 2], t[len(t) // 2:]
            sis.append(f"<si><r><t>{escape(a)}</t></r><r><rPr/><t>{escape(b)}</t></r><rPh><t>ヨミ</t></rPh></si>")
        else:
            sis.append(f"<si><t>{escape(t)}</t></si>")
    if shared:
        parts["xl/sharedStrings.xml"] = f'<sst xmlns="{ns}" count="{len(shared)}">{"".join(sis)}</sst>'
    sh = "".join(f'<sheet name={quoteattr(name)} sheetId="{n}" r:id="rId{n}"/>' for n, (name, _) in enumerate(sheets, 1))
    parts["xl/workbook.xml"] = f'<workbook xmlns="{ns}" xmlns:r="{REL_NS}"><sheets>{sh}</sheets></workbook>'
    tgt = (lambda n: f"/xl/worksheets/sheet{n}.xml") if abs_target else (lambda n: f"worksheets/sheet{n}.xml")
    rels = "".join(f'<Relationship Id="rId{n}" Type="{REL_NS}/worksheet" Target="{tgt(n)}"/>' for n in range(1, len(sheets) + 1))
    parts["xl/_rels/workbook.xml.rels"] = ('<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                                           f"{rels}</Relationships>")
    parts["[Content_Types].xml"] = '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"/>'
    parts.update(extra or {})
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for k, v in parts.items():
            z.writestr(k, v)
    return buf.getvalue()


CMDI_END = D(2026, 9, 25)             # 지어낸 마지막 금요일 — 발표가 늦어 TODAY보다 5주 앞


def cmdi_table(end=CMDI_END, header=("eow_friday", "Market CMDI", "IG CMDI", "HY CMDI", "Financial CMDI")):
    """2005-01-07부터 end까지 금요일 — 열마다 0.2 + 0.1·sin. 마지막과 28일 전만 정해 둔다(시장 전체 4주 +0.1345)."""
    ds = fridays(D(2005, 1, 7), end)
    rows = [list(header)]
    for i, d in enumerate(ds):
        rows.append([serial(d)] + [round(0.2 + 0.1 * math.sin(i / (9 + c)), 4) for c in range(len(header) - 1)])
    rows[-1][1:4] = [0.3456, 0.2789, 0.4012]
    rows[-5][1:4] = [0.2111, 0.2999, 0.4012]
    return rows


def cmdi_xlsx(**kw):
    return make_xlsx([("Notes", [["About this file"], ["Weekly index"]]), ("Index Data", cmdi_table(**kw))])


def patch_part(blob, name, fn):
    """xlsx 바이트의 부분 하나를 fn(글)으로 고친 사본."""
    with zipfile.ZipFile(io.BytesIO(blob)) as z:
        parts = {n: z.read(n) for n in z.namelist()}
    parts[name] = fn(parts[name].decode("utf-8")).encode("utf-8")
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        for k, v in parts.items():
            z.writestr(k, v)
    return buf.getvalue()

class FakeResp:
    def __init__(self, url, body):
        self.url, self.buf = url, io.BytesIO(body)

    def geturl(self):
        return self.url

    def read1(self, n):
        return self.buf.read(n)

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class FakeWeb:
    """가짜 opener — 주소 → 바이트 | (넘겨진 주소, 바이트) | 예외. 부른 주소·User-Agent·타임아웃을 적어 둔다."""
    def __init__(self, answers=None):
        self.answers = {cf.EBP_URL: ebp_csv(), cf.CMDI_URL: cmdi_xlsx()} if answers is None else answers
        self.calls = []

    def __call__(self, req, timeout=None):
        url = req if isinstance(req, str) else req.full_url
        ua = None if isinstance(req, str) else req.get_header("User-agent")
        self.calls.append((url, ua, timeout))
        a = self.answers.get(url)
        if isinstance(a, Exception):
            raise a
        if a is None:
            raise OSError("no route")
        final, body = a if isinstance(a, tuple) else (url, a)
        return FakeResp(final, body)


class FakeFred:
    def __init__(self, data, fail=(), cache=()):
        self.data, self.fail, self.cache, self.calls = data, set(fail), set(cache), []

    def __call__(self, sid, cache_dir, offline=False, timeout=None):
        self.calls.append((sid, timeout))
        if sid in self.fail:
            raise RuntimeError(f"{sid}: 원문 사유 https://bad.invalid/xyz-77")
        return list(self.data[sid]), ("cache" if sid in self.cache else "net")


def stage(S, today=TODAY):
    return cf.calc_stage(S, today)["values"]


class RuleTest(unittest.TestCase):
    def test_every_boundary(self):
        r = lambda *a: cf.rule_c(*a)[0]
        self.assertEqual(r(0.0, 0.0, 0.0), 0)
        self.assertEqual(r(9.99, 0.0769, 0.0), 0)                                  # 둘 다 문턱 바로 아래
        self.assertEqual(r(10.0, 0.0, 0.0), 1)                                     # S = 10 (이상)
        self.assertEqual(r(0.0, 0.077, 0.0), 1)                                    # N13 = +0.077 (이상)
        self.assertEqual(r(24.19, 0.5, 1.0), 1)                                    # S가 24.2 바로 아래면 2가 아니다
        self.assertEqual(r(24.2, 0.148, 0.0), 2)
        self.assertEqual(r(24.2, 0.1479, 0.0), 1)
        self.assertEqual(r(24.2, 0.0, 0.183), 2)                                   # 수준 0.183
        self.assertEqual(r(24.2, 0.0, 0.1829), 1)
        self.assertEqual(r(-30.0, -0.5, -1.0), 0)                                  # 완화 쪽은 0(숫자만)

    def test_level_two_needs_both_gauges(self):
        r = lambda *a: cf.rule_c(*a)[0]
        self.assertEqual(r(80.0, 0.0, 0.0), 1)                                     # SLOOS만 아주 높아도 1
        self.assertEqual(r(5.0, 0.9, 2.0), 1)                                      # NFCI만 높아도 1
        self.assertEqual(r(80.0, 0.9, 2.0), 2)

    def test_compare_after_six_decimal_rounding(self):
        n13 = 0.177 - 0.1                                                         # 0.07699999…
        self.assertLess(n13, cf.N1)
        self.assertEqual(cf.rule_c(0.0, n13, 0.0)[0], 1)
        self.assertEqual(cf.rule_c(24.2 - 4e-7, 0.2, 0.0)[0], 2)                   # 반올림하면 24.2
        self.assertEqual(cf.rule_c(24.2 - 6e-7, 0.2, 0.0)[0], 1)                   # 24.199999
        self.assertEqual(cf.rule_c(9.9999996, 0.0, 0.0)[0], 1)
        self.assertEqual(cf.rule_c(9.999999, 0.0, 0.0)[0], 0)

    def test_unknown_gauge_three_valued(self):
        self.assertEqual(cf.rule_c(None, 0.1, 0.0), (1, 1, 1))
        self.assertEqual(cf.rule_c(None, 0.2, 0.0), (None, 1, 2))
        self.assertEqual(cf.rule_c(None, 0.0, 0.0), (None, 0, 1))
        self.assertEqual(cf.rule_c(12.0, None, None), (1, 1, 1))
        self.assertEqual(cf.rule_c(30.0, None, None), (None, 1, 2))
        self.assertEqual(cf.rule_c(5.0, None, None), (None, 0, 1))
        self.assertEqual(cf.rule_c(30.0, None, 0.5), (2, 2, 2))
        self.assertEqual(cf.rule_c(None, None, None), (None, 0, 2))
        self.assertEqual([cf.level_text(*cf.rule_c(*a)) for a in ((None, 0.2, 0.0), (0.0, 0.0, 0.0))], ["?/2 (1~2)", "0/2"])

    def test_rule_reads_unrounded_values(self):
        S = world()
        S["DRTSCILM"] = [(d, 9.996) for d, _ in sloos_world()]                    # 표시(2자리)로는 10.0
        v = stage(S)
        self.assertEqual((v["s"], v["value"]), (10.0, 0))
        S = world()
        S["NFCICREDIT"] = nfci_world(last=0.07696, back=0.0)                      # 표시(4자리)로는 +0.077
        v = stage(S)
        self.assertEqual((v["n13"], v["value"]), (0.077, 0))
        line = cf.texts("stage", v, "2026-10-16")[0]
        self.assertTrue(line.startswith("긴축 0/2 — "), line)
        self.assertIn("13주 +0.077", line)
        S = world()
        S["DRTSCILM"] = [(d, 30.0) for d, _ in sloos_world()]
        S["NFCICREDIT"] = nfci_world(last=0.18296, back=0.18296)                  # 수준 표시 0.183 · 13주 0
        self.assertEqual((stage(S)["nl"], stage(S)["value"]), (0.183, 1))
        S["NFCICREDIT"] = nfci_world(last=0.1829996, back=0.1829996)             # 6자리 반올림이면 0.183 → 2
        self.assertEqual(stage(S)["value"], 2)

    def test_thresholds_are_the_fixed_ones_and_the_definition_states_them(self):
        self.assertEqual((cf.S1, cf.S2, cf.N1, cf.N2, cf.NL2, cf.FIXED), (10.0, 24.2, 0.077, 0.148, 0.183, "2026-10-29"))
        self.assertEqual((cf.NFCI_STALE, cf.SLOOS_STALE, cf.DD_WINDOW, cf.DD_REST), (14, 150, 252, 126))
        for frag in ("S ≥ 24.2 그리고 (N13 ≥ +0.148 또는 NL ≥ +0.183)", "S ≥ 10 또는 N13 ≥ +0.077", "150일", "14일",
                     "고정 2026-10-29", "예측력 미검증"):
            self.assertIn(frag, cf.STAGE_DEF)


class GaugeTest(unittest.TestCase):
    def test_sloos_latest_survey_usable_from_next_month_and_percentile(self):
        S = {"DRTSCILM": sloos_world(D(2026, 10, 1))}                             # 10월 조사가 이미 들어온 캐시
        sl, raw = cf.sloos(S, D(2026, 10, 30))
        self.assertEqual((sl["survey"], raw), ("2026-07-01", 0.0))                 # 10월 조사는 11월부터
        self.assertEqual(cf.sloos(S, D(2026, 11, 1))[0]["survey"], "2026-10-01")
        vals = [v for _, v in sloos_world()]
        self.assertEqual(sl["pct"], round(sum(v <= 0 for v in vals) / len(vals) * 100, 1))
        self.assertEqual(sl["pct"], 40.4)
        self.assertEqual(cf.sloos({"DRTSCILM": []}, TODAY), (None, None))

    def test_sloos_percentile_counts_from_1990_only(self):
        for pre in (99.0, -50.0):
            sl, _ = cf.sloos({"DRTSCILM": [(q, pre) for q in quarters(1985, 1, 1989, 4)] + sloos_world()}, TODAY)
            self.assertEqual(sl["pct"], 40.4)

    def test_staleness_edges(self):
        S = {"DRTSCILM": sloos_world()}
        self.assertFalse(cf.sloos(S, D(2026, 7, 1) + datetime.timedelta(days=150))[0]["stale"])
        self.assertTrue(cf.sloos(S, D(2026, 7, 1) + datetime.timedelta(days=151))[0]["stale"])
        N = {"NFCICREDIT": nfci_world()}
        self.assertFalse(cf.nfci(N, NF_END + datetime.timedelta(days=14))[0]["stale"])
        self.assertTrue(cf.nfci(N, NF_END + datetime.timedelta(days=15))[0]["stale"])

    def test_nfci_thirteen_weeks_and_percentiles_from_1990(self):
        s = nfci_world()
        nf, n13, nl = cf.nfci({"NFCICREDIT": s}, TODAY)
        self.assertEqual((nf["level"], nf["n13"], nf["asof"], nf["from"]), (-0.031, 0.04, "2026-10-16", "2026-07-17"))
        self.assertAlmostEqual(n13, 0.04)
        h = [(d, v) for d, v in s if d >= D(1990, 1, 1)]
        hist = [h[i][1] - h[i - 13][1] for i in range(13, len(h))]                 # 두 끝이 1990년 이후(구현과 따로)
        self.assertEqual(nf["pct_n13"], round(sum(x <= -0.031 - -0.071 for x in hist) / len(hist) * 100, 1))
        self.assertEqual(nf["n_hist"], len(hist))
        self.assertEqual(nf["pct_level"], round(sum(v <= -0.031 for _, v in h) / len(h) * 100, 1))
        gap = [(D(2026, 7, 16), x[1]) if x[0] == D(2026, 7, 17) else x for x in s]   # 13주 전이 하루 앞(목)이면 그 관측
        self.assertEqual(cf.nfci({"NFCICREDIT": gap}, TODAY)[0]["from"], "2026-07-16")
        gap = [x for x in s if x[0] != D(2026, 7, 17)]                            # 한 주가 빠지면(7일) 13주 변화 없음
        self.assertIsNone(cf.nfci({"NFCICREDIT": gap}, TODAY)[0]["n13"])
        far = [x for x in s if not D(2026, 7, 3) <= x[0] <= D(2026, 7, 17)]
        self.assertIsNone(cf.nfci({"NFCICREDIT": far}, TODAY)[0]["n13"])
        self.assertIn("13주 변화 계산 불가", cf.texts("stage", stage(dict(world(), NFCICREDIT=gap)), "2026-10-16")[0])

    def test_stale_gauge_gives_question_mark_with_range(self):
        S = world()
        self.assertEqual(stage(S)["value"], 0)
        S["NFCICREDIT"] = nfci_world(last=0.3, back=0.1)                          # N13 +0.2 · 수준 0.3
        S["DRTSCILM"] = [(d, 30.0) for d, _ in sloos_world()]
        self.assertEqual(stage(S)["value"], 2)
        old = D(2026, 7, 1) + datetime.timedelta(days=151)                        # SLOOS 151일 묵음 → S 모름
        S2 = {**S, "NFCICREDIT": nfci_world(end=old - datetime.timedelta(days=3), last=0.3, back=0.1)}
        v = stage(S2, old)
        self.assertEqual((v["value"], v["lo"], v["hi"], v["s_stale"]), (None, 1, 2, True))
        line = cf.texts("stage", v, "x")[0]
        self.assertTrue(line.startswith("긴축 ?/2 (1~2) — "), line)
        self.assertIn("묵음: 조사월부터 150일 넘음 — 모름으로", line)
        late = TODAY + datetime.timedelta(days=20)                                # NFCI 34일 묵음 → N13·수준 모름
        v = stage(S, late)
        self.assertEqual((v["value"], v["lo"], v["hi"], v["n_stale"]), (None, 1, 2, True))
        self.assertIn("묵음: 마지막 관측이 14일 넘음 — 모름으로", cf.texts("stage", v, "x")[0])
        with self.assertRaises(cf.ItemError):
            stage(dict(S, DRTSCILM=[(D(2026, 10, 1), 5.0)]))                       # 쓸 조사가 아직 없다


class AxisTest(unittest.TestCase):
    def test_invest_axis_exact_year_ago(self):
        v = cf.invest_axis(world())
        self.assertEqual((v["quarter"], v["axis"]), ("2026-07-01", "확장"))
        self.assertAlmostEqual(v["ch4"], 0.2, places=4)
        S = world()
        S["A679RC1Q027SBEA"] = [(q, g * 4.0 / 100) for q, g in S["GDP"]]           # 비중이 그대로면 소화
        self.assertEqual(cf.invest_axis(S)["axis"], "소화")
        S["A679RC1Q027SBEA"] = [x for x in S["A679RC1Q027SBEA"] if x[0] != D(2025, 7, 1)]   # 1년 전 분기가 없으면 비운다
        self.assertIsNone(cf.invest_axis(S))
        with self.assertRaises(cf.ItemError):
            cf.calc_cell(S, TODAY)

    def test_fund_axis_uses_the_public_ai_median(self):
        S = world()
        v, fin = cf.fund_axis(S), ai.calc_financing(S)["values"]
        self.assertEqual((v["ratio"], v["median"], v["median_from"]), (fin["ratio"], fin["median"], fin["from"]))
        self.assertEqual((v["ratio"], v["high"], v["axis"]), (90.0, False, "현금 조달"))
        pts = [x for d, x in ai.quarterly_ratio(S["BOGZ1FA105050005Q"], S["BOGZ1FA106000135Q"], 4) if d >= D(1990, 1, 1)]
        self.assertEqual(v["pct"], round(sum(x <= 90.0 for x in pts) / len(pts) * 100, 1))
        S["BOGZ1FA105050005Q"] = [(d, 99.9) if d >= D(2025, 7, 1) else (d, x) for d, x in S["BOGZ1FA105050005Q"]]
        v = cf.fund_axis(S)                                                       # 100% 아래여도 자기 중앙값보다 높으면 부채 조달
        self.assertLess(v["median"], v["ratio"])
        self.assertLess(v["ratio"], 100)
        self.assertEqual(v["axis"], "부채 조달")
        self.assertTrue(cf.texts("gap", cf.calc_gap(S, TODAY)["values"], "x")[0].endswith("— 해당"))

    def test_fund_axis_equal_to_median_is_not_high(self):
        S = world()
        S["BOGZ1FA105050005Q"] = [(q, 100.0) for q, _ in S["BOGZ1FA106000135Q"]]   # 모든 분기 100% → 값 = 중앙값
        c = cf.calc_cell(S, TODAY)["values"]
        self.assertEqual((c["ratio"], c["median"], c["high"], c["fund"]), (100.0, 100.0, False, "현금 조달"))
        self.assertIn("100.0% (2026Q2) ≤ 1985~ 중앙값 100.0%", cf.texts("cell", c, "x")[0])
        line = cf.texts("gap", cf.calc_gap(S, TODAY)["values"], "x")[0]
        self.assertTrue(line.endswith("— 해당 없음"), line)
        self.assertIn("1990~ 상위 0%", line)
        line = cf.texts("gap", cf.calc_gap(world(), TODAY)["values"], "x")[0]
        self.assertRegex(line, r"1990~ 하위 \d+% — 해당 없음$")


class DrawdownTest(unittest.TestCase):
    def test_band_and_first_entry(self):
        v = cf.calc_drawdown(world(), TODAY)["values"]
        ds = [d for d, _ in index_world()]
        self.assertEqual((v["ndx_dd"], v["ndx_band"], v["ndx_e10"], v["ndx_e20"]), (0, "in10", None, None))
        self.assertEqual((v["ai_dd"], v["ai_band"], v["ai_e10"], v["ai_e20"]), (-14, "10to20", ds[-30].isoformat(), None))
        self.assertEqual(v["ai_asof"], "2026-10-28")
        self.assertEqual([k for k, x in v.items() if isinstance(x, (int, float))], ["ndx_dd", "ai_dd"])   # 숫자는 이 둘뿐

    def test_whole_percent_rounds_half_away_from_zero(self):
        cases = [(0.0, 0), (-0.4, 0), (-0.49, 0), (-0.5, -1), (-12.4999, -12), (-12.5, -13), (-12.51, -13), (-9.5, -10),
                 (-19.5, -20), (-100.0, -100), (-13.87, -14), (-12.4999996, -13), (-12.499999, -12), (-0.0000004, 0)]
        for x, want in cases:
            got = cf.dd_pct(x)
            self.assertEqual((got, type(got)), (want, int), x)
        self.assertEqual(str(cf.dd_pct(-0.3)), "0")                                # −0이 아니라 0
        self.assertEqual(cf._dd(0), "0%")
        self.assertEqual(cf._dd(-14), "−14%")

    def test_drawdown_percent_from_the_series(self):
        S = dict(world(), NASDAQ100=index_world(drop=[(5, 0.875)]), NASDAQNQINTEL=index_world(drop=[(5, 0.905)]))
        v = cf.calc_drawdown(S, TODAY)["values"]                                  # −12.5% → −13 · −9.5% → −10(구간은 10% 안)
        self.assertEqual((v["ndx_dd"], v["ndx_band"]), (-13, "10to20"))
        self.assertEqual((v["ai_dd"], v["ai_band"]), (-10, "in10"))
        self.assertTrue(cf._consistent("drawdown", v))
        self.assertIn("AI 지수 고점 대비 −10% (10% 안)", cf.texts("drawdown", v, "2026-10-28")[0])
        for bad in (dict(v, ndx_dd=-9), dict(v, ai_dd=-11), dict(v, ndx_band="over20")):
            self.assertFalse(cf._consistent("drawdown", bad), bad)

    def test_band_boundaries(self):
        self.assertEqual([cf.band(x) for x in (0.0, -9.999999, -9.9999996, -10.0, -19.99, -20.0, -55.0)],
                         ["in10", "in10", "10to20", "10to20", "10to20", "over20", "over20"])

    def test_entry_needs_six_months_without_that_drawdown(self):
        s = index_world(drop=[(200, 0.85), (60, 0.85 * 0.97)])                    # 200일 전 −15% 진입, 그 뒤 계속 −10% 아래
        dd = cf.drawdowns(s)
        self.assertIsNone(cf.first_entries(dd, 10))
        self.assertNotEqual(cf.band(dd[-1][1]), "in10")
        s = index_world(drop=[(100, 0.75)])
        dd = cf.drawdowns(s)
        ds = [d for d, _ in s]
        self.assertEqual((cf.first_entries(dd, 10), cf.first_entries(dd, 20)), (ds[-100].isoformat(), ds[-100].isoformat()))
        self.assertEqual(cf.band(dd[-1][1]), "over20")

    def test_drawdown_window_is_252_observations(self):
        ds = bdays(TODAY, 300)
        dd = cf.drawdowns([(d, 2.0 if i == 0 else 1.0) for i, d in enumerate(ds)])   # 첫날만 고점 2
        self.assertEqual(len(dd), 300 - 251)
        self.assertEqual(dd[0], (ds[251], -50.0))
        self.assertEqual(dd[1], (ds[252], 0.0))

    def test_first_entry_needs_exactly_126_clear_observations(self):
        ds = bdays(TODAY, 140)

        def dd(gap):                                                              # 진입 · gap개 맑은 날 · 다시 진입
            hit = [True] + [False] * gap + [True] + [False] * (138 - gap)
            return [(d, -15.0 if h else -1.0) for d, h in zip(ds, hit)]
        self.assertEqual(cf.first_entries(dd(126), 10), ds[127].isoformat())
        self.assertIsNone(cf.first_entries(dd(125), 10))
        self.assertIsNone(cf.first_entries(dd(126), 20))

    def test_short_index_fails_the_item(self):
        S = dict(world(), NASDAQ100=index_world(n=100))
        with self.assertRaises(cf.ItemError):
            cf.calc_drawdown(S, TODAY)

    def test_text_lists_whole_percent_bands_and_dates_only(self):
        c = cf.calc_drawdown(world(), TODAY)
        line, extra = cf.texts("drawdown", c["values"], c["date"])
        ds = [d for d, _ in index_world()]
        self.assertEqual(line, f"2026-10-28 기준 나스닥100 고점 대비 0% (10% 안) · AI 지수 고점 대비 −14% (10~20% 아래) · "
                               f"최근 6개월 첫 진입: AI 지수 −10% {ds[-30].isoformat()}")
        v = dict(c["values"], ai_e10=None, ndx_asof="2026-10-27")
        self.assertIn("나스닥100 고점 대비 0% (10% 안, 2026-10-27 기준) · ", cf.texts("drawdown", v, c["date"])[0])
        self.assertTrue(cf.texts("drawdown", v, c["date"])[0].endswith("첫 진입: 없음"))
        for t in [line, *extra]:                                                  # 날짜·정해 둔 상수·정수 낙폭 밖의 숫자가 없다
            rest = re.sub(r"\d{4}-\d{2}-\d{2}", "", t)
            self.assertLessEqual(set(re.findall(r"\d+(?:\.\d+)?", rest)),
                                 {"10", "20", "252", "12", "126", "6", "100", "0.5", "0", "14"}, t)

    def test_whole_percent_comes_from_the_two_decimal_drawdown(self):
        # 비공개 원본(credit_block)은 낙폭을 소수 둘째 자리로 저장하고(_r(dd, 2)) 그 값을 줄에 쓴다 — 공개 정수 %는 그 값에서
        # 0.5를 0에서 먼 쪽으로(같은 날 두 쪽이 갈리지 않게). 구간은 반올림 전 값으로
        ds = bdays(TODAY, 300)

        def last(x):                                                              # 고점 100, 마지막 날만 고점 대비 x%
            return [(d, 100.0) for d in ds[:-1]] + [(ds[-1], 100.0 * (1 + x / 100))]
        for x, want, band in ((-12.4996, -13, "10to20"), (-12.49, -12, "10to20"), (-7.4983, -8, "in10"),
                              (-7.4949, -7, "in10"), (-9.9951, -10, "in10"), (-0.4951, -1, "in10"), (-0.4949, 0, "in10")):
            v = cf.calc_drawdown(dict(world(), NASDAQ100=last(x), NASDAQNQINTEL=last(x)), TODAY)["values"]
            self.assertEqual((v["ndx_dd"], v["ndx_band"], v["ai_dd"], v["ai_band"]), (want, band, want, band), x)
            self.assertTrue(cf._consistent("drawdown", v), x)
            self.assertIn(f"나스닥100 고점 대비 {cf._dd(want)} (", cf.texts("drawdown", v, ds[-1].isoformat())[0])


class _MainBase(unittest.TestCase):
    """main()을 임시 폴더에서 돌리는 틀 — 테스트는 아래 두 묶음에."""
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp)
        self.out = os.path.join(self.tmp, "data")
        self.work = os.path.join(self.tmp, ".work")
        self.path = os.path.join(self.out, cf.FILE)
        self.S = world()

    def run_main(self, fred=None, now=NOW, clock=None, web=None, args=()):
        fred = fred or FakeFred(self.S)
        self.web = web if web is not None else FakeWeb()
        buf = io.StringIO()
        kw = {"clock": clock} if clock else {}
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            code = cf.main(["--out", self.out, "--work", self.work, *args], fred_load=fred, now=now, opener=self.web, **kw)
        return code, buf.getvalue()

    def saved(self):
        with open(self.path, encoding="utf-8") as f:
            return json.load(f)


class MainTest(_MainBase):
    def test_first_run_writes_every_item(self):
        code, log = self.run_main()
        self.assertEqual(code, 0, log)
        js = self.saved()
        self.assertEqual(set(js), {"schema", "generated_at", "notice", "definition", "order", "items"})
        self.assertEqual((js["order"], js["definition"]),
                         (["stage", "ebp", "cmdi", "cell", "gap", "drawdown", "sec"], cf.STAGE_DEF))
        for key in cf.BY_KEY:
            it = js["items"][key]
            self.assertTrue(it["ok"], key)
            self.assertEqual(it["retrieved"], "2026-10-30")
            for src in it["sources"]:
                if src["series"] in cf.EXT:                                      # FRED 밖 — 출처 이름·파일 주소·인용
                    e = cf.EXT[src["series"]]
                    self.assertEqual((src["name"], src["url"], src["licence"], src["restricted"]),
                                     (e["name"], e["url"], e["licence"], False))
                    self.assertEqual(src["citation"], f"{e['title']}, retrieved from {e['url']}, October 30, 2026.")
                    continue
                self.assertEqual(src["licence"], cf.LICENCE[src["series"]])
                self.assertEqual(src["restricted"], src["series"] in ("NASDAQ100", "NASDAQNQINTEL"))
                self.assertTrue(src["citation"].startswith(cf.SOURCES[src["series"]][0] + ", "))
                self.assertIn(f"[{src['series']}], retrieved from FRED, Federal Reserve Bank of St. Louis; "
                              f"https://fred.stlouisfed.org/series/{src['series']}, October 30, 2026.", src["citation"])
        st = js["items"]["stage"]
        self.assertEqual((st["values"]["value"], st["date"]), (0, "2026-10-16"))
        self.assertTrue(st["line"].startswith("긴축 0/2 — SLOOS 대·중견 C&I 순긴축 0.0% (2026-07 조사, 1990~ p40)"))
        self.assertIn(cf.HYPO, st["extra"])
        self.assertIn(cf.PATH_NOTE, st["extra"])
        self.assertEqual(st["notices"], [cf.COMPUTED_NOTICE, cf.CITATION_NOTICE])
        self.assertEqual(js["items"]["drawdown"]["notices"], [cf.RESTRICTED_NOTICE, cf.COPYRIGHT_NOTICE])
        self.assertEqual({s["series"]: s["copyright"] for s in js["items"]["drawdown"]["sources"]}, cf.COPYRIGHT)
        self.assertEqual(js["items"]["ebp"]["notices"], [cf.EBP_NOTICE, cf.EBP_CITE, cf.EBP_SOURCE, cf.EBP_PD])
        self.assertEqual(js["items"]["cmdi"]["notices"], [cf.CMDI_DERIVED, cf.CMDI_DERIVED_EN, rp.nyfed_attribution("2026"),
                                                          rp.NOT_AFFILIATED, cf.CMDI_CITE])
        self.assertEqual(js["items"]["cell"]["notices"], [cf.COMPUTED_NOTICE])
        self.assertTrue(js["items"]["cell"]["line"].startswith("확장 × 현금 조달 — "))
        sec = js["items"]["sec"]                                                  # sec.json이 없다
        self.assertEqual((sec["ok"], sec["stale"], sec["error"]), (False, False, "SEC 자료 파일을 읽지 못함"))
        self.assertIn("[credit_fetch] stage 2026-10-16 기준", log)

    def test_easing_side_has_numbers_only(self):
        S = dict(self.S, DRTSCILM=[(d, -12.5) for d, _ in sloos_world()])
        v = stage(S)
        extra = cf.texts("stage", v, "x")[1]
        self.assertEqual(extra[1], cf.HYPO + cf.EASING)
        self.assertNotIn(cf.EASING, cf.texts("stage", stage(self.S), "x")[1][1])
        self.assertIn("순긴축 -12.5% ", cf.texts("stage", v, "x")[0])

    def test_index_values_highs_and_returns_never_appear(self):
        S = dict(self.S, NASDAQ100=index_world(drop=[(10, 0.7)]))                 # 20% 넘게 아래도
        self.run_main(fred=FakeFred(S))
        with open(self.path, encoding="utf-8") as f:
            dump = f.read()
        self.assertIn("over20", dump)
        for sid in ("NASDAQ100", "NASDAQNQINTEL"):
            px = S[sid]
            for d, v in px:                                                       # 지수 값(몇 가지 반올림)
                for t in (f"{v:.0f}", f"{v:.1f}", f"{v:.2f}", f"{v:.4f}", str(int(v))):
                    self.assertNotIn(t, dump, (sid, d, t))
            vals = [v for _, v in px]
            highs = {max(vals[max(0, i - 251):i + 1]) for i in range(len(vals) - 30, len(vals))}   # 12개월 고점
            for h in highs:
                for t in (f"{h:.0f}", f"{h:.1f}", f"{h:.2f}", f"{h:.4f}"):
                    self.assertNotIn(t, dump, (sid, "high", t))
            for k in (1, 5, 10, 11, 21, 63, 126, 252):                            # 수익률(%·비율, 몇 가지 반올림)
                r = vals[-1] / vals[-1 - k] - 1
                for t in (f"{r * 100:.2f}", f"{r * 100:.3f}", f"{r:.4f}", f"{r:.5f}"):
                    if len(re.sub(r"[^1-9]", "", t)) >= 3:                       # 우연히 겹칠 만큼 짧은 꼴은 건너뛴다
                        self.assertNotIn(t, dump, (sid, k, t))
                        self.assertNotIn(t.lstrip("-"), dump, (sid, k, t))
        dd = cf.drawdowns(S["NASDAQNQINTEL"])[-1][1]                              # 지금 낙폭은 정수만 — 소수 꼴은 없다
        for t in (f"{dd:.1f}", f"{-dd:.1f}", f"{dd:.2f}", f"{-dd:.2f}"):
            self.assertNotIn(t, dump, t)
        it = self.saved()["items"]["drawdown"]
        nums = {k: x for k, x in it["values"].items() if isinstance(x, (int, float)) and not isinstance(x, bool)}
        self.assertEqual(nums, {"ndx_dd": cf.dd_pct(cf.drawdowns(S["NASDAQ100"])[-1][1]), "ai_dd": -14})
        self.assertEqual(nums["ndx_dd"], -30)
        self.assertTrue(all(type(x) is int for x in nums.values()))
        allowed = {"10", "20", "252", "12", "126", "6", "100", "0.5", "0", "2016", "2025", "30", "14"}
        for t in [it["line"], *it["extra"], *it["notices"], it["name"]]:        # 글 속 숫자 = 날짜·상수·정수 낙폭·저작권 해뿐
            rest = re.sub(r"\d{4}-\d{2}-\d{2}", "", t)
            self.assertLessEqual(set(re.findall(r"\d+(?:\.\d+)?", rest)), allowed, t)
        self.assertNotIn("Â", dump)                                               # FRED 페이지의 깨진 ©는 고쳐 싣는다

    def test_one_missing_series_only_stales_its_items(self):
        self.run_main()
        code, log = self.run_main(fred=FakeFred(self.S, fail={"NFCICREDIT"}), now=NOW + datetime.timedelta(days=1))
        self.assertEqual(code, 0, log)
        items = self.saved()["items"]
        st = items["stage"]
        self.assertEqual((st["ok"], st["stale"], st["error"], st["failed_since"]), (False, True, "수신 실패", "2026-10-31"))
        self.assertEqual((st["retrieved"], st["values"]["value"]), ("2026-10-30", 0))
        self.assertTrue(all(items[k]["ok"] for k in ("cell", "gap", "drawdown")))
        self.assertIn("::warning::신용 긴축 참고 stage 받지 못함", log)
        self.assertNotIn("xyz-77", log)
        self.run_main(fred=FakeFred(self.S, cache={"BOGZ1FA106000135Q"}), now=NOW + datetime.timedelta(days=2))
        items = self.saved()["items"]
        self.assertEqual({k for k, it in items.items() if not it["ok"]}, {"cell", "gap", "sec"})
        self.assertTrue(items["ebp"]["ok"] and items["cmdi"]["ok"])
        self.assertEqual(items["gap"]["error"], "수신 실패 · 묵은 캐시는 싣지 않음")

    def test_first_failure_without_previous_has_no_numbers(self):
        self.run_main(fred=FakeFred(self.S, fail={"NASDAQNQINTEL"}))
        it = self.saved()["items"]["drawdown"]
        self.assertEqual((it["ok"], it["stale"], it["error"]), (False, False, "수신 실패"))
        self.assertNotIn("line", it)

    def test_older_data_is_not_taken(self):
        self.run_main()
        short = dict(self.S, NFCICREDIT=self.S["NFCICREDIT"][:-1])
        self.run_main(fred=FakeFred(short), now=NOW + datetime.timedelta(days=1))
        it = self.saved()["items"]["stage"]
        self.assertEqual((it["ok"], it["stale"], it["error"]), (False, True, "받은 자료가 직전 자료보다 오래됨"))
        self.assertEqual(it["values"]["n_asof"], "2026-10-16")

    def test_same_numbers_keep_the_file(self):
        self.run_main()
        with open(self.path, "rb") as f:
            first = f.read()
        self.run_main(now=NOW + datetime.timedelta(hours=20))
        with open(self.path, "rb") as f:
            self.assertEqual(f.read(), first)

    def test_a_broken_previous_file_is_not_carried(self):
        self.run_main()
        js = self.saved()
        js["items"]["stage"]["values"]["value"] = 2                               # 범위(0~0)와 어긋남
        js["items"]["drawdown"]["values"]["ai_band"] = -13.87                     # 구간 코드 대신 숫자
        js["items"]["ebp"]["values"]["ebp"] = "많음"                               # 수 대신 글
        js["items"]["cmdi"]["values"]["market"] = 1.7                             # 0~1 밖
        js["items"]["cell"]["values"]["fund"] = "매수"
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(js, f, ensure_ascii=False)
        bad = set(cf.SERIES)
        self.run_main(fred=FakeFred(self.S, fail=bad), now=NOW + datetime.timedelta(days=1), web=FakeWeb({}))
        items = self.saved()["items"]
        for key in ("stage", "drawdown", "cell", "ebp", "cmdi"):
            self.assertEqual((items[key]["ok"], items[key]["stale"]), (False, False), key)
            self.assertNotIn("line", items[key])
        self.assertTrue(items["gap"]["stale"])
        dump = json.dumps(self.saved(), ensure_ascii=False)
        self.assertNotIn("매수", dump)
        self.assertNotIn("13.87", dump)

    def test_budget_runs_out_without_waiting(self):
        t = [0.0]

        def clock():
            t[0] += 30.0
            return t[0]
        fred = FakeFred(self.S)
        code, log = self.run_main(fred=fred, clock=clock)
        self.assertLess(len(fred.calls), len(cf.SERIES))
        self.assertTrue(all(1 <= tmo <= cf.REQ_TIMEOUT for _, tmo in fred.calls))
        self.assertEqual(self.web.calls, [])                                      # 예산이 다 떨어져 FRED 밖은 부르지 않았다
        self.assertIn("::warning::", log)

    def test_nothing_fetched_exits_1(self):
        code, log = self.run_main(fred=FakeFred(self.S, fail=set(self.S)), web=FakeWeb({}))
        self.assertEqual(code, 1, log)
        self.assertTrue(all(not it["ok"] for it in self.saved()["items"].values()))

    def test_every_string_is_fixed_text_without_verdict_words(self):
        self.run_main(fred=FakeFred(self.S, fail={"GDP"}))
        self.run_main(now=NOW + datetime.timedelta(days=1), web=FakeWeb({cf.EBP_URL: ebp_csv()}))
        self.run_main(fred=FakeFred(self.S, fail={"DRTSCILM", "NASDAQ100"}), now=NOW + datetime.timedelta(days=2))
        dump = json.dumps(self.saved(), ensure_ascii=False)
        for word in list(FORBIDDEN_TEXT) + list(VERDICT):
            self.assertNotIn(word, dump, word)
        for word in list(FORBIDDEN_TEXT) + list(VERDICT):
            for spec in cf.ITEMS:
                self.assertNotIn(word, spec["title"])
            for t in (cf.NOTICE, cf.STAGE_DEF, cf.HYPO, cf.EASING, cf.PATH_NOTE, cf.RESTRICTED_NOTICE, cf.CITATION_NOTICE,
                      cf.COPYRIGHT_NOTICE, cf.EBP_NOTICE, cf.EBP_CITE, cf.EBP_SOURCE, cf.EBP_PD, cf.CMDI_DERIVED,
                      cf.CMDI_DERIVED_EN, cf.CMDI_CITE, *cf.CMDI_LABEL.values(),
                      *cf.BAND_NAME.values(), *cf.REASONS.values()):
                self.assertNotIn(word, t)
        urls = {u.rstrip(".") for u in re.findall(r"https?://[^\s,;)\"]+", dump)}
        self.assertEqual(urls, {f"https://fred.stlouisfed.org/series/{sid}" for sid in cf.SERIES} |
                         {sf.DOC_URL, cf.EBP_URL, cf.CMDI_URL})
        self.assertNotIn("bad.invalid", dump)
        self.assertLessEqual({it["error"] for it in self.saved()["items"].values()} - {None},
                             set(cf.REASONS.values()) | set(sf.REASONS.values()))
        nested = re.compile(r"\([^()]*\(")
        for t in re.findall(r'"((?:[^"\\]|\\.)*)"', dump):
            self.assertIsNone(nested.search(t), t)


def first_diff(a, b):
    """두 읽은 결과({열: [(날짜, 값)]})의 첫 차이 한 줄 — 긴 목록을 difflib로 견주면 실패할 때 몇 분씩 걸린다."""
    if set(a) != set(b):
        return f"열 {sorted(a)} != {sorted(b)}"
    for k in a:
        if len(a[k]) != len(b[k]):
            return f"{k}: 길이 {len(a[k])} != {len(b[k])}"
        for i, (x, y) in enumerate(zip(a[k], b[k])):
            if x != y:
                return f"{k}[{i}]: {x} != {y}"
    return None


class _Same:
    def same(self, a, b, msg=None):
        d = first_diff(a, b)
        if d:
            self.fail(f"{d} ({msg})" if msg is not None else d)


class EbpTest(_Same, unittest.TestCase):
    def test_parse_reads_pp_by_month_and_skips_blanks(self):
        rows = ebp_rows()
        rows[100][1] = None                                                       # 빈 EBP 칸 — 그 달 EBP만 건너뛴다
        rows[101][2] = None                                                       # 빈 GZ 칸
        got = cf.parse_ebp(ebp_csv(rows))
        self.assertEqual(len(got["ebp"]), len(rows) - 1)
        self.assertEqual(len(got["gz"]), len(rows) - 1)
        self.assertNotIn(rows[100][0], dict(got["ebp"]))
        self.assertIn(rows[100][0], dict(got["gz"]))
        self.assertEqual(got["ebp"][-1], (EBP_LAST, 0.1234))
        self.assertEqual(got["ebp"][0][0], D(1973, 1, 1))
        self.assertEqual(set(got), {"ebp", "gz"})                                 # 침체 확률 열은 읽지 않는다

    def test_parse_header_case_bom_and_three_date_forms(self):
        want = cf.parse_ebp(ebp_csv())
        forms = [lambda d: d.isoformat(), lambda d: f"{d.month}/{d.day}/{d.year}", lambda d: f"{d.year}-{d.month:02d}",
                 lambda d: f"{d.year}-{d.month:02d}-15"]                          # 달 중간 날짜도 그 달 첫날로
        for fmt in forms:
            for header in ("date,gz_spread,ebp,est_prob", " Date , GZ_Spread , EBP , Est_Prob "):
                self.same(cf.parse_ebp(ebp_csv(header=header, fmt=fmt, bom=True)), want, header)
        moved = ebp_csv(header="est_prob,ebp,date,gz_spread")                    # 열 차례가 달라도 이름으로
        lines = moved.decode().splitlines()
        swapped = [lines[0]] + [",".join([c[3], c[2], c[0], c[1]]) for c in (x.split(",") for x in lines[1:])]
        self.same(cf.parse_ebp("\n".join(swapped).encode()), want)
        self.same(cf.parse_ebp(b"note line\n" + ebp_csv()), want)            # 머리글 앞 한 줄

    def test_parse_refuses_a_file_it_does_not_recognise(self):
        for bad in (b"", b"date,gz_spread,est_prob\n2026-09-01,1.5,0.2\n", b"<html>moved</html>",
                    ebp_csv(rows=[[D(2026, 9, 1), None, 1.5, 0.1]]),             # 쓸 EBP 행이 없다
                    ebp_csv(rows=[[m, e * 300, g, p] for m, e, g, p in ebp_rows()]),     # EBP만 bp 꼴(20pp 넘음)
                    ebp_csv(rows=[[m, e, g * 100, p] for m, e, g, p in ebp_rows()])):    # GZ만 bp 꼴(50pp 넘음)
            with self.assertRaises(cf.LayoutError):
                cf.parse_ebp(bad)

    def test_calc_bp_percentile_and_exact_three_months(self):
        data = cf.parse_ebp(ebp_csv())
        v = cf.calc_ebp({cf.EBP: data}, TODAY)
        allv = [e for _, e in data["ebp"]]
        self.assertEqual(v["date"], "2026-09-01")
        self.assertEqual(v["values"], {"ebp": 12.3, "month": "2026-09-01", "since": "1973-01-01",
                                       "pct": round(sum(x <= 0.1234 for x in allv) / len(allv) * 100, 1),
                                       "ch3": 6.7, "gz": 187.7})
        line, extra = cf.texts("ebp", v["values"], v["date"])
        self.assertEqual(line, f"EBP +12bp (2026-09, 1973~ p{v['values']['pct']:.0f}) · 3개월 +7bp · GZ 스프레드 188bp")
        no_back = {"ebp": [x for x in data["ebp"] if x[0] != D(2026, 6, 1)], "gz": data["gz"][:-1]}
        w = cf.calc_ebp({cf.EBP: no_back}, TODAY)["values"]                      # 정확히 3개월 전 달이 없으면 변화 없음
        self.assertEqual((w["ch3"], w["gz"]), (None, None))
        self.assertEqual(cf.texts("ebp", w, "x")[0], f"EBP +12bp (2026-09, 1973~ p{w['pct']:.0f})")
        neg = cf.calc_ebp({cf.EBP: {"ebp": [(D(2026, 6, 1), -0.004), (D(2026, 9, 1), 0.002)], "gz": []}}, TODAY)["values"]
        self.assertEqual(cf.texts("ebp", neg, "x")[0], "EBP 0bp (2026-09, 2026~ p100) · 3개월 +1bp")   # −0이 아니라 0
        with self.assertRaises(cf.ItemError):
            cf.calc_ebp({cf.EBP: {"ebp": [], "gz": []}}, TODAY)

    def test_months_after_today_are_not_used(self):
        data = cf.parse_ebp(ebp_csv(ebp_rows(end=D(2026, 12, 1))))
        S = {cf.EBP: cf._upto(data, D(2026, 10, 30))}
        self.assertEqual(cf.calc_ebp(S, TODAY)["values"]["month"], "2026-10-01")

    def test_parse_any_line_end(self):
        want = cf.parse_ebp(ebp_csv())
        for nl in (b"\r", b"\r\n"):                                              # CR만 쓰는 파일도
            self.same(cf.parse_ebp(ebp_csv().replace(b"\n", nl)), want, nl)

    def test_unreadable_csv_is_a_layout_failure(self):
        big = b"date,gz_spread,ebp,est_prob\n2026-09-01,1.5," + b"9" * (131072 + 1) + b",0.1\n" + ebp_csv()
        unclosed = b'date,gz_spread,ebp\n"' + b"\xff\x00x" * 50000                 # 닫히지 않은 따옴표 → 칸 상한
        for i, bad in enumerate((big, unclosed, cmdi_xlsx(), bytes(range(256)) * 40)):   # 통합 문서·이진 찌꺼기도
            with self.assertRaises(cf.LayoutError, msg=i):
                cf.parse_ebp(bad)
        for bad in (big, unclosed):
            with self.assertRaises(cf.LayoutError) as cm:
                cf.parse_ebp(bad)
            self.assertEqual(str(cm.exception), "csv")
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp)
        for bad in (big, unclosed, cmdi_xlsx()):                                  # 수신 실패가 아니라 꼴 실패로
            with contextlib.redirect_stdout(io.StringIO()):
                data, errors = cf.load_all(tmp, fred_load=FakeFred(world()),
                                           opener=FakeWeb({cf.EBP_URL: bad, cf.CMDI_URL: cmdi_xlsx()}))
            self.assertEqual(errors, {cf.EBP: "layout"})
            self.assertIn(cf.CMDI, data)
        self.assertEqual(cf.REASONS["layout"], "받은 파일의 꼴을 알아보지 못함")


class CmdiTest(_Same, unittest.TestCase):
    def test_reads_index_data_with_whitelisted_columns(self):
        log = []
        got = cf.parse_cmdi(cmdi_xlsx(), log=log.append)
        self.assertEqual(set(got), {"market", "ig", "hy"})                       # 'Financial CMDI'는 버린다
        self.assertEqual(got["market"][-1], (CMDI_END, 0.3456))
        self.assertEqual(got["market"][0][0], D(2005, 1, 7))
        self.assertEqual(log[0], "CMDI 시트: Notes | Index Data")
        self.assertEqual(log[1], "CMDI 머리글(Index Data): eow_friday | Market CMDI | IG CMDI | HY CMDI | Financial CMDI")
        for t in log:                                                             # 로그에 값은 없다
            self.assertNotRegex(t, r"\d\.\d")

    def test_column_names_map_to_three_fixed_labels_only(self):
        keys = {"Market CMDI": "market", "market_cmdi": "market", "Corporate Bond Market Distress Index": "market",
                "IG": "ig", "IG CMDI": "ig", "Investment Grade CMDI": "ig", "investment-grade": "ig", "High Grade": "ig",
                "HY": "hy", "HY CMDI": "hy", "High Yield CMDI": "hy", "Speculative Grade": "hy",
                "CMDI": None, "Financial CMDI": None, "Non-Financial CMDI": None, "IG 4wk change": None, "High": None,
                "IG minus HY": None, "IG HY": None, "High Market CMDI": None, "eow_friday": None, "Utilities HY": None, "": None, None: None,
                3.0: None, "<b>IG</b>": None}
        for h, want in keys.items():
            self.assertEqual(cf.cmdi_key(h), want, h)

    def test_the_first_column_of_a_label_wins(self):
        tab = cmdi_table(header=("eow_friday", "Market CMDI", "market_cmdi", "IG CMDI", "Investment Grade"))
        for r in tab[1:]:
            r[2], r[4] = 0.9, 0.8
        got = cf.parse_cmdi(make_xlsx([("Index Data", tab)]))
        self.assertEqual((got["market"][-1][1], got["ig"][-1][1]), (0.3456, 0.4012))   # 뒤의 0.9·0.8이 아니라

    def test_falls_back_to_the_first_sheet_with_the_date_header(self):
        tab = cmdi_table()
        for sheets in ([("Sheet1", [["x"]]), ("Weekly", tab)],                  # 'Index Data' 시트가 없다
                       [("Index Data", [["no header here"]]), ("Readme", [["y"]]), ("Data2", tab)],   # 있는데 머리글이 없다
                       [("Weekly", tab), ("index data", tab[:3])]):              # 'Index Data' 꼴이 먼저
            log = []
            got = cf.parse_cmdi(make_xlsx(sheets), log=log.append)
            want_rows = 2 if sheets[-1][0] == "index data" else len(tab) - 1
            self.assertEqual(len(got["market"]), want_rows, [n for n, _ in sheets])

    def test_shared_strings_with_runs_inline_strict_absolute_and_text_dates(self):
        want = cf.parse_cmdi(cmdi_xlsx())
        tab = cmdi_table()
        variants = [make_xlsx([("Index Data", tab)], rich=("Market CMDI", "eow_friday")),
                    make_xlsx([("Index Data", tab)], inline=True),
                    make_xlsx([("Index Data", tab)], ns=STRICT_NS),
                    make_xlsx([("Index Data", tab)], abs_target=True),
                    make_xlsx([("Index Data", tab)], no_refs=True),
                    make_xlsx([("Index Data", tab)], fstr=("Market CMDI", "eow_friday")),
                    make_xlsx([("Index Data", [tab[0]] + [[(D(1899, 12, 30) + datetime.timedelta(days=int(r[0]))).isoformat()]
                                                          + r[1:] for r in tab[1:]])])]
        for i, x in enumerate(variants):
            self.same(cf.parse_cmdi(x), want, i)
        mdy = [tab[0]] + [[f"{d.month}/{d.day}/{d.year}"] + r[1:]
                          for r in tab[1:] for d in [D(1899, 12, 30) + datetime.timedelta(days=int(r[0]))]]
        self.same(cf.parse_cmdi(make_xlsx([("Index Data", mdy)])), want)

    def test_header_cells_in_the_log_are_cleaned(self):
        tab = cmdi_table(header=("eow_friday", "Market CMDI", "x\n::error::y" + "z" * 80, "a\x7fb\u200bc\u2028d"))
        tab = [r[:4] for r in tab]
        log = []
        cf.parse_cmdi(make_xlsx([("Index\tData", tab)]), log=log.append)
        self.assertTrue(all("\n" not in t and "\t" not in t for t in log))
        self.assertIn(("x ::error::y" + "z" * 80)[:40] + "…", log[1])
        self.assertTrue(log[1].startswith("CMDI 머리글(Index Data): "))
        self.assertTrue(log[1].endswith(" | a b c d"), log[1])                      # 제어·서식·줄 구분 문자는 공백으로
        self.assertTrue(all(ch.isprintable() for t in log for ch in t))

    def test_refuses_what_it_cannot_read(self):
        tab = cmdi_table()
        dtd = make_xlsx([("Index Data", tab)])
        with zipfile.ZipFile(io.BytesIO(dtd)) as z:
            parts = {n: z.read(n) for n in z.namelist()}
        parts["xl/workbook.xml"] = b'<?xml version="1.0"?><!DOCTYPE x [<!ENTITY a "aaaa">]>' + parts["xl/workbook.xml"]
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as z:
            for k, v in parts.items():
                z.writestr(k, v)
        bad = [b"", b"not a zip", buf.getvalue(),                                 # DTD·엔티티가 든 XML은 읽지 않는다
               make_xlsx([("Index Data", [["date", "Market CMDI"], [serial(CMDI_END), 0.3]])]),   # eow_friday 없음
               make_xlsx([("Index Data", [r[:1] + r[2:] for r in tab])]),       # 시장 전체 열 없음
               make_xlsx([("Index Data", [tab[0]] + [r[:1] + [r[1] * 100] + r[2:] for r in tab[1:]])])]   # 0~1 밖
        for i, x in enumerate(bad):
            with self.assertRaises(cf.LayoutError, msg=i):
                cf.parse_cmdi(x)
        log = []
        with self.assertRaises(cf.LayoutError):
            cf.parse_cmdi(bad[3], log=log.append)
        self.assertEqual(log, ["CMDI 시트: Index Data", "CMDI 머리글(eow_friday) 없음"])
        odd = [tab[0]] + [r[:2] + [r[2] * 100] + r[3:] for r in tab[1:]]          # 투자등급만 0~1 밖이면 그 열만 버린다
        self.assertEqual(set(cf.parse_cmdi(make_xlsx([("Index Data", odd)]))), {"market", "hy"})

    def test_calc_values_percentile_and_exact_four_weeks(self):
        cols = cf.parse_cmdi(cmdi_xlsx())
        v = cf.calc_cmdi({cf.CMDI: cols}, TODAY)
        self.assertEqual(v["date"], "2026-09-25")
        vals = v["values"]
        m = [x for _, x in cols["market"]]
        self.assertEqual((vals["market"], vals["market_date"], vals["market_since"], vals["market_ch4"]),
                         (0.3456, "2026-09-25", "2005-01-07", 0.1345))
        self.assertEqual(vals["market_pct"], round(sum(x <= 0.3456 for x in m) / len(m) * 100, 1))
        self.assertEqual((vals["ig_ch4"], vals["hy_ch4"]), (-0.021, 0.0))
        line, extra = cf.texts("cmdi", vals, v["date"])
        self.assertEqual(line, f"시장 전체 0.35 (2005~ p{vals['market_pct']:.0f}, 4주 +0.13) · "
                               f"투자등급 0.28 (2005~ p{vals['ig_pct']:.0f}, 4주 -0.02) · "
                               f"하이일드 0.40 (2005~ p{vals['hy_pct']:.0f}, 4주 0.00)")
        self.assertTrue(cf._consistent("cmdi", vals))
        gap = {k: [x for x in s if x[0] != CMDI_END - datetime.timedelta(days=28)] for k, s in cols.items()}
        w = cf.calc_cmdi({cf.CMDI: gap}, TODAY)["values"]                        # 28일 전 관측이 없으면 4주 변화 없음
        self.assertEqual((w["market_ch4"], w["ig_ch4"]), (None, None))
        self.assertNotIn("4주", cf.texts("cmdi", w, "2026-09-25")[0])
        only = {"market": cols["market"][:-1], "hy": cols["hy"]}                  # 열마다 날짜가 다르면 그 열에 날짜를
        w = cf.calc_cmdi({cf.CMDI: only}, TODAY)
        self.assertEqual((w["values"]["ig"], w["values"]["ig_date"], w["values"]["ig_pct"]), (None, None, None))
        line = cf.texts("cmdi", w["values"], w["date"])[0]
        self.assertTrue(line.startswith("시장 전체 0."), line)
        self.assertIn("하이일드 0.40 (2026-09-25 기준, 2005~ ", line)
        self.assertNotIn("투자등급", line)
        self.assertTrue(cf._consistent("cmdi", w["values"]))
        self.assertFalse(cf._consistent("cmdi", dict(w["values"], ig_date="2026-09-25")))
        with self.assertRaises(cf.ItemError):
            cf.calc_cmdi({cf.CMDI: {"hy": cols["hy"]}}, TODAY)

    def test_a_readme_sheet_naming_eow_friday_does_not_hide_the_data_sheet(self):
        tab = cmdi_table()
        readme = [["Variable", "Description"], ["eow_friday", "End-of-week Friday"], ["Market CMDI", "Market-wide index"]]
        for sheets in ([("ReadMe", readme), ("Data", tab)], [("Index Data", readme), ("Data", tab)]):
            log = []
            got = cf.parse_cmdi(make_xlsx(sheets), log=log.append)
            self.assertEqual(got["market"][-1], (CMDI_END, 0.3456), sheets[0][0])
            self.assertEqual(log[1], "CMDI 머리글(Data): eow_friday | Market CMDI | IG CMDI | HY CMDI | Financial CMDI")
        log = []                                                                  # 시장 전체 열이 있는 시트가 없으면
        with self.assertRaises(cf.LayoutError):                                   # 첫 후보의 머리글을 찍고 실패
            cf.parse_cmdi(make_xlsx([("ReadMe", readme), ("Notes", [["x"]])]), log=log.append)
        self.assertEqual(log, ["CMDI 시트: ReadMe | Notes", "CMDI 머리글(ReadMe): eow_friday | End-of-week Friday"])

    def test_date_header_case_spaces_and_separators(self):
        want = cf.parse_cmdi(cmdi_xlsx())
        for h in ("EOW_Friday", " eow_friday ", "EOW FRIDAY", "eow-friday", "eow__friday"):
            tab = cmdi_table()
            tab[0][0] = h
            self.same(cf.parse_cmdi(make_xlsx([("Index Data", tab)])), want, h)
        for h in ("eowfriday", "eow_fridays", "friday", "eow friday date"):
            tab = cmdi_table()
            tab[0][0] = h
            with self.assertRaises(cf.LayoutError, msg=h):
                cf.parse_cmdi(make_xlsx([("Index Data", tab)]))

    def test_fractional_serial_dates_take_the_day_part(self):
        self.assertEqual(cf._xl_date(serial(CMDI_END) + 0.75), CMDI_END)         # 시각(소수 부분)은 버린다 — 반올림 아님
        tab = cmdi_table()
        frac = [tab[0]] + [[r[0] + 0.75] + r[1:] for r in tab[1:]]
        self.same(cf.parse_cmdi(make_xlsx([("Index Data", frac)])), cf.parse_cmdi(cmdi_xlsx()))

    def test_serial_range_guard(self):
        self.assertEqual([cf._xl_date(v) for v in (1.0, 0.999, 0.0, -3.0, 2958465.5, 2958466.0, 3e6, 1e300)],
                         [D(1899, 12, 31), None, None, None, D(9999, 12, 31), None, None, None])
        tab = cmdi_table()
        for i, bad in ((1, 0.5), (2, -2.0), (3, 2958466.0), (4, 3e6)):            # 앞 네 주의 날짜만 범위 밖 — 그 행만 건너뛴다
            tab[i][0] = bad
        got = cf.parse_cmdi(make_xlsx([("Index Data", tab)]))
        self.assertEqual(len(got["market"]), len(tab) - 1 - 4)
        self.assertEqual(got["market"][0][0], CMDI_END - datetime.timedelta(days=7 * (len(tab) - 2 - 4)))
        none = [tab[0]] + [[3e6] + r[1:] for r in tab[1:]]                       # 모두 범위 밖 → 꼴 실패(수신 실패 아님)
        self.assert_layout(make_xlsx([("Index Data", none)]))

    def test_shared_string_index_past_the_table(self):
        tab = cmdi_table()
        n = len(tab)
        blob = make_xlsx([("Index Data", tab)])
        last = patch_part(blob, "xl/worksheets/sheet1.xml",                     # 마지막 주 시장 전체 칸 → 없는 공유 문자열
                          lambda x: x.replace(f'<c r="B{n}"><v>0.3456</v></c>', f'<c r="B{n}" t="s"><v>999</v></c>'))
        self.assertNotEqual(last, blob)
        got = cf.parse_cmdi(last)
        self.assertEqual(got["market"][-1][0], CMDI_END - datetime.timedelta(days=7))   # 그 칸만 건너뛴다
        self.assertEqual(got["ig"][-1], (CMDI_END, 0.2789))
        head = patch_part(blob, "xl/worksheets/sheet1.xml",                     # 'Market CMDI' 머리글 → 없는 공유 문자열
                          lambda x: x.replace('<c r="B1" t="s"><v>1</v></c>', '<c r="B1" t="s"><v>999</v></c>'))
        self.assertNotEqual(head, blob)
        self.assert_layout(head)

    def test_odd_shared_string_indexes_skip_the_cell_or_fail_as_layout(self):
        tab = cmdi_table()
        n = len(tab)
        blob = make_xlsx([("Index Data", tab)])
        for bad in ("\u00b2", "9" * 5000, "-1", "1.0", " 7x"):                       # 위첨자 숫자·int 한도 넘는 자리수 등
            cell = patch_part(blob, "xl/worksheets/sheet1.xml",
                              lambda x: x.replace(f'<c r="B{n}"><v>0.3456</v></c>', f'<c r="B{n}" t="s"><v>{bad}</v></c>'))
            self.assertNotEqual(cell, blob)
            got = cf.parse_cmdi(cell)
            self.assertEqual(got["market"][-1][0], CMDI_END - datetime.timedelta(days=7), repr(bad[:5]))
            head = patch_part(blob, "xl/worksheets/sheet1.xml",
                              lambda x: x.replace('<c r="B1" t="s"><v>1</v></c>', f'<c r="B1" t="s"><v>{bad}</v></c>'))
            self.assertNotEqual(head, blob)
            self.assert_layout(head)

    def test_broken_zip_members_are_layout_not_fetch(self):
        blob = make_xlsx([("Index Data", cmdi_table())])
        name = "xl/worksheets/sheet1.xml"
        def member_offset(b):
            z = zipfile.ZipFile(io.BytesIO(b))
            info = z.getinfo(name)
            hdr = info.header_offset
            fn, ex = int.from_bytes(b[hdr + 26:hdr + 28], "little"), int.from_bytes(b[hdr + 28:hdr + 30], "little")
            return info, hdr, hdr + 30 + fn + ex
        info, hdr, data_at = member_offset(blob)
        corrupt = bytearray(blob)                                              # 압축된 몸통 한가운데를 망가뜨린다
        mid = data_at + info.compress_size // 2
        for i in range(mid, mid + 8):
            corrupt[i] ^= 0xFF
        self.assert_layout(bytes(corrupt))
        buf = io.BytesIO()                                                     # 저장(무압축) 꼴로 다시 짓고 CRC만 틀리게
        with zipfile.ZipFile(io.BytesIO(blob)) as zin, zipfile.ZipFile(buf, "w", zipfile.ZIP_STORED) as zout:
            for it in zin.infolist():
                zout.writestr(it.filename, zin.read(it.filename))
        stored = bytearray(buf.getvalue())
        info, hdr, data_at = member_offset(bytes(stored))
        stored[data_at + 10] ^= 0x01
        self.assert_layout(bytes(stored))
        method = bytearray(blob)                                               # 지원하지 않는 압축 방식 번호(99)
        info, hdr, _ = member_offset(blob)
        method[hdr + 8:hdr + 10] = (99).to_bytes(2, "little")
        cd = bytes(method).rfind(b"PK\x01\x02" + bytes(method[hdr + 4:hdr + 6]), 0)
        z = zipfile.ZipFile(io.BytesIO(blob))
        for it in z.infolist():                                                # 중앙 디렉터리 쪽 방식 번호도 바꾼다
            if it.filename == name:
                pos = bytes(method).find(b"PK\x01\x02")
                while pos != -1:
                    fnl = int.from_bytes(method[pos + 28:pos + 30], "little")
                    if bytes(method[pos + 46:pos + 46 + fnl]).decode() == name:
                        method[pos + 10:pos + 12] = (99).to_bytes(2, "little")
                        break
                    pos = bytes(method).find(b"PK\x01\x02", pos + 4)
        self.assert_layout(bytes(method))

    def assert_layout(self, blob):
        """parse_cmdi는 LayoutError, load_all은 그 자료만 'layout'(뜻밖의 예외로 'fetch'가 되지 않는다)."""
        with self.assertRaises(cf.LayoutError):
            cf.parse_cmdi(blob)
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp)
        with contextlib.redirect_stdout(io.StringIO()):
            data, errors = cf.load_all(tmp, fred_load=FakeFred(world()), opener=FakeWeb({cf.EBP_URL: ebp_csv(),
                                                                                          cf.CMDI_URL: blob}))
        self.assertEqual(errors, {cf.CMDI: "layout"})
        self.assertIn(cf.EBP, data)


class ExtFetchTest(unittest.TestCase):
    """연준 이사회·뉴욕 연은 요청 — 이 프로젝트를 밝히는 User-Agent(이메일 없음), FRED에는 달지 않음, 넘겨짐·크기·시간 상한."""
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp)

    def fred_csv(self):
        return "\n".join(["observation_date,X"] + [f"{d.isoformat()},{v}" for d, v in sloos_world()]).encode()

    def test_user_agent_only_on_the_fed_hosts_and_timeouts(self):
        answers = {ff.FRED_CSV.format(sid=sid): self.fred_csv() for sid in cf.SERIES}
        answers.update({cf.EBP_URL: ebp_csv(), cf.CMDI_URL: cmdi_xlsx()})
        web = FakeWeb(answers)
        with contextlib.redirect_stdout(io.StringIO()):
            data, errors = cf.load_all(self.tmp, opener=web)
        self.assertEqual(errors, {})
        self.assertEqual([u for u, _, _ in web.calls], [ff.FRED_CSV.format(sid=sid) for sid in cf.SERIES] +
                         [cf.EBP_URL, cf.CMDI_URL])
        for url, ua, tmo in web.calls:
            self.assertLessEqual(tmo, cf.REQ_TIMEOUT)
            if "stlouisfed" in url:
                self.assertIsNone(ua)                                             # FRED는 기본 머리글 그대로
            else:
                self.assertEqual(ua, cf.UA)
                self.assertNotIn("@", ua)
        self.assertEqual(data[cf.EBP]["ebp"][-1], (EBP_LAST, 0.1234))
        for name in ("ebp_csv.csv", "Market_CMDI.xlsx"):                         # 캐시는 작업 폴더에(사이트 폴더 밖)
            self.assertTrue(os.path.exists(os.path.join(self.tmp, cf.CACHE, name)))

    def test_redirects_size_and_layout_fail_only_that_source(self):
        cases = [((cf.EBP_URL.replace("www.federalreserve.gov", "evil.invalid"), ebp_csv()), "fetch"),
                 ((cf.EBP_URL.replace("https://", "http://"), ebp_csv()), "fetch"),
                 (b"x" * (cf.MAX_BYTES + 1), "fetch"),
                 (OSError("proxy 403 원문 https://bad.invalid"), "fetch"),
                 (b"<html>moved</html>", "layout")]
        for answer, code in cases:
            web = FakeWeb({cf.EBP_URL: answer, cf.CMDI_URL: cmdi_xlsx()})
            with contextlib.redirect_stdout(io.StringIO()):
                data, errors = cf.load_all(self.tmp, fred_load=FakeFred(world()), opener=web)
            self.assertEqual(errors, {cf.EBP: code})
            self.assertIn(cf.CMDI, data)
        with self.assertRaises(ValueError):                                       # 정해 둔 호스트 밖 주소는 부르지도 않는다
            cf.fetch_bytes("https://evil.invalid/x.csv", cf.EBP_HOST, 1e9, opener=FakeWeb({}))
        web = FakeWeb()                                                           # 마감이 멀어도 요청 하나엔 10초까지
        self.assertEqual(cf.fetch_bytes(cf.EBP_URL, cf.EBP_HOST, 1e9, clock=lambda: 0.0, opener=web), ebp_csv())
        self.assertEqual(web.calls, [(cf.EBP_URL, cf.UA, cf.REQ_TIMEOUT)])

    def test_size_cap_is_five_megabytes_and_exact(self):
        self.assertEqual(cf.MAX_BYTES, 5_000_000)
        body = ebp_csv()
        pad = body + b"\n" * (cf.MAX_BYTES - len(body))                           # 빈 줄로 채운, 읽을 수 있는 파일
        self.assertEqual(len(pad), cf.MAX_BYTES)
        self.assertEqual(cf.fetch_bytes(cf.EBP_URL, cf.EBP_HOST, 1e9, clock=lambda: 0.0, opener=FakeWeb({cf.EBP_URL: pad})),
                         pad)                                                     # 상한과 같으면 받는다
        with self.assertRaisesRegex(ValueError, "^too large$"):
            cf.fetch_bytes(cf.EBP_URL, cf.EBP_HOST, 1e9, clock=lambda: 0.0, opener=FakeWeb({cf.EBP_URL: pad + b"\n"}))
        with contextlib.redirect_stdout(io.StringIO()):                           # 1바이트 넘으면 읽지 않고 수신 실패
            data, errors = cf.load_all(self.tmp, fred_load=FakeFred(world()),
                                       opener=FakeWeb({cf.EBP_URL: pad + b"\n", cf.CMDI_URL: cmdi_xlsx()}))
        self.assertEqual(errors, {cf.EBP: "fetch"})
        self.assertNotIn(cf.EBP, data)
        self.assertEqual(cf.REASONS["fetch"], "수신 실패")
        self.assertFalse(os.path.exists(os.path.join(self.tmp, cf.CACHE, "ebp_csv.csv")))   # 캐시에도 쓰지 않는다

    def test_each_request_gets_at_most_ten_seconds_of_the_budget(self):
        t = [0.0]

        def clock():
            return t[0]

        class Slow(FakeWeb):                                                      # 응답마다 시계를 9초 돌린다
            def __call__(self, req, timeout=None):
                t[0] += 9.0
                return super().__call__(req, timeout)
        web = Slow()
        fred = FakeFred(world())
        with contextlib.redirect_stdout(io.StringIO()):
            data, errors = cf.load_all(self.tmp, fred_load=lambda *a, **k: (t.__setitem__(0, t[0] + 6.0), fred(*a, **k))[1],
                                       clock=clock, opener=web)
        self.assertEqual([tmo for _, tmo in fred.calls], [10] * 8)              # 6초씩 8번 = 48초
        self.assertEqual([(u, tmo) for u, _, tmo in web.calls], [(cf.EBP_URL, 10), (cf.CMDI_URL, 3.0)])   # 12초 중 10 · 남은 3
        self.assertEqual(errors, {cf.CMDI: "fetch"})                              # 받는 중에 전체 마감을 넘었다
        self.assertIn(cf.EBP, data)

    def test_offline_reads_the_cache_and_does_not_call_out(self):
        web = FakeWeb()
        with contextlib.redirect_stdout(io.StringIO()):
            cf.load_all(self.tmp, fred_load=FakeFred(world()), opener=web)
            web2 = FakeWeb({})
            data, errors = cf.load_all(self.tmp, offline=True, fred_load=FakeFred(world()), opener=web2)
        self.assertEqual(web2.calls, [])
        self.assertEqual(errors, {})
        self.assertEqual(data[cf.CMDI]["market"][-1], (CMDI_END, 0.3456))


class ExtMainTest(_MainBase):
    """EBP·CMDI 칸 — 칸마다 실패·직전 값, 사유, 로그, 침체 확률 비노출, 화면 차례."""
    def test_lines_and_layout_log(self):
        code, log = self.run_main()
        self.assertEqual(code, 0, log)
        items = self.saved()["items"]
        self.assertTrue(items["ebp"]["line"].startswith("EBP +12bp (2026-09, 1973~ p"))
        self.assertTrue(items["cmdi"]["line"].startswith("시장 전체 0.35 (2005~ p"))
        self.assertEqual(items["cmdi"]["date"], "2026-09-25")
        self.assertIn("[credit_fetch] CMDI 시트: Notes | Index Data", log)
        self.assertIn("[credit_fetch] CMDI 머리글(Index Data): eow_friday | Market CMDI | IG CMDI | HY CMDI | Financial CMDI",
                      log)
        self.assertIn("[credit_fetch] ebp 2026-09-01 기준", log)
        for v in (0.3456, 0.2789, 0.4012, 0.1234, 1.8765):                         # 로그에 값은 찍지 않는다
            for t in (f"{v:.2f}", f"{v:.4f}", f"{v * 100:.1f}"):
                self.assertNotIn(t, log, t)

    def test_recession_probability_never_appears(self):
        self.run_main()
        with open(self.path, encoding="utf-8") as f:
            dump = f.read()
        for t in (f"{EST_PROB}", f"{EST_PROB:.2f}", f"{EST_PROB:.3f}", f"{EST_PROB * 100:.1f}", "est_prob"):
            self.assertNotIn(t, dump, t)

    def test_failure_keeps_the_previous_numbers_stale(self):
        self.run_main()
        code, log = self.run_main(now=NOW + datetime.timedelta(days=1),
                                  web=FakeWeb({cf.EBP_URL: OSError("x"), cf.CMDI_URL: b"<html/>"}))
        self.assertEqual(code, 0, log)
        items = self.saved()["items"]
        for key, why in (("ebp", "수신 실패"), ("cmdi", "받은 파일의 꼴을 알아보지 못함")):
            it = items[key]
            self.assertEqual((it["ok"], it["stale"], it["error"], it["failed_since"]), (False, True, why, "2026-10-31"))
            self.assertEqual(it["retrieved"], "2026-10-30")
            self.assertTrue(it["line"])
        self.assertIn("::warning::신용 긴축 참고 cmdi 받지 못함: 받은 파일의 꼴을 알아보지 못함", log)
        self.assertTrue(all(items[k]["ok"] for k in ("stage", "cell", "gap", "drawdown")))

    def test_first_layout_failure_has_no_numbers_and_older_file_is_refused(self):
        self.run_main(web=FakeWeb({cf.EBP_URL: ebp_csv(), cf.CMDI_URL: b"PK broken"}))
        it = self.saved()["items"]["cmdi"]
        self.assertEqual((it["ok"], it["stale"], it["error"]), (False, False, "받은 파일의 꼴을 알아보지 못함"))
        self.assertNotIn("line", it)
        self.assertEqual(it["sources"][0]["url"], cf.CMDI_URL)
        older = ebp_csv(ebp_rows(end=D(2026, 8, 1)))
        self.run_main(now=NOW + datetime.timedelta(days=1), web=FakeWeb({cf.EBP_URL: older, cf.CMDI_URL: cmdi_xlsx()}))
        it = self.saved()["items"]["ebp"]
        self.assertEqual((it["ok"], it["stale"], it["error"]), (False, True, "받은 자료가 직전 자료보다 오래됨"))
        self.assertEqual(it["values"]["month"], "2026-09-01")

    def test_revised_history_takes_a_new_retrieved_date(self):
        self.run_main()
        rows = ebp_rows()
        rows[-2][1] = 0.0999                                                      # 전 표본 다시 추정 — 앞 달이 바뀌어 분위가 움직인다
        rows[5][1] = 0.2
        self.run_main(now=NOW + datetime.timedelta(days=3), web=FakeWeb({cf.EBP_URL: ebp_csv(rows), cf.CMDI_URL: cmdi_xlsx()}))
        it = self.saved()["items"]["ebp"]
        self.assertTrue(it["ok"])
        self.assertEqual(it["retrieved"], "2026-11-02")


class SecMirrorTest(unittest.TestCase):
    """sec.json → credit.json의 sec 칸 — 숫자에서 문구를 다시 만들고, 상태(받음·받지 못함·사유)는 정해 둔 것만 옮긴다."""
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.out = os.path.join(self.tmp, "data")
        self.orig = sf.COMPANIES
        sf.COMPANIES = [tsf.CO_A, tsf.CO_B]
        self.S = world()

    def tearDown(self):
        sf.COMPANIES = self.orig
        shutil.rmtree(self.tmp)

    def sec_run(self, answer, now=NOW, env=None):
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            return sf.main(["--out", self.out], opener=tsf.FakeOpener(answer), now=now, clock=tsf.FakeClock(),
                           sleep=lambda s: None, env={"SEC_USER_AGENT": tsf.FAKE_UA} if env is None else env)

    def credit_run(self, now=NOW):
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            cf.main(["--out", self.out, "--work", os.path.join(self.tmp, "w")], fred_load=FakeFred(self.S), now=now,
                    opener=FakeWeb())
        with open(os.path.join(self.out, cf.FILE), encoding="utf-8") as f:
            return json.load(f)["items"]["sec"]

    def sec_json(self):
        with open(os.path.join(self.out, sf.FILE), encoding="utf-8") as f:
            return json.load(f)

    def test_ok_item_is_rebuilt_from_numbers(self):
        self.assertEqual(self.sec_run(tsf.world_answer()), 0)
        js = self.sec_json()
        js["items"]["funding"]["line"] = "<b>원격 글</b>"                         # 글은 옮기지 않고 숫자로 다시 만든다
        with open(os.path.join(self.out, sf.FILE), "w", encoding="utf-8") as f:
            json.dump(js, f, ensure_ascii=False)
        it = self.credit_run()
        self.assertEqual((it["ok"], it["key"], it["date"]), (True, "sec", "2026-09-30"))
        self.assertTrue(it["line"].startswith("2사 TTM 설비투자/영업현금 98%"))
        self.assertNotIn("원격 글", json.dumps(it, ensure_ascii=False))
        self.assertEqual(it["values"], js["items"]["funding"]["values"])

    def test_stale_and_failed_states_carry_their_fixed_reason(self):
        self.sec_run(tsf.world_answer())
        self.sec_run(lambda c, t: "boom", now=NOW + datetime.timedelta(days=1))
        it = self.credit_run(NOW + datetime.timedelta(days=1))
        self.assertEqual((it["ok"], it["stale"], it["error"], it["failed_since"]), (False, True, "수신 실패", "2026-10-31"))
        self.assertTrue(it["line"])
        shutil.rmtree(self.out)
        self.sec_run(None, env={})
        it = self.credit_run()
        self.assertEqual((it["ok"], it["stale"], it["error"]), (False, False, "연락처 미설정(SEC_USER_AGENT)"))
        self.assertNotIn("line", it)

    def test_missing_or_broken_sec_file_keeps_the_previous_sec_item(self):
        self.sec_run(tsf.world_answer())
        self.assertTrue(self.credit_run()["ok"])
        for broken in ("{깨짐", json.dumps({"schema": 1, "items": {"funding": {"ok": True, "line": "x"}}})):
            with open(os.path.join(self.out, sf.FILE), "w", encoding="utf-8") as f:
                f.write(broken)
            it = self.credit_run(NOW + datetime.timedelta(days=1))
            self.assertEqual((it["ok"], it["stale"], it["error"]), (False, True, "SEC 자료 파일을 읽지 못함"))
            self.assertTrue(it["line"].startswith("2사 TTM"))
        js = json.loads(json.dumps({"schema": 1, "items": {"funding": {"ok": False, "stale": False, "error": "<i>원문</i>"}}}))
        with open(os.path.join(self.out, sf.FILE), "w", encoding="utf-8") as f:
            json.dump(js, f)
        it = self.credit_run(NOW + datetime.timedelta(days=2))
        self.assertEqual(it["error"], "SEC 자료 파일을 읽지 못함")                  # 정해 둔 사유 밖이면 옮기지 않는다
        self.assertEqual(it["failed_since"], "2026-10-31")


class LicenceTest(unittest.TestCase):
    def test_series_list_is_fixed(self):
        self.assertEqual(set(cf.SERIES), {"DRTSCILM", "NFCICREDIT", "A679RC1Q027SBEA", "GDP", "BOGZ1FA105050005Q",
                                          "BOGZ1FA106000135Q", "NASDAQ100", "NASDAQNQINTEL"})
        self.assertEqual(set(cf.LICENCE), set(cf.SERIES))
        self.assertEqual({s for s, v in cf.LICENCE.items() if v != "public-domain"}, {"NFCICREDIT", "NASDAQ100", "NASDAQNQINTEL"})
        self.assertEqual(cf.RESTRICTED, {"NASDAQ100", "NASDAQNQINTEL"})
        self.assertLessEqual(cf.RESTRICTED - {"NASDAQ100"}, set(ai.RESTRICTED))
        for spec in cf.ITEMS:
            self.assertLessEqual(set(spec["series"]), set(cf.SERIES) | set(cf.EXT))
            if set(spec["series"]) & cf.RESTRICTED:                               # 재배포 제한 칸의 숫자는 지수마다 정수 낙폭 하나
                kinds = list(spec["values"].values())
                self.assertFalse({t for t in kinds if t.startswith(("num", "int", "unit"))}, spec["key"])
                self.assertEqual(kinds.count("dd"), len(set(spec["series"]) & cf.RESTRICTED), spec["key"])
                self.assertEqual(sorted(k for k, t in spec["values"].items() if t == "dd"), ["ai_dd", "ndx_dd"])
        for v in (0, -1, -100):
            self.assertTrue(cf._KIND["dd"](v))
        for v in (1, -101, -12.5, 0.0, True, None, "-3"):                         # 정수 0~−100 밖·소수·글은 받지 않는다
            self.assertFalse(cf._KIND["dd"](v), v)
        private = ("BAMLC0A1CAAA", "BAMLC0A2CAA", "BAMLC0A3CA", "BAMLC0A4CBBB", "BAMLC0A0CM", "BAMLC8A0C15PY",
                   "BAMLH0A0HYM2", "BAA10Y", "SP500")
        self.assertFalse(set(cf.FETCH) & set(private))
        self.assertEqual(cf.FETCH, cf.SERIES + ["EBP", "CMDI"])

    def test_nasdaq_titles_and_copyright_are_the_fred_page_text(self):
        # 2026-10-30 FRED 시리즈 쪽 Suggested Citation·Notes 그대로(NASDAQ100 쪽의 'Â©'는 '©'로 고쳤다)
        self.assertEqual(cf.SOURCES["NASDAQ100"], ("Nasdaq, Inc.", "NASDAQ-100"))
        self.assertEqual(cf.SOURCES["NASDAQNQINTEL"],
                         ("Nasdaq, Inc.", "Nasdaq Consumer Technical Association Artificial Intelligence Index"))
        self.assertEqual(cf.COPYRIGHT, {"NASDAQ100": "Copyright © 2016, NASDAQ OMX Group, Inc.",
                                        "NASDAQNQINTEL": "Copyright © 2025, NASDAQ, Inc."})
        self.assertEqual(set(cf.COPYRIGHT), cf.RESTRICTED)
        for t in (*cf.COPYRIGHT.values(), cf.COPYRIGHT_NOTICE):
            self.assertNotIn("Â", t)
        for c in cf.COPYRIGHT.values():
            self.assertIn(c, cf.COPYRIGHT_NOTICE)
        self.assertEqual(cf.citation("NASDAQNQINTEL", "2026-10-30"),
                         "Nasdaq, Inc., Nasdaq Consumer Technical Association Artificial Intelligence Index [NASDAQNQINTEL], "
                         "retrieved from FRED, Federal Reserve Bank of St. Louis; "
                         "https://fred.stlouisfed.org/series/NASDAQNQINTEL, October 30, 2026.")

    def test_outside_fred_sources_are_fixed(self):
        self.assertEqual(set(cf.EXT), {"EBP", "CMDI"})
        self.assertEqual(cf.EBP_URL, "https://www.federalreserve.gov/econres/notes/feds-notes/ebp_csv.csv")
        self.assertEqual(cf.CMDI_URL,
                         "https://www.newyorkfed.org/medialibrary/research/interactives/cmdi/downloads/Market%20CMDI.xlsx")
        self.assertEqual((cf.EXT["EBP"]["licence"], cf.EXT["CMDI"]["licence"]), ("public-domain", "nyfed-terms"))
        self.assertEqual(cf.EBP_CITE, 'Favara, Gilchrist, Lewis and Zakrajšek (2016), "Updating the Recession Risk and the '
                                      'Excess Bond Premium," FEDS Notes, Board of Governors of the Federal Reserve System.')
        self.assertEqual(cf.EBP_SOURCE, "Source: Board of Governors of the Federal Reserve System (ebp_csv.csv), "
                                        "site calculations.")
        self.assertEqual(cf.CMDI_CITE, 'Boyarchenko, Crump, Kovner and Shachar, "Corporate Bond Market Distress," '
                                       'FRBNY Staff Report 957.')
        self.assertIn("public domain", cf.EBP_PD)
        self.assertIn("인장", cf.EBP_PD)
        self.assertIn("not New York Fed values", cf.CMDI_DERIVED_EN)
        # 이 프로젝트를 밝히는 User-Agent — 이메일·연락처 없음(FRED에는 달지 않는다)
        self.assertEqual(cf.UA, "macro-regime-check/1.0 (+https://github.com/yun-macrolab/macro-regime-check)")
        self.assertNotIn("@", cf.UA)
        self.assertEqual((cf.BUDGET, cf.REQ_TIMEOUT), (60, 10))


class StaticTest(unittest.TestCase):
    def read(self, *parts):
        with open(os.path.join(REPO, *parts), encoding="utf-8") as f:
            return f.read()

    def test_screen_script_matches_the_files_and_writes_text_only(self):
        js = self.read("site", "credit.js")
        card = re.findall(r'"(\w+)"', js[js.index("const CARD = ["):].split("]")[0])
        self.assertEqual(card, cf.ORDER)
        reasons = re.findall(r'"([^"]+)"', js[js.index("const REASONS = ["):].split("];")[0])
        want = list(cf.REASONS.values()) + [r for r in sf.REASONS.values() if r not in cf.REASONS.values()]
        self.assertEqual(reasons, want)
        body = js[js.index("const STAGE_DEF = "):].split(";\n", 1)[0]
        self.assertEqual("".join(re.findall(r'"([^"]*)"', body)), cf.STAGE_DEF)
        self.assertIn('const LABEL = "참고 — 금리 예측 아님";', js)
        stress = re.findall(r'"(\w+)"', js[js.index("const STRESS = ["):].split("]")[0])
        self.assertEqual(tuple(stress), cf.STRESS)
        note = "".join(re.findall(r'"([^"]*)"', js[js.index("const STRESS_NOTE = "):].split(";\n", 1)[0]))
        for part in ("ICE", "공개할 수 없어", "EBP", "CMDI", "대신합니다."):
            self.assertIn(part, note)
        self.assertIn('el("p", { class: "credit-def" }, STAGE_DEF)', js)           # 정의는 늘 함께
        for tok in ("innerHTML", "outerHTML", "insertAdjacentHTML", "createElement", "fetch(", "eval("):
            self.assertNotIn(tok, js)
        code = re.sub(r"/\*.*?\*/|//[^\n]*", "", js, flags=re.S)
        for word in list(FORBIDDEN_TEXT) + list(VERDICT):
            self.assertNotIn(word, code, word)

    def test_card_shows_the_citation_the_notice_promises_and_one_intro(self):
        # CITATION_NOTICE는 'FRED 권장 인용을 함께 싣는다'고 적는다 — 카드가 그 licence의 citation을 글자로 싣는다
        js = self.read("site", "credit.js")
        code = re.sub(r"/\*.*?\*/|//[^\n]*", "", js, flags=re.S)
        lics = re.findall(r'"([^"]+)"', re.search(r"const CITE_LICENCES = \[([^\]]*)\];", code).group(1))
        self.assertEqual(lics, ["citation-required", "restricted"])
        self.assertEqual({sid for sid, v in cf.LICENCE.items() if v in lics}, {"NFCICREDIT", "NASDAQ100", "NASDAQNQINTEL"})
        self.assertIn("함께 싣는다", cf.CITATION_NOTICE)
        self.assertIn("FRED 권장 인용과 함께 싣는다", cf.RESTRICTED_NOTICE)              # 제한 자료도 인용을 싣는다
        self.assertIn("citeLines(items)", code)
        self.assertIn('"권장 인용: " + x.text', code)
        # 머리 안내는 합니다체 ABOUT 하나 — 자료 파일의 notice(한다체)를 겹쳐 싣지 않고, notice의 뜻은 ABOUT이 모두 담는다
        self.assertNotIn("d.notice", code)
        about = "".join(re.findall(r'"([^"]*)"', code[code.index("const ABOUT = "):].split(";\n", 1)[0]))
        for part in ("규칙 수에 들지 않습니다", "예측력은 검증하지 않았습니다", "측정 기록은 운영자가 과거 자료로 잰 숫자",
                     "금리를 예측하지 않습니다"):
            self.assertIn(part, about)
        for part in ("규칙 점검에 쓰지 않는", "예측력은 검증하지 않았다", "측정 기록은 운영자가 과거 자료로 잰 숫자",
                     "금리를 예측하지 않는다"):
            self.assertIn(part, cf.NOTICE)                                          # 견준 뜻이 notice에 아직 있다

    def test_workflow_runs_sec_then_credit_without_failing_the_run(self):
        wf = self.read(".github", "workflows", "daily.yml")
        for sid, cmd in (("id: sec", "python scripts/sec_fetch.py"), ("id: credit", "python scripts/credit_fetch.py")):
            step = wf[wf.index(sid):]
            self.assertIn("continue-on-error: true", step[:200])
            self.assertIn("timeout-minutes: 2", step[:200])
            self.assertIn(cmd, step[:400])
        self.assertLess(wf.index("id: ai_invest"), wf.index("id: sec"))
        self.assertLess(wf.index("id: sec"), wf.index("id: credit"))
        self.assertLess(wf.index("id: credit"), wf.index("공개 전 검사(새 산출물 포함)"))
        sec = wf[wf.index("id: sec"):wf.index("id: credit")]
        self.assertIn("SEC_USER_AGENT: ${{ secrets.SEC_USER_AGENT }}", sec)
        self.assertEqual(wf.count("secrets.SEC_USER_AGENT"), 1)                    # 그 단계에만
        alert = wf[wf.index("\n  alert:"):]
        self.assertNotIn("credit", alert)
        self.assertNotIn("sec_fetch", alert)
        self.assertIn("node --test scripts/test_credit_render.cjs", wf[wf.index("\n  check:"):wf.index("\n  update:")])

    def test_page_wires_the_card(self):
        page = self.read("site", "index.html")
        self.assertIn('getJson("data/credit.json")', page)
        self.assertIn('getJson("data/sec.json")', page)
        self.assertIn('<script src="credit.js"></script>', page)
        self.assertRegex(page, r'id\s*[:=]\s*"credit-slot"')
        self.assertIn("window.CreditCard.render(", page)
        self.assertIn('<a href="data/credit.json">', page)

    def test_readme_counts(self):
        readme = self.read("README.md")
        m = re.search(r"\*\*아침 쪽 Python 테스트 (\d+)개 \+ node 테스트 (\d+)개\*\*\((.*?)\)와 \*\*저녁판", readme)
        py_part, node_part = m.group(3).split(" / node: ")
        mine = unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__]).countTestCases()
        sec = unittest.defaultTestLoader.loadTestsFromModule(tsf).countTestCases()
        self.assertRegex(py_part, rf"(^|· )신용 긴축 참고 {mine}( ·|$)")
        self.assertRegex(py_part, rf"(^|· )SEC 조달 참고 {sec}( ·|$)")
        cjs = len(re.findall(r"^test\(", self.read("scripts", "test_credit_render.cjs"), flags=re.M))
        self.assertRegex(node_part, rf"(^|· )신용 카드 그리기 {cjs}( ·|$)")


if __name__ == "__main__":
    unittest.main(verbosity=1)
