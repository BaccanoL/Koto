<#
.SYNOPSIS
    Koto 标准回归测试运行器
    
.DESCRIPTION
    运行核心测试套件，验证系统功能完整性
    覆盖 Phase 2-5 的所有核心功能测试
    
.PARAMETER Verbose
    显示详细测试输出
    
.PARAMETER QuickCheck
    仅运行快速检查（不运行完整测试套件）
    
.EXAMPLE
    .\run_regression.ps1
    运行标准回归测试
    
.EXAMPLE
    .\run_regression.ps1 -Verbose
    运行详细模式的回归测试
#>

param(
    [switch]$Verbose,
    [switch]$QuickCheck
)

$ErrorActionPreference = "Continue"
$ProjectRoot = Split-Path -Parent (Split-Path -Parent $PSCommandPath)
Set-Location $ProjectRoot

Write-Host ""
Write-Host "════════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  Koto 标准回归测试" -ForegroundColor Cyan
Write-Host "════════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""
Write-Host "📍 项目目录: $ProjectRoot" -ForegroundColor Gray
Write-Host "📅 测试时间: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" -ForegroundColor Gray
Write-Host ""

# 检查 Python 环境
$pythonVersion = & python --version 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Python 未找到，请确保 Python 已安装并在 PATH 中" -ForegroundColor Red
    exit 1
}
Write-Host "✅ Python: $pythonVersion" -ForegroundColor Green

# 检查虚拟环境（可选）
if (Test-Path ".venv\Scripts\Activate.ps1") {
    Write-Host "💡 检测到虚拟环境 (.venv)" -ForegroundColor Yellow
    Write-Host "   提示: 运行 '.venv\Scripts\Activate.ps1' 激活虚拟环境" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "────────────────────────────────────────────────────────────────" -ForegroundColor DarkGray

# Quick Check 模式
if ($QuickCheck) {
    Write-Host ""
    Write-Host "⚡ 快速检查模式" -ForegroundColor Yellow
    Write-Host ""
    
    # 仅运行一个快速测试
    Write-Host "🧪 运行快速验证..." -ForegroundColor Cyan
    $result = & python -m unittest tests.test_phase2_regression.TestFactory.test_create_agent_has_all_tools 2>&1
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ 快速检查通过" -ForegroundColor Green
        exit 0
    } else {
        Write-Host "❌ 快速检查失败" -ForegroundColor Red
        Write-Host $result
        exit 1
    }
}

# 标准回归测试
Write-Host ""
Write-Host "🧪 运行核心测试套件 (Phase 2-5)" -ForegroundColor Cyan
Write-Host ""

$testPattern = "test_phase*.py"
$verboseFlag = if ($Verbose) { "-v" } else { "" }

# 运行测试
$startTime = Get-Date
$testOutput = & python -m unittest discover -s tests -p $testPattern $verboseFlag 2>&1
$exitCode = $LASTEXITCODE
$duration = (Get-Date) - $startTime

# 输出测试结果
Write-Host $testOutput

Write-Host ""
Write-Host "────────────────────────────────────────────────────────────────" -ForegroundColor DarkGray
Write-Host ""

# 解析结果
$ranMatch = $testOutput | Select-String -Pattern "Ran (\d+) tests? in ([\d.]+)s"
$okMatch = $testOutput | Select-String -Pattern "^OK$"
$failedMatch = $testOutput | Select-String -Pattern "FAILED"

if ($ranMatch) {
    $testCount = $ranMatch.Matches.Groups[1].Value
    $testTime = $ranMatch.Matches.Groups[2].Value
    Write-Host "📊 测试统计:" -ForegroundColor Cyan
    Write-Host "   总测试数: $testCount" -ForegroundColor White
    Write-Host "   运行时间: $testTime 秒" -ForegroundColor White
}

Write-Host ""
if ($exitCode -eq 0 -and $okMatch) {
    Write-Host "════════════════════════════════════════════════════════════════" -ForegroundColor Green
    Write-Host "  ✅ 所有测试通过！" -ForegroundColor Green
    Write-Host "════════════════════════════════════════════════════════════════" -ForegroundColor Green
    Write-Host ""
    Write-Host "✨ 系统状态: 生产就绪" -ForegroundColor Green
    Write-Host ""
    exit 0
} else {
    Write-Host "════════════════════════════════════════════════════════════════" -ForegroundColor Red
    Write-Host "  ❌ 测试失败" -ForegroundColor Red
    Write-Host "════════════════════════════════════════════════════════════════" -ForegroundColor Red
    Write-Host ""
    Write-Host "💡 提示:" -ForegroundColor Yellow
    Write-Host "   1. 查看上方错误信息" -ForegroundColor White
    Write-Host "   2. 运行 '.\scripts\run_regression.ps1 -Verbose' 查看详细输出" -ForegroundColor White
    Write-Host "   3. 检查 docs\TEST_DEPENDENCIES.md 了解测试依赖" -ForegroundColor White
    Write-Host ""
    exit 1
}
