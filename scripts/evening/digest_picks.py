#!/usr/bin/env python3
"""저녁판 AI 요약 층의 계약과 문장 검사 (2026-10-09) — data/digest_picks.json의 형태, 문장 하나를 내보내도 되는가.

규칙판(digest.json)은 Actions가 LLM 없이 내고 그대로다. 이 층은 PC에서만 만든다(evening_llm.py): 판의 항목 몇 개에 "무슨 일인지"를
한두 문장으로 얹는다. 이 파일에는 수신도 호출도 없다 — 형태와 검사뿐이라 원문이 없는 곳(게시 뒤 · CI · 화면 테스트)에서도 쓴다.
형태와 화면이 붙이는 규칙은 digest_schema.py 머리말의 'AI 요약 층'이 기준이다. 숫자는 digest_rules.TH, 낱말은 아래에 있다.

규칙판과 다른 점: 문장(fact)은 닫힌 값이 아니다 — 모델이 쓴 글자다. 그래서 문장마다 아래 검사를 모두 통과해야 실리고, 걸린 문장은
그 문장만 버린다(규칙판은 그대로 나간다). 버린 것은 사유별 개수만 남는다(dropped) — 버린 문장도, 원문도 어디에도 쓰지 않는다.
  shape   꼴 — 문자열 · fact_min_chars~fact_chars자 · 한국어 평서문 1~fact_sentences문장('…다.'로 맺는다) · 한글 · 영문 · 숫자와 몇 가지
          문장부호만(따옴표 · 꺾쇠 · @ · # · 제어 문자 · 보이지 않는 글자 없음) · 주소 · 전화번호 꼴 없음 · 채널 이름 · 라벨 없음
  banned  금지 낱말 — 권유(매수 · 매도 · 추천 · 비중 확대 · 팔아야 · 살 때 · 기회다 …) · 전망 꼴(…할 것이다 · 전망이다 · 예상된다 · 관측 ·
          '오를 것으로' …) · 방향 평가(호재 · 상방 압력 · 하락 재료 · 부담이다 …) · 광고(리딩방 · 구독 · 문의 · 검색 · 채널 …) · 지시문 꼴
          (무시하 · 시스템 · 프롬프트 …). 앞날을 가리키는 말(연말 · 내년 · 당분간 …)이 든 문장은 지난 일로 맺어야 한다. '…할 수 있다 ·
          필요하다 · 가능성이 크다 · …해야 한다'는 누가 그렇게 봤다고 옮긴 것('…다고 우려했다')만 둔다 — 글에 적힌 조심스러운 말을
          단정으로 바꾸게 만들지 않으려고. 정해 둔 꼴만 잡는다: 다른 말로 쓴 권유 · 전망을 다 막지는 못한다
  copy    베낌 — 공백 · 문장부호를 뺀 뒤 읽힌 글 하나와 연속 copy_run자 이상 겹치거나, 문장의 글자 copy_gram-gram 가운데 copy_ratio
          이상이 한 글에 들어 있거나, 조사를 뗀 어절 copy_stems개가 한 글과 같은 차례로 이어지거나(조사만 바꾼 문장), copy_piece자
          이상 겹친 토막들이 — 어느 글의 것이든 — 문장의 copy_cover 이상을 덮는다(여러 글의 토막을 이어 붙인 문장). 읽힌 글에 있는
          짧은 토막(이름 · 숫자 · 낱말)은 문장에 올 수 있다
  number  숫자 대조 — 문장의 모든 숫자가 읽힌 글의 한 줄에 같은 단위로 있다(7bp를 7%로, 6명을 6%로, 3년을 3%로 쓰지 못한다. 10년물 =
          10년). 숫자 앞 num_ctx_chars자 안의 꼬리표(예상 · 컨센 · 전월 · 직전 · 전년 …)는 문장과 글이 같아야 한다 — 그 숫자 앞에서
          (예상치를 결과처럼, 결과를 예상치처럼 쓰지 못하게. 문장 어딘가에 '예상'이 있는 것으로는 안 된다). 음수로 쓴 숫자는 글에서도
          음수여야 한다. 'A로 B를 웃돌았다 · B보다 낮았다'는 같은 단위의 두 숫자의 크기와 맞아야 한다
  term    낱말 — 문장에서 걸린 사전 낱말이 그 항목의 terms · words · 읽힌 글의 낱말 안에 있다(좁은 낱말이 있는 넓은 낱말은 된다 —
          '미 국채 금리'가 있으면 '금리', 나라를 밝힌 입찰이 있으면 '국채 입찰'). 읽힌 채널이 둘 이상이면 A · B급 낱말은 두 채널 이상이
          쓴 것만 받는다(글 하나가 주제를 넓히지 못하게). 판정이 갈리는 결과 낱말은 글과 반대로 쓰면 버린다(상회 ↔ 하회 · 인상 ↔ 인하 ·
          순매수 ↔ 순매도 · 확대 ↔ 축소 · 상향 ↔ 하향). 동결 · 부합은 읽힌 글에 있을 때만. 풀어 쓴 방향 말(올랐다 · 내렸다 · 웃돌았다 ·
          못 미쳤다 …)도 글에 그 방향이 없고 반대 방향만 있으면 버린다. '인하했다 · 기준금리를 내렸다' 같은 결정은 글에도 결정으로 적혀
          있어야 한다('인하 소수의견' · '인하 기대'는 결정이 아니다). 대부분 · 다수 · 일부 · 소수 같은 말은 글에 있을 때만
  name    이름 — 직함(의장 · 총재 · 위원 · 장관 · 대통령 · 대표 · 총리) 앞의 이름과 영문 토막(두 글자 이상 — 대문자든 소문자든 숫자가
          붙었든)은 읽힌 글에 있을 때만(그 항목 낱말의 토막 — FOMC · CPI · 연준 — 과 숫자의 단위 bp는 된다). 모델의 맥락에만 있던
          토막(계정 이름 · 폴더 이름 같은 것)이 문장에 실리지 않게
  none    모델이 그 항목을 쓰지 않았다(null)
앞의 둘(shape · banned)은 원문 없이 돈다 — fact_plain, validate_picks가 쓸 때 본다. 뒤의 넷은 읽힌 글이 있어야 한다.
'읽힌 글' = 모델에게 실제로 건넨 글자(주소 · 채널 이름을 가리고 llm_post_chars자에서 자른 것)다.

알고 있는 한계: 숫자도 사전 낱말도 없는 지어낸 사실('…회의를 열기로 했다')과 뜻을 틀리게 옮긴 문장은 어떤 검사도 막지 못한다 — 막는 것은
모델과 화면의 'AI 요약 — 틀릴 수 있습니다' 표시뿐이다. 방향 검사는 읽힌 글에 한쪽 방향만 있을 때만 가린다(금리는 올랐고 주가는 내렸다는
글에서는 못 가린다). 메모체 글의 숫자를 차례대로 엮은 문장은 네 어절까지는 베낌이 아니다. 한글로 옮겨 적은 사람 이름은 직함 앞일 때만 잡는다.
올라간 파일을 CI가 다시 볼 때는 형식만 본다(validate_picks plain=False) — 문장 규칙을 조인 뒤에도 요약 층이 규칙판의 문이 되지 않게.
"""
import hashlib
import json
import re

