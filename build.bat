@ECHO OFF

python pyinstaller\utils\Build.py wav-modem.spec

RD /S /Q build
DEL *.log
DEL *.pyc
