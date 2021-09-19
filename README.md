# Python Curses Text Editor

A bare-bones, command-line text editor made with the Python curses module. Supports window resizing, vertical and horizontal scrolling, help menu. (If you've dealt with `curses` before, I hope you can appreciate how finicky that all is.)

Sizable parts of code are primarily based off of:
- Tutorial at https://wasimlorgat.com/editor. Window, Buffer and Cursor class are virtually unchanged
- Python's [`curses.textpad.Textbox`](https://github.com/python/cpython/blob/main/Lib/curses/textpad.py) class, although hopefully less buggy for our use case
