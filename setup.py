from setuptools import setup
import sys

APP = ['macro_app.py']
DATA_FILES = []
OPTIONS = {
    'argv_emulation': True,
    'iconfile': None,
    'packages': ['pynput', 'tkinter'],
    'includes': ['pynput', 'tkinter', 'ttk'],
}

setup(
    app=APP,
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
)