import digest_rules as R
import digest_schema as S

TH = R.TH
FILE = "digest_picks.json"
MODE = "ai"
CHECKS = ("shape", "banned", "copy", "number", "term", "name")      # 검사하는 순서 — 먼저 걸린 것 하나가 사유가 된다
CODES = (*CHECKS, "none")
READ = (("bond", "source"), ("analyst", "source"))                  # 모델에게 읽히는 글의 채널 — 채권 · 애널 원천만
MODEL_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._\[\]-]{0,63}$")

# ---------- 낱말 (숫자는 digest_rules.TH) ----------

QUALIFIERS = ("예상", "컨센", "전월", "직전", "전년", "전분기", "전주", "전일")     # 숫자 앞에 붙어 그 숫자가 무엇인지 바꾸는 꼬리표
OPPOSITE = {"상회": "하회", "하회": "상회", "인상": "인하", "인하": "인상", "순매수": "순매도", "순매도": "순매수",
            "확대": "축소", "축소": "확대", "상향": "하향", "하향": "상향"}        # 판정이 갈리는 결과 낱말의 짝 — 글과 반대로 쓰면 버린다
ALONE = ("동결", "부합")                                                       # 짝이 없는 판정 — 읽힌 글에 있을 때만
QUANT = ("대부분", "대다수", "다수", "과반", "절반", "전원", "만장일치", "일부", "소수", "몇몇", "상당수")     # 몇이나 그랬는가 — 글에 있을 때만
# 풀어 쓴 방향 말의 두 묶음 — 문장이 쓴 묶음이 읽힌 글에 없고 반대 묶음만 있으면 뒤집힌 것이다(강세 · 약세는 가격과 금리가 엇갈려 뺀다)
_UP = re.compile(r"오르|올랐|올라|올리|올렸|올린|상승|웃돌|웃돈|상회|높아|높였|높았|높은|높게|늘었|늘어|늘린|증가|급등|반등|확대|상향|인상")
_DOWN = re.compile(r"내리|내렸|내려|내린|떨어|하락|밑돌|밑돈|하회|못\s?미[치쳤친]|낮아|낮췄|낮았|낮은|낮게|줄었|줄어|줄인|줄였|감소|급락|반락|축소|하향|인하")
# 통화정책 결정 — 문장이 '했다'고 쓰면 읽힌 글에도 결정으로 적혀 있어야 한다('인하 소수의견' · '인하 기대'는 결정이 아니다)
DECIDE = {"인상": "올렸|높였", "인하": "내렸|낮췄", "동결": "유지했|묶었"}
_GAP = r"(?:[^.\n]|(?<=[0-9])\.(?=[0-9])){0,12}"                               # 금리와 그 풀이말 사이 — 같은 문장 안의 몇 글자(소수점은 된다)
_HEDGE = re.compile(r"\s?(?:소수|의견|주장|요구|기대|전망|가능성|시사|필요|관측|베팅|확률|프라이싱|반영|압력|논의|검토)")
_CMP = re.compile(r"(?:을|를|보다)\s*(?:[가-힣]+\s){0,2}?(웃돌|웃돈|상회|높|밑돌|밑돈|하회|낮)")
TITLES = r"(?:부?의장|부?총재|위원(?!회)|장관|대통령|대표|총리)"
NOT_NAMES = frozenset(("다수", "일부", "여러", "대부분", "몇몇", "복수", "모든", "신임", "차기", "전임", "당시", "해당", "이들", "양측",
                       "다른", "주요", "일각", "상당수", "소수", "과반"))       # 직함 앞에 오지만 이름이 아닌 말
