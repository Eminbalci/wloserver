#!/bin/bash
echo "Installing required packages..."
pip install -r requirements.txt
echo "Starting server..."
python3 -m server.main
