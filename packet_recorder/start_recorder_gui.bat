@echo off
title WLO Packet Recorder - GUI
cd /d "%~dp0\.."
python -m packet_recorder.main
pause
