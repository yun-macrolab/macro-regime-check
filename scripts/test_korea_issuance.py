"""국고채 발행계획·매입·교환 수집(korea_issuance) — 지어낸 글과 숫자만(실제 보도자료·공고를 받아 넣지 않는다). 네트워크 불필요.

모양은 2026-10-28에 재정경제부 보도자료·결과 공고 PDF의 글 층을 읽어 본 것을 따랐고, 숫자·종목·사람 이름은 모두 지어냈다."""
import datetime as dt
import html
import io
import json
import os
import re
import tempfile
import unittest
import urllib.error
import urllib.parse
from pathlib import Path
from unittest.mock import patch

import korea_issuance as ki
import korea_market as k
import korea_status as status
from test_render_public import FORBIDDEN_TEXT

TODAY = dt.date(2030, 5, 20)
NOW = dt.datetime(2030, 5, 20, 3, tzinfo=k.UTC)
REPO = Path(__file__).resolve().parents[1]

# 5월 계획(당초 대비 문구·매입·교환·전월 실적이 다 있는 꼴). 경쟁입찰 합 14조 = 만기 합
PLAN = """- 1 -
보도시점 2030. 4. 25.(목) 17:00 배포 2030. 4. 25.(목) 17:00
‘30.5월 국고채 발행물량 당초계획대비
2조원 축소, 국고채 경쟁입찰 14.0조원 발행
 국고채 발행
  재정경제부는 5월 국고채 발행물량을 당초계획대비 2조원 축소하고,
  국고채는 전문딜러(PD)가 참여하는 경쟁입찰 방식으로는 14.0조원을 발행한다.
  연물별로는 2년물 2.0조원, 3년물 2.5조원, 5년물 2.2조원, 10년물 2.1조원,
20년물 0.8조원, 30년물 3.0조원, 50년물 1.3조원, 물가연동국고채 0.1조원을 발행한다.
 원화표시 외평채 발행
 재정경제부는 5월에는 전월대비 0.3조원 확대한 1.0조원의 원화표시 외평채 1년물을 발행한다.
담당 부서 국고실 국채정책과 책임자 과 장 가나다 (연락처-지어냄) 담당자 사무관 라마바 (contact-token-fake)
- 3 -
참고 1참고 1  2030년 5월 국고채 및 원화 외평채 경쟁입찰 발행 계획
□ ’30년 5월 140,000억원 국고채 경쟁입찰 발행
 ㅇ 5월 2일(목) 매출되는 국고채 2년물 20,000억원은
“국고03000-3203(30-1)”으로 통합 발행
 ㅇ 5월 7일(화) 매출되는 국고채 3년물 25,000억원은
“국고03000-3303(30-2)”으로 통합 발행
 ㅇ 5월 21일(화) 매출되는 국고채 5년물 22,000억원 중
“국고03000-3503(30-3)”으로 통합 발행
 ㅇ 5월 14일(화) 매출되는 국고채 10년물 21,000억원은
“국고03000-4003(30-4)”으로 통합 발행
 ㅇ 5월 9일(목) 매출되는 물가연동국고채 1,000억원은
“물가01000-4006(30-5)”로 통합 발행
 ㅇ 5월 22일(수) 매출되는 국고채 20년물 8,000억원은
“국고03000-5003(30-6)”으로 통합 발행
 ㅇ 5월 2일(목) 매출되는 국고채 30년물 30,000억원은
“국고03000-6003(30-7)”으로 통합 발행
 ㅇ 5월 13일(월) 매출되는 국고채 50년물 13,000억원은
“국고03000-8003(30-8)”으로 통합 발행
□ ’30년 5월 10,000억원의 원화표시 외평채 경쟁입찰 발행
 ㅇ 5월 20일(월) 매출되는 원화표시 외평채 1년물 10,000억원은
- 6 -
참고 3참고 3  2030년 5월 국고채 매입 계획
□ 총 22,000억원 규모 국고채 매입 계획
국고채 매입 세부종목 및 규모
일 시 매입대상 종목 규 모
5.15.(수)
  10:40～
  11:00
▪국고01000-3106(21-1)
 * 구체적 내용은 공고문(5월 10일, 한국은행 홈페이지)을 통해 추후 발표
22,000억원
- 7 -
참고 4참고 4  2030년 5월 국고채 교환 계획
□ 국고채 유동성 제고를 위해 30년물 경과 종목과 30년물 지표 종목 간
3,000억원 교환을 실시할 계획
5.14.(화)
  10:40～
국고03000-6003(30-7)
 * 구체적 내용은 공고문(5월 9일, 한국은행 홈페이지)을 통해 추후 발표
3,000억원
- 8 -
참고 5참고 5  2030년 4월 국고채 발행 실적
  □ 4월 국고채 발행규모는 151,230억원(명목채 150,230억 + 물가채 1,000억)
명목국고채
(단위 : 억원)
"""

# 1월 계획(전년 12월 실적이 'n조 m억원', 'N월에 비해', 교환 두 건 — 하나는 전년 12월 날짜, 30년물 금액이 '억은')
JAN = """보도시점 2030. 12. 26.(목) 17:00 배포 2030. 12. 26.(목) 17:00
1월 국고채 경쟁입찰 12.0조원 발행 계획
 재정경제부는 1월 120,000억원의 국고채를 경쟁입찰 방식으로 발행한다.
 1월 국고채 경쟁입찰 발행 규모는 12월에 비해 50,000억원 증가한 금액
이다. 연물별로는 2년물 30,000억원, 3년물 30,000억원, 30년물 60,000억원을 발행한다.
참고 1참고 1  2031년 1월 국고채 및 원화 외평채 경쟁입찰 발행 계획
□ ’31년 1월 120,000억원 국고채 경쟁입찰 발행
 ㅇ 1월 6일(월) 매출되는 국고채 2년물 30,000억원은
 ㅇ 1월 13일(월) 매출되는 국고채 3년물 30,000억원은
 ㅇ 1월 8일(수) 매출되는 국고채 30년물 60,000억은
참고 3참고 3  2031년 1월 국고채 교환 계획
□ 국고채 유동성 제고를 위해 10년물, 30년물 경과 종목과 30년물 지표 종목 간 2,000억원, 물가채 경과 종목과
10년물 지표 종목 간 1,000억원 교환을 실시할 계획
12.30.(월)
2,000억원
1.20.(월)
1,000억원
참고 4참고 4  2030년 12월 국고채 발행 실적
  □ 2030년 12월 국고채 발행규모는 9조 1,230억원
"""

BUYBACK = """제3차 국고채 매입 입찰결과
(’30.5.15.(수), 국채정책과)
1. 입찰개요
입찰일시 대금지급일 대 상 종 목 입찰금액
’30.5.15.(수)
10:40~11:00 ’30.5.17.(금)
 ▪ 31년 만기 2종목,
32년 만기 1종목
2.2조원
2.입찰결과
 【 응찰현황 】
 ㅇ 응찰금액 : 55,000억원 (응찰률 250.0%)
(단위 : 억원, %)
종 목 응찰금액 최저응찰금리 최고응찰금리 응찰가평금리
국고01000-3106-01 55,000 1.000 1.100 1.050
합 계 55,000
 【 낙찰결과 】
 ㅇ 낙찰금액 : 22,000억원
(단위 : 억원, %)
국고01000-3106-01 22,000 40.0 1.050 1.050 1.050
"""

# 교환 결과: 교환예정금액이 앞 종목 번호 끝자리와 줄만 바뀌어 붙는다(공백을 지우면 '…-30083,000억원')
EXCHANGE = """제5차 국고채 교환 입찰결과
(’30.5.14.(화), 국채정책과)
1. 입찰개요
입찰일시 차액정산
결제일 대 상 종 목 교환예정
금액
’30.5.14.(화)
10:40~11:00 ’3 0 .5 .1 6 .(목)
발행대상국고채 국고03000-6003-3008
3,000억원
매입대상국고채
국고02000-5503-30
2.입찰결과
 【 응찰현황 】
 ㅇ 응찰금액 : 7,500억원(응찰률 250.0%) (단위 : 억원, %)
【 낙찰결과 】
 ㅇ 낙찰금액 : 3,000억원 (단위 : 억원, %)
 ※ 발행대상종목 금리 : 1.234%
"""


def parse(text=PLAN, ym=(30, 5), today=TODAY):
    return ki.parse_plan_text(text, "MOSF_9", ym, today)


