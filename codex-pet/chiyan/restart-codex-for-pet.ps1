$ErrorActionPreference = 'Stop'
$logPath = 'D:\deskpet\codex-pet\chiyan\qa\restart-result.txt'
Start-Sleep -Seconds 4
try {
    Get-Process -Name ChatGPT -ErrorAction SilentlyContinue | Stop-Process -Force
    Start-Sleep -Seconds 3
    Start-Process -FilePath 'C:\Users\windows\AppData\Local\Programs\Codex\LaunchCodex.exe' -WindowStyle Normal
    Start-Sleep -Seconds 6
    $running = @(Get-Process -Name ChatGPT -ErrorAction SilentlyContinue)
    "restarted_at=$((Get-Date).ToString('o'))" | Set-Content -LiteralPath $logPath
    "process_count=$($running.Count)" | Add-Content -LiteralPath $logPath
    "selected_avatar=$((Get-Content -Raw 'C:\Users\windows\.codex\config.toml' | Select-String -Pattern 'selected-avatar-id = ""custom:chiyan""').Matches.Count)" | Add-Content -LiteralPath $logPath
}
catch {
    "error=$($_.Exception.Message)" | Set-Content -LiteralPath $logPath
}
