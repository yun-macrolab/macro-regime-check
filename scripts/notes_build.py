#!/usr/bin/env python3
"""읽기 노트 — notes/*.md(제한된 마크다운) → <out>/notes.json (2026-10-08 추가).

노트는 읽은 글을 내 말로 옮긴 공부 기록이다. 번역·전재가 아니다 — 원문의 문장·그림·표는 싣지 않고 링크로만 잇는다.
사이트(site/notes.js)는 이 JSON만 읽는다. 여기서 블록 배열로 미리 풀어 두므로 화면은 글자를 HTML로 해석하지 않는다.

받는 문법은 아래가 전부다. 그 밖의 것(원시 HTML, 인용문 >, 코드, 그림 ![…], 기울임, 맨 주소, https가 아닌 링크,
보이지 않는 글자(폭 없는 공백·방향을 뒤집는 글자 등), 모르는 지시 줄·펜스 등)은 조용히 넘기지 않고 파일 이름·줄 번호와 함께
멈춘다(test_notes_build.py가 강제).
  머리말  첫 줄 --- 부터 다음 --- 까지 '이름: 값' — 제목 · 날짜 · 출처 · 원문 제목 · 원문 주소 · 저자 · 발행일 ·
          읽는 시간(분) · 난이도 · 한 줄 결론. 열 개가 모두 있어야 하고 다른 이름은 받지 않는다.
          값을 큰따옴표로 감싸도 된다(감싼 따옴표는 뗀다) — 값이 **로 시작하거나 ': '가 들어 있으면 감싸 둔다
          (GitHub이 머리말을 YAML로 읽어 표로 보여 주는데, 그런 값은 따옴표가 없으면 YAML 오류 상자가 뜬다)
  제목    '## 글', '### 글'
  문단    이어 쓴 줄은 한 문단
  목록    '- 글' 또는 '1. 글'(1부터 차례로). 두 칸 들여 쓴 줄은 앞 항목에 잇는다. 목록 안의 목록은 없다.
          항목 사이에 빈 줄을 두지 않는다(두면 한 항목짜리 목록 여러 개가 되므로 멈춘다)
  표      '| 가 | 나 |' + 둘째 줄 '|---|---|' + 한 줄 이상
  글 안   **굵게**, [글](https://…)
  그림    '::사이트그래프 <규칙 키> | 캡션'   data/charts.json의 규칙 그래프(매일 갱신되는 사이트 자료)
          '::정적그래프 <그래프 키> | 캡션'   data/notes_charts.json의 그래프(받아 둔 값 — scripts/notes_charts.py)
          도식 펜스(백틱 셋 + '도식')       JSON으로 적은 개념도(kind: balance — 0선을 사이에 둔 힘 겨루기). 화면이 직접 그린다
  질문    '::질문' 아래 번호 목록 3개 — 글마다 한 번

파일 이름은 YYYY-MM-DD-영문-소문자.md이고 날짜는 머리말의 날짜와 같아야 한다(이름에서 .md를 뗀 것이 글 주소 #notes/<이름>).
노트 폴더 바로 아래의 .md만 읽는다. 폴더가 없거나 확장자를 달리 적은 글(.MD · .markdown)이 있으면 멈춘다.

산출: <out>/notes.json — {schema, notes: [최근 글부터 {slug, title, date, source, minutes, level, summary, blocks}]}
      같은 입력이면 같은 바이트(만든 시각을 싣지 않는다). test_notes_build.py가 저장된 파일과 다시 만든 것을 비교한다.
사용법: python notes_build.py [--notes notes] [--out data] [--check]
"""
import os, re, sys, json, argparse, datetime, unicodedata

SCHEMA = 1
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_NOTES = os.path.join(REPO, "notes")
DEFAULT_OUT = os.path.join(REPO, "data")
QUESTIONS = 3                     # 노트의 꼴: 질문 3개
TAG_WIDTH = 10                    # 도식 꼬리표의 폭 한도(한글·한자 2, 그 밖 1) — 그림 속 글자라 길면 칸 밖으로 나간다
HEAD = (("제목", "title"), ("날짜", "date"), ("출처", "source_name"), ("원문 제목", "source_title"),
        ("원문 주소", "source_url"), ("저자", "authors"), ("발행일", "published"), ("읽는 시간", "minutes"),
        ("난이도", "level"), ("한 줄 결론", "summary"))
