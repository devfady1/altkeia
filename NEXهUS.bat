@echo off
:: ═══════════════════════════════════════════
::  NEXUS CMS - Quick Launcher (Admin Required for DNS)
:: ═══════════════════════════════════════════
net session >nul 2>&1
if %errorLevel% neq 0 (
    powershell -Command "Start-Process '%~f0' -Verb RunAs"
    exit /b
)
start "" pythonw "C:\Users\windows10\Downloads\cms\altkeia\start.pyw"