UNIT_WORDS = frozenset(("bp", "bps", "pt"))                                    # 숫자에 붙는 영문 단위 — 이름 검사에서 뺀다
_PARTICLE_END = re.compile(r"(?:에서|에게|으로|까지|부터|[은는이가을를의도와과로에만며고])$")     # 조사로 끝난 토막은 이름 자리가 아니다
_JOSA = re.compile(r"(?:에서는|에서|에게|으로|이라고|라고|까지|부터|보다|처럼|[은는이가을를의도와과로에만])$")
_BANNED = tuple(re.compile(p, re.IGNORECASE) for p in (
    # 권유
    r"(?<!순)매수", r"(?<!순)매도", r"추천", r"권유", r"비중\s*(?:확대|축소|유지|조절)", r"오버\s?웨이트", r"언더\s?웨이트", r"overweight",
    r"underweight", r"(?:(?<![가-힣])사|팔아|담아|사들여|매입해|던져|갈아타)야", r"(?:살|팔|담을|늘릴|줄일|사들일|매입할|갈아탈)\s*(?:때|시점|기회|만\s?하)",
    r"기회(?:다|이다|로)", r"(?:롱|숏)\s?(?:포지션|뷰|전략|베팅)", r"매력", r"바람직", r"유리하다", r"유효하다", r"투자\s?의견", r"목표\s?주?가",
    # 전망 꼴
    r"것이다", r"전망이다", r"전망된다", r"전망이\s*(?:우세|많|커|확산|힘|나)", r"예상(?:된다|됐다|되고|되는|된|이다)", r"관측", r"보인다", r"듯하다",
    r"기대된다", r"우려된다", r"불가피", r"겠다",
    # 방향 · 평가
    r"호재", r"악재", r"긍정적", r"부정적", r"우호적", r"(?:상방|하방)\s*(?:압력|요인|재료|위험|리스크)", r"(?:상승|하락|강세|약세)\s*(?:요인|재료|압력)",
    r"부담(?:이다|으로|이\s*된|을\s*준)",
    # 광고 · 모집(digest_rules._AD도 함께 본다)
    r"리딩", r"무료", r"유료", r"선착순", r"구독", r"가입", r"문의", r"검색", r"텔레그램", r"카톡", r"카카오톡", r"오픈\s?채팅", r"유튜브", r"블로그",
    r"채널", r"입장\s*(?:링크|코드|가능)",
    # 지시문 꼴
    r"무시하", r"시스템", r"프롬프트", r"지시문", r"지시\s?사항", r"(?:이전|위|앞)의?\s*지시", r"명령어", r"출력하", r"설정\s?파일", r"비밀번호",
    r"토큰", r"API\s?키", r"ignore", r"system", r"prompt", r"instruction", r"assistant", r"jailbreak"))
