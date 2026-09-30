from setuptools import setup

APP = ['macro_app.py']
DATA_FILES = []
OPTIONS = {
    'argv_emulation': True,
    'iconfile': None,
    'packages': ['pynput'],
    'includes': ['pynput'],
    'excludes': ['tkinter', 'tcl', 'tk'],  # 시스템 Tkinter 사용
}

setup(
    app=APP,
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
)