class PlanTextTests(unittest.TestCase):
    def test_numbers_from_the_appendix(self):
        r = parse()
        self.assertEqual((r["month"], r["published"], r["competitive_100m"]), ("2030-05", "2030-04-25", 140000))
        self.assertEqual([(t["tenor"], t["amount_100m"]) for t in r["tenors"]],
                         [("2년", 20000), ("3년", 25000), ("5년", 22000), ("10년", 21000), ("20년", 8000),
                          ("30년", 30000), ("50년", 13000), ("물가채", 1000)])
        self.assertEqual((r["long_share_pct"], r["y30_share_pct"]), (36.4, 21.4))      # (8+30+13)/140, 30/140
        self.assertEqual(r["stated_plan_change_100m"], -20000)                         # 제목·본문 둘 다 2조 — 같은 값
        self.assertIsNone(r["stated_prev_change_100m"])                                # 외평채 문단의 '전월대비'는 읽지 않는다
        self.assertEqual(r["buyback_plan"], {"amount_100m": 22000, "dates": ["2030-05-15"]})
        self.assertEqual(r["exchange_plan"], {"amount_100m": 3000, "dates": ["2030-05-14"]})
        self.assertEqual(r["prev_actual"], {"month": "2030-04", "amount_100m": 151230})
        self.assertEqual(r["source_url"], ki.press_url("MOSF_9"))

    def test_only_allowlisted_fields_leave_the_parser(self):
        r = parse()
        self.assertEqual(set(r), {"id", "month", "published", "competitive_100m", "tenors", "long_share_pct", "y30_share_pct",
                                  "stated_prev_change_100m", "stated_plan_change_100m", "stated_plan_change_unread",
                                  "buyback_plan", "exchange_plan", "prev_actual", "source_url"})
        self.assertIs(r["stated_plan_change_unread"], False)
        dump = json.dumps(r, ensure_ascii=False)
        for secret in ("가나다", "라마바", "연락처", "contact-token", "국고03000", "통합", "재정경제부"):
            self.assertNotIn(secret, dump)

    def test_january_shape_crosses_the_year(self):
        r = parse(JAN, (31, 1), dt.date(2031, 1, 5))
        self.assertEqual((r["month"], r["competitive_100m"], r["stated_prev_change_100m"]), ("2031-01", 120000, 50000))
        self.assertEqual(r["prev_actual"], {"month": "2030-12", "amount_100m": 91230})     # '9조 1,230억원'
        self.assertEqual(r["exchange_plan"], {"amount_100m": 3000, "dates": ["2030-12-30", "2031-01-20"]})
        self.assertIsNone(r["buyback_plan"])
        self.assertEqual(r["tenors"][-1], {"tenor": "30년", "amount_100m": 60000})        # '60,000억은'
        self.assertIsNone(r["stated_plan_change_100m"])

    def test_stated_previous_month_words(self):
        for phrase, want in (("4월 전월보다 1조원 축소한 14조원 규모의", -10000), ("전월보다 0.5조원 확대한", 5000),
                             ("전월보다 2조원 증가한", 20000), ("전월보다 1조원 감소한", -10000),
                             ("4월에 비해 30,000억원 증가한", 30000), ("전월과 동일한 14조원", 0),
                             ("5월 국고채 경쟁입찰 발행규모는 4월과 동일한 금액이다.", 0),      # 2025-09 꼴: 'N월과 동일'(N = 전달)
                             ("5월 국고채 경쟁입찰 발행규모는 3월과 동일한 금액이다.", None)):  # 전달이 아니면 읽지 않는다
            text = PLAN.replace("국고채는 전문딜러(PD)가", phrase + " 국고채는 전문딜러(PD)가")
            self.assertEqual(parse(text)["stated_prev_change_100m"], want, phrase)

    def test_stated_original_plan_wordings(self):
        for phrase, want in (("당초계획(16조원) 대비 2조원 축소", -20000), ("당초 발행계획 대비 2조원 축소", -20000),
                             ("당초계획보다 2조원 축소", -20000), ("당초계획대비 2조원 감액", -20000),
                             ("당초계획대비 2조원을 축소", -20000), ("당초계획에 비해 2조원 축소", -20000),
                             ("당초대비 0.5조원 증액", 5000), ("당초계획 대비 5,000억원 확대", 5000)):
            text = PLAN.replace("당초계획대비\n2조원 축소", phrase).replace("당초계획대비 2조원 축소하고", phrase + "하고")
            r = parse(text)
            self.assertEqual((r["stated_plan_change_100m"], r["stated_plan_change_unread"]), (want, False), phrase)

    def test_unreadable_original_plan_wording_is_flagged_not_refused(self):
        text = PLAN.replace("당초계획대비\n2조원 축소", "당초계획대비 2.0조원 줄인").replace("당초계획대비 2조원 축소하고", "당초계획대비 2.0조원 줄이고")
        r = parse(text)
        self.assertEqual((r["stated_plan_change_100m"], r["stated_plan_change_unread"]), (None, True))
        r = parse(JAN, (31, 1), dt.date(2031, 1, 5))                     # '당초'가 없으면 표시도 없다
        self.assertEqual((r["stated_plan_change_100m"], r["stated_plan_change_unread"]), (None, False))

    def test_stated_values_must_agree(self):
        with self.assertRaisesRegex(ValueError, "^ambiguous plan fields$"):
            parse(PLAN.replace("당초계획대비 2조원 축소하고", "당초계획대비 3조원 축소하고"))
        with self.assertRaisesRegex(ValueError, "^plan field changed$"):     # 'N월에 비해'의 N이 전달이 아니다
            parse(PLAN.replace("국고채는 전문딜러(PD)가", "3월에 비해 1조원 증가한 국고채는 전문딜러(PD)가"))

    def test_appendix_must_add_up(self):
        with self.assertRaisesRegex(ValueError, "^plan sum mismatch$"):
            parse(PLAN.replace("국고채 50년물 13,000억원", "국고채 50년물 12,000억원"))
        with self.assertRaisesRegex(ValueError, "^ambiguous plan fields$"):
            parse(PLAN.replace("국고채 20년물 8,000억원", "국고채 10년물 8,000억원"))
        with self.assertRaisesRegex(ValueError, "^plan field changed$"):
            parse(PLAN.replace("국고채 20년물 8,000억원", "국고채 15년물 8,000억원"))

    def test_header_and_month(self):
        with self.assertRaisesRegex(ValueError, "^missing plan total$"):
            parse(PLAN.replace("국고채 경쟁입찰 발행\n", "국고채 발행\n"))
        with self.assertRaisesRegex(ValueError, "^plan month mismatch$"):
            parse(ym=(30, 6))
        with self.assertRaisesRegex(ValueError, "^plan outside range$"):
            parse(PLAN.replace("140,000억원 국고채", "1,400,000억원 국고채"))

    def test_release_date(self):
        with self.assertRaisesRegex(ValueError, "^missing release date$"):
            parse(PLAN.replace("배포 2030. 4. 25.", "배포시"))
        with self.assertRaisesRegex(ValueError, "^plan outside range$"):      # 미래 보도자료
            parse(today=dt.date(2030, 4, 20))
        with self.assertRaisesRegex(ValueError, "^plan outside range$"):      # 계획 달에서 너무 먼 보도
            parse(PLAN.replace("배포 2030. 4. 25.", "배포 2029. 12. 1."))
        r = parse(PLAN.replace("보도시점 2030. 4. 25.(목) 17:00 배포", "보도시점 배포시 배포"))   # '배포시 배포 날짜' 꼴(2026-03-26 실측)
        self.assertEqual(r["published"], "2030-04-25")

    def test_lead_paragraph_must_exist(self):
        with self.assertRaisesRegex(ValueError, "^plan field changed$"):
            parse(PLAN.replace("연물별로는", "만기별로는"))

    def test_buyback_and_exchange_sections(self):
        with self.assertRaisesRegex(ValueError, "^plan field changed$"):
            parse(PLAN.replace("□ 총 22,000억원 규모 국고채 매입 계획", "□ 국고채 매입 계획"))
        with self.assertRaisesRegex(ValueError, "^plan field changed$"):
            parse(PLAN.replace("간\n3,000억원 교환을", "간 교환을"))
        no_ops = PLAN[:PLAN.index("참고 3참고 3")] + PLAN[PLAN.index("- 8 -"):]
        r = parse(no_ops)
        self.assertEqual((r["buyback_plan"], r["exchange_plan"]), (None, None))
        with self.assertRaisesRegex(ValueError, "^plan outside range$"):     # 계획 달에서 먼 날짜
            parse(PLAN.replace("5.15.(수)", "9.15.(수)"))
        # 본문에 매입(바이백)이 적혔는데 참고 매입 계획 절이 없다 — '계획 없음'으로 두지 않고 건너뛴다
        body_only = no_ops.replace("국고채는 전문딜러(PD)가", "국고채 매입(바이백)을 총 2.2조원 수준으로 실시할 예정이며, 국고채는 전문딜러(PD)가")
        with self.assertRaisesRegex(ValueError, "^plan field changed$"):
            parse(body_only)

    def test_previous_actual_is_only_the_month_before(self):
        r = parse(PLAN.replace("□ 4월 국고채 발행규모는", "□ 3월 국고채 발행규모는"))
        self.assertIsNone(r["prev_actual"])
        with self.assertRaisesRegex(ValueError, "^ambiguous plan fields$"):
            parse(PLAN + "\n4월 국고채 발행규모는 151,000억원\n")


def pdf_bytes(text):
    """ASCII 글 한 줄짜리 진짜 PDF(pypdf가 읽는 길을 그대로 지나게)."""
    stream = ("BT /F1 12 Tf 10 50 Td (" + text + ") Tj ET").encode()
    objs = [b"<< /Type /Catalog /Pages 2 0 R >>", b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 200 100] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>",
            b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream",
            b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"]
    out, offs = bytearray(b"%PDF-1.4\n"), []
    for i, o in enumerate(objs, 1):
        offs.append(len(out)); out += f"{i} 0 obj\n".encode() + o + b"\nendobj\n"
    xref = len(out)
    out += f"xref\n0 {len(objs)+1}\n0000000000 65535 f \n".encode() + b"".join(f"{o:010d} 00000 n \n".encode() for o in offs)
    out += f"trailer\n<< /Size {len(objs)+1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    return bytes(out)


