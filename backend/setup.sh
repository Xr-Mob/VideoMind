#!/bin/bash
echo "Setting up VideoMind AI Backend..."
echo

echo "Creating virtual environment..."
python3 -m venv venv

echo "Activating virtual environment..."
source venv/bin/activate

echo "Installing dependencies..."
pip install -r requirements.txt

echo
echo "Setup complete! To start the backend:"
echo "1. Activate the virtual environment: source venv/bin/activate"
echo "2. Create a .env file with your GEMINI_API_KEY"
echo "3. Run: python main.py"
echo 