DIRS = ("up", "down", "both")     # 도식의 힘이 미는 쪽
SPOTS = ("above", "zero", "below")  # 도식에서 합친 값이 놓이는 자리

SLUG = re.compile(r"(\d{4}-\d{2}-\d{2})-[a-z0-9]+(?:-[a-z0-9]+)*")
URL = re.compile(r"https://[A-Za-z0-9.-]+(?::\d+)?(?:/[^\s()<>\"'`\\]*)?")
LINK = re.compile(r"\[([^\[\]]+)\]\(([^()\s]*)\)")
ITEM = re.compile(r"(-|\d+\.) +(\S.*)")
FIGURE = re.compile(r"::(사이트그래프|정적그래프) +([a-z0-9_]{1,40}) *\| *(\S.*)")
RULE = re.compile(r"(?:=+|-{3,}|\*{3,}|_{3,})\s*")
# 글 안에서 받지 않는 것 — 마크다운·HTML로는 뜻이 있지만 이 빌더는 풀지 않는 문법
REJECT = (
    (re.compile(r"[\x00-\x1f\x7f]"), "탭·제어 문자는 받지 않는다"),
    (re.compile(r"`"), "코드(백틱)는 받지 않는다"),
    (re.compile(r"\\"), "역슬래시는 받지 않는다"),
    (re.compile(r"<[A-Za-z/!?]"), "원시 HTML은 받지 않는다"),
    (re.compile(r"&#?[A-Za-z0-9]+;"), "HTML 엔티티는 받지 않는다 — 글자를 그대로 쓴다"),
    (re.compile(r"~~"), "취소선은 받지 않는다"),
    (re.compile(r"https?:|ftp:|www\.", re.I), "맨 주소는 받지 않는다 — [글](https://…)로 쓴다"),
    (re.compile(r"\]\(|\]\["), "링크 모양이 어긋났다 — [글](https://…)만 받는다"),
    (re.compile(r"\*"), "기울임(*…*)·별표 하나는 받지 않는다"),
    (re.compile(r"(?<![A-Za-z0-9])_[^_\s](?:[^_]*[^_\s])?_(?![A-Za-z0-9])"), "기울임(_…_)은 받지 않는다"),
)


class NoteError(ValueError):
    """노트 원본이 받는 문법을 벗어났다 — 어느 파일 몇째 줄인지 함께 알린다."""

    def __init__(self, line, reason, name=None):
        self.line, self.reason, self.name = line, reason, name
        super().__init__(f"{name or '노트'} {line}째 줄: {reason}" if line else f"{name or '노트'}: {reason}")


# ---------- 글 안 문법 ----------

def _hidden(text):
    """보이지 않는 글자(유니코드 범주 Cc 제어 · Cf 서식 — 폭 없는 공백, 방향을 뒤집는 글자, 글 가운데의 BOM 등)가
    있으면 그 이름(U+XXXX), 없으면 None. 눈에 안 보여 원본과 화면이 달라지고, 주소에 섞이면 다른 주소처럼 보인다."""
    return next((f"U+{ord(c):04X}" for c in text if unicodedata.category(c) in ("Cc", "Cf")), None)


def _check(text, line):
    for pattern, reason in REJECT:
        if pattern.search(text):
            raise NoteError(line, reason)
    if _hidden(text):
        raise NoteError(line, f"보이지 않는 글자({_hidden(text)})는 받지 않는다")


def _address(url):
    """링크로 걸 수 있는 주소인가 — https://… 꼴이고 보이지 않는 글자가 섞이지 않았다."""
    return bool(URL.fullmatch(url)) and not _hidden(url)


def _piece(text, bold, href=None):
    return {"text": text, **({"bold": True} if bold else {}), **({"href": href} if href else {})}


def _links(part, bold, line):
    """굵게 안팎의 한 토막 → 조각들. 링크는 https 주소만."""
    out, pos = [], 0
    for m in LINK.finditer(part):
        label, url = m.group(1).strip(), m.group(2)
        if not label or not _address(url):
            raise NoteError(line, "링크는 [글](https://…)만 받는다")
        _check(part[pos:m.start()] + label, line)
        out += ([_piece(part[pos:m.start()], bold)] if m.start() > pos else []) + [_piece(label, bold, url)]
        pos = m.end()
    _check(part[pos:], line)
    return out + ([_piece(part[pos:], bold)] if pos < len(part) else [])


