#!/usr/bin/env python3
"""공개 전 검사 — 실명·학교·학회·로컬 경로·토큰 같은 검사어가 공개될 것 어디에도 없는지 확인한다.

실행:  python scripts/check_blind.py    (저장소 안 어디서든)
검사 범위 — 공개 저장소에서 누구나 꺼내 볼 수 있는 것 전부:
  - 작업 트리: 추적 파일과 새로 추가될 파일(.gitignore 제외)의 이름·내용, 스테이징된 내용
  - 과거 기록: HEAD와 모든 ref(브랜치·태그·노트)에서 닿는 커밋·태그·트리·파일 전부 — 지운 파일, 고친 줄, 옛 이름,
    병합에서만 생긴 파일, 트리 항목 이름, git replace로 가린 원래 커밋까지.
    커밋·태그 머리 전체(작성자·커미터·태거, 서명 태그 병합의 mergetag 등)와 메시지 포함
  - ref 이름, 커밋·태그 이메일(GitHub noreply만 허용)
검사어: 로컬은 저장소 루트의 .blind_patterns(git 제외), CI는 환경변수 BLIND_PATTERNS(GitHub Secret).
  검사어를 이 파일에 쓰지 않는다 — 쓰면 이 파일이 공개되면서 그 자체가 노출된다.
  검사어 줄에 보이지 않는 문자(폭 없는 공백·중간 BOM·제어 문자)가 있으면 검사 불가 — 그 검사어가 조용히 죽기 때문.
비교: 양쪽을 NFKC(전각·호환 문자·한글 자모 분해를 합침)와 casefold로 맞춘 뒤 부분 문자열.
  한 줄씩 보고, 한 번 더 넓게 본다 — HTML 엔티티와 JSON·JS 이스케이프(겹 역슬래시, 역슬래시 u 네 자리)를 풀고
  줄바꿈을 포함한 공백 묶음을 공백 하나로. CP949·UTF-16으로 바꾼 검사어 바이트도 원래 바이트에서 찾는다.
출력은 공개 Actions 로그에 남는다 — 경로·줄 번호·객체 ID만. 경로에 검사어가 있으면 경로도 가리고, git 오류 원문은 찍지 않는다.
UTF-8 텍스트로 읽을 수 없는 것(바이너리·UTF-16·CP949·압축 문서·Git LFS 포인터, UTF-8이 아닌 파일 이름)은
  검사할 수 없으므로 통과시키지 않는다.
종료코드: 0 통과 / 1 발견 / 2 검사 불가(검사어 없음·읽을 수 없는 것·얕은 클론·grafts·git 오류·예기치 못한 오류) — 2는 통과가 아니다.
CI: actions/checkout에 fetch-depth: 0(브랜치·태그 전부) + notes를 따로 받는다.
  PR 참조(refs/pull)는 받지 않는다 — 이 저장소는 PR을 쓰지 않고, 남이 연 PR이 검사를 영구히 막거나 공개 로그로
  검사어를 떠보는 통로가 되지 않게. PR을 쓰게 되면 자기 PR만 골라 받도록 다시 설계할 것.
로컬: .githooks/pre-push가 push 전에 이 검사를 돌린다(git config core.hooksPath .githooks). CI 검사는 이미 공개된 뒤에 돈다.
"""
import html, os, re, subprocess, sys, unicodedata

MASK = "(이름에 검사어)"
BS = chr(92)        # 역슬래시
BOM = chr(0xFEFF)
LFS_POINTER = "version https://git-lfs.github.com/spec/v1"
NOREPLY = re.compile(r"(@users\.noreply\.github\.com|^noreply@github\.com)$")
# 커밋·태그 머리: 사람 줄에서 이메일을 뽑고, 해시 줄과 시각은 검사에서 뺀다(숫자 검사어와 우연히 겹치지 않게)
IDENT = re.compile(r"(?:author|committer|tagger) .*<([^>\n]*)> -?\d+ [+-]\d{4}$")
HASH_LINE = re.compile(r"(?:mergetag )?(?:tree|parent|object) [0-9a-f]{40,64}$")
STAMP = re.compile(r"(<[^>\n]*>) -?\d+ [+-]\d{4}$")
U_ESCAPE = re.compile(re.escape(BS) + r"u([0-9a-fA-F]{4})")
INVISIBLE = {"Cf", "Cc", "Zl", "Zp", "Cs"}   # 서식(폭 없는 공백·BOM)·제어·줄/문단 구분·서로게이트
RAW_ENCODINGS = ("cp949", "utf-16-le", "utf-16-be")


