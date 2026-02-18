# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['flet_app.py'],
    pathex=[],
    binaries=[],
    datas=[('app', 'app')],
    hiddenimports=['transformers', 'torch', 'torchvision', 'PIL', 'numpy', 'huggingface_hub', 'flet', 'kornia', 'kornia.geometry', 'kornia.filters', 'timm', 'timm.models', 'timm.models.layers', 'timm.models.registry', 'timm.layers', 'timm.models.vision_transformer', 'timm.models.resnet', 'timm.models.efficientnet', 'timm.data', 'timm.optim', 'timm.scheduler', 'kornia.enhance', 'flet.platform'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='NoBG',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['assets/icon.icns'],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='NoBG',
)
app = BUNDLE(
    coll,
    name='NoBG.app',
    icon='assets/icon.icns',
    bundle_identifier=None,
)