def inline(text, line=0):
    """글 안 문법 → 조각 목록 [{text, bold?, href?}]. 굵게 안에 링크는 되고, 굵게를 겹쳐 쓰지는 못한다."""
    if "![" in text:                              # 링크로 읽히기 전에 — 그림은 지시 줄로만 넣는다
        raise NoteError(line, "그림(![…])은 받지 않는다 — 그림 지시 줄을 쓴다")
    parts = text.split("**")
    if len(parts) % 2 == 0:
        raise NoteError(line, "굵게(**)가 닫히지 않았다")
    out = []
    for i, part in enumerate(parts):
        if i % 2 and not part.strip():
            raise NoteError(line, "빈 굵게(** **)")
        out += _links(part, i % 2 == 1, line)
    return out


def plain(text, line=0, limit=120):
    """꾸밈없는 한 줄(제목·이름 등) — 굵게·링크가 섞였거나 너무 길면 멈춘다."""
    pieces = inline(text, line)
    if len(pieces) != 1 or set(pieces[0]) != {"text"}:
        raise NoteError(line, "여기에는 굵게·링크를 쓰지 않는다")
    if len(text) > limit:
        raise NoteError(line, f"{limit}자를 넘는다")
    return text


# ---------- 머리말 ----------

def _day(value, line):
    try:
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
            raise ValueError
        return datetime.date.fromisoformat(value).isoformat()
    except ValueError:
        raise NoteError(line, "날짜는 YYYY-MM-DD") from None


def _head(raw, slug):
    """머리말에서 읽은 {이름: (줄, 값)} → 노트의 머리 dict."""
    def text(key, limit=120):
        return plain(raw[key][1], raw[key][0], limit)
    line, url = raw["source_url"]
    if not _address(url):
        raise NoteError(line, "원문 주소는 https://… 여야 한다")
    line, minutes = raw["minutes"]
    if not re.fullmatch(r"[1-9]\d{0,2}", minutes):
        raise NoteError(line, "읽는 시간은 분 단위 숫자(1~999)")
    line, summary = raw["summary"]
    if len(summary) > 400:
        raise NoteError(line, "한 줄 결론이 400자를 넘는다")
    date = _day(raw["date"][1], raw["date"][0])
    if date != slug[:10]:
        raise NoteError(raw["date"][0], "날짜가 파일 이름의 날짜와 다르다")
    return {"slug": slug, "title": text("title", 80), "date": date,
            "source": {"name": text("source_name"), "title": text("source_title", 200), "url": url,
                       "authors": text("authors"), "published": _day(raw["published"][1], raw["published"][0])},
            "minutes": int(minutes), "level": text("level"), "summary": inline(summary, line)}


def parse_head(lines, slug):
    """머리말(--- … ---) → (노트의 머리 dict, 본문이 시작하는 줄의 위치)."""
    if not lines or lines[0].strip() != "---":
        raise NoteError(1, "첫 줄은 머리말을 여는 --- 여야 한다")
    end = next((i for i in range(1, len(lines)) if lines[i].strip() == "---"), None)
    if end is None:
        raise NoteError(1, "머리말을 닫는 --- 가 없다")
    names, raw = dict(HEAD), {}
    for no, line in enumerate(lines[1:end], 2):
        if not line.strip():
            continue
        name, sep, value = line.partition(":")
        key = names.get(name.strip())
        if not sep or key is None:
            raise NoteError(no, "머리말이 받지 않는 줄 — " + " · ".join(n for n, _ in HEAD))
        if key in raw:
            raise NoteError(no, f"'{name.strip()}'이 두 번 나온다")
        value = value.strip()
        if len(value) > 1 and value[0] == value[-1] == '"':      # 감싼 큰따옴표는 뗀다
            value = value[1:-1].strip()
        if not value:
            raise NoteError(no, f"'{name.strip()}'의 값이 비었다")
        raw[key] = (no, value)
    missing = [n for n, k in HEAD if k not in raw]
    if missing:
        raise NoteError(end + 1, "머리말에 빠진 이름: " + ", ".join(missing))
    return _head(raw, slug), end + 1


# ---------- 본문 블록 ----------

