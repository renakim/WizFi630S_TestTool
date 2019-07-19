# -*- mode: python ; coding: utf-8 -*-

block_cipher = None


a = Analysis(['C:\\workspace\\python_workspace\\projects_python3x\\WizFi630S_TestTool\\src\\main\\python\\main.py'],
             pathex=['C:\\workspace\\python_workspace\\projects_python3x\\WizFi630S_TestTool\\target\\PyInstaller'],
             binaries=[],
             datas=[],
             hiddenimports=[],
             hookspath=['c:\\users\\javak\\appdata\\local\\programs\\python\\python37-32\\lib\\site-packages\\fbs\\freeze\\hooks'],
             runtime_hooks=['C:\\Users\\javak\\AppData\\Local\\Temp\\tmpuhwxpn1z\\fbs_pyinstaller_hook.py'],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          [],
          exclude_binaries=True,
          name='MyApp',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=False,
          console=False , icon='C:\\workspace\\python_workspace\\projects_python3x\\WizFi630S_TestTool\\src\\main\\icons\\Icon.ico')
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=False,
               upx=False,
               upx_exclude=[],
               name='MyApp')
