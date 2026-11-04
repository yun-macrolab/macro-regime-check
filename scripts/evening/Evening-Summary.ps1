<#
.SYNOPSIS
  Evening AI summary layer: run it now, or register / remove the weekday scheduled task.

.DESCRIPTION
  Register the copy of this script that lives INSIDE the publish-only folder - a clone or worktree of the
  public repository that is used for nothing else. The task action stores that folder (-RepoDir) and the
  path of the copy inside it, and evening_llm.py moves that folder to the tip of origin/main before it works,
  so the task always runs the code that is on main.

    Evening-Summary.ps1 -Schedule -RepoDir <folder> [-At 17:45] [-Late 23:30] [-Morning 07:30]
                                                                  register task MacroEveningSummary
    Evening-Summary.ps1 -Unschedule                               remove the task
    Evening-Summary.ps1 -Yes -RepoDir <folder>                    run now: evening_llm.py run --repo-dir <folder> --dispatch

  The task has three triggers. GitHub's own scheduled collection can run hours late and recompute the same
  edition, so one run at 17:45 would leave the last edition of the day without sentences:
    Mon-Fri -At       start the rules edition (if it is due) and write the sentences
    Mon-Fri -Late     follow an edition that was recomputed in the evening
    Tue-Sat -Morning  follow an edition that was recomputed overnight
  Every run passes --dispatch, but evening_llm.py starts the rules workflow only when it is due: the edition
  date is a weekday, it is after 17:30 KST, that edition is not up yet, and the edition is not withdrawn.
  A missed run that starts late (next morning, Saturday) therefore never publishes an edition of its own.
  When nothing changed since the last run, no post is read and Claude is not called.

  The repository variable EVENING_ENABLED is read first. If it is not "true" nothing is started, read or
  asked (sentences that are already up are replaced by an empty layer). Taking the evening edition down
  for good: switch the variable off AND run -Unschedule.
  -Unschedule ALSO STOPS THE FED PEOPLE REMARK PUBLISHER below, takedowns included: a remark the operator
  marks N in the private log would then stay on people.html. To stop only the evening edition, switch
  EVENING_ENABLED off and keep the task - the people step runs regardless of the switch. To stop both,
  first delete data/people_remarks.json and scripts/people_push.py on main, then run -Unschedule.

  The run is hidden (no console window) and its exit code is passed on:
    0  published, or nothing to do (also when the switch is off)
    2  the summary layer was not published (the rules edition is untouched)
    1  unexpected failure
  On failure a short note is left in %USERPROFILE%\.macro-notes\evening-summary-error.txt; it is removed on success.
  Each run adds one or two lines to %USERPROFILE%\.macro-notes\evening-summary.log (counts, dates and codes only).

  The publish-only folder also needs the local .blind_patterns file (it is not in git): the pre-publish check
  refuses to commit without it.

  Fed people remarks: BEFORE the evening run a SEPARATE step runs scripts\people_push.py with the same Python
  and PATH (--repo-dir <folder> --source %USERPROFILE%\.macro-notes\people-remarks.json). It publishes only
  data/people_remarks.json (the automatic classification written by the private pipeline), runs whether
  EVENING_ENABLED is on or off (people_push.py moves the folder to origin/main itself), never changes the
  exit code or the error file above, and is skipped quietly while the folder does not hold that script yet.
  It goes first because its sync undoes what an interrupted earlier run of either publisher left behind
  (its own file and the evening one) and it restores its file whenever it stops - so a people run that was
  killed half way (shutdown, the 40-minute limit) never makes the evening publish stop as "dirty".
  It adds one line per run to %USERPROFILE%\.macro-notes\people-push.log (codes and counts only).
#>
[CmdletBinding()]
param(
    [string]$RepoDir = "",
    [switch]$Yes,
    [switch]$Schedule,
    [switch]$Unschedule,
    [string]$At = "17:45",
    [string]$Late = "23:30",
    [string]$Morning = "07:30",
    [string]$TaskName = "MacroEveningSummary"
)

