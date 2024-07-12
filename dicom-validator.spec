# This file tells PyInstaller how to compile.
# From PowerShell prompt, use:
# pyinstaller dicom-validator.spec -y

# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_submodules
from PyInstaller.utils.hooks import collect_all

datas = []
binaries = []
hiddenimports = []
hiddenimports += collect_submodules('pydicom')
tmp_ret = collect_all('lxml')
datas += tmp_ret[0];  hiddenimports += tmp_ret[2]

validate_iods_a = Analysis(
    ['dicom_validator/validate_iods.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

dump_dcm_info_a = Analysis(
    ['dicom_validator/dump_dcm_info.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)


validate_iods_pyz = PYZ(validate_iods_a.pure)

validate_iods_exe = EXE(
    validate_iods_pyz,
    validate_iods_a.scripts,
    validate_iods_a.binaries,
    validate_iods_a.datas,
    [],
    name='validate_iods',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

dump_dcm_info_pyz = PYZ(dump_dcm_info_a.pure)

dump_dcm_info_exe = EXE(
    dump_dcm_info_pyz,
    dump_dcm_info_a.scripts,
    dump_dcm_info_a.binaries,
    dump_dcm_info_a.datas,
    [],
    name='dump_dcm_info',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
