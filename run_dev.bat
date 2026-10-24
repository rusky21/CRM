@echo off
title StudioCRM Multi-Account Telegram Mini App
echo ==========================================================
echo    Starting StudioCRM Telegram Development Environment
echo ==========================================================

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0run_dev.ps1"
pause
