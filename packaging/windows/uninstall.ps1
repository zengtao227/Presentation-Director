# Removes Presentation Director for the current user. Decks in Documents\Presentation Director are kept.
$ErrorActionPreference = 'Continue'
$Dest = Join-Path $env:LOCALAPPDATA 'PresentationDirector'
$wb = Join-Path $env:USERPROFILE '.workbuddy'
$mcpPath = Join-Path $wb 'mcp.json'
if (Test-Path $mcpPath) {
    $config = [IO.File]::ReadAllText($mcpPath) | ConvertFrom-Json
    if ($config.mcpServers -and $config.mcpServers.PSObject.Properties['presentation-director']) {
        $config.mcpServers.PSObject.Properties.Remove('presentation-director')
        [IO.File]::WriteAllText($mcpPath, ($config | ConvertTo-Json -Depth 20), (New-Object System.Text.UTF8Encoding($false)))
    }
}
Remove-Item (Join-Path $wb 'skills\presentation-director') -Recurse -Force -ErrorAction SilentlyContinue
$claudeDesktopCfg = Join-Path $env:APPDATA 'Claude\claude_desktop_config.json'
if (Test-Path $claudeDesktopCfg) {
    $config = [IO.File]::ReadAllText($claudeDesktopCfg) | ConvertFrom-Json
    if ($config.mcpServers -and $config.mcpServers.PSObject.Properties['presentation-director']) {
        $config.mcpServers.PSObject.Properties.Remove('presentation-director')
        [IO.File]::WriteAllText($claudeDesktopCfg, ($config | ConvertTo-Json -Depth 20), (New-Object System.Text.UTF8Encoding($false)))
    }
}
$toml = Join-Path $env:USERPROFILE '.codex\config.toml'
if (Test-Path $toml) {
    $keep = @(); $skip = $false
    foreach ($line in [IO.File]::ReadAllLines($toml)) {
        if ($line -match '^\s*\[') { $skip = $line -match '^\s*\[mcp_servers\.presentation-director(\]|\.)' }
        if (-not $skip) { $keep += $line }
    }
    [IO.File]::WriteAllLines($toml, [string[]]$keep, (New-Object System.Text.UTF8Encoding($false)))
}
Remove-Item (Join-Path $env:USERPROFILE '.codex\skills\presentation-director') -Recurse -Force -ErrorAction SilentlyContinue
$claudeCli = Get-Command claude -ErrorAction SilentlyContinue
if ($claudeCli) { & $claudeCli.Source mcp remove --scope user presentation-director 2>&1 | Out-Null }
Remove-Item (Join-Path $env:USERPROFILE '.claude\skills\presentation-director') -Recurse -Force -ErrorAction SilentlyContinue
Get-Process python, node -ErrorAction SilentlyContinue |
    Where-Object { $_.Path -and $_.Path.StartsWith($Dest, [StringComparison]::OrdinalIgnoreCase) } |
    Stop-Process -Force
# Leave the install folder first so it is not the current directory while it is removed.
Set-Location $env:TEMP
Remove-Item $Dest -Recurse -Force
Write-Host 'Presentation Director 已卸载。你做的演示文稿仍保存在「文档\Presentation Director」。'
