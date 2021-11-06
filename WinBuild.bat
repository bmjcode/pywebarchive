@ECHO OFF
REM Update the Python version below as appropriate for your system.
py -3.6-32 -m PyInstaller ^
    --clean -w -F -n Webarchive.Extractor extractor-gui.py
py -3.6 -m PyInstaller ^
    --clean -w -F -n Webarchive.Extractor.x64 extractor-gui.py