class AttachmentTests(unittest.TestCase):
    def view(self, sn, name, atch="ATCH_000000000000001"):
        return (f'<a class="view" href="/com/synap/synapView.do;jsessionid=AbC-1_x.node10?atchFileId={atch}&amp;fileSn={sn}" '
                f'target="_blank" title="{html.escape(name)} 파일 새 창 열림">미리보기</a>')

    def test_pdf_is_chosen_by_title_not_by_order(self):
        for first, second in ((("1", "가.hwpx"), ("2", "가.pdf")), (("1", "가.pdf"), ("2", "가.hwpx"))):
            raw = (self.view(*first) + self.view(*second)) * 2            # 화면에 같은 첨부가 두 번(넓은·좁은 화면)
            sn = first[0] if first[1].endswith("pdf") else second[0]
            self.assertEqual(ki.attachment_pdf_url(raw.encode()),
                             ki.FILE_DOWN + "?atchFileId=ATCH_000000000000001&fileSn=" + sn)

    def test_ambiguous_or_foreign_attachments_are_refused(self):
        for raw in (self.view("1", "가.hwpx"), self.view("1", "가.pdf") + self.view("2", "나.pdf"),
                    '<a class="view" href="https://other.invalid/com/synap/synapView.do?atchFileId=ATCH_1&fileSn=1" title="가.pdf 파일 새 창 열림">x</a>',
                    self.view("1", "가.pdf", atch="ATCH_١٢")):
            with self.assertRaisesRegex(ValueError, "^ambiguous attachment$"):
                ki.attachment_pdf_url(raw.encode())

    def test_pdf_text_reads_a_real_pdf_and_refuses_other_files(self):
        self.assertIn("Fake 123", ki.pdf_text(pdf_bytes("Fake 123")))
        for raw in (b"PK\x03\x04hwpx", b"<html>", b""):
            with self.assertRaisesRegex(ValueError, "^unexpected attachment$"):
                ki.pdf_text(raw)
        with self.assertRaisesRegex(ValueError, "^unexpected attachment$"):
            ki.pdf_text(pdf_bytes("x"), max_pages=0)                      # 쪽수 상한


def plan_list(items):
    return "".join(f'<li><h3><a href="javascript:fn_egov_select(\'{i}\');">{html.escape(t)}</a></h3></li>' for i, t in items).encode()


def ops_list(items):
    return "".join(f"<a href='javascript:fn_egov_updateView(\"{i}\");'>{html.escape(t)}</a>" for i, t in items).encode()


class LinkTests(unittest.TestCase):
    def test_monthly_plans_only(self):
        raw = plan_list([("MOSF_5", "30.5월 국고채, 재정증권, 원화표시 외평채 발행 계획"),
                         ("MOSF_4", "'30.4월 국고채 경과물 0.5조원 모집 발행 계획"),
                         ("MOSF_3", "2030년도 원화외평채 발행계획 및 제도개선 방향"),
                         ("MOSF_2", "30.1월 국고채, 원화표시 외평채 발행 계획 및 재정증권 발행, 한국은행 일시차입 현황"),
                         ("MOSF_١", "30.3월 국고채, 재정증권, 원화표시 외평채 발행 계획"),
                         ("MOSF_7", "30.13월 국고채, 재정증권, 원화표시 외평채 발행 계획")])
        self.assertEqual(ki.plan_links(raw), [("MOSF_5", (30, 5)), ("MOSF_2", (30, 1))])
        with self.assertRaisesRegex(ValueError, "^no plan notices$"):
            ki.plan_links(plan_list([("MOSF_4", "'30.4월 국고채 경과물 0.5조원 모집 발행 계획")]))

    def test_other_monthly_title_shapes(self):
        raw = plan_list([("MOSF_6", "2030년 6월 국고채 발행계획 및 국채시장 동향"),                       # 머리기사 꼴
                         ("MOSF_5", "30.5월 국고채 경쟁입찰 14.0조원, 원화표시 외평채 1.0조원 발행 계획"),   # 2025년 꼴
                         ("MOSF_4", "30.4월 국고채 발행 계획"),
                         ("MOSF_3", "2030년도 국고채 발행계획 및 국채시장 정책방향"),                     # 연간 계획 — 달 없음
                         ("MOSF_2", "2030년 2월 국고채 개인투자용 발행 계획"),
                         ("MOSF_1", "30.1월 국고채 발행 실적")])                                         # '발행 계획'이 없다
        self.assertEqual(ki.plan_links(raw), [("MOSF_6", (30, 6)), ("MOSF_5", (30, 5)), ("MOSF_4", (30, 4))])
        self.assertEqual(urllib.parse.parse_qs(urllib.parse.urlsplit(ki.PLAN_LIST).query)["searchKeyword"], ["발행 계획"])

    def test_correction_wins_over_the_original_month(self):
        raw = plan_list([("MOSF_51", "30.5월 국고채, 재정증권, 원화표시 외평채 발행 계획(정정)"),
                         ("MOSF_50", "30.5월 국고채, 재정증권, 원화표시 외평채 발행 계획"),
                         ("MOSF_40", "30.4월 국고채, 재정증권, 원화표시 외평채 발행 계획")])
        links = ki.plan_links(raw)
        self.assertEqual(links, [("MOSF_51", (30, 5)), ("MOSF_40", (30, 4))])     # 같은 달은 목록 위(새) 것 하나만
        stored = []
        for _ in range(2):                                                        # 두 번 연달아 돌아도 정정 값이 남는다
            got = [{"id": i, "month": f"2030-{ym[1]:02d}", "competitive_100m": 110000 if i == "MOSF_51" else 100000}
                   for i, ym in ki.to_read(links, {r["id"] for r in stored}, ki.READ_PLANS)]
            stored = ki.merge_plans(got, stored)
            self.assertEqual([(r["month"], r["id"], r["competitive_100m"]) for r in stored],
                             [("2030-04", "MOSF_40", 100000), ("2030-05", "MOSF_51", 110000)])

    def test_second_list_page_url(self):
        self.assertEqual(ki.plan_list_url(1), ki.PLAN_LIST)
        self.assertEqual(ki.plan_list_url(2), ki.PLAN_LIST + "&pageIndex=2")
        q = urllib.parse.parse_qs(urllib.parse.urlsplit(ki.plan_list_url(2)).query)
        self.assertEqual((q["searchKeyword"], q["pageIndex"]), (["발행 계획"], ["2"]))
        for bad in (0, "2", 2.0, 10):
            with self.assertRaises(ValueError): ki.plan_list_url(bad)

    def test_page2_only_when_the_reporting_february_is_missing(self):
        L = lambda *yms: [(f"MOSF_{y}{m:02d}", (y, m)) for y, m in yms]
        live = L(*[(26, m) for m in range(10, 2, -1)])                         # 2026-10-28 첫 쪽: 10월~3월
        self.assertEqual(ki.page2_target(live, set()), (26, 2))
        self.assertEqual(ki.page2_target(live, {"2026-05", "2026-10"}), (26, 2))
        self.assertIsNone(ki.page2_target(live, {"2026-02"}))                  # 평소: 2월이 저장돼 있다
        self.assertIsNone(ki.page2_target(live + L((26, 2)), set()))           # 2월이 첫 쪽에 있다
        jan = L((27, 1), *[(26, m) for m in range(12, 4, -1)])                 # 1월 계획 → 보고 연도는 전년
        self.assertEqual(ki.page2_target(jan, set()), (26, 2))
        self.assertIsNone(ki.page2_target(jan, {"2026-02"}))
        self.assertIsNone(ki.page2_target(L((27, 2), (27, 1), (26, 12)), set()))  # 2월 계획이 가장 새 것
        self.assertEqual(ki.page2_target(L((27, 3)), set()), (27, 2))
        self.assertIsNone(ki.page2_target(L((26, 10), (26, 1)), set()))        # 가장 오래된 달이 2월보다 앞 — 둘째 쪽에 2월은 없다
        self.assertIsNone(ki.page2_target([], set()))

    def test_join_links_keeps_page1_and_new_ids_and_months_only(self):
        first = [("MOSF_10", (26, 10)), ("MOSF_9", (26, 9)), ("MOSF_3", (26, 3))]
        second = [("MOSF_3", (26, 3)), ("MOSF_31", (26, 3)), ("MOSF_9", (26, 1)), ("MOSF_2", (26, 2)), ("MOSF_1", (26, 1))]
        self.assertEqual(ki.join_links(first, second), first + [("MOSF_2", (26, 2)), ("MOSF_1", (26, 1))])
        many = [(f"MOSF_5{i:02d}", (25, i)) for i in range(12, 0, -1)]
        out = ki.join_links(first, many)
        self.assertEqual(len(out), ki.MAX_PLANS)
        self.assertEqual(out[:3], first)
        self.assertEqual(out[3:], many[:ki.MAX_PLANS - 3])
        # oldest를 주면 둘째 쪽은 그 달부터만(첫 쪽은 그대로)
        self.assertEqual(ki.join_links(first, second, (26, 2)), first + [("MOSF_2", (26, 2))])
        self.assertEqual(ki.join_links(first, many, (25, 11)), first + many[:2])
        self.assertEqual(ki.join_links([("MOSF_1", (26, 1))], [("MOSF_2", (25, 2))], (25, 2)), [("MOSF_1", (26, 1)), ("MOSF_2", (25, 2))])

    def test_operation_results_only(self):
        raw = ops_list([("MOSF_9", "2030년도 제3차 국고채 매입 입찰 결과('30.5.15.)"),
                        ("MOSF_8", "2030년도 제2차 원화외평채 매입 입찰 결과('30.5.12)"),
                        ("MOSF_7", "2030년도 제5차 국고채 교환 입찰 결과('30.5.14.)"),
                        ("MOSF_6", "국고채 10년물 “국고03000-4003” 통합발행 경쟁입찰 결과('30.5.13.)"),
                        ("MOSF_5", "2030년도 제2차 국고채 매입 입찰 결과('30.2.30.)")])
        self.assertEqual(ki.op_links(raw, "buyback"), [("MOSF_9", "2030-05-15")])
        self.assertEqual(ki.op_links(raw, "exchange"), [("MOSF_7", "2030-05-14")])

    def test_urls_are_fixed_and_ids_checked(self):
        self.assertTrue(ki.PLAN_LIST.startswith("https://mofe.go.kr/nw/nes/nesdta.do?"))
        self.assertEqual(ki.RESULTS, k.RESULTS)
        self.assertEqual(ki.result_url("MOSF_1"), k.result_url("MOSF_1"))
        self.assertEqual(urllib.parse.parse_qs(urllib.parse.urlsplit(ki.ops_list_url("exchange")).query)["searchKeyword"],
                         ["국고채 교환 입찰 결과"])
        for bad in ("MOSF_١", "MOSF_1&x=1", "../x"):
            with self.assertRaises(ValueError): ki.press_url(bad)
            with self.assertRaises(ValueError): ki.result_url(bad)