$ErrorActionPreference = "Stop"
$NotesDir = Join-Path $env:USERPROFILE ".macro-notes"
$ErrorFile = Join-Path $NotesDir "evening-summary-error.txt"

function Resolve-Repo([string]$Dir) {
    if ([string]::IsNullOrWhiteSpace($Dir)) { throw "RepoDir is required" }
    $full = (Resolve-Path -LiteralPath $Dir).Path.TrimEnd("\")
    if (-not (Test-Path -LiteralPath (Join-Path $full "scripts\evening\evening_llm.py"))) {
        throw "RepoDir does not hold scripts\evening\evening_llm.py"
    }
    return $full
}

function Find-Python {
    # Python 3.13 by its install path - the default "python" on this PC is an older one
    $candidates = @(
        (Join-Path $env:LOCALAPPDATA "Programs\Python\Python313\python.exe"),
        (Join-Path $env:ProgramFiles "Python313\python.exe"),
        "C:\Python313\python.exe"
    )
    foreach ($p in $candidates) {
        if (Test-Path -LiteralPath $p) { return $p }
    }
    throw "Python 3.13 not found"
}

if ($Unschedule) {
    if (Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue) {
        Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
        Write-Output "removed task $TaskName"
        Write-Output "note: this also stopped the Fed people remark publisher (scripts\people_push.py), takedowns included:"
        Write-Output "  a remark marked N in the private log now stays on people.html."
        Write-Output "  to stop only the evening edition: switch EVENING_ENABLED off and register the task again with -Schedule."
        Write-Output "  to stop both: delete data/people_remarks.json and scripts/people_push.py on main."
    } else {
        Write-Output "no task named $TaskName"
    }
    exit 0
}

if ($Schedule) {
    $repo = Resolve-Repo $RepoDir
    $self = Join-Path $repo "scripts\evening\Evening-Summary.ps1"
    if (-not (Test-Path -LiteralPath $self)) { throw "Evening-Summary.ps1 not found inside RepoDir" }
    [void](Find-Python)
    $culture = [System.Globalization.CultureInfo]::InvariantCulture
    $when = [datetime]::ParseExact($At, "HH:mm", $culture)
    $whenLate = [datetime]::ParseExact($Late, "HH:mm", $culture)
    $whenMorning = [datetime]::ParseExact($Morning, "HH:mm", $culture)
    # hidden PowerShell, not a console window: closing a visible window would kill the run half way
    $arg = '-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "{0}" -Yes -RepoDir "{1}"' -f $self, $repo
    $action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $arg
    # the evening run, a late run and a run the morning after (Tue-Sat = the mornings after Mon-Fri)
    $triggers = @(
        (New-ScheduledTaskTrigger -Weekly -DaysOfWeek Monday,Tuesday,Wednesday,Thursday,Friday -At $when),
        (New-ScheduledTaskTrigger -Weekly -DaysOfWeek Monday,Tuesday,Wednesday,Thursday,Friday -At $whenLate),
        (New-ScheduledTaskTrigger -Weekly -DaysOfWeek Tuesday,Wednesday,Thursday,Friday,Saturday -At $whenMorning)
    )
    $settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit (New-TimeSpan -Minutes 40) -MultipleInstances IgnoreNew
    $user = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
    $principal = New-ScheduledTaskPrincipal -UserId $user -LogonType Interactive -RunLevel Limited
    Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $triggers -Settings $settings -Principal $principal -Force | Out-Null
    Write-Output ("registered task {0}: Mon-Fri {1} and {2}, Tue-Sat {3}, folder {4}" -f $TaskName, $At, $Late, $Morning, $repo)
    exit 0
}

if (-not $Yes) {
    Write-Output "usage: Evening-Summary.ps1 -Yes -RepoDir <folder>  |  -Schedule -RepoDir <folder> [-At HH:mm]  |  -Unschedule"
    exit 64
}

$code = 1
$ready = $false
try {
    $repo = Resolve-Repo $RepoDir
    $py = Find-Python
    New-Item -ItemType Directory -Force -Path $NotesDir | Out-Null
    # Python 3.13 first on PATH (the pre-push hook calls "python"), then the usual homes of claude, gh and git
    $extra = @(
        (Split-Path -Parent $py),
        (Join-Path $env:USERPROFILE ".local\bin"),
        (Join-Path $env:ProgramFiles "GitHub CLI"),
        (Join-Path $env:ProgramFiles "Git\cmd")
    ) | Where-Object { Test-Path -LiteralPath $_ }
    $env:PATH = (@($extra) + @($env:PATH)) -join ";"
    $ready = $true
} catch {
    $code = 1
}

# Fed people remarks - a separate step with its own try/catch, BEFORE the evening step: its sync undoes the
# leftovers of an interrupted earlier run (its own file and the evening one) and it restores its file whenever it
# stops, so the evening publish below never finds the folder dirty because of it. It never touches $code or the
# error file, it runs even when the evening switch is off (people_push.py does its own sync to origin/main), and it
# is skipped quietly while the folder does not hold the script yet. Its result goes to people-push.log only.
try {
    if ($ready) {
        $people = Join-Path $repo "scripts\people_push.py"
        if (Test-Path -LiteralPath $people) {
            $source = Join-Path $NotesDir "people-remarks.json"
            $peopleArgs = @("-X", "utf8", ('"{0}"' -f $people), "--repo-dir", ('"{0}"' -f $repo), "--source", ('"{0}"' -f $source))
            $q = Start-Process -FilePath $py -ArgumentList $peopleArgs -WindowStyle Hidden -Wait -PassThru
            [void]$q.ExitCode
        }
    }
} catch {
}

# The evening summary - its exit code is the exit code of this script
try {
    if (-not $ready) { throw "setup failed" }
    $script = Join-Path $repo "scripts\evening\evening_llm.py"
    $argList = @("-X", "utf8", ('"{0}"' -f $script), "run", "--repo-dir", ('"{0}"' -f $repo), "--dispatch")
    $p = Start-Process -FilePath $py -ArgumentList $argList -WindowStyle Hidden -Wait -PassThru
    $code = $p.ExitCode
} catch {
    $code = 1
}

if ($code -eq 0) {
    Remove-Item -LiteralPath $ErrorFile -Force -ErrorAction SilentlyContinue
} else {
    $stamp = Get-Date -Format "yyyy-MM-ddTHH:mm:ss"
    $lines = @(
        "evening summary: nothing was published by this run",
        "at=$stamp exit=$code",
        "exit 2 = the summary layer was not published; the rules edition is untouched. exit 1 = unexpected failure.",
        "Read the last lines of evening-summary.log in this folder and look for code=...",
        "  code=exit, result, timeout or missing   open a terminal and start claude once (the login may have expired)",
        "  code=tools or code=tool_use  the claude CLI did not start isolated; nothing was sent or the answer was dropped",
        "  code=context                 more than the question reached the model (CLAUDE.md, rules, a plugin); no post was sent",
        "  code=switch                  the EVENING_ENABLED variable could not be read (gh login, network); nothing was started",
        "  code=unread                  no post could be fetched from the channel previews",
        "  code=blind                   .blind_patterns is missing in the publish folder, or a sentence matched it",
        "  code=dirty, scope or head    the publish folder holds other changes or is not at origin/main; use it for nothing else",
        "  code=moved                   the edition changed or was withdrawn while the sentences were made; the next run redoes it",
        "  code=push                    the push was refused (gh login, network, or the pre-push check)"
    )
    try {
        New-Item -ItemType Directory -Force -Path $NotesDir | Out-Null
        Set-Content -LiteralPath $ErrorFile -Value $lines -Encoding ASCII
    } catch {
    }
}

exit $code
