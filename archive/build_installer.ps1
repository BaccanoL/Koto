# Koto 应用 - PowerShell 安装包生成脚本
# 如果在执行窗口打开时看到错误，请在 PowerShell 中运行此脚本

param(
    [switch]$SkipDeps = $false,
    [switch]$SkipZip = $false,
    [switch]$SkipNSIS = $false,
    [string]$PythonPath = $null
)

# 配置
$APP_NAME = "Koto"
$APP_VERSION = "1.0.0"
$SCRIPT_DIR = Split-Path -Parent $MyInvocation.MyCommand.Path
$TIMESTAMP = Get-Date -Format "yyyy-MM-dd HH:mm:ss"

# 颜色输出
function Write-Status {
    param(
        [string]$Message,
        [ValidateSet("Success", "Error", "Warning", "Info")]
        [string]$Type = "Info"
    )
    
    $colors = @{
        "Success" = "Green"
        "Error" = "Red"
        "Warning" = "Yellow"
        "Info" = "Cyan"
    }
    
    Write-Host "[$($colors[$Type])][$TIMESTAMP]$Message" -ForegroundColor $colors[$Type]
}

function Write-Section {
    param([string]$Title)
    Write-Host ""
    Write-Host ("=" * 60) -ForegroundColor Cyan
    Write-Host "  $Title" -ForegroundColor Cyan
    Write-Host ("=" * 60) -ForegroundColor Cyan
}

# Main 逻辑
Write-Host ""
Write-Host "╔════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║                                                            ║" -ForegroundColor Cyan
Write-Host "║         Koto 应用 - Windows 安装包生成器                  ║" -ForegroundColor Cyan
Write-Host "║                                                            ║" -ForegroundColor Cyan
Write-Host "╚════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

Write-Section "初始化"

# 检查 Python
if ($PythonPath -and (Test-Path $PythonPath)) {
    $python = $PythonPath
} else {
    $python = (Get-Command python -ErrorAction SilentlyContinue).Source
}

if (-not $python) {
    Write-Status "Python 未找到！请先安装 Python 3.8+" -Type "Error"
    Write-Status "访问: https://www.python.org/downloads/" -Type "Info"
    exit 1
}

Write-Status "✅ 找到 Python: $python" -Type "Success"

# 验证版本
$pythonVersion = & $python --version
Write-Status "版本: $pythonVersion" -Type "Success"

# 切换到项目目录
Push-Location $SCRIPT_DIR
Write-Status "工作目录: $SCRIPT_DIR" -Type "Success"

# 创建/激活虚拟环境
Write-Section "配置虚拟环境"

if (-not (Test-Path ".venv")) {
    Write-Status "创建虚拟环境..." -Type "Info"
    & $python -m venv .venv
    if ($LASTEXITCODE -ne 0) {
        Write-Status "虚拟环境创建失败" -Type "Error"
        exit 1
    }
}

Write-Status "✅ 虚拟环境已配置" -Type "Success"

# 激活虚拟环境
$activateScript = ".venv\Scripts\Activate.ps1"
if (Test-Path $activateScript) {
    & $activateScript
    Write-Status "✅ 虚拟环境已激活" -Type "Success"
} else {
    Write-Status "虚拟环境激活脚本未找到" -Type "Error"
    exit 1
}

# 安装依赖
if (-not $SkipDeps) {
    Write-Section "安装依赖"
    
    Write-Status "升级 pip..." -Type "Info"
    pip install --upgrade pip setuptools wheel wheel-cli -q
    
    Write-Status "安装 PyInstaller..." -Type "Info"
    pip install pyinstaller -q
    
    if ($LASTEXITCODE -eq 0) {
        Write-Status "✅ 所有依赖已安装" -Type "Success"
    } else {
        Write-Status "⚠️  某些依赖安装失败，继续尝试..." -Type "Warning"
    }
} else {
    Write-Status "⏭️  跳过依赖安装" -Type "Warning"
}

# 运行 Python 构建脚本
Write-Section "生成安装包"

Write-Status "执行 Python 构建脚本..." -Type "Info"
python build_installer.py

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "╔════════════════════════════════════════════════════════════╗" -ForegroundColor Green
    Write-Host "║                    ✅ 完成！                              ║" -ForegroundColor Green
    Write-Host "╚════════════════════════════════════════════════════════════╝" -ForegroundColor Green
    Write-Host ""
    
    $installerPath = Join-Path $SCRIPT_DIR "installer"
    if (Test-Path $installerPath) {
        Write-Status "📁 安装包位置: $installerPath" -Type "Success"
        Write-Status "📦 文件列表:" -Type "Info"
        
        Get-ChildItem $installerPath -File | ForEach-Object {
            $size = [math]::Round($_.Length / 1MB, 2)
            Write-Host "   • $($_.Name) ($size MB)"
        }
    }
    
    Write-Host ""
    Write-Status "👉 下一步: 复制安装包到任意 Windows 电脑即可使用" -Type "Success"
    
} else {
    Write-Status "安装包生成失败！" -Type "Error"
    exit 1
}

Pop-Location