# 누가 그렇게 봤다고 옮긴 것('…할 수 있다고 우려했다')은 사실이다 — 바로 뒤에 전하는 말(_SAID)이 올 때만 둔다
_QUOTABLE = tuple(re.compile(p) for p in (r"야\s*(?:한다|할|함|된다|하는)", r"필요하다", r"수\s*있다", r"가능성이\s*(?:높|크|있)"))
_SAID = re.compile(r"[가-힣]{0,3}고\s?(?:봤|보았|평가했|밝혔|말했|우려했|설명했|언급했|진단했|판단했|전했|강조했|지적했|주장했|적었)다")
_WILL = re.compile(r"([가-힣])\s?것(?:으로|이라는|이란)")                  # 앞 글자의 받침이 ㄹ이면 앞일이다('오를 것으로' — '오른 것으로'는 아니다)
_SOON = re.compile(r"연말|연내|내년|다음\s?(?:달|주|회의|분기)|당분간|앞으로|향후|조만간")     # 앞날을 가리키는 말 — 문장이 지난 일로 맺지 않으면 전망이다
_CHARS = re.compile(r"^[가-힣A-Za-z0-9 .,·%()~/+:&-]+$")             # 문장에 올 수 있는 글자 — 따옴표 · 꺾쇠 · @ · # · 줄바꿈은 없다
_END = re.compile(r"(.)\.(?= |$)")                                    # 문장을 맺는 마침표와 그 앞 글자
_DECIMAL = re.compile(r"(?<=[0-9])\.(?=[0-9])")
_LINKISH = re.compile(r"https?:|www\.|[A-Za-z0-9-]+\.[A-Za-z]{2,}", re.IGNORECASE)
_PHONE = re.compile(r"[0-9]{2,4}-[0-9]{3,4}-[0-9]{4}|[0-9]{%d,}" % TH["fact_digits_max"])
_NUM = re.compile(r"(?<![0-9.,A-Za-z])(?:[0-9]{1,3}(?:,[0-9]{3})+|[0-9]+)(?:\.[0-9]+)?")
# 숫자 뒤의 단위 — 기호 단위는 한 칸 띄어도 되고 한글 단위는 붙어 있어야 한다. 긴 것이 먼저. 여기 없는 것은 붙은 첫 글자를 단위로 본다
_UNITS = (("%p", r"\s?%\s?pt?|\s?%\s?포인트|\s?퍼센트\s?포인트"), ("%", r"\s?%|\s?퍼센트"), ("bp", r"\s?bps?|\s?베이시스\s?포인트"),
          ("년", "년물?"),                                               # 10년물 = 10년(만기)
          *((u, u) for u in ("조원", "조달러", "조", "억원", "억달러", "억", "만명", "천명", "명", "만계약", "계약", "달러", "원", "배",
                             "개월", "분기", "월", "일", "주", "차례", "차", "회", "번", "건", "개", "곳", "위", "시", "분")))
_UNIT = re.compile("|".join(f"(?P<u{i}>{p})" for i, (_, p) in enumerate(_UNITS)), re.IGNORECASE)
_TITLED = re.compile(r"((?:[가-힣A-Za-z]{2,12} )?[가-힣A-Za-z]{2,12}) ?" + TITLES + r"(?=[은는이가을를의와과도,. ]|$)")
_TOKEN = re.compile(r"[A-Za-z][A-Za-z0-9]*")
_HOUSE = re.compile(r"[가-힣A-Za-z]+(?:증권|리서치|자산운용)")


# ---------- 문장 검사 ----------

def names_of(sources):
    """출처 목록 → 문장에 나오면 안 되는 이름들(소문자): 채널 이름 · 라벨(4자 이상) · 라벨 속 하우스 이름(…증권 · …리서치)."""
    out = set()
    for c in sources["channels"]:
        out.add(c["handle"].casefold())
        out.update(x.casefold() for x in (c["label"], *_HOUSE.findall(c["label"])) if len(x) >= 4)
    return tuple(sorted(out))


def ok_form(fact):
    """형식 — 문자열 · 길이 · 정해 둔 글자. 올라가 있는 파일을 문장 규칙 없이 읽을 때(validate_picks plain=False)도 이것은 본다."""
    return isinstance(fact, str) and TH["fact_min_chars"] <= len(fact) <= TH["fact_chars"] and bool(_CHARS.fullmatch(fact))


def ok_shape(fact, names=()):
    """꼴 — 한국어 평서문 한두 문장, 정해 둔 글자만, 주소 · 전화 · 채널 이름 없음."""
    if not ok_form(fact) or fact != fact.strip() or "  " in fact:
        return False
    ends = _END.findall(fact)
    if not fact.endswith("다.") or set(ends) != {"다"} or len(ends) > TH["fact_sentences"] \
            or fact.count(".") != len(ends) + len(_DECIMAL.findall(fact)):
        return False
    letters = [c for c in fact if c.isalpha()]
    if sum("가" <= c <= "힣" for c in letters) < TH["fact_hangul_min"] * len(letters):
        return False
    low = fact.casefold()
    return not (_LINKISH.search(fact) or _PHONE.search(fact) or any(n in low for n in names))


