# W8 overnight watchdog for an unattended repeat campaign. Written session 14 for the q56
# redirect/deny top-up; parameterised session 15 so it is not single-use.
#
#   powershell -File w8-watchdog.ps1 -Log D:\...\runs\q56\repeat-control.log -Marker 'SESSION 15'
#
# TWO JOBS, AND ONLY ONE OF THEM IS STILL A PRIMARY DEFENCE.
#
# 1. Killing a hung verifier (F57). ⚠ **F57 IS FIXED IN THE HARNESS AS OF 2026-08-14** - w8-run now
#    bounds each verifier (--verify-timeout-s, default 300) and kills the whole process tree, so
#    this half is a BACKSTOP, not the mechanism. Keep it anyway: it catches a spinner the harness
#    could not reap, and its message is the only thing that would say so out loud.
# 2. Reloading the champion if LM Studio has dropped it. **This one has no equivalent anywhere in
#    the harness.** LM Studio unloaded the model by itself during an idle gap in session 14 despite
#    `lms ps` reporting no TTL, and every cell after that would have errored.
#
# WHAT IT KILLS, AND WHY THE RULE IS SAFE. Only a process that is (a) an interpreter/compiler by
# name, (b) a DESCENDANT of a live w8-run.exe, and (c) has burned more than $CpuLimit seconds of
# user-mode CPU in its own right. Session 11 verified 224 cells in 2.5 h end to end, so a single
# verifier holding 10 minutes of pure CPU is unambiguous - it cannot be a slow-but-working rust
# build. The ancestry test is what stops it touching LM Studio, the editor, or anything of David's.
#
# It reports progress but never restarts a run: a killed run loses every cell it had measured
# (w8-run writes cells.jsonl in one call at the very end), so healing is always in-place.

param(
    # The repeat loop's log. Progress is read from it; the watchdog never writes to it.
    [string]$Log = 'D:\dev\ABCC_20_powerd_by_claudette\runs\q56\repeat-rd3.log',
    # Progress is counted from the last line matching this, so a relaunch does not re-count an
    # earlier attempt's cells. Set it to whatever banner the loop echoes at start.
    [string]$Marker = 'SESSION 14 RELAUNCH',
    # Seconds of user-mode CPU in one interpreter before it is treated as F57 rather than as work.
    [int]$CpuLimit = 600
)

$ErrorActionPreference = 'Continue'

$Killable = @('python.exe', 'python3.exe', 'node.exe', 'rustc.exe', 'pytest.exe', 'deno.exe')

function Get-TailAfterMarker {
    if (-not (Test-Path $Log)) { return @() }
    $lines = Get-Content -Path $Log -ErrorAction SilentlyContinue
    if (-not $lines) { return @() }
    $idx = -1
    for ($i = $lines.Count - 1; $i -ge 0; $i--) {
        if ($lines[$i] -match $Marker) { $idx = $i; break }
    }
    if ($idx -lt 0) { return $lines }
    return $lines[$idx..($lines.Count - 1)]
}

$seenMarks = 0
"WATCHDOG armed: killing w8-run descendants over ${CpuLimit}s CPU, reloading the model if dropped."

while ($true) {

    # ---- 1. heal a hung verifier (F57) -------------------------------------------------
    $all = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue
    if ($all) {
        $byId = @{}
        foreach ($p in $all) { $byId[[int]$p.ProcessId] = $p }
        $runnerIds = @($all | Where-Object { $_.Name -eq 'w8-run.exe' } | ForEach-Object { [int]$_.ProcessId })

        if ($runnerIds.Count -gt 0) {
            foreach ($p in $all) {
                if ($Killable -notcontains $p.Name) { continue }
                $cpu = [math]::Round($p.UserModeTime / 10000000, 0)
                if ($cpu -le $CpuLimit) { continue }

                # walk up to a live w8-run.exe; bounded so a cycle cannot spin us
                $cur = [int]$p.ParentProcessId
                $isDesc = $false
                for ($d = 0; $d -lt 12; $d++) {
                    if ($cur -eq 0) { break }
                    if ($runnerIds -contains $cur) { $isDesc = $true; break }
                    if (-not $byId.ContainsKey($cur)) { break }
                    $cur = [int]$byId[$cur].ParentProcessId
                }
                if (-not $isDesc) { continue }

                try {
                    Stop-Process -Id $p.ProcessId -Force -ErrorAction Stop
                    "WATCHDOG KILLED hung verifier $($p.Name) pid=$($p.ProcessId) after ${cpu}s CPU - F57. Run resumes; that cell scores fail."
                } catch {
                    "WATCHDOG could not kill pid=$($p.ProcessId): $($_.Exception.Message)"
                }
            }
        }
    }

    # ---- 2. keep the champion loaded ---------------------------------------------------
    try {
        $resp = Invoke-RestMethod -Uri 'http://localhost:1234/api/v0/models' -TimeoutSec 10
        $live = @($resp.data | Where-Object { $_.state -ne 'not-loaded' })
        if ($live.Count -eq 0) {
            "WATCHDOG: LM Studio has NO model loaded - reloading the champion."
            & lms load qwen3.6-35b-a3b-mtp@iq3_s -c 65536 --gpu max --parallel 1 -y 2>&1 | Out-Null
            $again = Invoke-RestMethod -Uri 'http://localhost:1234/api/v0/models' -TimeoutSec 10
            $ok = @($again.data | Where-Object { $_.state -ne 'not-loaded' })
            if ($ok.Count -gt 0) {
                "WATCHDOG: reload OK - $($ok[0].id) ctx=$($ok[0].loaded_context_length)"
            } else {
                "WATCHDOG: RELOAD FAILED - remaining cells will error until a model is loaded."
            }
        }
    } catch { }

    # ---- 3. report progress at each repetition / pause boundary -------------------------
    $tail = Get-TailAfterMarker
    $marks = @($tail | Where-Object { $_ -match '^===== (repetition|cooling)' })
    if ($marks.Count -gt $seenMarks) {
        $cells = @($tail | Where-Object { $_ -match 'first-edit\s+(pass|fail|error|timeout|invalid)' }).Count
        $t = (nvidia-smi --query-gpu=temperature.gpu --format=csv,noheader,nounits 2>$null)
        foreach ($m in $marks[$seenMarks..($marks.Count - 1)]) {
            "$m  [GPU ${t}C, $cells cells done this relaunch]"
        }
        $seenMarks = $marks.Count
    }

    # ---- 4. finished? -------------------------------------------------------------------
    if ($tail | Where-Object { $_ -match '^ALL DONE' }) {
        $errs = @($tail | Where-Object { $_ -match 'spawn: the subject closed' }).Count
        "ALL DONE - three repetitions finished. spawn-errors in this relaunch: $errs"
        break
    }

    Start-Sleep -Seconds 60
}