def _heading(lines, i):
    m = re.fullmatch(r"(#{2,3}) +(\S.*)", lines[i].rstrip())
    if not m:
        raise NoteError(i + 1, "제목은 '## 글'과 '### 글'만 받는다")
    return {"type": "heading", "level": len(m.group(1)), "text": plain(m.group(2), i + 1)}, i + 1


def _list(lines, i):
    """'- 글' 또는 '1. 글' 목록 한 덩어리(빈 줄에서 끝난다)."""
    ordered, items, j = lines[i][0] != "-", [], i
    while j < len(lines) and lines[j].strip():
        m = ITEM.fullmatch(lines[j].rstrip())
        if m and (m.group(1) != "-") != ordered:
            raise NoteError(j + 1, "한 목록에 '-'와 번호를 섞지 않는다")
        if m and ordered and int(m.group(1)[:-1]) != len(items) + 1:
            raise NoteError(j + 1, "번호는 1부터 차례로 쓴다")
        if m:
            items = items + [(j + 1, m.group(2))]
        elif items and re.match(r" {2,}\S", lines[j]) and not ITEM.fullmatch(lines[j].strip()):
            items = items[:-1] + [(items[-1][0], items[-1][1] + " " + lines[j].strip())]
        elif not items:
            raise NoteError(j + 1, "'-'·'+'·'숫자.'로 시작하는 줄은 목록으로 읽는다 — 목록은 '- 글'과 '1. 글'만 받는다")
        else:
            raise NoteError(j + 1, "목록의 줄이 아니다 — 목록 안의 목록은 없고, 목록 뒤에는 빈 줄을 둔다")
        j += 1
    k = next((k for k in range(j, len(lines)) if lines[k].strip()), len(lines))      # 빈 줄 다음의 첫 줄
    m = ITEM.fullmatch(lines[k].rstrip()) if j < k < len(lines) else None
    if m and (m.group(1) != "-") == ordered:        # 같은 종류의 항목이 이어진다 — 조용히 한 항목짜리 목록 여러 개로 만들지 않는다
        raise NoteError(k + 1, "목록 항목 사이에는 빈 줄을 두지 않는다")
    return {"type": "list", "ordered": ordered, "items": [inline(text, no) for no, text in items]}, j


def _cells(line, no):
    s = line.strip()
    if not (len(s) > 1 and s.startswith("|") and s.endswith("|")):
        raise NoteError(no, "표의 줄은 |로 시작해 |로 끝난다")
    return [c.strip() for c in s[1:-1].split("|")]


def _table(lines, i):
    j = i
    while j < len(lines) and lines[j].startswith("|"):
        j += 1
    rows = [_cells(lines[k], k + 1) for k in range(i, j)]
    if len(rows) < 3 or not all(re.fullmatch(r":?-+:?", c) for c in rows[1]):
        raise NoteError(i + 2, "표는 머리 줄, 둘째 줄 |---|---|, 그 아래 한 줄 이상")
    for k, row in enumerate(rows):
        if len(row) != len(rows[0]):
            raise NoteError(i + k + 1, f"칸 수가 머리 줄({len(rows[0])}칸)과 다르다")
    def cells(k):
        return [inline(c, i + k + 1) if c else [] for c in rows[k]]
    return {"type": "table", "head": cells(0), "rows": [cells(k) for k in range(2, len(rows))]}, j


def _questions(lines, i):
    j = i + 1
    while j < len(lines) and not lines[j].strip():
        j += 1
    if j >= len(lines) or not lines[j].startswith("1. "):
        raise NoteError(i + 1, "::질문 아래에는 번호 목록이 온다")
    block, end = _list(lines, j)
    if len(block["items"]) != QUESTIONS:
        raise NoteError(j + 1, f"질문은 {QUESTIONS}개")
    return {"type": "questions", "items": block["items"]}, end


def _directive(lines, i):
    line = lines[i].rstrip()
    if line == "::질문":
        return _questions(lines, i)
    m = FIGURE.fullmatch(line)
    if not m:
        raise NoteError(i + 1, "모르는 지시 줄 — '::사이트그래프 키 | 캡션' · '::정적그래프 키 | 캡션' · '::질문'")
    kind, field = ("site_chart", "rule") if m.group(1) == "사이트그래프" else ("static_chart", "chart")
    return {"type": "figure", "kind": kind, field: m.group(2), "caption": inline(m.group(3), i + 1)}, i + 1


