@echo off
setlocal
cd /d "%~dp0"

rem Manual Voice Recorder
rem Usage:
rem   manual_voice.cmd [chapter_number] [recorder_options]
rem   manual_voice.cmd [csv_path] [recorder_options]
rem Examples:
rem   manual_voice.cmd
rem   manual_voice.cmd 0
rem   manual_voice.cmd 1 --check
rem   manual_voice.cmd "work\chapter1_voice_mapping\chapter1_omnivoice_studio.csv" --check

set "DEFAULT_CSV=work\chapter0_voice_mapping\chapter0_omnivoice_studio.csv"
set "CSV_PATH=%DEFAULT_CSV%"

if "%~1"=="" goto run_default
if /I "%~1"=="--check" goto run_default
if /I "%~1"=="--help" goto run_default
if /I "%~1"=="-h" goto run_default
if /I "%~1"=="--output" goto run_default

rem If first argument is numeric, treat it as a chapter number.
set "ARG1=%~1"
for /f "delims=0123456789" %%A in ("%ARG1%") do goto use_path
set "CSV_PATH=work\chapter%ARG1%_voice_mapping\chapter%ARG1%_omnivoice_studio.csv"
shift
call :run %1 %2 %3 %4 %5 %6 %7 %8 %9
goto :eof

:use_path
set "CSV_PATH=%~1"
shift
call :run %1 %2 %3 %4 %5 %6 %7 %8 %9
goto :eof

:run_default
call :run %*
goto :eof

:run
python scripts\manual_voice_recorder.py --csv "%CSV_PATH%" %*
if errorlevel 1 (
    echo.
    echo Manual Voice Recorder failed.
    echo If recording libraries are missing, run:
    echo python -m pip install numpy sounddevice
    echo.
    pause
)
exit /b %errorlevel%
