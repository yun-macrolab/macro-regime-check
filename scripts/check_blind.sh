#!/usr/bin/env bash
# 공개 전 검사: 실명·학교·학회·로컬 경로·토큰이 추적 파일과 커밋 기록에 없는지 확인한다.
# 검사어는 이 파일에 쓰지 않는다 — 쓰면 이 파일이 공개되면서 그 자체가 노출된다.
#   로컬: 저장소 루트의 .blind_patterns (git 제외)    CI: 환경변수 BLIND_PATTERNS (GitHub Secret)
# 출력은 파일 이름과 줄 번호만 — 공개 저장소의 Actions 로그에 일치한 내용이 찍히지 않게.
# 종료코드: 0 통과 / 1 발견 / 2 검사 불가(검사어 없음·grep 오류) — 2는 통과로 치지 않는다
set -uo pipefail
# Git Bash의 grep 3.0은 로캘이 비어 있거나 C면 한글 검사어 + -i에서 비정상 종료(rc=134)한다.
# 그때 결과가 "0건"으로 보이는 것을 막으려고 로캘을 고정하고, 아래에서 grep 오류를 따로 잡는다.
export LC_ALL=C.UTF-8
cd "$(git rev-parse --show-toplevel)" || exit 2

pat=$(mktemp)
trap 'rm -f "$pat"' EXIT
if [ -n "${BLIND_PATTERNS:-}" ]; then
  printf '%s\n' "$BLIND_PATTERNS" > "$pat"
elif [ -f .blind_patterns ]; then
  cat .blind_patterns > "$pat"
else
  echo "검사어 없음: .blind_patterns 또는 BLIND_PATTERNS가 필요하다" >&2
  exit 2
fi
tr -d '\r' < "$pat" | grep -v '^[[:space:]]*#' | grep -v '^[[:space:]]*$' > "$pat.clean"
mv "$pat.clean" "$pat"
if [ ! -s "$pat" ]; then
  echo "검사어가 비어 있다" >&2
  exit 2
fi

fail=0
err=0
# scan <설명> : 표준입력에서 검사어를 찾는다. 0=발견 1=없음 2=grep 오류
scan() {
  grep -i -F -f "$pat" >/dev/null
  local rc=$?
  if [ "$rc" -ge 2 ]; then
    echo "✗ 검사 실행 오류(grep rc=$rc): $1" >&2
    err=1
  fi
  return "$rc"
}

if git ls-files --error-unmatch .blind_patterns >/dev/null 2>&1; then
  echo "✗ .blind_patterns가 git에 추적되고 있다" >&2
  fail=1
fi

# 1) 추적 중이거나 새로 추가될 파일(.gitignore 제외)의 내용
while IFS= read -r -d '' f; do
  [ -f "$f" ] || continue
  out=$(grep -n -i -F -f "$pat" -- "$f")
  rc=$?
  if [ "$rc" -ge 2 ]; then
    echo "✗ 검사 실행 오류(grep rc=$rc): $f" >&2
    err=1
  elif [ "$rc" -eq 0 ]; then
    echo "✗ $f: 줄 $(printf '%s\n' "$out" | cut -d: -f1 | paste -sd, -)"
    fail=1
  fi
done < <(git ls-files -z -co --exclude-standard)

# 2) 파일 이름
if git ls-files -co --exclude-standard | scan "파일 이름"; then
  echo "✗ 파일 이름에 검사어가 있다"
  fail=1
fi

# 3) 커밋 기록: 작성자·커미터 이름과 이메일, 메시지. 이메일은 GitHub noreply만 허용
if git rev-parse --verify -q HEAD >/dev/null; then
  if git log --format='%an%n%ae%n%cn%n%ce%n%B' | scan "커밋 기록"; then
    echo "✗ 커밋 기록(작성자·이메일·메시지)에 검사어가 있다"
    fail=1
  fi
  bad=$(git log --format='%ae%n%ce' | sort -u | grep -cv '@users\.noreply\.github\.com$')
  if [ "$bad" -gt 0 ]; then
    echo "✗ noreply가 아닌 커밋 이메일 ${bad}개"
    fail=1
  fi
fi

if [ "$err" -ne 0 ]; then
  echo "검사 불가 — 결과를 신뢰할 수 없다" >&2
  exit 2
fi
if [ "$fail" -eq 0 ]; then
  echo "✓ 검사어 $(wc -l < "$pat")개 — 추적 파일·파일 이름·커밋 기록 모두 0건"
fi
exit "$fail"
