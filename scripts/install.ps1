<#
.SYNOPSIS
    远程一键安装 toolbox 技能到项目或 AI 编程工具（平铺模式）。

.DESCRIPTION
    从远程下载 toolbox 仓库（git clone），运行 install_skills.py 将技能
    安装到指定位置。等同于：
        python install_skills.py [参数]

    用法（PowerShell 管道）：
        irm https://你的域名/path/to/install.ps1 | iex

    或下载到本地执行：
        curl.exe -LO https://你的域名/path/to/install.ps1
        .\install.ps1 -To claude -Common

.PARAMETER Target
    目标项目目录（默认：当前目录）
.PARAMETER Dir
    目标目录名，仅项目模式有效（默认：skills）
.PARAMETER To
    安装到 AI 工具全局目录：claudecode, cursor, workbuddy, windsurf, trae, atomcode, codex
.PARAMETER Global
    自动检测本机已安装的 AI 工具并安装
.PARAMETER Category
    只安装指定分类（如 code-quality）
.PARAMETER Skills
    只安装指定技能（逗号分隔）
.PARAMETER Common
    安装常用技能（14 个核心开发技能）
.PARAMETER Interactive
    交互式选择技能
.PARAMETER Force
    覆盖已有目录
.PARAMETER DryRun
    预览操作，不实际复制
.PARAMETER RepoUrl
    toolbox 仓库地址（默认：$Script:DefaultRepoUrl）
.PARAMETER Branch
    仓库分支（默认：main）
.PARAMETER CleanCache
    清理缓存后重新下载

.EXAMPLE
    irm https://raw.atomgit.com/atomgit_atomcode/atomcode/raw/main/scripts/install.ps1 | iex
.EXAMPLE
    irm https://raw.atomgit.com/atomgit_atomcode/atomcode/raw/main/scripts/install.ps1 | iex
    iex "& { $(irm https://...) } -To claude -Common"
#>

param(
    [string]$Target = "",
    [string]$Dir = "skills",
    [string]$To = "",
    [switch]$Global = $false,
    [string]$Category = "",
    [string]$Skills = "",
    [switch]$Common = $false,
    [switch]$Interactive = $false,
    [switch]$Force = $false,
    [switch]$DryRun = $false,
    [string]$RepoUrl = "",
    [string]$Branch = "main",
    [switch]$CleanCache = $false
)

# ── 默认配置 ─────────────────────────────────────────────
$Script:DefaultRepoUrl = "https://github.com/atomgit-atomcode/toolbox"

# ── 工具函数 ─────────────────────────────────────────────

function Write-Banner {
    Write-Host "╔══════════════════════════════════════════╗" -ForegroundColor Cyan
    Write-Host "║   Toolbox Skills Installer (PowerShell)  ║" -ForegroundColor Cyan
    Write-Host "╚══════════════════════════════════════════╝" -ForegroundColor Cyan
}

function Get-ToolboxDir {
    $cacheBase = Join-Path $env:TEMP "toolbox"
    if (-not (Test-Path $cacheBase)) {
        New-Item -ItemType Directory -Path $cacheBase -Force | Out-Null
    }
    return $cacheBase
}

function Ensure-Toolbox {
    param([string]$RepoUrl, [string]$Branch, [switch]$Clean)

    $toolboxDir = Get-ToolboxDir
    $repoDir = Join-Path $toolboxDir "repo"

    if ($Clean -and (Test-Path $repoDir)) {
        Write-Host "🧹 清理缓存..." -ForegroundColor Yellow
        Remove-Item -Recurse -Force $repoDir -ErrorAction SilentlyContinue
    }

    if (Test-Path (Join-Path $repoDir "install_skills.py")) {
        Write-Host "📦 使用缓存: $repoDir" -ForegroundColor Green
        # Try to update
        try {
            Push-Location $repoDir
            git pull --ff-only 2>$null | Out-Null
            Pop-Location
            Write-Host "↻ 已更新到最新" -ForegroundColor Green
        } catch {
            Write-Host "⚠ 更新失败，继续使用缓存版本" -ForegroundColor Yellow
            Pop-Location
        }
    } else {
        Write-Host "📥 下载 toolbox 从 $RepoUrl ..." -ForegroundColor Yellow
        try {
            git clone --depth 1 --branch $Branch $RepoUrl $repoDir 2>&1 | Out-Null
            if ($LASTEXITCODE -ne 0) { throw "git clone 失败" }
            Write-Host "✓ 下载完成" -ForegroundColor Green
        } catch {
            Write-Error "下载失败: $_"
            exit 1
        }
    }

    return $repoDir
}

# ── 入口 ─────────────────────────────────────────────────

function Main {
    Write-Banner

    # 仓库 URL：优先参数 > 环境变量 > 默认
    $effectiveRepoUrl = $RepoUrl
    if ([string]::IsNullOrEmpty($effectiveRepoUrl)) {
        $effectiveRepoUrl = [Environment]::GetEnvironmentVariable("TOOLBOX_REPO", "User")
    }
    if ([string]::IsNullOrEmpty($effectiveRepoUrl)) {
        $effectiveRepoUrl = [Environment]::GetEnvironmentVariable("TOOLBOX_REPO", "Machine")
    }
    if ([string]::IsNullOrEmpty($effectiveRepoUrl)) {
        $effectiveRepoUrl = $Script:DefaultRepoUrl
    }

    # 下载/更新 toolbox
    $repoDir = Ensure-Toolbox -RepoUrl $effectiveRepoUrl -Branch $Branch -Clean:$CleanCache

    # 构建 install_skills.py 参数
    $pyArgs = @()

    if ($Target) {
        $pyArgs += "--target"; $pyArgs += $Target
    } else {
        $pyArgs += "--target"; $pyArgs += (Get-Location).Path
    }

    if ($Dir -ne "skills") {
        $pyArgs += "--dir"; $pyArgs += $Dir
    }

    if ($To) {
        $pyArgs += "--to"; $pyArgs += $To
    }
    if ($Global) {
        $pyArgs += "--global"
    }
    if ($Category) {
        $pyArgs += "--category"; $pyArgs += $Category
    }
    if ($Skills) {
        $pyArgs += "--skills"; $pyArgs += $Skills
    }
    if ($Common) {
        $pyArgs += "--common"
    }
    if ($Interactive) {
        $pyArgs += "--interactive"
    }
    if ($Force) {
        $pyArgs += "--force"
    }
    if ($DryRun) {
        $pyArgs += "--dry-run"
    }

    # 如果没有指定任何技能选择，默认 --common
    $hasSkillSelection = $Category -or $Skills -or $Common -or $Interactive
    if (-not $hasSkillSelection) {
        $pyArgs += "--common"
    }

    $installScript = Join-Path $repoDir "install_skills.py"

    if (-not (Test-Path $installScript)) {
        Write-Error "未找到 install_skills.py，请检查仓库地址"
        exit 1
    }

    Write-Host "`n🚀 运行: python install_skills.py $($pyArgs -join ' ')" -ForegroundColor Cyan
    Write-Host ""

    # 设置 TOOLBOX_PATH 确保脚本能找到 skills/
    $env:TOOLBOX_PATH = $repoDir

    & python $installScript @pyArgs

    $exitCode = $LASTEXITCODE
    if ($exitCode -ne 0) {
        Write-Host "❌ 安装失败 (exit: $exitCode)" -ForegroundColor Red
    } else {
        Write-Host "`n✅ 安装完成" -ForegroundColor Green
    }

    exit $exitCode
}

Main
