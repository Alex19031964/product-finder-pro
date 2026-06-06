#!/bin/bash
echo "Checking Python installation..."
if ! command -v python3 &>/dev/null; then
    echo "Python not found. Please install Python from https://python.org"
    read -p "Press Enter to exit..."
    exit 1
fi

echo "Installing required packages..."
pip3 install streamlit pandas --quiet

echo ""
echo "Starting Product Finder Pro..."
echo "The app will open in your browser automatically."
echo "To stop the app, press Ctrl+C"
echo ""

streamlit run app.py --server.headless false