def _jong(c):
    """한글 글자의 받침 번호(없으면 0, 한글이 아니면 -1) — ㄹ은 8, ㅆ은 20."""
    return (ord(c) - 0xAC00) % 28 if "가" <= c <= "힣" else -1


def ok_banned(fact):
    """금지 낱말 — 권유 · 전망 꼴 · 방향 평가 · 광고 · 지시문 꼴이 없다. 앞날을 가리키는 말이 든 문장은 지난 일로 맺어야 한다."""
    if not isinstance(fact, str) or any(p.search(fact) for p in (*_BANNED, *R._AD)):
        return False
    if any(not _SAID.match(fact, m.end()) for p in _QUOTABLE for m in p.finditer(fact)):
        return False
    if any(_jong(m.group(1)) == 8 for m in _WILL.finditer(fact)):
        return False
    return not any(_SOON.search(s) and _jong(s.rstrip()[-1]) != 20 for s in fact.split("다.") if s.strip())


def _flat(s):
    return "".join(c for c in R.norm_text(s).casefold() if c.isalnum())


def _stems(s):
    """어절마다 문장부호와 끝의 조사를 뗀 줄기들 — 조사만 바꾼 문장을 알아보는 데 쓴다(거칠지만 문장과 글에 똑같이 한다)."""
    out = []
    for w in map(_flat, R.norm_text(s).split()):
        m = _JOSA.search(w)
        while m and m.start() >= 2:
            w = w[:m.start()]
            m = _JOSA.search(w)
        out += [w] if w else []
    return out


def _covered(f, flats):
    """문장 글자 가운데 copy_piece자 이상 겹친 토막(어느 글의 것이든)에 덮인 글자 수."""
    n, i = 0, 0
    while i < len(f):
        k = 0
        while i + k < len(f) and any(f[i:i + k + 1] in t for t in flats):
            k += 1
        n, i = (n + k, i + k) if k >= TH["copy_piece"] else (n, i + 1)
    return n


def ok_copy(fact, texts):
    """베낌이 아니다 — 읽힌 글 하나와 연속 copy_run자 이상 겹치지 않고, 문장의 글자 n-gram이 한 글에 copy_ratio 이상 들어 있지 않고,
    조사를 뗀 어절 copy_stems개가 한 글과 같은 차례로 이어지지 않고, 여러 글에서 뜯은 긴 토막들이 문장의 copy_cover 이상을 덮지 않는다."""
    f, run, n, k = _flat(fact), TH["copy_run"], TH["copy_gram"], TH["copy_stems"]
    grams, flats, stems = [f[i:i + n] for i in range(len(f) - n + 1)], [_flat(t) for t in texts], _stems(fact)
    rows = {tuple(stems[i:i + k]) for i in range(len(stems) - k + 1)}
    for t, raw in zip(flats, texts):
        if any(f[i:i + run] in t for i in range(len(f) - run + 1)):
            return False
        if grams and sum(g in t for g in grams) >= TH["copy_ratio"] * len(grams):
            return False
        theirs = _stems(raw)
        if any(tuple(theirs[i:i + k]) in rows for i in range(len(theirs) - k + 1)):
            return False
    return not f or _covered(f, flats) < TH["copy_cover"] * len(f)


def _unit(line, at):
    """숫자 바로 뒤(at)의 단위 → (맞춘 꼴, 끝 자리). 아는 단위가 없으면 붙은 첫 한글 글자(조사면 없음)나 영문 토막, 그것도 없으면 빈 글자."""
    m = _UNIT.match(line, at)
    if m:
        return next(_UNITS[i][0] for i in range(len(_UNITS)) if m.group(f"u{i}") is not None), m.end()
    tail = line[at:at + 1]
    if "가" <= tail <= "힣":
        return ("" if tail in "은는이가을를의에로과와도만" else tail), at
    word = re.match(r"[A-Za-z]+", line[at:])
    return (word.group(0).casefold(), at + word.end()) if word else ("", at)


def _nums(line):
    """한 줄의 숫자들 → [(값, 음수인가, 단위, 앞에 붙은 꼬리표들, 시작, 끝)]. 값은 쉼표 · 끝자리 0을 뗀 꼴, 꼬리표는 앞 숫자 뒤부터
    num_ctx_chars자 안의 것, 끝은 단위까지."""
    out, prev = [], 0
    for m in _NUM.finditer(line):
        a = m.start()
        whole, _, frac = m.group(0).replace(",", "").partition(".")
        frac = frac.rstrip("0")
        neg = a > 0 and line[a - 1] in "-−" and (a < 2 or not (line[a - 2].isalnum() or line[a - 2] in "%)"))
        near = line[max(prev, a - TH["num_ctx_chars"]):a]
        unit, end = _unit(line, m.end())
        out.append((str(int(whole)) + ("." + frac if frac else ""), neg, unit, frozenset(q for q in QUALIFIERS if q in near), a, end))
        prev = m.end()
    return out


