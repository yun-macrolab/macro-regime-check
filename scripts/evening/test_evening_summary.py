#!/usr/bin/env python3
"""예약 등록 스크립트(Evening-Summary.ps1)의 정적 검사 — ASCII, 문법, 기본값, 등록되는 작업의 꼴. 실행하지 않는다.

실행:  python -m unittest discover -s scripts/evening   (저장소 루트에서)
파일의 글자만 본다. 문법은 PowerShell의 파서로만 확인한다(스크립트를 돌리지 않는다 — 예약 작업을 만들지도, 요약을 돌리지도 않는다).
PowerShell이 없는 곳에서는 문법 검사만 건너뛴다.
"""
import os
import re
import shutil
import subprocess
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
PATH = os.path.join(HERE, "Evening-Summary.ps1")
PARSE = ("$e = $null; $t = $null; [void][System.Management.Automation.Language.Parser]::ParseFile($env:EVENING_PS1, [ref]$t, [ref]$e); "
         "exit $e.Count")


class ScriptTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(PATH, "rb") as f:
            cls.raw = f.read()
        cls.text = cls.raw.decode("ascii", "replace").replace("\r\n", "\n")
        cls.code = "\n".join(x for x in cls.text.split("#>", 1)[1].split("\n") if not x.lstrip().startswith("#"))

    def test_ascii_only_with_consistent_line_endings(self):
        self.assertTrue(self.raw.isascii())                                   # 주석도 영어 — 어느 코드 페이지의 PowerShell이 읽어도 같다
        self.assertFalse(self.raw.startswith(b"\xef\xbb\xbf"))
        crlf, lf = self.raw.count(b"\r\n"), self.raw.count(b"\n")
        self.assertIn(crlf, (0, lf))                                          # 줄 끝이 섞이지 않는다(Windows에 받으면 CRLF)
        self.assertNotIn(b"\t", self.raw)

    def test_syntax(self):
        ps = shutil.which("powershell") or shutil.which("pwsh")
        if not ps:
            self.skipTest("PowerShell이 없다")
        r = subprocess.run([ps, "-NoProfile", "-NonInteractive", "-Command", PARSE], env={**os.environ, "EVENING_PS1": PATH},
                           capture_output=True, timeout=120)
        self.assertEqual(r.returncode, 0, r.stdout[-500:])

    def test_parameters_and_defaults(self):
        block = self.code.split("param(", 1)[1].split("\n)", 1)[0]
        want = {"RepoDir": '[string]$RepoDir = ""', "Yes": "[switch]$Yes", "Schedule": "[switch]$Schedule", "Unschedule": "[switch]$Unschedule",
                "At": '[string]$At = "17:45"', "Late": '[string]$Late = "23:30"', "Morning": '[string]$Morning = "07:30"', "TaskName": '[string]$TaskName = "MacroEveningSummary"'}
        self.assertEqual(re.findall(r"\$(\w+)", block), list(want))
        for line in want.values():
            self.assertIn(line, block)

    def test_registered_task(self):
        """평일 17:45 · 23:30과 이튿날 07:30(화~토), 숨김 실행, 놓친 실행은 켜진 뒤에, 배터리에서도, 40분 제한, 겹치면 새 실행을 버린다.
        뒤의 두 트리거는 늦게 돈 예약 수집이 다시 계산한 판을 따라간다 — 17:45 한 번뿐이면 그날의 마지막 판에 문장이 없다."""
        code = self.code
        week, after = "Monday,Tuesday,Wednesday,Thursday,Friday", "Tuesday,Wednesday,Thursday,Friday,Saturday"
        self.assertEqual(re.findall(r"New-ScheduledTaskTrigger -Weekly -DaysOfWeek (\S+) -At (\$\w+)\)", code),
                         [(week, "$when"), (week, "$whenLate"), (after, "$whenMorning")])
        self.assertIn("-Trigger $triggers", code)
        for name in ("At", "Late", "Morning"):
            self.assertIn('[datetime]::ParseExact($%s, "HH:mm", $culture)' % name, code)
        self.assertNotIn("Sunday", code)
        for word in ("-StartWhenAvailable",
                     "-AllowStartIfOnBatteries", "-DontStopIfGoingOnBatteries", "-ExecutionTimeLimit (New-TimeSpan -Minutes 40)",
                     "-MultipleInstances IgnoreNew", "-LogonType Interactive", "-RunLevel Limited",
                     "Register-ScheduledTask -TaskName $TaskName", "Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false"):
            self.assertIn(word, code, word)
        action = re.search(r"\$arg = '([^']+)' -f \$self, \$repo", code)
        self.assertEqual(action.group(1), '-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "{0}" -Yes -RepoDir "{1}"')
        self.assertIn('$self = Join-Path $repo "scripts\\evening\\Evening-Summary.ps1"', code)     # 게시 전용 폴더 안의 것을 등록한다
        self.assertIn('New-ScheduledTaskAction -Execute "powershell.exe" -Argument $arg', code)
        self.assertNotIn("-RunLevel Highest", code)

    def test_run_is_hidden_guarded_and_passes_the_exit_code_on(self):
        code = self.code
        self.assertRegex(code, r"if \(-not \$Yes\) \{[^}]*exit 64\s*\}")        # -Yes 없이 그냥 열면(더블클릭) 아무것도 돌지 않는다
        self.assertIn('"run", "--repo-dir", (\'"{0}"\' -f $repo), "--dispatch"', code)
        self.assertIn('"-X", "utf8"', code)
        self.assertIn("Start-Process -FilePath $py -ArgumentList $argList -WindowStyle Hidden -Wait -PassThru", code)
        self.assertIn("$code = $p.ExitCode", code)
        self.assertRegex(code, r"exit \$code\s*$")
        self.assertIn("Python313", code)
        for word in ('".macro-notes"', '"evening-summary-error.txt"', "Remove-Item -LiteralPath $ErrorFile", "Set-Content -LiteralPath $ErrorFile"):
            self.assertIn(word, code, word)
        self.assertLess(code.index("if ($code -eq 0)"), code.index("Set-Content -LiteralPath $ErrorFile"))
        for word in ("code=context", "code=switch", "code=moved", "code=unread", "result, timeout or missing", "dirty, scope or head"):
            self.assertIn(word, code, word)                                   # 오류 안내에 새로 생긴 코드도 있다
        for word in ("Invoke-Expression", "iex ", "DownloadString", "Invoke-WebRequest", "token", "password", "git push", "-Force origin"):
            self.assertNotIn(word.lower(), code.lower(), word)

    def test_header_says_which_copy_to_register(self):
        head = self.text.split("#>", 1)[0]
        for word in ("INSIDE the publish-only folder", "-Schedule -RepoDir", "-Unschedule", "-Yes -RepoDir", "evening-summary.log",
                     "evening-summary-error.txt", "EVENING_ENABLED", "only when it is due", "AND run -Unschedule", "three triggers"):
            self.assertIn(word, head, word)


if __name__ == "__main__":
    unittest.main()
