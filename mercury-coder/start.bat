@echo off
REM Mercury Coder Startup Script for Windows

echo ========================================
echo   Mercury Coder Startup Script
echo ========================================
echo.

REM Function to check if a port is in use and kill the process
:check_and_kill_port
setlocal
set port=%1
set service_name=%2

echo Checking port %port% for %service_name%...

for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":%port%" ^| findstr "LISTENING"') do (
    echo   Found process %%a on port %port%
    echo   Killing process %%a...
    taskkill /F /PID %%a >nul 2>&1
    timeout /t 2 /nobreak >nul
)

REM Check again
netstat -aon | findstr ":%port%" | findstr "LISTENING" >nul 2>&1
if %errorlevel% == 0 (
    echo   Warning: Port %port% may still be in use
) else (
    echo   Port %port% is free
)
endlocal
goto :eof

REM Get script directory
cd /d "%~dp0"

echo Step 1: Checking existing processes...
echo.

call :check_and_kill_port 8000 "Backend"
call :check_and_kill_port 5173 "Frontend"

echo.
echo Step 2: Starting backend...
echo.

cd backend
if not exist ".env" (
    echo Error: backend\.env file not found
    echo Please create backend\.env with your BEDROCK_API_KEY
    pause
    exit /b 1
)

start "Mercury Coder Backend" /MIN cmd /c "python main.py > ..\backend.log 2>&1"
cd ..

echo   Backend process started
echo   Waiting for backend to be ready...

REM Wait for backend (max 30 seconds)
set attempts=0
:wait_backend
set /a attempts+=1
if %attempts% gtr 30 (
    echo   Error: Backend failed to start within 30 seconds
    echo   Check backend.log for details
    pause
    exit /b 1
)

curl -s http://127.0.0.1:8000/health >nul 2>&1
if %errorlevel% neq 0 (
    timeout /t 1 /nobreak >nul
    goto wait_backend
)

echo   Backend is ready!
echo.
echo Step 3: Starting frontend...
echo.

start "Mercury Coder Frontend" cmd /c "npm run dev:vite > frontend.log 2>&1"

timeout /t 3 /nobreak >nul

echo.
echo ========================================
echo   Both services are running!
echo ========================================
echo.
echo Backend:  http://127.0.0.1:8000
echo Frontend: http://localhost:5173
echo.
echo Press any key to stop all services...
pause >nul

echo.
echo Stopping services...
taskkill /F /FI "WINDOWTITLE eq Mercury Coder Backend*" >nul 2>&1
taskkill /F /FI "WINDOWTITLE eq Mercury Coder Frontend*" >nul 2>&1
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":8000" ^| findstr "LISTENING"') do taskkill /F /PID %%a >nul 2>&1
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":5173" ^| findstr "LISTENING"') do taskkill /F /PID %%a >nul 2>&1

echo All services stopped.









