def _once(pairs):
    """JSON 객체 하나의 (이름, 값)들 → dict. 같은 이름이 두 번 나오면 멈춘다(뒤 것이 조용히 이기지 않게)."""
    names = [k for k, _ in pairs]
    twice = next((k for k in names if names.count(k) > 1), None)
    if twice is not None:
        raise ValueError(f"도식의 JSON에 이름 '{twice[:20]}'이 두 번 나온다")
    return dict(pairs)


def _fence(lines, i):
    if lines[i].rstrip() != "```도식":
        raise NoteError(i + 1, "펜스는 도식만 받는다(코드 블록은 없다)")
    end = next((j for j in range(i + 1, len(lines)) if lines[j].rstrip() == "```"), None)
    if end is None:
        raise NoteError(i + 1, "도식 펜스가 닫히지 않았다")
    try:
        raw = json.loads("\n".join(lines[i + 1:end]), object_pairs_hook=_once)
    except json.JSONDecodeError as e:                 # 펜스를 연 줄이 아니라 JSON이 틀린 그 줄을 알린다
        raise NoteError(i + 1 + e.lineno, f"도식의 JSON을 읽을 수 없다({e.msg})") from None
    except RecursionError:
        raise NoteError(i + 1, "도식의 JSON이 너무 깊게 겹쳤다") from None
    except ValueError as e:                           # _once가 알린 것
        raise NoteError(i + 1, str(e)) from None
    return {"type": "figure", "kind": "diagram", "diagram": diagram(raw, i + 1)}, end + 1


def _reader(line):
    """이 줄에서 시작하는 블록을 읽는 함수 — 문단이면 None."""
    if line.startswith("```"):
        return _fence
    if line.startswith("::"):
        return _directive
    if line.startswith("#"):
        return _heading
    if line.startswith("|"):
        return _table
    if re.match(r"[-+]|\d+\. ", line) and not RULE.fullmatch(line):
        return _list
    return None


def _para(lines, i):
    j, parts = i, []
    while j < len(lines) and lines[j].strip() and (j == i or _reader(lines[j]) is None):
        if lines[j][0] in " \t>" or RULE.fullmatch(lines[j]):
            raise NoteError(j + 1, "문단의 줄이 아니다 — 들여쓰기·인용문(>)·가로줄·밑줄 제목은 받지 않는다")
        parts.append(lines[j].strip())
        j += 1
    return {"type": "para", "spans": inline(" ".join(parts), i + 1)}, j


def parse_blocks(lines, start):
    """본문 줄 → 블록 목록. 빈 줄이 블록을 가른다."""
    blocks, i = [], start
    while i < len(lines):
        if not lines[i].strip():
            i += 1
            continue
        block, i = (_reader(lines[i]) or _para)(lines, i)
        blocks.append(block)
    return blocks


# ---------- 도식 선언 ----------

def _pick(raw, line, what, required, optional=()):
    """dict에 정해 둔 이름만 있는지 본다 — 빠졌거나 모르는 이름이 있으면 멈춘다."""
    if not isinstance(raw, dict) or not set(required) <= set(raw) <= set(required) | set(optional):
        raise NoteError(line, f"도식의 {what}: 이름이 다르다 — 있어야 하는 것 {', '.join(required)}"
                        + (f" · 있어도 되는 것 {', '.join(optional)}" if optional else ""))
    return raw


def _label(value, line, limit=80):
    if not isinstance(value, str) or not value.strip():
        raise NoteError(line, "도식의 글은 비지 않은 문자열")
    return plain(value.strip(), line, limit)


def _items(value, line, what, low, high):
    if not isinstance(value, list) or not low <= len(value) <= high:
        raise NoteError(line, f"도식의 {what}: {low}~{high}개짜리 목록")
    return value


def _one_of(value, allowed, line, what):
    if type(value) not in (str, int) or value not in allowed:
        raise NoteError(line, f"도식의 {what}: {' · '.join(map(str, allowed))} 중 하나")
    return value