def _ordered(fact, nums):
    """'A로 B를 웃돌았다 · B보다 낮았다' — 같은 문장에서 B 앞의 같은 단위 숫자 A와 크기를 견줘 그 말과 맞는가."""
    for i, (v, neg, unit, _, a, end) in enumerate(nums):
        m = _CMP.match(fact, end)
        before = [x for x in nums[:i] if x[2] == unit and x[4] > fact.rfind("다. ", 0, a)]
        if m and before:
            x, y = (float(n[0]) * (-1 if n[1] else 1) for n in (before[-1], nums[i]))
            if x == y or (x > y) != (m.group(1) in ("웃돌", "웃돈", "상회", "높")):
                return False
    return True


def ok_number(fact, texts):
    """숫자 대조 — 문장의 숫자마다, 읽힌 글의 어느 줄에 같은 숫자가 같은 단위 · 같은 꼬리표로 있다. 두 숫자를 견준 말은 크기와 맞는다."""
    seen = {}
    for t in texts:
        for line in t.split("\n"):
            for v, neg, unit, tags, _, _ in _nums(R.norm_text(line)):
                seen.setdefault(v, []).append((neg, unit, tags))
    mine = _nums(fact)
    return _ordered(fact, mine) and all(any((tneg or not neg) and tunit == unit and ttags == tags for tneg, tunit, ttags in seen.get(v, ()))
                                        for v, neg, unit, tags, _, _ in mine)


def _vocab(item, texts):
    """그 항목에서 써도 되는 사전 낱말 — 항목의 낱말 · 함께 나온 낱말, 그리고 읽힌 글의 낱말. 읽힌 채널이 둘 이상이면 주제를 정하는
    낱말(A · B급)은 두 채널 이상이 쓴 것만 받는다(글 하나가 주제를 넓히지 못하게 — '금리' 같은 C급 낱말은 한 글에만 있어도 된다).
    item에 src가 없으면 글마다 다른 채널로 본다."""
    src = item.get("src") or ()
    chans = [s[0] for s in src] if len(src) == len(texts) else list(range(len(texts)))
    by = {}
    for ch, t in zip(chans, texts):
        for h in R.match_terms(t):
            by.setdefault(h["term"], set()).add(ch)
    need = 2 if len(set(chans)) >= 2 else 1
    return set(item.get("terms", ())) | {w["term"] for w in item.get("words", ())} | {t for t, who in by.items() if len(who) >= need or R.grade_of(t) == "C"}


def _decided(fact, texts):
    """문장이 결정으로 쓴 것(인하했다 · 기준금리를 내렸다)이 읽힌 글에도 결정으로 적혀 있는가 — 뒤에 소수의견 · 기대 같은 말이 붙은 자리는 세지 않는다."""
    for word, verbs in DECIDE.items():
        if re.search(rf"{word}(?:했|됐|하기로|[을를]\s*(?:결정|단행))|(?:기준|정책)\s?금리{_GAP}(?:{verbs})", fact):
            there = re.compile(rf"{word}|금리{_GAP}(?:{verbs})")
            if not any(not _HEDGE.match(t, m.end()) for t in texts for m in there.finditer(t)):
                return False
    return True


def ok_term(fact, item, texts):
    """낱말 — 문장의 사전 낱말이 그 항목 · 읽힌 글의 것이고, 결과 · 방향 · 결정 · 수량을 글과 다르게 쓰지 않았다."""
    allowed = _vocab(item, texts)
    if any(not R.covered(h["term"], allowed) for h in R.match_terms(fact)):
        return False
    seen = {r["result"] for t in texts for r in R.match_results(t)}
    said = {r["result"] for r in R.match_results(fact)}
    if any(w not in seen and (w in ALONE or OPPOSITE.get(w) in seen) for w in said):
        return False
    whole = "\n".join(texts)
    if any(mine.search(fact) and not mine.search(whole) and other.search(whole) for mine, other in ((_UP, _DOWN), (_DOWN, _UP))):
        return False
    return _decided(fact, texts) and not any(q in fact and q not in whole for q in QUANT)


