# ChatApp - Quick Deploy to Railway
# Run this PowerShell script to prepare your app for deployment

Write-Host "====================================" -ForegroundColor Cyan
Write-Host " ChatApp Railway Deployment Script" -ForegroundColor Cyan
Write-Host "====================================" -ForegroundColor Cyan
Write-Host ""

$projectPath = "C:\Users\Hp\Documents\Python Projects\Python_WebApp\chatApp"
Set-Location $projectPath

# Step 1: Check if Git is installed
Write-Host "[1/5] Checking Git..." -ForegroundColor Yellow
if (!(Get-Command git -ErrorAction SilentlyContinue)) {
    Write-Host "❌ Git not found!" -ForegroundColor Red
    Write-Host "Install from: https://git-scm.com/download/win" -ForegroundColor Red
    exit 1
}
Write-Host "✅ Git found" -ForegroundColor Green

# Step 2: Initialize Git repo (if not already done)
Write-Host ""
Write-Host "[2/5] Setting up Git repository..." -ForegroundColor Yellow
if (!(Test-Path ".git")) {
    git init
    git add .
    git commit -m "Initial commit - ChatApp backend ready for deployment"
    Write-Host "✅ Git repository initialized" -ForegroundColor Green
} else {
    Write-Host "✅ Git repository already exists" -ForegroundColor Green
}

# Step 3: Check for remote
Write-Host ""
Write-Host "[3/5] Checking GitHub remote..." -ForegroundColor Yellow
$remote = git remote get-url origin 2>$null
if ($remote) {
    Write-Host "✅ Remote found: $remote" -ForegroundColor Green
} else {
    Write-Host "⚠️  No GitHub remote configured" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor Cyan
    Write-Host "1. Create a repository on GitHub: https://github.com/new" -ForegroundColor White
    Write-Host "2. Run: git remote add origin https://github.com/YOUR_USERNAME/chatapp-backend.git" -ForegroundColor White
    Write-Host "3. Run: git push -u origin main" -ForegroundColor White
}

# Step 4: Display deployment instructions
Write-Host ""
Write-Host "[4/5] Deployment Instructions" -ForegroundColor Yellow
Write-Host ""
Write-Host "Option 1: Deploy via Railway Dashboard (Recommended)" -ForegroundColor Cyan
Write-Host "1. Go to: https://railway.app" -ForegroundColor White
Write-Host "2. Login with GitHub" -ForegroundColor White
Write-Host "3. Click 'New Project' → 'Deploy from GitHub repo'" -ForegroundColor White
Write-Host "4. Select your chatapp-backend repository" -ForegroundColor White
Write-Host "5. Railway will auto-detect Python and deploy!" -ForegroundColor White
Write-Host ""
Write-Host "Option 2: Deploy via Railway CLI" -ForegroundColor Cyan
Write-Host "1. Install: npm i -g @railway/cli" -ForegroundColor White
Write-Host "2. Login: railway login" -ForegroundColor White
Write-Host "3. Deploy: railway init && railway up" -ForegroundColor White

# Step 5: Display next steps
Write-Host ""
Write-Host "[5/5] After Deployment" -ForegroundColor Yellow
Write-Host ""
Write-Host "1. Add PostgreSQL database in Railway dashboard" -ForegroundColor White
Write-Host "2. Set SECRET_KEY and JWT_SECRET environment variables" -ForegroundColor White
Write-Host "3. Get your public URL from Railway settings" -ForegroundColor White
Write-Host "4. Update ApiConfig.kt in ChatAppKotlin project" -ForegroundColor White
Write-Host "5. Rebuild APK and distribute!" -ForegroundColor White

Write-Host ""
Write-Host "====================================" -ForegroundColor Cyan
Write-Host " See DEPLOY_GUIDE.md for full instructions" -ForegroundColor Cyan
Write-Host "====================================" -ForegroundColor Cyan
Write-Host ""

pause