class OperationTests(unittest.TestCase):
    def test_buyback(self):
        r = ki.parse_op_text(BUYBACK, "MOSF_9", "buyback", "2030-05-15", TODAY)
        self.assertEqual(r, {"id": "MOSF_9", "kind": "buyback", "date": "2030-05-15", "offered_100m": 22000,
                             "bids_100m": 55000, "bid_cover_pct": 250.0, "awarded_100m": 22000, "source_url": ki.result_url("MOSF_9")})

    def test_exchange_amount_is_not_glued_to_the_bond_code(self):
        r = ki.parse_op_text(EXCHANGE, "MOSF_7", "exchange", "2030-05-14", TODAY)
        self.assertEqual((r["offered_100m"], r["bids_100m"], r["bid_cover_pct"], r["awarded_100m"]), (3000, 7500, 250.0, 3000))

    def test_exchange_amount_glued_to_the_code_is_picked_by_the_bid_ratio(self):
        # pypdf 6.10.2(requirements.txt, Actions)는 표 칸 사이에 공백을 넣지 않아 '…-3008' + '3,000억원'이 붙는다(2026-10-29:
        # 이 꼴로 교환 결과 전부가 field_changed). 붙은 숫자의 끝에서 쓸 수 있는 꼴 중 응찰금액 ÷ 금액 = 응찰률인 것 하나만
        glued = EXCHANGE.replace("-3008\n3,000억원", "-30083,000억원")
        head, rest = EXCHANGE.split("2.입찰결과", 1)
        flat = re.sub(r"\s+", "", head) + "2.입찰결과" + rest                    # 머리 전체가 공백 없이
        for text in (glued, flat):
            r = ki.parse_op_text(text, "MOSF_7", "exchange", "2030-05-14", TODAY)
            self.assertEqual((r["offered_100m"], r["bids_100m"], r["bid_cover_pct"], r["awarded_100m"]), (3000, 7500, 250.0, 3000))
        for bad in (glued.replace("응찰률 250.0%", "응찰률 25.0%"),           # 어느 후보도 응찰률과 맞지 않는다
                    glued.replace("-30083,000억원", "X30083,000억원")):         # 종목 번호('-…')에 붙은 꼴이 아니다
            with self.assertRaisesRegex(ValueError, "^op (field changed|outside range)$"):
                ki.parse_op_text(bad, "MOSF_7", "exchange", "2030-05-14", TODAY)
        self.assertEqual(ki.glued_offer("국고03000-6003-30083,000억원", 7500, 250.0), [("3,000", "억")])
        self.assertEqual(ki.glued_offer("국고03000-6003-30081.5조원", 37500, 250.0), [("1.5", "조")])
        self.assertEqual(ki.glued_offer("국고03000-6003-30083,000억원", 7500, 25.0), [])

    def test_refusals(self):
        cases = [(BUYBACK, "exchange", "2030-05-15", "op kind mismatch"),
                 (BUYBACK, "buyback", "2030-05-16", "op date mismatch"),
                 (BUYBACK.replace("2.입찰결과", "2.결과"), "buyback", "2030-05-15", "op field changed"),
                 (BUYBACK.replace("응찰률 250.0%", "응찰률 25.0%"), "buyback", "2030-05-15", "op outside range"),
                 (BUYBACK.replace("낙찰금액 : 22,000억원", "낙찰금액 : 32,000억원"), "buyback", "2030-05-15", "op outside range"),
                 (BUYBACK.replace("2.2조원", "2.2조원 1.0조원"), "buyback", "2030-05-15", "op field changed"),
                 (BUYBACK.replace("ㅇ 낙찰금액", "ㅇ 낙찰액"), "buyback", "2030-05-15", "op field changed")]
        for text, kind, date, msg in cases:
            with self.assertRaisesRegex(ValueError, "^" + msg + "$"):
                ki.parse_op_text(text, "MOSF_9", kind, date, TODAY)
        with self.assertRaisesRegex(ValueError, "^future operation$"):
            ki.parse_op_text(BUYBACK, "MOSF_9", "buyback", "2030-05-15", dt.date(2030, 5, 14))

    def test_fixed_skip_codes(self):
        for msg, code in ki.SKIP_REASONS.items():
            self.assertRegex(code, r"^[a-z_]+$")
            self.assertEqual(k.skip_reason(ValueError(msg)), code)


def plan_text(month, total, long_, actual=None, published=None):
    """달마다 다른 지어낸 계획(만기 둘: 3년 + 30년). actual = 전달 실적(억원)."""
    yy, mm = month
    pm = 12 if mm == 1 else mm - 1
    pub = published or (dt.date(2000 + yy, mm, 1) - dt.timedelta(days=5))
    tail = f"참고 4참고 4  20{yy}년 {pm}월 국고채 발행 실적\n□ {pm}월 국고채 발행규모는 {actual:,}억원\n" if actual else ""
    return (f"보도시점 배포 {pub.year}. {pub.month}. {pub.day}.(목) 17:00\n연물별로는 3년물 등을 발행한다.\n"
            f"참고 1참고 1 계획\n□ ’{yy}년 {mm}월 {total:,}억원 국고채 경쟁입찰 발행\n"
            f" ㅇ {mm}월 2일(목) 매출되는 국고채 3년물 {total - long_:,}억원은\n ㅇ {mm}월 3일(금) 매출되는 국고채 30년물 {long_:,}억원은\n"
            + tail)


BOARD_PLANS = {"MOSF_30": ((30, 5), 140000, 30000, 151230), "MOSF_29": ((30, 4), 150000, 40000, 160000),
               "MOSF_28": ((30, 3), 160000, 50000, 170000)}
BOARD_OPS = {"MOSF_90": ("buyback", "2030-05-15", BUYBACK), "MOSF_70": ("exchange", "2030-05-14", EXCHANGE)}


def board(plans=None, pdfs=None, views=None, lists=None, ids=None, op_ids=None, ops=None):
    """보도자료 목록·상세·첨부, 입찰 결과 목록(매입·교환)·상세·첨부를 돌려주는 가짜 fetch.
    값이 예외면 그 요청에서 던진다. 다른 묶음은 빈 응답(실패)."""
    plans, pdfs, views, lists, ops = plans or BOARD_PLANS, pdfs or {}, views or {}, lists or {}, ops or BOARD_OPS
    ids = list(plans) if ids is None else ids
    op_ids = list(ops) if op_ids is None else op_ids
    def fetch(url, *args):
        def give(v):
            if isinstance(v, Exception): raise v
            return v
        if url == ki.PLAN_LIST:
            return give(lists.get("plans", plan_list([(i, f"{plans[i][0][0]}.{plans[i][0][1]}월 국고채, 재정증권, 원화표시 외평채 발행 계획")
                                                      for i in ids])))
        if url == ki.plan_list_url(2):
            return give(lists.get("plans2", b""))
        for kind in ki.OPS:
            if url == ki.ops_list_url(kind):
                word = ki.OPS_LABEL[kind]
                return give(lists.get(kind, ops_list([(i, f"2030년도 제1차 국고채 {word} 입찰 결과('{ops[i][1][2:].replace('-', '.')}.)")
                                                      for i in op_ids if ops[i][0] == kind])))
        q = urllib.parse.parse_qs(urllib.parse.urlsplit(url).query)
        if url.startswith(ki.PRESS_DETAIL) or url.startswith(ki.RESULT_DETAIL):
            i = (q.get("searchNttId1") or q.get("searchSn"))[0]
            n = i.split("_")[1]
            return give(views.get(i, (f'<a class="view" href="/com/synap/synapView.do?atchFileId=ATCH_{n}&amp;fileSn=2" '
                                      f'title="x.pdf 파일 새 창 열림">v</a>').encode()))
        if url.startswith(ki.FILE_DOWN):
            i = "MOSF_" + q["atchFileId"][0].split("_")[1]
            if i in pdfs: return give(pdfs[i])
            text = plan_text(*plans[i]) if i in plans else ops[i][2]
            return b"%PDF-" + text.encode()
        return b""
    return fetch


def fake_pdf(raw, max_pages=12):
    if not raw.startswith(b"%PDF-"): raise ValueError("unexpected attachment")
    return raw[5:].decode()


def run_build(fetch, old=None, now=NOW):
    with patch.object(ki, "pdf_text", fake_pdf), patch("builtins.print") as out:
        r = k.build(old or {}, now, fetch)
    return r, "\n".join(str(c.args[0]) for c in out.call_args_list)