def ok_name(fact, item, texts):
    """이름 — 직함 앞의 이름(두 토막까지)과 영문 토막(대소문자 · 숫자가 붙었든)이 읽힌 글에 있다. 그 항목 낱말의 토막 · 숫자의 단위는 된다."""
    flat = "".join(map(_flat, texts))
    words = {w.casefold() for t in _vocab(item, texts) for w in t.split()}
    known = lambda w: w.casefold() in words or _flat(w) in flat or (w.endswith("의") and _flat(w[:-1]) in flat)
    for m in _TITLED.finditer(fact):
        *far, near = m.group(1).split(" ")
        if near not in NOT_NAMES and not known(near):
            return False
        if any(w not in NOT_NAMES and not _PARTICLE_END.search(w) and not known(w) for w in far):
            return False
    return all(known(w) for w in _TOKEN.findall(fact) if len(w) > 1 and w.casefold() not in UNIT_WORDS)


def fact_checks(fact, item, texts, names=()):
    """검사마다의 결과 {사유: 통과했는가} — 순서는 CHECKS. 문자열이 아니면 모두 거짓."""
    if not isinstance(fact, str):
        return {c: False for c in CHECKS}
    return {"shape": ok_shape(fact, names), "banned": ok_banned(fact), "copy": ok_copy(fact, texts), "number": ok_number(fact, texts),
            "term": ok_term(fact, item, texts), "name": ok_name(fact, item, texts)}


def fact_code(fact, item, texts, names=()):
    """문장을 버릴 사유(먼저 걸린 것 하나) — 실어도 되면 None. item = 판의 항목(terms · words), texts = 그 항목에서 읽힌 글들."""
    if fact is None:
        return "none"
    return next((c for c, ok in fact_checks(fact, item, texts, names).items() if not ok), None)


def fact_plain(fact, names=()):
    """원문 없이 도는 검사 — 꼴과 금지 낱말. 걸리면 사유, 아니면 None."""
    return "shape" if not ok_shape(fact, names) else None if ok_banned(fact) else "banned"


# ---------- 파일의 형태 ----------

def basis(date, asked):
    """무엇을 물었는가의 지문(sha256 앞 16자리) — 판 날짜 + 항목의 열쇠와 읽힌 글. 같으면 다시 묻지 않는다. 항목의 순서는 보지 않는다."""
    rows = sorted([a["key"], [[ch, n] for ch, n in a["src"]]] for a in asked)
    return hashlib.sha256(json.dumps([date, rows], ensure_ascii=True, separators=(",", ":")).encode("ascii")).hexdigest()[:16]


def picks_doc(date, at, model, asked, facts, dropped=None):
    """물은 항목(asked: [{key, id, src}])과 검사를 통과한 문장({key: fact}) → 파일의 자료. 통과하지 못한 항목은 사유별 개수만 남는다."""
    items = [{"key": a["key"], "id": a["id"], "src": [[ch, n] for ch, n in a["src"]], "fact": facts[a["key"]]}
             for a in asked if a["key"] in facts]
    return {"schema": S.SCHEMA, "date": date, "made_at": at, "mode": MODE, "model": model, "basis": basis(date, asked),
            "items": items, "dropped": {c: int((dropped or {}).get(c, 0)) for c in CODES}}


def blank_picks(date, at):
    """문장이 하나도 없는 파일 — 물을 것이 없던 날, 판을 내린 날(전날 문장이 남지 않게)."""
    return picks_doc(date, at, None, [], {})


def _keys(v, path, names):
    if type(v) is not dict:
        S._fail(path, "객체가 아님")
    if set(v) != set(names):
        S._fail(path, "칸이 빠졌거나 정해지지 않은 칸이 있음")


def _item(x, path, date, roles, names, plain=True):
    _keys(x, path, ("key", "id", "src", "fact"))
    S._re(S.KEY_RE, "열쇠 꼴이 아님")(x["key"], f"{path}.key")
    S._re(S.ID_RE, "항목 id 꼴이 아님")(x["id"], f"{path}.id")
    if x["id"][:8] != date.replace("-", ""):
        S._fail(f"{path}.id", "id의 날짜가 판 날짜와 다름")
    src = x["src"]
    if type(src) is not list or not 1 <= len(src) <= TH["llm_posts_max"]:
        S._fail(f"{path}.src", "읽힌 글이 없거나 너무 많음")
    for i, s in enumerate(src):
        if type(s) is not list or len(s) != 2:
            S._fail(f"{path}.src[{i}]", "[채널, 글 번호] 꼴이 아님")
        S._re(S.HANDLE_RE, "채널 이름 꼴이 아님")(s[0], f"{path}.src[{i}]")
        S._int(1, S.MAX_POST)(s[1], f"{path}.src[{i}]")
        if roles is not None and roles.get(s[0]) not in READ:
            S._fail(f"{path}.src[{i}]", "채권 · 애널 원천 채널의 글이 아님")
    S._unique([tuple(s) for s in src], f"{path}.src", "읽힌 글")
    if fact_plain(x["fact"], names) if plain else not ok_form(x["fact"]):
        S._fail(f"{path}.fact", "문장이 꼴이나 금지 낱말 검사에 걸림")