def _tag(value, line):
    """합이 놓이는 자리에 붙는 꼬리표 — 그림 속 글자라 폭을 대강 잰다(한글·한자 2, 그 밖 1)."""
    tag = _label(value, line, 10)
    if sum(2 if unicodedata.east_asian_width(c) in "WF" else 1 for c in tag) > TAG_WIDTH:
        raise NoteError(line, "도식의 꼬리표(tag)는 한글 5자(영문·숫자 10자)까지 — 길면 칸 밖으로 나간다")
    return tag


def _force(raw, line):
    f = _pick(raw, line, "forces 항목", ("key", "label", "short", "effect"))
    if not isinstance(f["key"], str) or not re.fullmatch(r"[a-z][a-z0-9_]{0,19}", f["key"]):
        raise NoteError(line, "도식의 힘 key는 영문 소문자·숫자·밑줄")
    return {"key": f["key"], "label": _label(f["label"], line, 40), "short": _label(f["short"], line, 12),
            "effect": _label(f["effect"], line, 40)}


def _column(raw, keys, line):
    c = _pick(raw, line, "columns 항목", ("label", "forces", "net"), ("highlight",))
    forces = []
    for f in _items(c["forces"], line, "칸의 forces", 0, len(keys)):
        f = _pick(f, line, "칸의 힘", ("key", "dir", "size", "note"))
        if f["key"] not in keys or f["key"] in [x["key"] for x in forces]:
            raise NoteError(line, "도식의 칸: 머리의 forces에 적은 힘을 한 번씩만 쓴다")
        forces.append({"key": f["key"], "dir": _one_of(f["dir"], DIRS, line, "dir"),
                       "size": _one_of(f["size"], (1, 2, 3), line, "size"), "note": _label(f["note"], line, 60)})
    net = []
    for n in _items(c["net"], line, "칸의 net", 1, 2):
        n = _pick(n, line, "칸의 net 항목", ("pos", "note"), ("tag",))
        net.append({"pos": _one_of(n["pos"], SPOTS, line, "pos"),
                    **({"tag": _tag(n["tag"], line)} if "tag" in n else {}), "note": _label(n["note"], line, 60)})
    if len({n["pos"] for n in net}) != len(net):
        raise NoteError(line, "도식의 칸: net 둘은 자리(pos)가 달라야 한다 — 같으면 꼬리표가 겹친다")
    if "highlight" in c and not isinstance(c["highlight"], bool):
        raise NoteError(line, "도식의 highlight는 true/false")
    return {"label": _label(c["label"], line, 30), **({"highlight": c["highlight"]} if "highlight" in c else {}),
            "forces": forces, "net": net}


def diagram(raw, line=0):
    """도식 선언 검증 → 정해 둔 꼴의 새 dict. 지금 아는 kind는 balance 하나 — 0선을 사이에 두고 위·아래로 미는 힘과
    그 합이 놓이는 자리를 칸마다 그린다. 길이(size 1~3)는 대강의 크기일 뿐 수치가 아니다. 화면이 그리는 한도에 맞춘다:
    힘 둘, 칸마다 자리 둘(서로 다른 pos), 꼬리표는 TAG_WIDTH까지, 설명 글(alt) 600자."""
    d = _pick(raw, line, "머리", ("kind", "title", "alt", "zero", "net", "forces", "columns"), ("foot",))
    if d["kind"] != "balance":
        raise NoteError(line, "도식의 kind는 balance만 받는다")
    forces = [_force(f, line) for f in _items(d["forces"], line, "forces", 1, 2)]
    keys = [f["key"] for f in forces]
    if len(set(keys)) != len(keys):
        raise NoteError(line, "도식의 힘 key가 겹친다")
    return {"kind": "balance", "title": _label(d["title"], line, 60), "alt": _label(d["alt"], line, 600),
            "zero": _label(d["zero"], line, 30), "net": _label(d["net"], line, 40), "forces": forces,
            "columns": [_column(c, keys, line) for c in _items(d["columns"], line, "columns", 1, 4)],
            **({"foot": _label(d["foot"], line, 120)} if "foot" in d else {})}


# ---------- 노트 · 산출물 ----------