class CheckError(Exception):
    """검사 불가 — 결과를 믿을 수 없다(종료코드 2). 메시지에 경로·검사어·git 오류 원문을 넣지 않는다."""


def git(*args, stdin=None):
    env = {k: v for k, v in os.environ.items() if k != "GIT_GRAFT_FILE"}
    env["GIT_NO_REPLACE_OBJECTS"] = "1"   # replace로 가린 원래 커밋도 공개 저장소엔 남는다
    r = subprocess.run(["git", "-c", "core.quotePath=false", *args], input=stdin, capture_output=True, env=env)
    if r.returncode != 0:
        raise CheckError(f"git {args[0]} 실패(rc={r.returncode})")
    return r.stdout


def decode_path(b):
    return b.decode("utf-8", "surrogateescape")


def bad_name(s):
    """UTF-8이 아닌 바이트가 들어간 이름(decode_path가 서로게이트로 남긴 것)."""
    return any(0xDC80 <= ord(c) <= 0xDCFF for c in s)


def fold(s):
    """비교용 형태 — NFKC + casefold."""
    return unicodedata.normalize("NFKC", unicodedata.normalize("NFKC", s).casefold())


def loose(s):
    """넓은 보기 — 이스케이프·엔티티를 풀고 공백 묶음(줄바꿈 포함)을 공백 하나로."""
    s = U_ESCAPE.sub(lambda m: chr(int(m.group(1), 16)), s).replace(BS + BS, BS)
    return re.sub(r"\s+", " ", html.unescape(s))


def as_text(data):
    """UTF-8 텍스트면 문자열, 아니면 None."""
    if b"\x00" in data:
        return None
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return None


def load_patterns(root):
    text = os.environ.get("BLIND_PATTERNS")
    if not text:
        path = os.path.join(root, ".blind_patterns")
        if not os.path.isfile(path):
            raise CheckError("검사어 없음: .blind_patterns 또는 BLIND_PATTERNS가 필요하다")
        with open(path, "rb") as f:
            text = as_text(f.read())
        if text is None:
            raise CheckError("검사어 파일을 UTF-8 텍스트로 읽을 수 없다 — UTF-8로 다시 저장할 것")
    pats = set()
    for no, line in enumerate(text.removeprefix(BOM).splitlines(), 1):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if any(unicodedata.category(c) in INVISIBLE for c in line):
            raise CheckError(f"검사어 {no}번째 줄에 보이지 않는 문자(폭 없는 공백·BOM·제어 문자)가 있다 — 다시 입력할 것")
        pats.add(fold(line))
    if not pats:
        raise CheckError("검사어가 비어 있다")
    return sorted(pats)


class Report:
    def __init__(self, pats):
        self.pats, self.found, self.errors = pats, [], []
        self.raw = set()   # 다른 인코딩으로 바꾼 검사어 바이트
        for p in pats:
            for enc in RAW_ENCODINGS:
                if enc == "cp949" and p.isascii():
                    continue   # ASCII의 CP949 바이트는 UTF-8과 같다 — 텍스트 검사가 본다
                try:
                    self.raw.add(p.encode(enc))
                except UnicodeEncodeError:
                    pass

    def has(self, s):
        views = (fold(s), fold(loose(s)))
        return any(p in v for p in self.pats for v in views)

    def has_bytes(self, data):
        return any(b in data for b in self.raw)

    def name(self, path):
        return MASK if self.has(path) or bad_name(path) else path

    def lines_hit(self, text):
        return [i for i, line in enumerate(text.splitlines(), 1) if self.has(line)]


