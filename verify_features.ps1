# PowerShell script to verify protected features
# Run this before committing: .\verify_features.ps1

Write-Host "🔍 Checking for protected features..." -ForegroundColor Cyan

$errors = 0

# Check for "Bulk Imports:" label
if (Select-String -Path "app_enhanced.py" -Pattern "Bulk Imports:" -Quiet) {
    Write-Host "✅ 'Bulk Imports:' label found" -ForegroundColor Green
} else {
    Write-Host "❌ ERROR: 'Bulk Imports:' label is missing!" -ForegroundColor Red
    Write-Host "   This is a PROTECTED FEATURE. See PROTECTED_FEATURES.md" -ForegroundColor Yellow
    $errors++
}

# Check for all 6 import methods
$methods = @("importAIRecommended", "import45Star", "import3Star", "importAllReviews", "importWithPhotos", "importWithoutPhotos")
$missing = @()

foreach ($method in $methods) {
    if (Select-String -Path "app_enhanced.py" -Pattern $method -Quiet) {
        Write-Host "✅ Method '$method' found" -ForegroundColor Green
    } else {
        Write-Host "❌ ERROR: Method '$method' is missing!" -ForegroundColor Red
        $missing += $method
        $errors++
    }
}

# Check for progress loader
if (Select-String -Path "app_enhanced.py" -Pattern "rk-import-loader" -Quiet) {
    Write-Host "✅ Progress loader found" -ForegroundColor Green
} else {
    Write-Host "❌ ERROR: Progress loader (rk-import-loader) is missing!" -ForegroundColor Red
    $errors++
}

# Check for helper methods
$helpers = @("showImportLoader", "hideImportLoader", "updateImportProgress", "setBulkImportButtonsEnabled")
foreach ($helper in $helpers) {
    if (Select-String -Path "app_enhanced.py" -Pattern $helper -Quiet) {
        Write-Host "✅ Helper method '$helper' found" -ForegroundColor Green
    } else {
        Write-Host "❌ ERROR: Helper method '$helper' is missing!" -ForegroundColor Red
        $errors++
    }
}

# Check for product thumbnail
if (Select-String -Path "app_enhanced.py" -Pattern "Target Product Selected" -Quiet) {
    Write-Host "✅ Product thumbnail code found" -ForegroundColor Green
} else {
    Write-Host "⚠️  WARNING: Product thumbnail code may be missing" -ForegroundColor Yellow
}

if ($errors -eq 0) {
    Write-Host "`n✅ All protected features verified!" -ForegroundColor Green
    exit 0
} else {
    Write-Host "`n❌ Found $errors error(s). Please fix before committing." -ForegroundColor Red
    Write-Host "   See PROTECTED_FEATURES.md for details" -ForegroundColor Yellow
    exit 1
}

