$ProjectRoot = "B:\VS CODE\TY\EDAI"
$Python = "C:\Users\shlok\.conda\envs\blindspot\python.exe"
$Postgres = "C:\Users\shlok\.conda\envs\blindspot\Library\bin\postgres.exe"

Write-Host "Starting ANVAYA SAMHATI..." -ForegroundColor Cyan

# PostgreSQL
Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-Command",
    "& '$Postgres' -D '$ProjectRoot\database\pgdata' -p 5432"
)

Start-Sleep -Seconds 2

# Backend
Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-Command",
    "Set-Location '$ProjectRoot\backend'; & '$Python' -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload"
)

Start-Sleep -Seconds 3

# Frontend
Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-Command",
    "Set-Location '$ProjectRoot\frontend'; npm run dev"
)

Write-Host ""
Write-Host "ANVAYA SAMHATI startup commands launched." -ForegroundColor Green
Write-Host ""
Write-Host "PostgreSQL : 5432"
Write-Host "Backend    : http://127.0.0.1:8000"
Write-Host "Swagger    : http://127.0.0.1:8000/docs"
Write-Host "Frontend   : http://localhost:5173"
Write-Host ""