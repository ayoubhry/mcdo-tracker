#!/bin/bash

echo "Désinstallation des navigateurs Playwright..."
playwright uninstall

echo "Désinstallation des modules Python..."
pip3 uninstall -y flask flask-cors playwright --break-system-packages

echo "Nettoyage terminé avec succès !"
