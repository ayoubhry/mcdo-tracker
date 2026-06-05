@echo off
echo Desinstallation des navigateurs Playwright...
playwright uninstall

echo Desinstallation des modules Python...
pip uninstall -y flask flask-cors playwright

echo Nettoyage termine avec succes !
pause
