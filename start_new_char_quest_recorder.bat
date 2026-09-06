@echo off
title WLRI New Character & First Quest Recorder
echo =================================================================
echo   Wonderland Online (WLRI) - New Character & First Quest Recorder
echo =================================================================
echo.
echo Raw PCAP Output: C:\Users\muham\OneDrive\Masaustu\paketler\yeni_karakter_ve_ilk_gorev.pcapng
echo Gap Analysis Report: docs\new_char_first_quest_gap_report.md
echo.
echo Starting sniffer... 
echo You can now create your character and complete the first quest in the game!
echo Press 'Q' or Enter (or Ctrl+C) in this window when you are done.
echo.

python tools/live_game_gap_analyzer.py --duration 0 --pcap-out "C:\Users\muham\OneDrive\Masaüstü\paketler\yeni_karakter_ve_ilk_gorev.pcapng" --out "docs\new_char_first_quest_gap_report.md"
pause