class BuildTests(unittest.TestCase):
    def test_two_new_feeds_and_summary(self):
        r, _ = run_build(board())
        for name in ("ktb_plans", "ktb_ops"):
            self.assertTrue(r["feeds"][name]["ok"], name)
            self.assertEqual(r["feeds"][name]["skipped"], [])
        self.assertEqual([p["month"] for p in r["ktb_plans"]], ["2030-03", "2030-04", "2030-05"])
        self.assertEqual([(o["date"], o["kind"]) for o in r["ktb_ops"]], [("2030-05-15", "buyback"), ("2030-05-14", "exchange")])
        s = r["ktb_summary"]
        self.assertEqual((s["latest_month"], s["prev_month_change_100m"]), ("2030-05", -10000))
        self.assertEqual(s["progress"]["months"], ["2030-02", "2030-03", "2030-04"])
        self.assertEqual(s["progress"]["missing"], ["2030-01"])
        self.assertIsNone(s["progress"]["pct"])                     # 1월 실적이 없다 — 비율을 내지 않는다
        self.assertIsNone(s["progress"]["limit_100m"])               # 2030년 한도는 표에 없다

    def test_reads_newest_and_unseen_only_and_keeps_older_months(self):
        r1, _ = run_build(board())
        old = {"schema": 1, "feeds": {n: r1["feeds"][n] for n in ("ktb_plans", "ktb_ops")}}
        old["feeds"]["ktb_plans"]["data"].insert(0, dict(r1["ktb_plans"][0], id="MOSF_10", month="2029-11"))
        seen = []
        inner = board()
        def fetch(url, *a):
            seen.append(url); return inner(url, *a)
        r2, _ = run_build(fetch, old)
        files = [u for u in seen if u.startswith(ki.FILE_DOWN)]
        self.assertEqual(len(files), 3)                               # 최신 계획 1 + 매입 1 + 교환 1(각 최신만 다시)
        self.assertEqual([p["month"] for p in r2["ktb_plans"]], ["2029-11", "2030-03", "2030-04", "2030-05"])

    def test_one_unreadable_plan_keeps_the_others_and_its_old_value(self):
        bad = {"MOSF_29": b"%PDF-" + plan_text(*BOARD_PLANS["MOSF_29"]).replace("연물별로는", "만기별로는").encode()}
        r, log = run_build(board(pdfs=bad))
        f = r["feeds"]["ktb_plans"]
        self.assertTrue(f["ok"])
        self.assertEqual([p["month"] for p in r["ktb_plans"]], ["2030-03", "2030-05"])
        self.assertEqual(f["skipped"], [{"id": "MOSF_29", "reason": "field_changed"}])
        self.assertIn("ktb_plans skip MOSF_29: field_changed", log)
        prev = ki.parse_plan_text(plan_text(*BOARD_PLANS["MOSF_29"]), "MOSF_29", (30, 4), TODAY)
        old = {"schema": 1, "feeds": {"ktb_plans": {"data": [prev], "last_success": "previous"}}}
        bad["MOSF_30"] = urllib.error.URLError("secret host")      # 최신도 못 읽음 — 남은 하나(3월)만 새로
        r, _ = run_build(board(pdfs=bad, ids=["MOSF_30", "MOSF_29", "MOSF_28"]), old,
                         now=dt.datetime(2030, 5, 2, 3, tzinfo=k.UTC))    # 5월 2일 — 4월 계획까지면 아직 묵지 않음
        self.assertEqual([p["month"] for p in r["ktb_plans"]], ["2030-03", "2030-04"])
        self.assertEqual(r["ktb_plans"][1], prev)

    def test_nothing_readable_fails_only_this_feed_and_keeps_data(self):
        old = {"schema": 1, "feeds": {"ktb_plans": {"data": [{"id": "old", "month": "2030-05"}], "last_success": "previous"},
                                      "ktb_ops": {"data": [{"id": "o", "date": "2030-05-01"}], "last_success": "prev-ops"}}}
        bad = {i: b"<html>secret</html>" for i in list(BOARD_PLANS) + list(BOARD_OPS)}
        r, _ = run_build(board(pdfs=bad), old)
        for name, last in (("ktb_plans", "previous"), ("ktb_ops", "prev-ops")):
            f = r["feeds"][name]
            self.assertEqual((f["ok"], f["reason"], f["last_success"]), (False, "unreadable_notices", last))
            self.assertEqual({s["reason"] for s in f["skipped"]}, {"pdf_shape"})
        self.assertEqual(r["ktb_plans"], [{"id": "old", "month": "2030-05"}])
        self.assertEqual(r["ktb_ops"], [{"id": "o", "date": "2030-05-01"}])
        self.assertNotIn("secret", json.dumps(r, ensure_ascii=False))

    def test_list_failures_and_codes(self):
        r, _ = run_build(board(lists={"plans": urllib.error.URLError("secret"), "buyback": b"<p>changed</p>", "exchange": b"<p>x</p>"}))
        self.assertEqual((r["feeds"]["ktb_plans"]["reason"], r["feeds"]["ktb_ops"]["reason"]), ("unavailable", "unavailable"))
        self.assertEqual(r["ktb_summary"], {"latest_month": None, "prev_month_change_100m": None, "progress": None})
        r, log = run_build(board(lists={"exchange": b"<p>changed</p>"}))  # 한 종류 목록만 비면 다른 종류로 갱신하되 사유 코드로 남긴다
        self.assertTrue(r["feeds"]["ktb_ops"]["ok"])
        self.assertEqual([o["kind"] for o in r["ktb_ops"]], ["buyback"])
        self.assertEqual(r["feeds"]["ktb_ops"]["skipped"], [{"id": "exchange", "reason": "no_notices"}])
        self.assertRegex(ki.NO_NOTICES, r"^[a-z_]+$")

    def test_empty_kind_list_is_warned_in_actions(self):
        fetch, build = board(lists={"buyback": b"<p>changed</p>"}), k.build
        with tempfile.TemporaryDirectory() as folder, patch.object(k, "build", lambda old, now: build(old, NOW, fetch)), \
                patch.object(ki, "pdf_text", fake_pdf), patch("builtins.print") as out:
            k.main(["--out", folder])
        self.assertIn("::warning::국고채 매입·교환 결과 공고 1건을 읽지 못함 — buyback no_notices", [str(c.args[0]) for c in out.call_args_list])

    def test_timeout_marks_the_rest(self):
        r, _ = run_build(board(views={"MOSF_29": k.FeedError("timeout")}))
        f = r["feeds"]["ktb_plans"]
        self.assertTrue(f["ok"])
        self.assertEqual(f["skipped"], [{"id": "MOSF_29", "reason": "timeout"}, {"id": "MOSF_28", "reason": "not_tried"}])
        r, _ = run_build(board(views={"MOSF_30": k.FeedError("timeout")}, ids=["MOSF_30"]))
        self.assertEqual(r["feeds"]["ktb_plans"]["reason"], "timeout")

    def test_freshness(self):
        late = NOW + dt.timedelta(days=45)                                # 7월 4일: 최신 5월 계획 — 6월 계획도 없다
        r, _ = run_build(board(), now=late)
        self.assertEqual((r["feeds"]["ktb_plans"]["ok"], r["feeds"]["ktb_plans"]["reason"]), (False, "stale"))
        self.assertTrue(r["feeds"]["ktb_ops"]["ok"])                       # 매입·교환은 날짜로 묵음을 따지지 않는다
        r, _ = run_build(board(), now=NOW + dt.timedelta(days=16))       # 6월 5일: 5월 계획이면 아직 7일 여유 안
        self.assertTrue(r["feeds"]["ktb_plans"]["ok"])
        r, _ = run_build(board(), now=NOW + dt.timedelta(days=20))       # 6월 9일: 8일부터는 6월 계획이 있어야 한다
        self.assertEqual((r["feeds"]["ktb_plans"]["ok"], r["feeds"]["ktb_plans"]["reason"]), (False, "stale"))
        for day, want in ((7, None), (8, "stale")):                       # 경계: 7일까지 지난달, 8일부터 그달
            try:
                k.validate_freshness("ktb_plans", [{"month": "2030-05"}], None, dt.date(2030, 6, day)); got = None
            except k.FeedError as e:
                got = str(e)
            self.assertEqual(got, want, day)
        with self.assertRaises(k.FeedError) as e:
            k.validate_freshness("ktb_plans", [{"month": "2030-04"}], [{"month": "2030-05"}], dt.date(2030, 5, 3))
        self.assertEqual(str(e.exception), "regressed")
        for name in ("ktb_plans", "ktb_ops"):
            with self.assertRaises(k.FeedError): k.validate_freshness(name, [], None, TODAY)

    def steady(self):
        """모든 달·결과를 이미 읽은 뒤의 이전 자료(평소엔 가장 새 공고 하나씩만 다시 읽는다)."""
        r, _ = run_build(board())
        return {"schema": 1, "feeds": {n: dict(r["feeds"][n], last_success="previous") for n in ("ktb_plans", "ktb_ops")}}

    def test_transient_failure_of_a_kept_notice_keeps_the_feed_green(self):
        old = self.steady()
        for err, code in ((urllib.error.URLError("secret host"), "network"), (k.FeedError("timeout"), "timeout"),
                          (urllib.error.HTTPError("https://x.invalid", 503, "x", None, None), "http_503")):
            r, log = run_build(board(views={"MOSF_30": err, "MOSF_90": err, "MOSF_70": err}), old)
            for name, ident in (("ktb_plans", "MOSF_30"), ("ktb_ops", "MOSF_90")):
                f = r["feeds"][name]
                self.assertTrue(f["ok"], (name, code))
                self.assertEqual(f["data"], old["feeds"][name]["data"], (name, code))       # 전에 읽은 값 그대로
                self.assertIn({"id": ident, "reason": code}, f["skipped"], (name, code))     # 사유 코드는 남는다
            self.assertNotIn("secret", json.dumps(r, ensure_ascii=False))

    def test_lasting_or_new_failures_still_fail(self):
        old = self.steady()
        r, _ = run_build(board(views={"MOSF_30": urllib.error.HTTPError("https://x.invalid", 404, "x", None, None)}), old)
        self.assertEqual((r["feeds"]["ktb_plans"]["ok"], r["feeds"]["ktb_plans"]["reason"]), (False, "unavailable"))   # 404는 덮지 않는다
        r, _ = run_build(board(pdfs={"MOSF_30": b"<html>"}), old)                         # 양식 문제도 그대로 실패
        self.assertEqual((r["feeds"]["ktb_plans"]["ok"], r["feeds"]["ktb_plans"]["reason"]), (False, "unreadable_notices"))
        plans = dict(BOARD_PLANS, MOSF_31=((30, 6), 150000, 40000, 140000))
        r, _ = run_build(board(plans=plans, ids=["MOSF_31", "MOSF_30", "MOSF_29", "MOSF_28"],
                               views={"MOSF_31": urllib.error.URLError("x")}), old)       # 새 달 공고는 일시 오류여도 실패
        self.assertEqual((r["feeds"]["ktb_plans"]["ok"], r["feeds"]["ktb_plans"]["reason"]), (False, "unavailable"))
        self.assertEqual(r["ktb_plans"], old["feeds"]["ktb_plans"]["data"])

    def test_an_older_never_read_plan_is_not_hidden_by_the_kept_newest(self):
        old = self.steady()
        old["feeds"]["ktb_plans"]["data"] = [r for r in old["feeds"]["ktb_plans"]["data"] if r["id"] != "MOSF_28"]
        r, _ = run_build(board(views={"MOSF_30": urllib.error.URLError("x"), "MOSF_28": urllib.error.URLError("x")}), old)
        f = r["feeds"]["ktb_plans"]
        self.assertEqual((f["ok"], f["reason"]), (False, "unavailable"))      # 3월은 한 번도 읽지 못했다 — 덮지 않는다
        self.assertEqual({s_["id"] for s_ in f["skipped"]}, {"MOSF_30", "MOSF_28"})

    def test_auctions_keep_their_old_semantics(self):
        old = {"schema": 1, "feeds": {"auctions": {"data": [{"id": "MOSF_1", "date": "2030-05-01"}], "last_success": "p"}}}
        def fetch(url, *a):
            if url == k.RESULTS:
                return ops_list([("MOSF_1", "국고채 10년물 “국고03000-4003” 통합발행 경쟁입찰 결과('30.5.13.)")])
            raise urllib.error.URLError("x")
        with patch.object(k, "result_links", lambda raw: [("MOSF_1", "10")]):
            r, _ = run_build(fetch, old)
        self.assertEqual((r["feeds"]["auctions"]["ok"], r["feeds"]["auctions"]["reason"]), (False, "unavailable"))

    def test_status_knows_the_new_feeds_and_actions_warning(self):
        self.assertTrue({"ktb_plans", "ktb_ops"} <= status.FEEDS)
        bad = {"MOSF_29": b"PK hwpx"}
        fetch, build = board(pdfs=bad), k.build
        with tempfile.TemporaryDirectory() as folder, patch.object(k, "build", lambda old, now: build(old, NOW, fetch)), \
                patch.object(ki, "pdf_text", fake_pdf), patch("builtins.print") as out:
            code = k.main(["--out", folder])
            saved = json.loads((Path(folder) / "korea.json").read_text(encoding="utf-8"))
        lines = [str(c.args[0]) for c in out.call_args_list]
        self.assertEqual(code, 1)                                         # 다른 묶음(빈 응답)은 실패
        self.assertTrue(saved["feeds"]["ktb_plans"]["ok"])
        self.assertIn("::warning::국고채 발행계획 보도자료 1건을 읽지 못함 — MOSF_29 pdf_shape", lines)


