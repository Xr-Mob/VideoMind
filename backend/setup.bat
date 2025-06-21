@echo off
echo Setting up VideoMind AI Backend...
echo.

echo Creating virtual environment...
python -m venv venv

echo Activating virtual environment...
call venv\Scripts\activate.bat

echo Installing dependencies...
pip install -r requirements.txt

echo.
echo Setup complete! To start the backend:
echo 1. Activate the virtual environment: venv\Scripts\activate.bat
echo 2. Create a .env file with your GEMINI_API_KEY
echo 3. Run: python main.py
echo.
pause 