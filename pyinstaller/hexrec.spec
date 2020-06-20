# -*- mode: python ; coding: utf-8 -*-
from pkg_resources import iter_entry_points

block_cipher = None

all_commands = []
hiddenimports = []

for ep in iter_entry_points('hexrec_types'):
    all_commands.append("{} = {}:{}".format(ep.name, ep.module_name, ep.attrs[0]))
    hiddenimports.append(ep.module_name)

hook_script_text = f'''
import pkg_resources
eps = {all_commands}

def iter_entry_points(group, name=None):
    for ep in eps:
        parsed = pkg_resources.EntryPoint.parse(ep)
        parsed.dist = pkg_resources.Distribution()
        yield parsed

pkg_resources.iter_entry_points = iter_entry_points
'''

with open('runtime_hooks.py', 'wt') as f:
    f.write(hook_script_text)

a = Analysis(
    ['hexrec_cli.py'],
    pathex=['.'],
    binaries=[],
    datas=[],
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=['runtime_hooks.py'],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(
    a.pure,
    a.zipped_data,
    cipher=block_cipher,
)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='hexrec',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
)