# 2026-10-28 실제 목록의 꼴: 첫 쪽(10건) = 10월~3월 계획 8건 + 경과물 모집 2건, 둘째 쪽 = 2026년 2·1월, 2025년 12~10월. 숫자는 지어냄
LIVE_NOW = dt.datetime(2026, 10, 28, 3, tzinfo=k.UTC)
LIVE_ACTUAL = {m: 198000 for m in range(1, 10)} | {9: 196730}                  # 1~9월 합 178.073조원
LIVE_PLANS = {f"MOSF_{y}{m:02d}": ((y, m), 150000, 40000, LIVE_ACTUAL.get(m - 1, 180000) if y == 26 else 170000)
              for y, ms in ((26, range(1, 11)), (25, range(10, 13))) for m in ms}
LIVE_PAGE1 = [f"MOSF_26{m:02d}" for m in range(10, 2, -1)]
LIVE_PAGE2 = ["MOSF_2602", "MOSF_2601", "MOSF_2512", "MOSF_2511", "MOSF_2510"]


def live_lists(page1=LIVE_PAGE1, page2=LIVE_PAGE2):
    title = lambda i: f"{LIVE_PLANS[i][0][0]}.{LIVE_PLANS[i][0][1]}월 국고채, 재정증권, 원화표시 외평채 발행 계획"
    p1 = [(i, title(i)) for i in page1]
    p1[3:3] = [("MOSF_901", "'26.7월 국고채 경과물 0.5조원 모집 발행 계획"), ("MOSF_900", "'26.5월 국고채 경과물 0.5조원 모집 발행 계획")]
    return {"plans": plan_list(p1), "plans2": plan_list([(i, title(i)) for i in page2])}


class SecondPageTests(unittest.TestCase):
    def run_live(self, old=None, lists=None):
        seen, inner = [], board(plans=LIVE_PLANS, lists=lists or live_lists())
        def fetch(url, *a):
            seen.append(url); return inner(url, *a)
        r, log = run_build(fetch, old, now=LIVE_NOW)
        return r, log, seen.count(ki.plan_list_url(2)), {"schema": 1, "feeds": {"ktb_plans": r["feeds"]["ktb_plans"]}}

    def test_two_runs_reach_january_and_the_ratio_then_page2_stops(self):
        self.assertEqual(ki.READ_PLANS, 6)
        r, _, p2, old = self.run_live()
        self.assertEqual(p2, 1)
        self.assertEqual([p["month"] for p in r["ktb_plans"]], [f"2026-{m:02d}" for m in range(5, 11)])
        self.assertEqual(r["ktb_summary"]["progress"]["missing"], ["2026-01", "2026-02", "2026-03"])
        r, _, p2, old = self.run_live(old)
        self.assertEqual(p2, 1)                                                # 2월이 아직 없다 — 한 번 더
        self.assertTrue(r["feeds"]["ktb_plans"]["ok"])
        months = [p["month"] for p in r["ktb_plans"]]
        self.assertTrue({f"2026-{m:02d}" for m in range(2, 11)} <= set(months), months)
        p = r["ktb_summary"]["progress"]
        self.assertEqual((p["year"], p["missing"], p["actual_100m"], p["pct"]), (2026, [], 1780730, 78.9))
        self.assertEqual(min(months), "2026-02")                              # 둘째 쪽의 2월보다 오래된 계획은 읽지 않는다
        self.assertEqual(r["feeds"]["ktb_plans"]["skipped"], [])
        r, _, p2, _ = self.run_live(old)
        self.assertEqual(p2, 0)                                                # 평소: 2월이 저장돼 있으면 둘째 쪽을 읽지 않는다
        self.assertEqual(r["ktb_summary"]["progress"]["pct"], 78.9)

    def test_odd_saved_rows_do_not_break_the_page2_rule(self):
        junk = [None, 5, {"month": ["2026-02"], "id": ["MOSF_2602"]}, {"month": {"m": 1}, "id": {"i": 1}}, {"id": "MOSF_2610"}]
        old = {"schema": 1, "feeds": {"ktb_plans": {"data": junk, "last_success": "p"},
                                      "ktb_ops": {"data": [{"id": ["x"], "date": "2026-10-01"}], "last_success": "p"}}}
        r, _, p2, _ = self.run_live(old)
        self.assertTrue(r["feeds"]["ktb_plans"]["ok"])
        self.assertEqual(p2, 1)                                                # 깨진 행의 2월은 저장된 달로 치지 않는다
        self.assertEqual([p["month"] for p in r["ktb_plans"]], [f"2026-{m:02d}" for m in range(5, 11)])

    def test_page2_is_not_read_when_february_is_on_page1(self):
        _, _, p2, _ = self.run_live(lists=live_lists(page1=[f"MOSF_26{m:02d}" for m in range(10, 1, -1)]))
        self.assertEqual(p2, 0)

    def test_page2_problems_keep_the_feed(self):
        for bad, name in ((urllib.error.URLError("secret"), "URLError"), (k.FeedError("timeout"), "FeedError"),
                          (b"<p>changed</p>", "ValueError"), (urllib.error.HTTPError("https://x.invalid", 500, "x", None, None), "HTTPError")):
            r, log, p2, _ = self.run_live(lists=dict(live_lists(), plans2=bad))
            f = r["feeds"]["ktb_plans"]
            self.assertEqual(p2, 1, name)
            self.assertTrue(f["ok"], name)
            self.assertEqual(f["skipped"], [], name)
            self.assertEqual([p["month"] for p in r["ktb_plans"]], [f"2026-{m:02d}" for m in range(5, 11)], name)
            self.assertIn(f"[korea_market] ktb_plans page2: {name}", log.splitlines(), name)
            self.assertNotIn("secret", json.dumps(r, ensure_ascii=False) + log)


