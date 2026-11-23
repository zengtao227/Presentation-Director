# Presentation Director installer (per user, Windows PowerShell 5.1+).
# Copies the app to %LOCALAPPDATA%\PresentationDirector, makes sure LibreOffice is present,
# registers the connector and skill with WorkBuddy, and runs a self-test.
param([switch]$Quiet)

$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
[Console]::OutputEncoding = [Text.Encoding]::UTF8
$LoVersion = '26.2.7'
$LoSha256 = '480fecf759fc6393bd614fbf43753eb95a8198fc1a065d41b727e3b664cd1e59'
$LoUrl = "https://download.documentfoundation.org/libreoffice/stable/$LoVersion/win/x86_64/LibreOffice_${LoVersion}_Win_x86-64.msi"

$Src = Join-Path $PSScriptRoot 'files'
$Dest = Join-Path $env:LOCALAPPDATA 'PresentationDirector'
$Log = Join-Path $env:TEMP 'PresentationDirector-install.log'
$Utf8NoBom = New-Object System.Text.UTF8Encoding($false)
Start-Transcript -Path $Log -Force | Out-Null

function Say($text) { Write-Host $text }
function Show-Message($text, $icon) {
    if ($Quiet) { return }
    Add-Type -AssemblyName PresentationFramework
    [System.Windows.MessageBox]::Show($text, 'Presentation Director', 'OK', $icon) | Out-Null
}
function Find-Soffice {
    foreach ($base in @($env:ProgramFiles, ${env:ProgramFiles(x86)})) {
        if (-not $base) { continue }
        $p = Join-Path $base 'LibreOffice\program\soffice.exe'
        if (Test-Path $p) { return $p }
    }
    return $null
}