def check_content(rep, data, where):
    """파일 내용 하나 — 발견은 rep.found, 읽을 수 없으면 rep.errors."""
    text = as_text(data)
    if rep.has_bytes(data) and (text is None or not rep.has(text)):
        rep.found.append(f"{where}: 다른 인코딩(CP949·UTF-16) 바이트로 검사어가 있다")
    if text is None or text.startswith(LFS_POINTER):
        rep.errors.append(f"UTF-8 텍스트가 아니라(바이너리·다른 인코딩·LFS 포인터) 검사할 수 없는 파일: {where}")
        return
    hit = rep.lines_hit(text)
    if hit:
        rep.found.append(f"{where}: 줄 {','.join(map(str, hit))}")
    elif rep.has(text):
        rep.found.append(f"{where}: 줄바꿈·이스케이프를 걸친 일치")


def read_worktree(root, path):
    full = os.path.join(root, path)
    if os.path.islink(full):
        return os.readlink(full).encode("utf-8", "surrogateescape")
    if not os.path.isfile(full):
        return None   # 추적 중이지만 작업 트리에서 지운 파일 — 내용은 스테이징·과거 기록 검사가 본다
    with open(full, "rb") as f:
        return f.read()


def check_worktree(rep, root):
    """작업 트리의 이름·내용. 반환: 검사한 파일 수."""
    paths = [decode_path(p) for p in git("ls-files", "-z", "-co", "--exclude-standard").split(b"\0") if p]
    if git("ls-files", "-z", "--", ".blind_patterns"):
        rep.found.append(".blind_patterns가 git에 추적되고 있다")
    for path in paths:
        try:
            data = read_worktree(root, path)
        except OSError:
            rep.errors.append(f"읽을 수 없는 파일: {rep.name(path)}")
            continue
        if data is not None:
            check_content(rep, data, rep.name(path))
    if any(bad_name(p) for p in paths):
        rep.errors.append("UTF-8이 아닌 파일 이름이 있다")
    if any(rep.has(p) for p in paths):
        rep.found.append("파일 이름에 검사어가 있다")
    return len(paths)


def list_objects():
    """검사할 객체 {sha: 경로}. HEAD와 모든 ref에서 닿는 객체 + 스테이징된 파일. 경로는 git이 고른 대표 이름 하나."""
    objs = {}
    for line in decode_path(git("rev-list", "--all", "--objects")).split("\n"):
        sha, _, path = line.partition(" ")
        if sha:
            objs.setdefault(sha, path)
    for entry in git("ls-files", "-z", "-s").split(b"\0"):
        meta, _, path = entry.partition(b"\t")
        fields = meta.split()
        if len(fields) == 3 and fields[0] != b"160000":   # 160000 = 하위 모듈(이 저장소의 객체가 아님)
            objs.setdefault(fields[1].decode(), decode_path(path))
    return objs


def history_paths():
    """커밋마다 바뀐 전체 경로 — 옛 이름(--no-renames), 병합에서 생긴 경로(-m), 첫 커밋(--root) 포함."""
    out = git("log", "--all", "-m", "--root", "--no-renames", "--name-only", "-z", "--format=")
    return [p.strip("\n") for p in decode_path(out).split("\0") if p.strip("\n")]


def read_objects(shas):
    """git cat-file --batch 한 번으로 (sha, 종류, 내용)을 차례로 낸다. 없는 객체(부분 클론 등)는 검사 불가."""
    out = git("cat-file", "--batch", stdin="".join(s + "\n" for s in shas).encode("ascii"))
    i = 0
    for sha in shas:
        nl = out.index(b"\n", i)
        head = out[i:nl].split()
        if len(head) != 3 or head[0].decode() != sha or not head[2].isdigit():
            raise CheckError("과거 객체를 읽을 수 없다(없는 객체 — 부분 클론이거나 저장소 손상)")
        start = nl + 1
        size = int(head[2])
        yield sha, head[1].decode(), out[start:start + size]
        i = start + size + 1


def tree_names(data, raw_len):
    """트리 객체의 항목 이름들 — 항목은 '<모드> <이름>\\0<해시 바이트>'."""
    names, i = [], 0
    while i < len(data):
        sp = data.index(b" ", i)
        nul = data.index(b"\0", sp)
        names.append(decode_path(data[sp + 1:nul]))
        i = nul + 1 + raw_len
    return names


