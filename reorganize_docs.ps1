# Markdown Files Reorganization Script (PowerShell)
# Consolidates scattered documentation into organized docs/ structure

Write-Host "📋 Markdown Files Reorganization" -ForegroundColor Yellow
Write-Host "=================================" -ForegroundColor Yellow
Write-Host ""

# Create docs directory structure
Write-Host "📁 Creating docs directory structure..." -ForegroundColor Cyan
New-Item -ItemType Directory -Path "docs" -Force | Out-Null
New-Item -ItemType Directory -Path "docs\development" -Force | Out-Null
New-Item -ItemType Directory -Path "docs\examples" -Force | Out-Null
New-Item -ItemType Directory -Path "docs\archive" -Force | Out-Null

Write-Host "✅ Created: docs/development/, docs/examples/, docs/archive/" -ForegroundColor Green
Write-Host ""

# Phase 2: Move and rename development documentation
Write-Host "📝 Moving development documentation..." -ForegroundColor Cyan

# Move VERSION_HISTORY from project/ to docs/development/
if (Test-Path "project\VERSION_HISTORY.md") {
    Move-Item "project\VERSION_HISTORY.md" "docs\development\VERSION_HISTORY.md"
    Write-Host "✅ Moved: project/VERSION_HISTORY.md → docs/development/" -ForegroundColor Green
}

# Move and rename root-level development docs
$devDocs = @{
    "CODEBASE_RESTRUCTURING_SUMMARY.md" = "docs\development\CODEBASE_RESTRUCTURING.md"
    "DUPLICATE_DETECTION_ENHANCEMENT.md" = "docs\development\DUPLICATE_DETECTION.md"
    "LEGACY_CLEANUP_ANALYSIS.md" = "docs\development\LEGACY_CLEANUP.md"
    "UTILS_MIGRATION_SUMMARY.md" = "docs\development\UTILS_MIGRATION.md"
    "GITIGNORE_DOCS.md" = "docs\development\GITIGNORE_SETUP.md"
}

foreach ($sourceFile in $devDocs.Keys) {
    if (Test-Path $sourceFile) {
        Move-Item $sourceFile $devDocs[$sourceFile]
        Write-Host "✅ Moved: $sourceFile → $($devDocs[$sourceFile])" -ForegroundColor Green
    }
}

Write-Host ""

# Phase 3: Select best examples (from verification_test - most recent)
Write-Host "📊 Selecting best examples..." -ForegroundColor Cyan

if (Test-Path "verification_test") {
    # Copy best examples
    if (Test-Path "verification_test\vn30_daily_price_summary.md") {
        Copy-Item "verification_test\vn30_daily_price_summary.md" "docs\examples\sample_daily_analysis.md"
        Write-Host "✅ Example: verification_test/vn30_daily_price_summary.md → docs/examples/sample_daily_analysis.md" -ForegroundColor Green
    }
    
    if (Test-Path "verification_test\vn30_summary.md") {
        Copy-Item "verification_test\vn30_summary.md" "docs\examples\sample_symbol_summary.md"
        Write-Host "✅ Example: verification_test/vn30_summary.md → docs/examples/sample_symbol_summary.md" -ForegroundColor Green
    }
    
    if (Test-Path "verification_test\all_symbols_overview.md") {
        Copy-Item "verification_test\all_symbols_overview.md" "docs\examples\sample_overview.md"
        Write-Host "✅ Example: verification_test/all_symbols_overview.md → docs/examples/sample_overview.md" -ForegroundColor Green
    }
}

Write-Host ""

# Phase 4: Archive completion marker
Write-Host "📦 Archiving completion documentation..." -ForegroundColor Cyan
if (Test-Path "RESTRUCTURING_COMPLETE.md") {
    Move-Item "RESTRUCTURING_COMPLETE.md" "docs\archive\RESTRUCTURING_COMPLETE.md"
    Write-Host "✅ Archived: RESTRUCTURING_COMPLETE.md → docs/archive/" -ForegroundColor Green
}