def parse_note(slug, text):
    """노트 한 편(파일 이름에서 .md를 뗀 것, 글 전체) → 노트 dict. 문법을 벗어나면 NoteError(줄 번호)."""
    if not SLUG.fullmatch(slug):
        raise NoteError(0, "파일 이름은 YYYY-MM-DD-영문-소문자.md")
    lines = text.lstrip("\ufeff").replace("\r\n", "\n").replace("\r", "\n").split("\n")
    head, start = parse_head(lines, slug)
    blocks = parse_blocks(lines, start)
    if not blocks:
        raise NoteError(start + 1, "본문이 없다")
    if sum(b["type"] == "questions" for b in blocks) != 1:
        raise NoteError(len(lines), "질문(::질문) 블록은 글마다 한 번 있어야 한다")
    count = iter(range(1, len(blocks) + 1))
    return {**head, "blocks": [{**b, "id": f"s{next(count)}"} if b["type"] == "heading" else b for b in blocks]}


def collect(notes_dir):
    """[(파일 이름에서 .md를 뗀 것, 글)] — 이름순. 폴더 바로 아래의 .md만 읽는다(하위 폴더와 다른 파일은 보지 않는다).
    폴더가 없거나 확장자를 달리 적은 글(.MD · .markdown)이 있으면 NoteError — 조용히 빈 목록·빠진 글이 되지 않게."""
    if not os.path.isdir(notes_dir):
        raise NoteError(0, "노트 폴더가 없다", notes_dir)
    names = sorted(os.listdir(notes_dir))
    odd = [n for n in names if not n.endswith(".md") and n.lower().endswith((".md", ".markdown"))]
    if odd:
        raise NoteError(0, "노트의 확장자는 소문자 .md", odd[0])
    out = []
    for name in (n for n in names if n.endswith(".md")):
        with open(os.path.join(notes_dir, name), encoding="utf-8", newline="") as f:
            out.append((name[:-3], f.read()))
    return out


def build(sources):
    """[(이름, 글)] → 산출물 dict. 최근 글이 먼저(날짜, 같으면 이름의 역순). 한 편이라도 어긋나면 NoteError."""
    notes = []
    for slug, text in sources:
        try:
            notes.append(parse_note(slug, text))
        except NoteError as e:
            raise NoteError(e.line, e.reason, slug + ".md") from None
    return {"schema": SCHEMA, "notes": sorted(notes, key=lambda n: (n["date"], n["slug"]), reverse=True)}


def dumps(data):
    return json.dumps(data, ensure_ascii=False, indent=1) + "\n"


def stored(path):
    """저장된 파일의 글(줄바꿈은 \\n으로 맞춘다). 없거나 못 읽으면 None."""
    try:
        with open(path, encoding="utf-8") as f:
            return f.read()
    except (OSError, ValueError):
        return None


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:      # 어느 운영체제에서 만들어도 같은 바이트
        f.write(text)
    os.replace(tmp, path)


def utf8_console():
    """내보내는 글을 UTF-8로 — 한글 윈도 콘솔(cp949)에는 긴 줄표 같은 글자가 없어, 그대로 두면 안내 문구 대신
    UnicodeEncodeError가 뜬다(check_blind.py와 같은 처리). 테스트가 끼워 넣은 StringIO처럼 바꿀 수 없는 것은 그대로 둔다."""
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")


def main(argv=None):
    utf8_console()
    ap = argparse.ArgumentParser(description="notes/*.md → 읽기 노트 자료(<out>/notes.json)")
    ap.add_argument("--notes", default=DEFAULT_NOTES, help="노트 원본 폴더 (기본: 저장소의 notes/)")
    ap.add_argument("--out", default=DEFAULT_OUT, help="사이트 데이터 폴더 (기본: 저장소의 data/)")
    ap.add_argument("--check", action="store_true", help="쓰지 않고 저장된 파일과 같은지만 본다(다르면 종료코드 1)")
    a = ap.parse_args(argv)
    path = os.path.join(os.path.abspath(a.out), "notes.json")
    try:
        data = build(collect(os.path.abspath(a.notes)))
    except (NoteError, OSError, UnicodeDecodeError) as e:      # 한 편이라도 어긋나면 저장된 파일은 그대로 둔다
        print(f"[notes_build] {e}", file=sys.stderr)
        return 1
    text = dumps(data)
    if a.check:
        same = stored(path) == text
        print("[notes_build] 저장된 notes.json이 원본과 " + ("같다" if same else "다르다 — notes_build.py를 다시 돌릴 것"))
        return 0 if same else 1
    write(path, text)
    print(f"[notes_build] 노트 {len(data['notes'])}편 → {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
