# run_batch_repeat.ps1
# Repeatedly run attacker\run_batch.ps1 N times with a configurable delay.
# Usage: .\run_batch_repeat.ps1 -N 150 -DelaySeconds 3

param(
    [int]$N = 10,
    [int]$DelaySeconds = 3
)

Write-Host "Starting run_batch_repeat: N=$N, DelaySeconds=$DelaySeconds"
for ($i = 1; $i -le $N; $i++) {
    $start = Get-Date
    Write-Host "=== Run $i / $N — START: $start ==="
    try {
        # run the existing orchestrator (it archives to logs\archive)
        .\attacker\run_batch.ps1
    } catch {
        Write-Host "Error during run ${i}: $($_.Exception.Message)" -ForegroundColor Red
    }
    $end = Get-Date
    $dur = [int](($end - $start).TotalSeconds)
    Write-Host "=== Run $i / $N — END: $end (duration: ${dur}s) ==="
    if ($i -lt $N) {
        Write-Host "Sleeping $DelaySeconds seconds before next run..."
        Start-Sleep -Seconds $DelaySeconds
    }
}
Write-Host "Completed all $N runs."
