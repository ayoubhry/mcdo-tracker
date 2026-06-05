@echo off
echo Installation des dependances Python...
pip install flask flask-cors playwright

echo Installation du navigateur Chromium...
playwright install chromium

echo Lancement du serveur...
python api_server.py

pause