try {
    Say '[1/4] 复制程序文件…'
    if (-not (Test-Path $Src)) { throw "找不到安装文件夹 $Src。请先把整个压缩包解压，再双击 Setup.cmd。" }
    # A running connector keeps python.exe open; stop only our own copy before replacing files.
    Get-Process python, node -ErrorAction SilentlyContinue |
        Where-Object { $_.Path -and $_.Path.StartsWith($Dest, [StringComparison]::OrdinalIgnoreCase) } |
        Stop-Process -Force -ErrorAction SilentlyContinue
    New-Item -ItemType Directory -Force -Path $Dest | Out-Null
    & robocopy $Src $Dest /MIR /R:2 /W:1 /NFL /NDL /NJH /NJS /NP | Out-Null
    if ($LASTEXITCODE -ge 8) { throw "复制文件失败（robocopy 代码 $LASTEXITCODE）" }
    $Python = Join-Path $Dest 'python\python.exe'
    $Node = Join-Path $Dest 'node\node.exe'

    Say '[2/4] 检查用来逐页预览检查的软件…'
    # PowerPoint or WPS already on the computer does the page renders; LibreOffice is only a fallback.
    # WPS also registers "PowerPoint.Application", so PowerPoint counts only if POWERPNT.EXE answers it.
    $officeApp = $null
    $pptClsid = (Get-ItemProperty 'Registry::HKEY_CLASSES_ROOT\PowerPoint.Application\CLSID' -EA SilentlyContinue).'(default)'
    if ($pptClsid) {
        foreach ($view in @('CLSID', 'WOW6432Node\CLSID')) {
            $server = (Get-ItemProperty "Registry::HKEY_CLASSES_ROOT\$view\$pptClsid\LocalServer32" -EA SilentlyContinue).'(default)'
            if ($server -match 'POWERPNT\.EXE') { $officeApp = 'PowerPoint'; break }
        }
    }
    if (-not $officeApp -and (Test-Path 'Registry::HKEY_CLASSES_ROOT\KWPP.Application')) { $officeApp = 'WPS' }
    $soffice = Find-Soffice
    if ($officeApp) {
        Say "    使用已安装的 $officeApp，无需另装软件"
    } elseif (-not $soffice) {
        Say '    没有找到 PowerPoint 或 WPS，改为安装免费的 LibreOffice'
        $msi = Join-Path $env:TEMP "LibreOffice_${LoVersion}_Win_x86-64.msi"
        $ok = (Test-Path $msi) -and ((Get-FileHash $msi -Algorithm SHA256).Hash -eq $LoSha256)
        if (-not $ok) {
            Say "    正在从 LibreOffice 官方网站下载（约 360 MB，视网速需要几分钟）…"
            try { Start-BitsTransfer -Source $LoUrl -Destination $msi -ErrorAction Stop }
            catch { Invoke-WebRequest -Uri $LoUrl -OutFile $msi -UseBasicParsing }
            if ((Get-FileHash $msi -Algorithm SHA256).Hash -ne $LoSha256) { throw 'LibreOffice 安装包校验失败，请重新运行安装。' }
        }
        Say '    正在安装 LibreOffice（如果 Windows 询问是否允许更改，请点「是」）…'
        # REGISTER_NO_MSO_TYPES=1: do not take over .pptx/.docx/.xlsx, so Office or WPS stays the user's default.
        $msiArgs = @('/i', "`"$msi`"", '/norestart', 'REGISTER_NO_MSO_TYPES=1', $(if ($Quiet) { '/qn' } else { '/passive' }))
        $isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
        if ($isAdmin) { $p = Start-Process msiexec.exe -ArgumentList $msiArgs -Wait -PassThru }
        else { $p = Start-Process msiexec.exe -ArgumentList $msiArgs -Verb RunAs -Wait -PassThru }
        if ($p.ExitCode -notin 0, 3010) { throw "LibreOffice 安装没有完成（代码 $($p.ExitCode)）" }
        $soffice = Find-Soffice
        if (-not $soffice) { throw 'LibreOffice 安装后仍找不到 soffice.exe' }
        Say "    LibreOffice: $soffice"
    }

    Say '[3/4] 接入本机的 AI 工具…'
    $SkillSrc = Join-Path $Dest 'engine\host-skill\SKILL.md'
    $McpEnv = [ordered]@{ PD_NODE = $Node; PYTHONUTF8 = '1' }
    $hosts = @()

    function Set-JsonMcpServer($path, [bool]$withType) {
        $config = [pscustomobject]@{ mcpServers = [pscustomobject]@{} }
        if (Test-Path $path) {
            Copy-Item $path "$path.bak-presentation-director" -Force
            $raw = [IO.File]::ReadAllText($path)
            if ($raw.Trim()) { $config = $raw | ConvertFrom-Json }
            if (-not $config.PSObject.Properties['mcpServers']) { $config | Add-Member mcpServers ([pscustomobject]@{}) }
        }
        $server = [ordered]@{}
        if ($withType) { $server.type = 'stdio' }
        $server.command = $Python
        $server.args = @('-m', 'engine.mcp_server')
        $server.env = [pscustomobject]$McpEnv
        $config.mcpServers | Add-Member -NotePropertyName 'presentation-director' -NotePropertyValue ([pscustomobject]$server) -Force
        [IO.File]::WriteAllText($path, ($config | ConvertTo-Json -Depth 20), $Utf8NoBom)
    }
    function Copy-Skill($skillsRoot) {
        $dir = Join-Path $skillsRoot 'presentation-director'
        New-Item -ItemType Directory -Force -Path $dir | Out-Null
        Copy-Item $SkillSrc (Join-Path $dir 'SKILL.md') -Force
    }

    # WorkBuddy
    $wb = Join-Path $env:USERPROFILE '.workbuddy'
    if (Test-Path $wb) {
        Set-JsonMcpServer (Join-Path $wb 'mcp.json') $true
        Copy-Skill (Join-Path $wb 'skills')
        $hosts += 'WorkBuddy'
    }

    # Codex (CLI and desktop app share ~/.codex/config.toml)
    $codex = Join-Path $env:USERPROFILE '.codex'
    if (Test-Path $codex) {
        $toml = Join-Path $codex 'config.toml'
        $lines = @()
        if (Test-Path $toml) {
            Copy-Item $toml "$toml.bak-presentation-director" -Force
            $skip = $false
            foreach ($line in [IO.File]::ReadAllLines($toml)) {
                if ($line -match '^\s*\[') { $skip = $line -match '^\s*\[mcp_servers\.presentation-director(\]|\.)' }
                if (-not $skip) { $lines += $line }
            }
        }
        # TOML literal strings ('...') keep Windows backslashes as they are.
        $lines += ''
        $lines += '[mcp_servers.presentation-director]'
        $lines += "command = '$Python'"
        $lines += "args = ['-m', 'engine.mcp_server']"
        $lines += "env = { PD_NODE = '$Node', PYTHONUTF8 = '1' }"
        [IO.File]::WriteAllLines($toml, [string[]]$lines, $Utf8NoBom)
        Copy-Skill (Join-Path $codex 'skills')
        $hosts += 'Codex'
    }

    # Claude desktop app
    $claudeDesktop = Join-Path $env:APPDATA 'Claude'
    if (Test-Path $claudeDesktop) {
        Set-JsonMcpServer (Join-Path $claudeDesktop 'claude_desktop_config.json') $false
        $hosts += 'Claude 桌面版'
    }

    # Claude Code: register through its own CLI rather than editing ~/.claude.json directly.
    $claudeCli = Get-Command claude -ErrorAction SilentlyContinue
    if ($claudeCli) {
        $ErrorActionPreference = 'Continue'
        & $claudeCli.Source mcp remove --scope user presentation-director 2>&1 | Out-Null
        & $claudeCli.Source mcp add --scope user presentation-director --env "PD_NODE=$Node" --env 'PYTHONUTF8=1' -- $Python -m engine.mcp_server 2>&1 | Out-Null
        $added = $LASTEXITCODE -eq 0
        $ErrorActionPreference = 'Stop'
        if ($added) {
            Copy-Skill (Join-Path $env:USERPROFILE '.claude\skills')
            $hosts += 'Claude Code'
        }
    }

    $workbuddyNote = ''
    if ($hosts.Count -gt 0) {
        Say ('    已接入：' + ($hosts -join '、'))
    } else {
        $workbuddyNote = "`n`n这台电脑上没有找到 WorkBuddy、Codex 或 Claude。请先安装并打开一次其中之一，再重新运行本安装。"
        Say '    没有找到可接入的 AI 工具（跳过）'
    }

    Say '[4/4] 自检：生成并检查一份样例演示…'
    $env:PD_NODE = $Node
    $env:PYTHONUTF8 = '1'
    if ($soffice) { $env:PD_SOFFICE = $soffice }
    # Windows PowerShell turns any stderr line from a native program into a terminating error under 'Stop'.
    $ErrorActionPreference = 'Continue'
    $out = & $Python -m engine.cli selftest 2>&1 | Out-String
    $ErrorActionPreference = 'Stop'
    $jsonStart = $out.IndexOf('{')
    $report = if ($jsonStart -ge 0) { $out.Substring($jsonStart) | ConvertFrom-Json } else { $null }
    if (-not $report -or -not $report.passed) { throw "自检没有通过：`n$out" }
    Say "    自检通过：$($report.pages) 页，渲染器 $($report.renderer)"

    Stop-Transcript | Out-Null
    Show-Message ("Presentation Director 安装完成。`n`n已接入：$($hosts -join '、')。`n`n下一步：完全退出并重新打开你用的 AI 工具（WorkBuddy 请在「专家·技能·连接器」里确认 presentation-director 已启用，提示「信任」时点信任），然后对它说：用这份资料做一份 PPT。" + $workbuddyNote) 'Information'
    exit 0
} catch {
    Say "安装失败：$($_.Exception.Message)"
    Stop-Transcript | Out-Null
    Show-Message ("安装没有完成：`n$($_.Exception.Message)`n`n安装记录在：$Log") 'Error'
    exit 1
}
