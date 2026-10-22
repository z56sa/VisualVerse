@echo off
chcp 65001 >nul
cd /d "%~dp0"
start "" python electron_ui.py
