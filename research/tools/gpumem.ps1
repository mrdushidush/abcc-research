$procid = (Get-CimInstance Win32_Process -Filter "Name='llama-server.exe'").ProcessId
if (-not $procid) { Write-Output "no llama-server running"; exit 1 }
Write-Output "llama-server pid = $procid"
$all = (Get-Counter -ListSet 'GPU Process Memory').PathsWithInstances
$mine = $all | Where-Object { $_ -like "*pid_${procid}_*" }
Write-Output ("matching counter instances: {0} (of {1} total)" -f $mine.Count, $all.Count)
if ($mine.Count -eq 0) {
  Write-Output "NO INSTANCES MATCHED -- instrument cannot see this process; do not read 0 as a measurement"
  $all | Select-Object -First 4 | ForEach-Object { Write-Output "  sample path: $_" }
  exit 2
}
$s = Get-Counter -Counter $mine -ErrorAction Stop
foreach ($grp in @('Dedicated Usage','Shared Usage','Total Committed')) {
  $sum = ($s.CounterSamples | Where-Object { $_.Path -like "*$grp*" } |
          Measure-Object -Property CookedValue -Sum).Sum
  Write-Output ("  {0,-18} {1,10:N0} MiB" -f $grp, ($sum/1MB))
}
