# attacker\run_batch.ps1
# Run a series of attacker scripts + a benign operator, then archive events.csv

# Define output directory path for archiving logs
$OutDir = "logs\archive\" + (Get-Date -Format "yyyyMMdd_HHmmss")
New-Item -ItemType Directory -Force -Path $OutDir | Out-Null
Write-Host "Archive dir: $OutDir"

# start benign operator in background job (long running) - it will be stopped later
$benignJob = Start-Job -ScriptBlock { & python attacker\benign_operator.py }
Write-Host ("Started benign operator job (Id: {0})" -f $benignJob.Id)

function Run-Step {
    param($Label, $CommandScript)
    Write-Host ("Running {0}..." -f $Label)
    try {
        & $CommandScript
    } catch {
        Write-Host ("Error running {0}:" -f $Label) -ForegroundColor Red
        Write-Host $_.Exception.Message -ForegroundColor Red
    }
    Start-Sleep -Seconds 2
}

# --- Attack scenarios (run sequentially) ---
Run-Step "recon_probe" { & python attacker\recon_probe.py }

Run-Step "flood_attack (rate=20,duration=15)" { & python attacker\flood_attack.py 20 15 }

Run-Step "cooling_spoof" { & python attacker\cooling_spoof.py }

Run-Step "burst_attack" { & python attacker\burst_attack.py }

# slow_and_low: run synchronously (consider adding short-mode in script)
Write-Host "Running slow_and_low (may be long) ..."
try {
    & python attacker\slow_and_low.py
} catch {
    Write-Host "Error running slow_and_low:" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
}
Start-Sleep -Seconds 2

Run-Step "randomized_attack" { & python attacker\randomized_attack.py }

Run-Step "malformed_payload" { & python attacker\malformed_payload.py }

# Give some extra time for background processes to finish writing logs
Start-Sleep -Seconds 5

# stop benign job (if still running) - compatible across PowerShell versions
if (Get-Job -Id $benignJob.Id -ErrorAction SilentlyContinue) {
    try {
        Stop-Job -Id $benignJob.Id -ErrorAction SilentlyContinue
        Remove-Job -Id $benignJob.Id -ErrorAction SilentlyContinue
        Write-Host "Stopped benign operator job"
    } catch {
        Write-Host ("Failed to stop benign job: {0}" -f $_.Exception.Message) -ForegroundColor Yellow
    }
}

# archive dataset
Copy-Item logs\events.csv "$OutDir\events.csv" -Force

Write-Host "`n[SUCCESS] Saved dataset to $OutDir\events.csv"
Get-Content "$OutDir\events.csv" -Tail 10