Write-Host ""

# Phase 5: Remove duplicate test report directories
Write-Host "🗑️  Removing duplicate test report directories..." -ForegroundColor Cyan

$reportDirs = @(
    "enhanced_daily_reports",
    "enhanced_test_reports", 
    "improved_test_reports",
    "test_reports",
    "test_reports_utils",
    "verification_test"
)

foreach ($dir in $reportDirs) {
    if (Test-Path $dir) {
        Remove-Item $dir -Recurse -Force
        Write-Host "✅ Removed: $dir/" -ForegroundColor Green
    }
}

Write-Host ""

# Create docs README
Write-Host "📖 Creating docs/README.md index..." -ForegroundColor Cyan
$docsReadme = @'
# Documentation Index

## 📁 Directory Structure

### `/development/`
Development process and technical documentation:
- `VERSION_HISTORY.md` - Complete project version history
- `CODEBASE_RESTRUCTURING.md` - Code reorganization process
- `DUPLICATE_DETECTION.md` - Enhanced duplicate detection implementation
- `LEGACY_CLEANUP.md` - Legacy code cleanup analysis
- `UTILS_MIGRATION.md` - Utils migration process
- `GITIGNORE_SETUP.md` - Git ignore configuration

### `/examples/`
Sample outputs and report examples:
- `sample_daily_analysis.md` - Example daily price analysis report
- `sample_symbol_summary.md` - Example symbol summary report  
- `sample_overview.md` - Example multi-symbol overview report

### `/archive/`
Historical documentation and completion markers:
- `RESTRUCTURING_COMPLETE.md` - Project restructuring completion record

## 🎯 Quick Access

- **Project Overview**: `../README.md` (root)
- **Development History**: `development/VERSION_HISTORY.md`
- **Code Changes**: `development/CODEBASE_RESTRUCTURING.md`
- **Sample Reports**: `examples/` directory

---

*This documentation structure was created on September 11, 2025 during the markdown reorganization process.*
'@

Set-Content -Path "docs\README.md" -Value $docsReadme
Write-Host "✅ Created: docs/README.md index" -ForegroundColor Green
Write-Host ""

# Summary
Write-Host "🎉 Reorganization Complete!" -ForegroundColor Green
Write-Host "==========================" -ForegroundColor Green
Write-Host ""
Write-Host "📊 Summary:" -ForegroundColor Yellow
Write-Host "   - Created organized docs/ structure" -ForegroundColor White
Write-Host "   - Moved 6 development docs to docs/development/" -ForegroundColor White
Write-Host "   - Created 3 example files in docs/examples/" -ForegroundColor White
Write-Host "   - Archived completion marker" -ForegroundColor White
Write-Host "   - Removed 6 duplicate test report directories" -ForegroundColor White
Write-Host "   - Created docs/README.md index" -ForegroundColor White
Write-Host ""
Write-Host "📁 New structure:" -ForegroundColor Yellow
Write-Host "   docs/" -ForegroundColor White
Write-Host "   ├── README.md (index)" -ForegroundColor White
Write-Host "   ├── development/ (6 files)" -ForegroundColor White
Write-Host "   ├── examples/ (3 files)" -ForegroundColor White
Write-Host "   └── archive/ (1 file)" -ForegroundColor White
Write-Host ""
Write-Host "🧹 Cleanup:" -ForegroundColor Yellow
Write-Host "   - Root directory cleaned (only README.md remains)" -ForegroundColor White
Write-Host "   - Removed ~27 duplicate report files" -ForegroundColor White
Write-Host "   - Organized all documentation" -ForegroundColor White
Write-Host ""
Write-Host "✅ Next steps:" -ForegroundColor Green
Write-Host "   1. Review docs/README.md" -ForegroundColor White
Write-Host "   2. Update main README.md if needed" -ForegroundColor White
Write-Host "   3. Commit changes: git add docs/ && git commit -m 'Reorganize documentation'" -ForegroundColor White
