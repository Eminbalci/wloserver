@echo off
title WLO Packet Recorder - CLI
cd /d "%~dp0\.."
python -m packet_recorder.main --cli
pause
