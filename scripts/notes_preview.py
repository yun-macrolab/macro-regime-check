#!/usr/bin/env python3
"""미리보기 조립 — 배포와 같은 모양(site/ + data/)을 작업 폴더 .work/notes/preview/ 에 만든다(커밋·배포되지 않는 폴더).

워크플로의 '사이트 조립' 단계와 같은 일을 한다: site/의 파일을 그대로, data/를 그 아래 data/로.
조립하기 전에 data/notes.json이 notes/*.md와 맞는지 보고, 어긋나 있으면 조립하지 않는다(옛 글을 미리보지 않게).

사용법: python scripts/notes_preview.py [--out .work/notes/preview]
보기:   python -m http.server 8765 --directory .work/notes/preview   →  http://localhost:8765/#notes
"""
import os, sys, shutil, argparse

SCRIPTS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPTS)
import notes_build as nb

REPO = os.path.dirname(SCRIPTS)
DEFAULT_OUT = os.path.join(REPO, ".work", "notes", "preview")


def assemble(out, repo=REPO):
    """out을 비우고 site/ + data/ 사본을 넣는다 → 넣은 파일 수."""
    if os.path.isdir(out):
        shutil.rmtree(out)
    shutil.copytree(os.path.join(repo, "site"), out)
    shutil.copytree(os.path.join(repo, "data"), os.path.join(out, "data"))
    return sum(len(files) for _, _, files in os.walk(out))


def main(argv=None):
    nb.utf8_console()                                         # cp949 콘솔에서도 안내 문구(긴 줄표·화살표)가 죽지 않게
    ap = argparse.ArgumentParser(description="읽기 노트 미리보기 조립(site/ + data/ → .work/notes/preview/)")
    ap.add_argument("--out", default=DEFAULT_OUT, help="조립할 폴더 (기본: .work/notes/preview)")
    a = ap.parse_args(argv)
    out = os.path.abspath(a.out)
    work = os.path.join(REPO, ".work")
    if not out.startswith(work + os.sep):                     # 비우고 다시 만드는 폴더라 작업 폴더 밖은 받지 않는다
        print("[notes_preview] 미리보기 폴더는 .work/ 아래여야 한다", file=sys.stderr)
        return 1
    try:
        fresh = nb.dumps(nb.build(nb.collect(nb.DEFAULT_NOTES)))
    except (nb.NoteError, OSError, UnicodeDecodeError) as e:
        print(f"[notes_preview] 노트 원본을 읽을 수 없다: {e}", file=sys.stderr)
        return 1
    if nb.stored(os.path.join(nb.DEFAULT_OUT, "notes.json")) != fresh:
        print("[notes_preview] data/notes.json이 notes/*.md와 다르다 — python scripts/notes_build.py 를 먼저 돌릴 것", file=sys.stderr)
        return 1
    count = assemble(out)
    print(f"[notes_preview] 파일 {count}개 → {out}")
    print(f'[notes_preview] 보기: python -m http.server 8765 --directory "{out}"  →  http://localhost:8765/#notes')
    return 0


if __name__ == "__main__":
    sys.exit(main())
