# -*- mode: python ; coding: utf-8 -*-
import os
import casadi
from PyInstaller.utils.hooks import collect_all

# Pegamos o caminho absoluto do ícone para evitar que o PyInstaller se perca
icone_path = os.path.abspath('logo.ico')

datas = [(icone_path, '.')]
binaries = []
hiddenimports = ["casadi._casadi", "cadquery", "vtk", "pyvista"]

# 1. Coletar pacotes padrão
packages_to_collect = [
    "cadquery",
    "OCP",
    "vtk",
    "pyvista",
    "pyvistaqt"
]

for pkg in packages_to_collect:
    d, b, h = collect_all(pkg)
    datas += d
    binaries += b
    hiddenimports += h

# 2. Tratamento agressivo para o Casadi
casadi_dir = os.path.dirname(casadi.__file__)

binaries += [
    (os.path.join(casadi_dir, '*.dll'), '.'),
    (os.path.join(casadi_dir, '*.pyd'), '.')
]

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
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
    name='Visualizador de STEP',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False, 
    icon=icone_path, # <--- Usando a variável com o caminho absoluto aqui
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Visualizador de STEP',
)