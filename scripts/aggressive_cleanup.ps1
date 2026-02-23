# Complete cleanup of root directory - aggressive removal
# Keep ONLY launcher files and subdirectories

Write-Host "Starting aggressive root directory cleanup..." -ForegroundColor Cyan

# Files to KEEP (entry points only)
$keepFiles = @(
    "koto_app.py",
    "launch.py",
    "Koto.bat",
    "koto.spec",
    "Koto.vbs",
    "requirements.txt",
    ".gitignore",
    "pyvenv.cfg",
    "__init__.py",
    "cleanup.ps1"
)

# Get all root-level files
$allFiles = Get-ChildItem -Path . -File | Where-Object { $_.Name -notin $keepFiles }

Write-Host "`n📋 Files to be removed: $($allFiles.Count)" -ForegroundColor Yellow
Write-Host "Keeping only: $($keepFiles.Count) launcher files`n"

# Categorize files before moving
$toMove = @{
    "tests" = $allFiles | Where-Object { $_.Name -match '^test_.*\.py$' }
    "docs" = $allFiles | Where-Object { $_.Extension -in @(".md") }
    "scripts" = $allFiles | Where-Object { $_.Extension -in @(".py") -and $_.Name -notmatch '^test_' }
    "archive" = $allFiles | Where-Object { $_.Extension -in @(".db", ".log", ".json", ".txt", ".docx", ".cpython-311.pyc") }
    "icons" = $allFiles | Where-Object { $_.Extension -in @(".ico", ".png", ".svg") }
    "build" = $allFiles | Where-Object { $_.Name -match '(build|icon|run|installer)' -and $_.Extension -in @(".py", ".bat", ".ps1") }
}

# Move to tests
if ($toMove["tests"].Count -gt 0) {
    Write-Host "✓ Moving $($toMove['tests'].Count) test files to tests/"
    $toMove["tests"] | ForEach-Object { Move-Item -Path $_.FullName -Destination "tests\" -Force -ErrorAction SilentlyContinue }
}

# Move to docs
if ($toMove["docs"].Count -gt 0) {
    Write-Host "✓ Moving $($toMove['docs'].Count) documentation files to docs/"
    $toMove["docs"] | ForEach-Object { Move-Item -Path $_.FullName -Destination "docs\" -Force -ErrorAction SilentlyContinue }
}

# Move to scripts
if ($toMove["scripts"].Count -gt 0) {
    Write-Host "✓ Moving $($toMove['scripts'].Count) Python scripts to scripts/"
    $toMove["scripts"] | ForEach-Object { Move-Item -Path $_.FullName -Destination "scripts\" -Force -ErrorAction SilentlyContinue }
}

# Move to archive (create if needed)
if ($toMove["archive"].Count -gt 0) {
    if (-not (Test-Path "archive")) {
        New-Item -ItemType Directory -Path "archive" -Force | Out-Null
    }
    Write-Host "✓ Moving $($toMove['archive'].Count) database/log/data files to archive/"
    $toMove["archive"] | ForEach-Object { Move-Item -Path $_.FullName -Destination "archive\" -Force -ErrorAction SilentlyContinue }
}

# Move to icons
if ($toMove["icons"].Count -gt 0) {
    if (-not (Test-Path "resources")) {
        New-Item -ItemType Directory -Path "resources" -Force | Out-Null
    }
    Write-Host "✓ Moving $($toMove['icons'].Count) icon files to resources/"
    $toMove["icons"] | ForEach-Object { Move-Item -Path $_.FullName -Destination "resources\" -Force -ErrorAction SilentlyContinue }
}

# Move to build
if ($toMove["build"].Count -gt 0) {
    if (-not (Test-Path "build")) {
        New-Item -ItemType Directory -Path "build" -Force | Out-Null
    }
    Write-Host "✓ Moving $($toMove['build'].Count) build-related files to build/"
    $toMove["build"] | ForEach-Object { Move-Item -Path $_.FullName -Destination "build\" -Force -ErrorAction SilentlyContinue }
}

# Show final root directory
Write-Host "`n=== ROOT DIRECTORY AFTER CLEANUP ===" -ForegroundColor Green
$finalFiles = Get-ChildItem -Path . -Depth 0 | Where-Object { $_.PSIsContainer -eq $false }
$finalFiles | ForEach-Object {
    Write-Host "  ✓ $($_.Name)"
}

$finalDirs = Get-ChildItem -Path . -Depth 0 | Where-Object { $_.PSIsContainer -eq $true }
Write-Host "`n=== SUBDIRECTORIES ===" -ForegroundColor Green
$finalDirs | ForEach-Object {
    Write-Host "  📁 $($_.Name)"
}

Write-Host "`n✅ Root directory cleanup complete!" -ForegroundColor Green
Write-Host "📊 Summary:"
Write-Host "  Files in root: $($finalFiles.Count)"
Write-Host "  Subdirectories: $($finalDirs.Count)"
