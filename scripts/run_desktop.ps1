# ==================== Koto Desktop PowerShell 启动脚本 ====================
# 为 PowerShell 用户提供的启动脚本
# 功能：检查环境、安装依赖、启动应用

param(
    [switch]$NoDepCheck,  # 跳过依赖检查
    [string]$PythonPath   # 自定义 Python 路径
)

# 设置编码
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::UTF8

# 颜色定义
$Green = [System.ConsoleColor]::Green
$Yellow = [System.ConsoleColor]::Yellow
$Red = [System.ConsoleColor]::Red
$Cyan = [System.ConsoleColor]::Cyan

function Write-Header {
    param([string]$Message)
    Write-Host ""
    Write-Host ("=" * 60) -ForegroundColor $Cyan
    Write-Host "  $Message" -ForegroundColor $Cyan
    Write-Host ("=" * 60) -ForegroundColor $Cyan
    Write-Host ""
}

function Write-Step {
    param([int]$Step, [string]$Message)
    Write-Host "[$Step/3] $Message..." -ForegroundColor $Cyan
}

function Write-Success {
    param([string]$Message)
    Write-Host "  ✓ $Message" -ForegroundColor $Green
}

function Write-Error {
    param([string]$Message)
    Write-Host "  ✗ $Message" -ForegroundColor $Red
}

function Write-Warning {
    param([string]$Message)
    Write-Host "  ⚠ $Message" -ForegroundColor $Yellow
}

# 获取脚本所在目录
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

Write-Header "Koto Desktop 应用启动器"

# 检查 Python
Write-Step 1 "检查 Python 环境"

if ($PythonPath -and (Test-Path $PythonPath)) {
    $Python = $PythonPath
    Write-Success "使用指定的 Python: $PythonPath"
} else {
    $Python = (Get-Command python -ErrorAction SilentlyContinue).Source
    if (-not $Python) {
        Write-Error "未找到 Python"
        Write-Host ""
        Write-Host "请从以下网址下载 Python 3.8+:"
        Write-Host "  https://www.python.org/downloads/"
        Write-Host ""
        Write-Host "安装时请勾选 'Add Python to PATH'"
        Write-Host ""
        exit 1
    }
    Write-Success "Python 已找到: $Python"
}

# 验证版本
& $Python --version

# 检查依赖
if (-not $NoDepCheck) {
    Write-Step 2 "检查依赖"
    
    $Result = & $Python -c "import PySide6; print('OK')" 2>&1
    
    if ($Result -ne "OK") {
        Write-Warning "PySide6 未安装，正在安装..."
        
        if (-not (Test-Path ".venv")) {
            Write-Host "  创建虚拟环境..."
            & $Python -m venv .venv
            if ($LASTEXITCODE -ne 0) {
                Write-Error "虚拟环境创建失败"
                exit 1
            }
            Write-Success "虚拟环境已创建"
        }
        
        # 激活虚拟环境
        & ".\\.venv\Scripts\Activate.ps1"
        
        Write-Host "  安装依赖中..." -ForegroundColor $Yellow
        & pip install -q -r requirements.txt
        if ($LASTEXITCODE -ne 0) {
            Write-Error "依赖安装失败"
            exit 1
        }
    }
    
    Write-Success "所有依赖已就绪"
} else {
    Write-Success "跳过依赖检查"
}

# 准备环境
Write-Step 3 "准备环境"

if (-not (Test-Path "logs")) {
    New-Item -ItemType Directory -Path "logs" -Force | Out-Null
    Write-Success "日志目录已创建"
} else {
    Write-Success "日志目录已就绪"
}

# 启动应用
Write-Host ""
Write-Host "✓ 所有检查完成，正在启动 Koto Desktop..." -ForegroundColor $Green
Write-Host "  ⏳ 应用正在启动，请稍候..." -ForegroundColor $Yellow
Write-Host ""

& $Python koto_desktop.py

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Error "应用启动失败"
    Write-Host ""
}
