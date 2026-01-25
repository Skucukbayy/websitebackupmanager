#!/bin/bash
source venv/bin/activate
export PORT=5050
echo "Uygulama başlatılıyor: http://localhost:5050"
python app.py
