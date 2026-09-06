@echo off
title WLRI Live Packet & Feature Gap Analyzer
echo ===================================================
echo   Wonderland Online (WLRI) Live Gap Analyzer
echo ===================================================
echo Target Client: C:\Games\WLRI\aLogin.exe
echo Report Destination: docs\live_wlri_feature_gaps.md
echo.
echo Starting sniffer... Open the game and perform actions!
echo Press 'Q' or Enter (or Ctrl+C) in this window to stop and save the report.
echo.

python tools/live_game_gap_analyzer.py --duration 0
pause
