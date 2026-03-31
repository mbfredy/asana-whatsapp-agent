#!/bin/bash

# Asana WhatsApp Agent - Quick Setup Script
# Run this to set up the project locally

set -e

echo "=================================================="
echo "  Asana WhatsApp Agent - Setup Script"
echo "=================================================="
echo ""

# Check Python installation
echo "1. Checking Python installation..."
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 is not installed"
    echo "Install from https://www.python.org/downloads/"
    exit 1
fi

PYTHON_VERSION=$(python3 --version)
echo "✓ Found $PYTHON_VERSION"
echo ""

# Create virtual environment
echo "2. Creating virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "✓ Virtual environment created"
else
    echo "✓ Virtual environment already exists"
fi

# Activate virtual environment
echo "3. Activating virtual environment..."
source venv/bin/activate
echo "✓ Virtual environment activated"
echo ""

# Install dependencies
echo "4. Installing dependencies..."
pip install -q -r requirements.txt
echo "✓ Dependencies installed"
echo ""

# Setup .env file
echo "5. Setting up environment file..."
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo "✓ Created .env file"
    echo ""
    echo "IMPORTANT: Edit .env and add your credentials:"
    echo "  - TWILIO_ACCOUNT_SID"
    echo "  - TWILIO_AUTH_TOKEN"
    echo "  - TWILIO_PHONE"
    echo "  - ANTHROPIC_API_KEY"
    echo "  - ASANA_PAT"
    echo ""
else
    echo "✓ .env file already exists"
fi

# Test imports
echo "6. Testing Python imports..."
python3 -c "import flask; import anthropic; import twilio; import apscheduler" 2>/dev/null
if [ $? -eq 0 ]; then
    echo "✓ All imports successful"
else
    echo "ERROR: Failed to import required modules"
    exit 1
fi
echo ""

echo "=================================================="
echo "  Setup Complete!"
echo "=================================================="
echo ""
echo "Next steps:"
echo ""
echo "1. Edit .env with your API credentials"
echo "   nano .env"
echo ""
echo "2. Test your configuration:"
echo "   python3 test_locally.py"
echo ""
echo "3. Run the app locally:"
echo "   python3 app.py"
echo ""
echo "4. In another terminal, expose with ngrok:"
echo "   ngrok http 5000"
echo ""
echo "5. Update Twilio webhook URL in the console"
echo ""
echo "6. Send a test WhatsApp message!"
echo ""
echo "For more details, see README.md or QUICKSTART.md"
echo ""
