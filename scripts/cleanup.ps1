# Move test files to tests directory
$testFiles = Get-ChildItem -Path . -Name "test_*.py" -File
foreach ($file in $testFiles) {
    Move-Item -Path $file -Destination "tests\" -Force
    Write-Host "✓ Moved: $file → tests/"
}

# Move documentation files to docs directory  
$docFiles = Get-ChildItem -Path . -Name "*.md" -File
foreach ($file in $docFiles) {
    Move-Item -Path $file -Destination "docs\" -Force
    Write-Host "✓ Moved: $file → docs/"
}

# Move utility/debug scripts to scripts directory
$scriptFiles = @(
    "analyze_code_quality.py",
    "debug_context_injection.py", 
    "debug_registration.py",
    "debug_trend_tools.py",
    "DEPLOYMENT_CHECKLIST.py",
    "generate_cleanup_plan.py",
    "quick_stability_check.py",
    "test_summary.py",
    "TRIGGER_IMPLEMENTATION_FINAL_REPORT.py",
    "verify_all_phase5.py",
    "verify_datetime_fix.py",
    "verify_flexible_modes.py",
    "verify_phase5b_integration.py"
)

foreach ($file in $scriptFiles) {
    if (Test-Path $file) {
        Move-Item -Path $file -Destination "scripts\" -Force
        Write-Host "✓ Moved: $file → scripts/"
    }
}

# List remaining root files
Write-Host "`n=== Root Directory After Cleanup ===" -ForegroundColor Green
Get-ChildItem -Path . -MaxDepth 1 -File | Where-Object { $_.Extension -in @(".py", ".md", ".bat", ".vbs", ".spec") } | ForEach-Object {
    Write-Host "  - $($_.Name)"
}

Write-Host "`n✅ File reorganization complete!"
