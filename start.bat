@echo off
echo ===================================================
echo 🚀 STARTING PATROL MD SYSTEM
echo ===================================================

:: Start Next.js Frontend in a new window
echo Starting Next.js Website...
start "Patrol MD - Website" cmd /k "cd site && npm run dev"

:: Start Python Bot in a new window
echo Starting Python Autonomous Bot...
start "Patrol MD - Python Bot" cmd /k "python main.py --paper"

echo.
echo Both components are launching in separate windows!
echo Wait a few seconds, then open http://localhost:3000 in your browser.
echo ===================================================
pause
