@echo off
REM CFAO Process Monitor Agent - Setup Script
echo Setting up CFAO Process Monitor Agent...

REM Check if .env exists
if not exist .env (
    echo Error: .env file not found. Please copy .env.example to .env and configure your settings.
    pause
    exit /b 1
)

REM Install Python dependencies
echo Installing Python dependencies...
pip install -r requirements.txt

REM Install Playwright browsers
echo Installing Playwright browsers...
playwright install chromium

REM Create necessary directories
if not exist data mkdir data
if not exist logs mkdir logs

echo Setup complete!
echo.
echo To run the agent:
echo - Single test run: python Agent.py --once
echo - Scheduled run: python Agent.py
echo - Run tests: python test.py
echo.
echo To deploy with Docker:
echo - docker-compose up -d
echo.
pause