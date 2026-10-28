"""국고채 발행계획·매입·교환 수집(korea_issuance) — 지어낸 글과 숫자만(실제 보도자료·공고를 받아 넣지 않는다). 네트워크 불필요.

모양은 2026-10-28에 재정경제부 보도자료·결과 공고 PDF의 글 층을 읽어 본 것을 따랐고, 숫자·종목·사람 이름은 모두 지어냈다."""
import datetime as dt
import html
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
                                  "stated_prev_change_100m", "stated_plan_change_100m", "buyback_plan", "exchange_plan",
                                  "prev_actual", "source_url"})
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
                             ("4월에 비해 30,000억원 증가한", 30000), ("전월과 동일한 14조원", 0)):
            text = PLAN.replace("국고채는 전문딜러(PD)가", phrase + " 국고채는 전문딜러(PD)가")
            self.assertEqual(parse(text)["stated_prev_change_100m"], want, phrase)

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


def board(plans=None, pdfs=None, views=None, lists=None, ids=None, op_ids=None):
    """보도자료 목록·상세·첨부, 입찰 결과 목록(매입·교환)·상세·첨부를 돌려주는 가짜 fetch.
    값이 예외면 그 요청에서 던진다. 다른 묶음은 빈 응답(실패)."""
    plans, pdfs, views, lists = plans or BOARD_PLANS, pdfs or {}, views or {}, lists or {}
    ids = list(plans) if ids is None else ids
    op_ids = list(BOARD_OPS) if op_ids is None else op_ids
    def fetch(url, *args):
        def give(v):
            if isinstance(v, Exception): raise v
            return v
        if url == ki.PLAN_LIST:
            return give(lists.get("plans", plan_list([(i, f"{plans[i][0][0]}.{plans[i][0][1]}월 국고채, 재정증권, 원화표시 외평채 발행 계획")
                                                      for i in ids])))
        for kind in ki.OPS:
            if url == ki.ops_list_url(kind):
                word = ki.OPS_LABEL[kind]
                return give(lists.get(kind, ops_list([(i, f"2030년도 제1차 국고채 {word} 입찰 결과('{BOARD_OPS[i][1][2:].replace('-', '.')}.)")
                                                      for i in op_ids if BOARD_OPS[i][0] == kind])))
        q = urllib.parse.parse_qs(urllib.parse.urlsplit(url).query)
        if url.startswith(ki.PRESS_DETAIL) or url.startswith(ki.RESULT_DETAIL):
            i = (q.get("searchNttId1") or q.get("searchSn"))[0]
            n = i.split("_")[1]
            return give(views.get(i, (f'<a class="view" href="/com/synap/synapView.do?atchFileId=ATCH_{n}&amp;fileSn=2" '
                                      f'title="x.pdf 파일 새 창 열림">v</a>').encode()))
        if url.startswith(ki.FILE_DOWN):
            i = "MOSF_" + q["atchFileId"][0].split("_")[1]
            if i in pdfs: return give(pdfs[i])
            text = plan_text(*plans[i]) if i in plans else BOARD_OPS[i][2]
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
        r, _ = run_build(board(pdfs=bad, ids=["MOSF_30", "MOSF_29", "MOSF_28"]), old)
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
        r, _ = run_build(board(lists={"exchange": b"<p>changed</p>"}))      # 한 종류 목록만 비면 다른 종류로 갱신
        self.assertTrue(r["feeds"]["ktb_ops"]["ok"])
        self.assertEqual([o["kind"] for o in r["ktb_ops"]], ["buyback"])

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
        r, _ = run_build(board(), now=NOW + dt.timedelta(days=20))       # 6월 9일: 5월 계획이면 아직 지난달
        self.assertTrue(r["feeds"]["ktb_plans"]["ok"])
        with self.assertRaises(k.FeedError) as e:
            k.validate_freshness("ktb_plans", [{"month": "2030-04"}], [{"month": "2030-05"}], TODAY)
        self.assertEqual(str(e.exception), "regressed")
        for name in ("ktb_plans", "ktb_ops"):
            with self.assertRaises(k.FeedError): k.validate_freshness(name, [], None, TODAY)

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
        self.assertEqual(ki.to_read([("1", 0), ("2", 0), ("3", 0), ("4", 0)], {"1", "2"}, 2), [("1", 0), ("3", 0)])
        self.assertEqual(ki.to_read([], set(), 3), [])


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

    def test_feed_names_match_the_status_list(self):
        js = (REPO / "site" / "korea.js").read_text(encoding="utf-8")
        names = re.search(r"const names = \{(.*?)\};", js)[1]
        self.assertEqual(set(re.findall(r"(\w+):\"", names)), status.FEEDS)


if __name__ == "__main__":
    unittest.main()