class ReadOrderTests(unittest.TestCase):
    """읽을 순서 — 새 공고 먼저, 매입·교환 번갈아, 이미 읽은 가장 새 공고 다시 읽기는 끝에(2026-10-29 실측 뒤)."""
    L = staticmethod(lambda *ids: [(i, 0) for i in ids])

    def test_to_read_puts_the_stored_newest_last_and_keeps_the_set(self):
        links = self.L("1", "2", "3", "4", "5")
        self.assertEqual(ki.to_read(links, {"1", "3"}, 3), self.L("2", "4", "1"))          # 가장 새 것(저장됨)은 끝
        self.assertEqual(ki.to_read(links, {"2"}, 3), self.L("1", "3", "4"))               # 가장 새 것이 새 공고면 맨 앞
        self.assertEqual(ki.to_read(links, {"1", "2", "3", "4", "5"}, 3), self.L("1"))   # 다 읽었으면 다시 읽기 하나
        self.assertEqual(ki.to_read(links, {"1"}, 1), self.L("1"))                         # cap 1 — 다시 읽기만
        self.assertEqual(ki.to_read(links, set(), 2), self.L("1", "2"))
        for prev in (set(), {"1"}, {"2", "4"}, {"1", "2", "3"}, {"9"}):                    # 집합은 전과 같다: 가장 새 것 + 새 것 cap−1개
            for cap in (1, 2, 3, 6):
                got = ki.to_read(links, prev, cap)
                want = {"1"} | {i for i, _ in links[1:] if i not in prev}
                self.assertEqual(len(got), min(cap, len(want)), (prev, cap))
                self.assertEqual({i for i, _ in got}, {"1"} | {i for i, _ in [l for l in links[1:] if l[0] not in prev][:cap - 1]})
                self.assertEqual([i for i, _ in got if i in prev], ["1"] if "1" in prev else [])   # 다시 읽기는 가장 새 것 하나뿐
                if "1" in prev: self.assertEqual(got[-1][0], "1")

    def test_ops_queue_alternates_kinds_and_rereads_last(self):
        B = [("B1", "2030-05-15"), ("B2", "2030-04-15"), ("B3", "2030-03-15"), ("B4", "2030-02-15")]
        E = [("E1", "2030-05-14"), ("E2", "2030-04-14")]
        ids = lambda q: [(i, kind) for i, (kind, _) in q]
        q = ki.ops_queue({"buyback": B, "exchange": E}, {"B1"}, 3)                 # 매입 밀림 많음, 교환은 모두 새것
        self.assertEqual(ids(q), [("B2", "buyback"), ("E1", "exchange"), ("B3", "buyback"), ("E2", "exchange"), ("B1", "buyback")])
        self.assertEqual(q[0], ("B2", ("buyback", "2030-04-15")))                  # 읽을 때 넘길 값(종류, 입찰일)
        q = ki.ops_queue({"buyback": B, "exchange": E}, {"B1", "E1"}, 3)
        self.assertEqual(ids(q), [("B2", "buyback"), ("E2", "exchange"), ("B3", "buyback"), ("B1", "buyback"), ("E1", "exchange")])
        q = ki.ops_queue({"buyback": B, "exchange": []}, {"B1"}, 3)                # 한 종류가 비어도 다른 종류는 그대로
        self.assertEqual(ids(q), [("B2", "buyback"), ("B3", "buyback"), ("B1", "buyback")])
        q = ki.ops_queue({"buyback": B, "exchange": E}, {i for i, _ in B + E}, 3)  # 모두 읽었으면 종류마다 다시 읽기 하나씩만
        self.assertEqual(ids(q), [("B1", "buyback"), ("E1", "exchange")])
        self.assertEqual(ki.ops_queue({"buyback": [], "exchange": []}, set(), 3), [])
        q = ki.ops_queue({"buyback": B, "exchange": E}, set(), ki.READ_OPS)         # 종류별 cap은 전과 같다
        self.assertEqual(sorted(ids(q)), sorted([(i, "buyback") for i, _ in B[:ki.READ_OPS]] + [(i, "exchange") for i, _ in E]))


def op_text(kind, date):
    """BUYBACK·EXCHANGE의 입찰일만 바꾼 지어낸 결과 PDF 글."""
    d = dt.date.fromisoformat(date)
    mark = f"’{d.year % 100}.{d.month}.{d.day}."
    return BUYBACK.replace("’30.5.15.", mark) if kind == "buyback" else EXCHANGE.replace("’30.5.14.", mark)


# 2026-10-29 실행의 꼴: 발행계획은 3~10월이 저장돼 있고 2월(1월 실적)이 둘째 쪽, 매입은 가장 새 것만 저장, 교환은 한 번도 못 읽음
SLOW_OPS = {i: (kind, day, op_text(kind, day)) for i, kind, day in (
    ("MOSF_83", "buyback", "2026-10-21"), ("MOSF_82", "buyback", "2026-09-16"), ("MOSF_81", "buyback", "2026-08-20"),
    ("MOSF_73", "exchange", "2026-10-14"), ("MOSF_72", "exchange", "2026-09-09"), ("MOSF_71", "exchange", "2026-08-12"))}


def old_to_read(links, prev_ids, cap):          # 고치기 전 순서(비교용): 가장 새 것 다시 읽기가 맨 앞
    rest = [l for l in links[1:] if l[0] not in prev_ids]
    return [links[0]] + rest[:cap - 1] if links else []


def old_ops_queue(per_kind, prev_ids, cap):     # 고치기 전 순서(비교용): 매입을 다 읽고 교환
    return [(i, (kind, d)) for kind, found in per_kind.items() for i, d in old_to_read(found, prev_ids, cap)]


class SlowBoardTests(unittest.TestCase):
    """재정경제부 요청 하나에 cost초가 걸리는 가짜 시계·opener로 PublicFetcher를 그대로 돌린다(전체 180초, 국고채 묶음 각 60초)."""
    def slow_run(self, cost, old_order=False, fail=None):
        stored = [ki.parse_plan_text(plan_text(*LIVE_PLANS[f"MOSF_26{m:02d}"]), f"MOSF_26{m:02d}", (26, m), LIVE_NOW.date())
                  for m in range(3, 11)]
        old = {"schema": 1, "feeds": {"ktb_plans": {"data": stored, "last_success": "p"},
                                      "ktb_ops": {"data": [ki.parse_op_text(SLOW_OPS["MOSF_83"][2], "MOSF_83", "buyback", "2026-10-21",
                                                                            LIVE_NOW.date())], "last_success": "p"}}}
        clock, seen, inner = [0.0], [], board(plans=LIVE_PLANS, lists=live_lists(), ops=SLOW_OPS)
        def opener(url, data=None, timeout=None):
            seen.append(url)
            if fail and fail(url):                                      # 이 요청은 매번 시간 초과(요청 상한을 다 쓴다)
                clock[0] += timeout; raise TimeoutError()
            if url.startswith("https://mofe.go.kr"): clock[0] += cost
            return io.BytesIO(inner(url))
        fetch = k.PublicFetcher(clock=lambda: clock[0], sleep=lambda n: None, opener=opener)
        with patch.object(ki, "to_read", old_to_read if old_order else ki.to_read), \
                patch.object(ki, "ops_queue", old_ops_queue if old_order else ki.ops_queue):
            r, _ = run_build(fetch, old, now=LIVE_NOW)
        files = [u for u in seen if u.startswith(ki.PRESS_DETAIL) or u.startswith(ki.RESULT_DETAIL)]
        return r, [urllib.parse.parse_qs(urllib.parse.urlsplit(u).query) for u in files]

    def skips(self, r, name):
        return {s_["id"]: s_["reason"] for s_ in r["feeds"][name]["skipped"]}

    def test_february_plan_is_read_before_the_newest_is_reread(self):
        r, _ = self.slow_run(10, old_order=True)                     # 목록 두 쪽 20초 + 다시 읽기 20초 → 2월은 창 끝에 걸린다
        self.assertEqual(self.skips(r, "ktb_plans"), {"MOSF_2602": "timeout"})
        self.assertEqual(r["ktb_summary"]["progress"]["missing"], ["2026-01"])
        r, opened = self.slow_run(10)
        self.assertEqual([q["searchNttId1"][0] for q in opened if "searchNttId1" in q], ["MOSF_2602", "MOSF_2610"])
        self.assertEqual(self.skips(r, "ktb_plans"), {"MOSF_2610": "timeout"})        # 다시 읽기만 빠지고 전에 읽은 값이 남는다
        self.assertTrue(r["feeds"]["ktb_plans"]["ok"])
        p = r["ktb_summary"]["progress"]
        self.assertEqual((p["missing"], p["pct"]), ([], 78.9))
        self.assertEqual(r["ktb_plans"][-1]["id"], "MOSF_2610")

    def test_no_new_notice_read_in_the_window_is_a_timeout_with_old_data_kept(self):
        # 새 공고(2월)가 창을 다 쓰면 다시 읽기는 시도도 못 한다 — 새로 읽은 것이 없으니 묶음은 timeout 실패, 저장된 값은 그대로
        feb = lambda url: "MOSF_2602" in url
        r, _ = self.slow_run(10, old_order=True, fail=feb)            # 고치기 전: 다시 읽기가 앞에서 성공해 ok였다
        self.assertTrue(r["feeds"]["ktb_plans"]["ok"])
        r, _ = self.slow_run(10, fail=feb)
        f = r["feeds"]["ktb_plans"]
        self.assertEqual((f["ok"], f["reason"]), (False, "timeout"))
        self.assertEqual(self.skips(r, "ktb_plans"), {"MOSF_2602": "network", "MOSF_2610": "timeout"})   # 요청 시간 초과는 network, 창 끝은 timeout
        self.assertEqual([p["month"] for p in r["ktb_plans"]], [f"2026-{m:02d}" for m in range(3, 11)])
        self.assertEqual(f["last_success"], "p")

    def test_exchange_is_not_starved_behind_buybacks(self):
        r, _ = self.slow_run(8, old_order=True)                      # 고치기 전: 매입 셋 뒤의 교환은 시도도 못 함
        sk = self.skips(r, "ktb_ops")
        self.assertEqual({sk[i] for i in ("MOSF_73", "MOSF_72", "MOSF_71")}, {"not_tried"})
        self.assertEqual({o["kind"] for o in r["ktb_ops"]}, {"buyback"})
        r, opened = self.slow_run(8)
        self.assertEqual([q["searchSn"][0] for q in opened if "searchSn" in q][:3], ["MOSF_82", "MOSF_73", "MOSF_81"])
        sk = self.skips(r, "ktb_ops")
        self.assertEqual(sk, {"MOSF_81": "timeout", "MOSF_72": "not_tried", "MOSF_71": "not_tried", "MOSF_83": "not_tried"})
        self.assertTrue(r["feeds"]["ktb_ops"]["ok"])
        self.assertEqual([(o["id"], o["kind"]) for o in r["ktb_ops"]],      # 새 매입 하나 + 교환 하나(60초 창 — 45초면 교환이 끝에 걸린다)
                         [("MOSF_83", "buyback"), ("MOSF_73", "exchange"), ("MOSF_82", "buyback")])


