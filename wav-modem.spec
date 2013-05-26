# -*- mode: python -*-
a = Analysis(['wav-modem.py'],
             pathex=['C:\\STORAGE\\stuff\\work\\ekselcom\\2013.05.21.wav-modem'],
             hiddenimports=[],
             hookspath=None)
pyz = PYZ(a.pure)
exe = EXE(pyz,
          a.scripts,
          a.binaries + [('ftd2xx.dll', 'ftd2xx.dll', 'BINARY')],
          a.zipfiles,
          a.datas,
          name=os.path.join('dist', 'wav-modem.exe'),
          debug=False,
          strip=None,
          upx=True,
          console=False )
app = BUNDLE(exe,
             name=os.path.join('dist', 'wav-modem.exe.app'))
