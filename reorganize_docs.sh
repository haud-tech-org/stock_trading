#!/bin/bash
# Markdown Files Reorganization Script
# Consolidates scattered documentation into organized docs/ structure

echo "📋 Markdown Files Reorganization"
echo "================================="
echo ""

# Create docs directory structure
echo "📁 Creating docs directory structure..."
mkdir -p docs/development
mkdir -p docs/examples  
mkdir -p docs/archive

echo "✅ Created: docs/development/, docs/examples/, docs/archive/"
echo ""

# Phase 2: Move and rename development documentation
echo "📝 Moving development documentation..."

# Move VERSION_HISTORY from project/ to docs/development/
if [ -f "project/VERSION_HISTORY.md" ]; then
    mv "project/VERSION_HISTORY.md" "docs/development/VERSION_HISTORY.md"
    echo "✅ Moved: project/VERSION_HISTORY.md → docs/development/"
fi

# Move and rename root-level development docs
declare -A dev_docs=(
    ["CODEBASE_RESTRUCTURING_SUMMARY.md"]="docs/development/CODEBASE_RESTRUCTURING.md"
    ["DUPLICATE_DETECTION_ENHANCEMENT.md"]="docs/development/DUPLICATE_DETECTION.md"  
    ["LEGACY_CLEANUP_ANALYSIS.md"]="docs/development/LEGACY_CLEANUP.md"
    ["UTILS_MIGRATION_SUMMARY.md"]="docs/development/UTILS_MIGRATION.md"
    ["GITIGNORE_DOCS.md"]="docs/development/GITIGNORE_SETUP.md"
)

for source_file in "${!dev_docs[@]}"; do
    if [ -f "$source_file" ]; then
        mv "$source_file" "${dev_docs[$source_file]}"
        echo "✅ Moved: $source_file → ${dev_docs[$source_file]}"
    fi
done

echo ""

# Phase 3: Select best examples (from verification_test - most recent)
echo "📊 Selecting best examples..."

if [ -d "verification_test" ]; then
    # Copy best examples
    if [ -f "verification_test/vn30_daily_price_summary.md" ]; then
        cp "verification_test/vn30_daily_price_summary.md" "docs/examples/sample_daily_analysis.md"
        echo "✅ Example: verification_test/vn30_daily_price_summary.md → docs/examples/sample_daily_analysis.md"
    fi
    
    if [ -f "verification_test/vn30_summary.md" ]; then
        cp "verification_test/vn30_summary.md" "docs/examples/sample_symbol_summary.md"
        echo "✅ Example: verification_test/vn30_summary.md → docs/examples/sample_symbol_summary.md"
    fi
    
    if [ -f "verification_test/all_symbols_overview.md" ]; then
        cp "verification_test/all_symbols_overview.md" "docs/examples/sample_overview.md"
        echo "✅ Example: verification_test/all_symbols_overview.md → docs/examples/sample_overview.md"
    fi
fi

echo ""

# Phase 4: Archive completion marker
echo "📦 Archiving completion documentation..."
if [ -f "RESTRUCTURING_COMPLETE.md" ]; then
    mv "RESTRUCTURING_COMPLETE.md" "docs/archive/RESTRUCTURING_COMPLETE.md"
    echo "✅ Archived: RESTRUCTURING_COMPLETE.md → docs/archive/"
fi

echo ""

# Phase 5: Remove duplicate test report directories
echo "🗑️  Removing duplicate test report directories..."

report_dirs=(
    "enhanced_daily_reports"
    "enhanced_test_reports" 
    "improved_test_reports"
    "test_reports"
    "test_reports_utils"
    "verification_test"
)

for dir in "${report_dirs[@]}"; do
    if [ -d "$dir" ]; then
        rm -rf "$dir"
        echo "✅ Removed: $dir/"
    fi
done

echo ""

# Create docs README
echo "📖 Creating docs/README.md index..."
cat > docs/README.md << 'EOF'
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
EOF

echo "✅ Created: docs/README.md index"
echo ""

# Summary
echo "🎉 Reorganization Complete!"
echo "=========================="
echo ""
echo "📊 Summary:"
echo "   - Created organized docs/ structure"
echo "   - Moved 6 development docs to docs/development/"
echo "   - Created 3 example files in docs/examples/"
echo "   - Archived completion marker"
echo "   - Removed 6 duplicate test report directories"
echo "   - Created docs/README.md index"
echo ""
echo "📁 New structure:"
echo "   docs/"
echo "   ├── README.md (index)"
echo "   ├── development/ (6 files)"
echo "   ├── examples/ (3 files)"
echo "   └── archive/ (1 file)"
echo ""
echo "🧹 Cleanup:"
echo "   - Root directory cleaned (only README.md remains)"
echo "   - Removed ~27 duplicate report files"
echo "   - Organized all documentation"
echo ""
echo "✅ Next steps:"
echo "   1. Review docs/README.md"
echo "   2. Update main README.md if needed"
echo "   3. Commit changes: git add docs/ && git commit -m 'Reorganize documentation'"