def validate_picks(d, sources=None, plain=True):
    """data/digest_picks.json의 자료. sources(sources.json)를 주면 읽힌 글이 채권 · 애널 원천 채널의 것인지, 문장에 채널 이름 · 라벨이
    없는지도 본다. plain=False면 문장은 형식(문자열 · 길이 · 글자)만 본다 — 올라간 뒤에 문장 규칙이 조여져도 읽을 수 있게(CI의 올라간
    파일 테스트가 쓴다 — 요약 층이 규칙판의 문이 되지 않게). 틀리면 ValueError — 어느 칸이 왜만(값은 싣지 않는다)."""
    _keys(d, "picks", ("schema", "date", "made_at", "mode", "model", "basis", "items", "dropped"))
    S._is(S.SCHEMA)(d["schema"], "picks.schema")
    S._is(MODE)(d["mode"], "picks.mode")
    S._date(d["date"], "picks.date")
    S._iso(d["made_at"], "picks.made_at")
    S._null(S._re(MODEL_RE, "모델 이름 꼴이 아님"))(d["model"], "picks.model")
    S._re(S.SHA_RE, "지문 꼴이 아님")(d["basis"], "picks.basis")
    if type(d["items"]) is not list or len(d["items"]) > TH["llm_items_max"]:
        S._fail("picks.items", "목록이 아니거나 너무 많음")
    roles = None if sources is None else {c["handle"]: (c["group"], c["role"]) for c in sources["channels"]}
    names = () if sources is None else names_of(sources)
    for i, x in enumerate(d["items"]):
        _item(x, f"picks.items[{i}]", d["date"], roles, names, plain)
    S._unique([x["key"] for x in d["items"]], "picks.items", "항목의 열쇠")
    _keys(d["dropped"], "picks.dropped", CODES)
    for c in CODES:
        S._int(0, TH["llm_items_max"])(d["dropped"][c], f"picks.dropped.{c}")
    if len(d["items"]) + sum(d["dropped"].values()) > TH["llm_items_max"]:
        S._fail("picks.dropped", "실린 것과 버린 것이 물을 수 있는 수보다 많음")
    if len(S.dump(d).encode("utf-8")) > TH["picks_bytes_max"]:
        S._fail("picks", "크기 상한을 넘음")
    return d


def read_picks(path, sources=None, plain=True):
    """파일을 읽어 검증한 자료 — 없거나 깨졌거나 형식이 아니면 None(없는 셈 친다)."""
    try:
        return validate_picks(S.read_json(path), sources, plain)
    except (OSError, ValueError, TypeError, KeyError, AttributeError):
        return None


def write_picks(path, d, sources=None):
    """검증한 뒤에만 쓴다(원자적 교체)."""
    S.write_json(path, validate_picks(d, sources))


def same_basis(picks, date, asked):
    """올라가 있는 파일이 같은 판 날짜 · 같은 항목 · 같은 글로 만든 것인가 — 그러면 다시 묻지 않는다."""
    try:
        validate_picks(picks)
    except (ValueError, TypeError, KeyError, AttributeError):
        return False
    return picks["date"] == date and picks["basis"] == basis(date, asked)


# ---------- 화면이 문장을 붙이는 규칙 ----------

def items_of(digest):
    return list(digest.get("must", [])) + [x for g in digest.get("rest", []) for x in g["items"]]


def attach(digest, picks, sources=None):
    """판과 요약 층 → {항목의 열쇠: 문장}. 화면(site/evening.js)이 지키는 규칙의 파이썬 판이다: 파일이 형식에 맞고, 판 날짜가 같고,
    내린 판이 아니고, 열쇠가 그 판의 항목에 있고, 읽힌 글이 그 항목 링크의 부분집합일 때만 붙인다. id로는 잇지 않는다
    (씨앗 글로 만든 값이라 같은 판을 다시 계산하면 달라질 수 있다)."""
    try:
        validate_picks(picks, sources)
    except (ValueError, TypeError, KeyError, AttributeError):
        return {}
    if digest.get("status") == "withdrawn" or picks["date"] != digest.get("date"):
        return {}
    links = {x["key"]: {ln["url"] for ln in x["links"]} for x in items_of(digest)}
    return {p["key"]: p["fact"] for p in picks["items"]
            if p["key"] in links and {S.post_url(ch, n) for ch, n in p["src"]} <= links[p["key"]]}