def check_meta(rep, sha, kind, data, emails):
    """커밋·태그 객체: 머리 전체(해시 줄·시각 제외)와 메시지. 사람 줄의 이메일은 모아서 noreply 확인."""
    text = as_text(data)
    if text is None:
        rep.errors.append(f"{kind} {sha[:7]} 원문을 UTF-8로 읽을 수 없다")
        return
    head, _, message = text.partition("\n\n")
    lines = [line[1:] if line.startswith(" ") else line for line in head.split("\n")]   # mergetag 등의 이어지는 줄
    emails.update(m.group(1) for line in lines if (m := IDENT.match(line)))
    visible = "\n".join(STAMP.sub(r"\1", line) for line in lines if not HASH_LINE.match(line))
    if rep.has(visible) or rep.has(message):
        rep.found.append(f"{kind} {sha[:7]}의 머리(작성자·이메일 등)나 메시지에 검사어가 있다")


def check_blob(rep, sha, path, data):
    check_content(rep, data, f"과거 커밋의 파일 {rep.name(path)} (blob {sha[:7]} — git log --all --find-object={sha[:7]})")


def check_history(rep):
    """과거 기록 전체. 반환: (검사한 객체 수, 커밋 수)."""
    refs = [r for r in decode_path(git("for-each-ref", "--format=%(refname)")).split("\n") if r]
    if any(rep.has(r) for r in refs):
        rep.found.append("ref(브랜치·태그) 이름에 검사어가 있다")
    objs = list_objects()
    names = history_paths() + list(objs.values())
    emails, commits = set(), 0
    for sha, kind, data in read_objects(list(objs)):
        if kind in ("commit", "tag"):
            commits += kind == "commit"
            check_meta(rep, sha, kind, data, emails)
        elif kind == "tree":
            names.extend(tree_names(data, len(sha) // 2))
        elif kind == "blob":
            check_blob(rep, sha, objs[sha], data)
    if any(bad_name(n) for n in names + refs):
        rep.errors.append("UTF-8이 아닌 과거 파일 이름이나 ref 이름이 있다")
    if any(rep.has(n) for n in names):
        rep.found.append("과거 커밋의 파일 이름에 검사어가 있다")
    bad = [e for e in emails if not NOREPLY.search(e)]
    if bad:
        rep.found.append(f"noreply가 아닌 커밋·태그 이메일 {len(bad)}개")
    return len(objs), commits


def run():
    root = decode_path(git("rev-parse", "--show-toplevel")).strip()
    os.chdir(root)
    if git("rev-parse", "--is-shallow-repository").strip() != b"false":
        raise CheckError("얕은 클론이라 과거 기록을 다 볼 수 없다 (actions/checkout에 fetch-depth: 0)")
    if os.path.exists(decode_path(git("rev-parse", "--git-path", "info/grafts")).strip()):
        raise CheckError("info/grafts가 있어 과거 기록이 잘려 보일 수 있다")
    rep = Report(load_patterns(root))
    files = check_worktree(rep, root)
    objects, commits = check_history(rep)
    return rep, files, objects, commits


def main():
    for stream in (sys.stdout, sys.stderr):
        stream.reconfigure(encoding="utf-8", errors="replace")
    try:
        rep, files, objects, commits = run()
    except CheckError as e:
        print(f"검사 불가: {e}", file=sys.stderr)
        return 2
    except Exception as e:   # 예기치 못한 오류도 '발견(1)'이 아니라 '검사 불가(2)' — 원문·경로는 찍지 않는다
        print(f"검사 불가: 예기치 못한 오류({type(e).__name__})", file=sys.stderr)
        return 2
    for msg in rep.found:
        print(f"✗ {msg}")
    for msg in rep.errors:
        print(f"✗ 검사 불가: {msg}", file=sys.stderr)
    if rep.errors:
        print("검사 불가 — 결과를 신뢰할 수 없다", file=sys.stderr)
        return 2
    if rep.found:
        return 1
    print(f"✓ 검사어 {len(rep.pats)}개 — 작업 트리 파일 {files}개·과거 객체 {objects}개(커밋 {commits}개) 모두 0건")
    return 0


if __name__ == "__main__":
    sys.exit(main())