class SummaryTests(unittest.TestCase):
    def plans(self, months, actual=True):
        out = []
        for i, (y, m) in enumerate(months):
            pm = (y, m - 1) if m > 1 else (y - 1, 12)
            out.append({"month": f"{y}-{m:02d}", "competitive_100m": 100000 + i * 10000,
                        "prev_actual": {"month": f"{pm[0]}-{pm[1]:02d}", "amount_100m": 200000} if actual else None})
        return out

    def test_progress_against_a_registered_limit(self):
        limits = {2030: {"limit_100m": 2_000_000, "published": "2029-12-20", "source_url": "https://mofe.go.kr/x"}}
        with patch.dict(ki.ANNUAL_LIMITS, limits, clear=True):
            s = ki.summary(self.plans([(2030, m) for m in range(2, 6)]))       # 실적 1~4월
            self.assertEqual((s["progress"]["actual_100m"], s["progress"]["pct"], s["progress"]["through"]), (800000, 40.0, "2030-04"))
            self.assertEqual(s["prev_month_change_100m"], 10000)
            s = ki.summary(self.plans([(2030, 1)]))                            # 1월 계획 → 전년 12월 실적: 그해(2029) 한도 없음
            self.assertEqual((s["progress"]["year"], s["progress"]["limit_100m"], s["progress"]["pct"]), (2029, None, None))
            self.assertIsNone(s["prev_month_change_100m"])                     # 전달 계획이 없다
            s = ki.summary(self.plans([(2030, 2), (2030, 4)]))                 # 2월 실적이 빠짐
            self.assertEqual((s["progress"]["missing"], s["progress"]["pct"]), (["2030-02"], None))
            self.assertIsNone(s["prev_month_change_100m"])

    def test_registered_limits_cite_their_source(self):
        for year, v in ki.ANNUAL_LIMITS.items():
            self.assertTrue(v["source_url"].startswith(ki.PRESS_DETAIL + "?"), year)
            self.assertRegex(v["published"], r"^\d{4}-\d{2}-\d{2}$")
            self.assertLess(v["published"], f"{year}-01-01")
            self.assertTrue(0 < v["limit_100m"] < 10_000_000)
        readme = (REPO / "README.md").read_text(encoding="utf-8")
        self.assertIn("225.7조원", readme)                                      # 표의 값과 출처를 README에도 적는다
        self.assertIn("MOSF_000000000076306", readme)

    def test_broken_saved_rows_do_not_stop_the_snapshot(self):
        junk = [None, 5, {"month": "2030-05"}, {"month": 7, "competitive_100m": 1}, {"month": "2030-04", "competitive_100m": "x"},
                {"month": "2030-03", "competitive_100m": 100000, "prev_actual": {"month": "2030-02", "amount_100m": "x"}},
                {"month": "2030-02", "competitive_100m": 90000, "prev_actual": "2030-01"}]
        s = ki.summary(junk)
        self.assertEqual((s["latest_month"], s["prev_month_change_100m"], s["progress"]), ("2030-03", 10000, None))
        old = {"schema": 1, "feeds": {"ktb_plans": {"data": junk, "last_success": "p"}, "ktb_ops": {"data": junk, "last_success": "p"}}}
        r, _ = run_build(lambda *a: b"", old)                              # 모두 실패 — 깨진 이전 자료를 그대로 두되 요약은 낸다
        self.assertEqual(r["ktb_summary"]["latest_month"], "2030-03")

    def test_merge_keeps_order_and_caps(self):
        prev = [{"id": f"P{m}", "month": f"2029-{m:02d}"} for m in range(1, 13)]
        got = [{"id": "N", "month": "2030-01"}, {"id": "R", "month": "2029-12"}]
        merged = ki.merge_plans(got, prev + ["junk", {"id": "x"}])
        self.assertEqual(len(merged), ki.MAX_PLANS)
        self.assertEqual((merged[0]["month"], merged[-2]["id"], merged[-1]["id"]), ("2029-02", "R", "N"))
        ops = ki.merge_ops([{"id": "a", "date": "2030-01-02"}], [{"id": "a", "date": "2030-01-01"}, {"id": "b", "date": "2030-01-03"}, 5])
        self.assertEqual([(o["id"], o["date"]) for o in ops], [("b", "2030-01-03"), ("a", "2030-01-02")])
        self.assertEqual(ki.to_read([("1", 0), ("2", 0), ("3", 0), ("4", 0)], {"1", "2"}, 2), [("3", 0), ("1", 0)])
        self.assertEqual(ki.to_read([], set(), 3), [])

    def test_ops_keep_a_year_of_buybacks_with_exchanges(self):
        """매입·교환이 한 목록이라 12행이면 달마다 둘씩 반년 치뿐 — 24행(2026-10-29)이면 한 해의 매입이 다 남는다."""
        self.assertEqual(ki.MAX_OPS, 24)
        year = [{"id": f"{k}{m}", "kind": k, "date": f"2030-{m:02d}-{d}"} for m in range(1, 13) for k, d in (("buyback", 20), ("exchange", 10))]
        ops = ki.merge_ops(year[12:], year[:12] + [{"id": "old", "kind": "exchange", "date": "2029-12-10"}])
        self.assertEqual(len(ops), 24)
        self.assertEqual(sorted(o["date"][:7] for o in ops if o["kind"] == "buyback"), [f"2030-{m:02d}" for m in range(1, 13)])
        self.assertNotIn("old", [o["id"] for o in ops])
        self.assertEqual((ops[0]["id"], ops[-1]["id"]), ("buyback12", "exchange1"))


class SiteTextTests(unittest.TestCase):
    """화면 글(korea.js의 발행계획 칸)은 고정 문구뿐 — 판정·방향 낱말 없이, 링크는 sourceLink로만."""
    VERDICT = ("판정", "신호", "경보", "충족", "문턱", "유의", "⚠", "축소", "확대", "증가", "감소", "상승", "하락",
               "부담", "우려", "호재", "악재", "강세", "약세", "→")
    NOTICE = "이 사이트의 규칙 판정에 쓰지 않는 참고 자료입니다."

    def block(self):
        js = (REPO / "site" / "korea.js").read_text(encoding="utf-8")
        start = js.index("// 국고채 발행계획·매입(바이백)·교환")
        return js[start:js.index("  function setView(", start)]

    def test_no_verdict_or_private_words(self):
        body = re.sub(r"/\*.*?\*/|//[^\n]*", "", self.block(), flags=re.S)
        self.assertEqual(body.count(self.NOTICE), 1)
        text = body.replace(self.NOTICE, "").replace("재정경제부", "")       # 출처 이름(부처명) 말고는 '재정'도 없다
        for word in list(FORBIDDEN_TEXT) + list(self.VERDICT):
            self.assertNotIn(word, text, word)

    def test_links_and_dom_only_through_helpers(self):
        body = self.block()
        for tok in ("innerHTML", "createElement", "fetch(", "href=", "location.", "eval("):
            self.assertNotIn(tok, body)
        self.assertIn("sourceLink(", body)
        self.assertIn("연간 한도 미등록", body)                                # 한도가 표에 없으면 추정하지 않고 이렇게만

    def test_sum_is_named_as_release_figures_with_its_caveat(self):
        body = self.block()
        self.assertIn("보도자료 발행 규모 합계", body)
        self.assertNotIn("발행 실적 누계", body)
        self.assertIn("뒤에 확정되는 20년물 비경쟁인수와 모집분은 빠져 있어 재정경제부가 밝힌 누계와 다를 수 있습니다", body)
        readme = (REPO / "README.md").read_text(encoding="utf-8")
        self.assertIn("보도자료 발행 규모 합계", readme)
        self.assertIn("국고채 발행계획 수정", readme)                       # 연간 한도 표를 사람이 고치는 손볼 일

    def test_feed_names_match_the_status_list(self):
        js = (REPO / "site" / "korea.js").read_text(encoding="utf-8")
        names = re.search(r"const names = \{(.*?)\};", js)[1]
        self.assertEqual(set(re.findall(r"(\w+):\"", names)), status.FEEDS)


if __name__ == "__main__":
    unittest.main()
