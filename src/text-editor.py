"""
Simple command line text editor to edit files within PyOS

Initial code based off tutorial at: https://wasimlorgat.com/editor

Todo:
- Help screen
- Title bar 
"""
import curses
import curses.ascii
from os import name
from time import sleep

class Window(object):
    def __init__(self, n_rows, n_cols, row=0, col=0) -> None:
        self.n_rows = n_rows
        self.n_cols = n_cols
        self.row = row
        self.col = col

        self.switched = False

    def update_screen_size(self, scr: curses.window, csr):
        """Takes given screen and readjusts rows and cols to new size"""
        new_rows, new_cols = scr.getmaxyx()
        new_rows -= 1
        new_cols -= 1

        # Re-set window height
        self.n_rows = new_rows
        self.n_cols = new_cols

        # Move cursor to somewhere safely on screen
        if (new_rows - self.n_rows) != 0:
            self.row = csr.row  # Place cursor at top of new sized screen
        
        # If absolute csr position > window width, change csr.col to onscreen
        if (csr.col - self.col) > self.n_cols:
            csr.col = self.col + self.n_cols - 1

    @property 
    def bottom(self):
        return self.row + self.n_rows - 1

    def up(self, cursor):
        if cursor.row == self.row -1 and self.row > 0:
            self.row -= 1

    def down(self, buffer, cursor):
        if cursor.row == self.bottom + 1 and self.bottom < len(buffer) - 1:
            self.row += 1
    
    def translate(self, cursor):
        return cursor.row - self.row, cursor.col - self.col

    def horizontal_scroll(self, cursor, left_margin=1, right_margin=1):
        current_page = cursor.col // (self.n_cols - right_margin)
        self.col = max(current_page * (self.n_cols  - right_margin) - left_margin, 0)

class Cursor(object):
    def __init__(self, row=0, col=0, col_hint=None) -> None:
        self.row = row 
        self.col = col
        self._col_hint = col if col_hint is None else col_hint

    @property
    def col(self):
           return self._col

    @col.setter 
    def col(self, col):
        self._col = col 
        self._col_hint = col

    def up(self, buffer):
        if self.row > 0:
            self.row -= 1
            self._clamp_col(buffer)
    
    def down(self, buffer):
        if self.row < buffer.bottom:
            self.row += 1
            self._clamp_col(buffer)
    
    def left(self, buffer):
        if self.col > 0:
            self.col -= 1
        elif self.row > 0:
            # wrap col
            self.row -= 1
            self.col = len(buffer[self.row])

    def right(self, buffer):
        if self.col < len(buffer[self.row]):
            self.col += 1
        elif self.row < buffer.bottom:
            self.row += 1
            self.col = 0

    def _clamp_col(self, buffer):
        self._col = min(self._col_hint, len(buffer[self.row]))

class Buffer(object):
    def __init__(self, lines) -> None:
        self.lines = lines

    def __len__(self):
        return len(self.lines)

    def __getitem__(self, index):
        return self.lines[index]

    def result(self):
        return self.lines

    @property 
    def bottom(self):
        return len(self) - 1
    
    def insert(self, cursor, string):
        row, col = cursor.row, cursor.col
        current = self.lines.pop(row)
        new = current[:col] + string + current[col:]
        self.lines.insert(row, new)
    
    def split(self, cursor):
        row, col = cursor.row, cursor.col
        current = self.lines.pop(row)
        self.lines.insert(row, current[:col])
        self.lines.insert(row + 1, current[col:])

    def delete(self, cursor):
        row, col = cursor.row, cursor.col
        if (row, col) < (self.bottom, len(self[row])):
            current = self.lines.pop(row)
            if col < len(current):
                new = current[:col] + current[col + 1:]
                self.lines.insert(row, new)
            else:
                next = self.lines.pop(row)
                new = current + next
                self.lines.insert(row, new)

class TextPad(object):
    """A container for window, cursor and buffer to create a single interface
    for editing a file."""

    HELPSTRING = """TEXT EDITOR HELP
A bare bones text editor to edit files. You can move
around with arrow keys, type, delete (mostly), etc. 

COMMANDS:
CTL+I       Show help screen
Ctl+W       Save and quit
Ctl+C       Quit (do not save)
    """

    def __init__(self, scr, win: Window, cursor: Cursor, buffer: Buffer, debug=False) -> None:
        self.scr = scr
        self.win = win 
        self.csr = cursor 
        self.buf = buffer 
        self.save_on_exit = False
        self.debug = debug

    def right(self):
        self.csr.right(self.buf)
        self.win.down(self.buf, self.csr)
        self.win.horizontal_scroll(self.csr)

    def left(self):
        self.csr.left(self.buf)
        self.win.up(self.csr)
        self.win.horizontal_scroll(self.csr)
    
    def help_screen(self):
        """
        Static display-only help screen. Will not resize to screen, has no cursor.
        """
        help_str = self.HELPSTRING.split("\n")
        
        while True:
            self.draw_screen(buf=help_str)
            self.add_help_command_to_screen(help_str="Press CTL+I to leave help screen")
            self.scr.refresh()
            ch = self.scr.getch()
            if ch == curses.ascii.TAB:              # ^I
                return 1
            if ch == curses.ascii.ETX:              # ^C
                return 0


    def check_movement(self, ch):
        """Checks if an arrow key or movement was pressed and carries out
        movement"""
        # Movement
        if ch == curses.KEY_UP:                     # Up
            self.csr.up(self.buf)
            self.win.up(self.csr)
            self.win.horizontal_scroll(self.csr)
            return 1
        elif ch == curses.KEY_DOWN:                 # Down
            self.csr.down(self.buf)
            self.win.down(self.buf, self.csr)
            self.win.horizontal_scroll(self.csr)
            return 1
        elif ch == curses.KEY_LEFT:                 # Left
            self.csr.left(self.buf) 
            self.win.up(self.csr)
            self.win.horizontal_scroll(self.csr)
            return 1
        elif ch == curses.KEY_RIGHT:                # Right
            self.csr.right(self.buf)
            self.win.down(self.buf, self.csr)
            self.win.horizontal_scroll(self.csr)
            return 1
        return 0

    def do_command(self, ch):
        """Taken from Python curses.textpad module. Process single editing
        command"""
        # Movement
        if self.check_movement(ch):
            return 1

        # Printable
        if ch == ord('\n'):                                     # Newline
            self.buf.split(self.csr)
            self.right()
        elif curses.ascii.isprint(ch):                          # Printable ascii
            self.buf.insert(self.csr, chr(ch))
            for _ in chr(ch):
                self.right()
        
        # Delete character
        elif ch == curses.KEY_DC or ch == curses.ascii.EOT:     # Delete key or ^D
            self.buf.delete(self.csr)
        elif ch == 0x7f or ch == curses.ascii.DEL:              # Backspace
            if (self.csr.row, self.csr.col) > (0, 0):
                self.left()
                self.buf.delete(self.csr)

        # Help
        elif ch == curses.ascii.TAB:                            # ^I (Help)
            return self.help_screen()

        # Quit with or without save
        elif ch == curses.ascii.ETB:                            # ^W (Write)
            self.save_on_exit = True
            print("SAVING...")
            return 0
        elif ch == curses.ascii.ETX:                            # ^C (Keyboard interrupt)
            return 0
        
        return 1

    def add_debug_to_screen(self):
        new_rows, new_cols = self.scr.getmaxyx()
        new_rows -= 1
        new_cols -= 1
        details = [
            f"R{self.csr.row}, C{self.csr.col}",
            f"Window height: {self.win.n_rows}",
            f"Window width:  {self.win.n_cols}",
            f"Window col:    {self.win.col}",
            f"Window row:    {self.win.row}",
            f"Num lines:     {len(self.buf.lines)}",
            f"Line length:   {len(self.buf[self.csr.row])}",
        ]

        # Get longest string so all strings can be padded to same length
        maxlen = len(max(details, key=len))

        for i in range(min(len(details), self.win.n_rows)):
            row = self.win.n_rows - i
            info_str = details[i].rjust(maxlen)

            # To place on right hand side, need to calculate offset from left
            # But if screen shorter than string, offset = 0 and left-chop the string
            offset = self.win.n_cols - len(info_str)
            col_offset = max(offset, 0)
            info_str = info_str[max(-offset, 0):]
            
            self.scr.addstr(row, col_offset, info_str, curses.A_REVERSE)

    def add_help_command_to_screen(self, help_str=None):
        """Shows key combination for help menu in bottom left of screen, chop
        from right if going offscreen"""
        if help_str == None:
            help_str = "Ctl+I for help screen"
        chop = min(len(help_str), self.win.n_cols)
        self.scr.addstr(self.win.n_rows, 0, help_str[:chop], curses.A_REVERSE)

    def draw_screen(self, buf=None):
        """Can pass in any list of strings to display on screen"""
        if buf == None:
            buf = self.buf

        self.scr.erase()

        for row, line in enumerate(buf[self.win.row:self.win.row+self.win.n_rows]):

            # ----- Horizontal scrolling -----
            # --- Row specific---
            if row == self.csr.row - self.win.row and self.win.col > 0:
                line = "«" + line[self.win.col+1:]
            if len(line) > self.win.n_cols:
                line = line[:self.win.n_cols-1] + "»"
            self.scr.addstr(row, 0, line)
            
        self.win.update_screen_size(self.scr, self.csr)

        if self.debug:
            self.add_debug_to_screen()
        self.add_help_command_to_screen()

        self.scr.move(*self.win.translate(self.csr))

        self.scr.refresh()

    def edit(self, validate=None) -> None:
        """
        Results of edit are returned upon exit. Can be obtained from buffer.result()
        """
        self.save_on_exit = False
        while True:
            self.draw_screen()
            ch = self.scr.getch()
            if validate:
                ch = validate(ch)
            if not ch:
                continue
            if not self.do_command(ch):
                self.scr.clear()
                if self.save_on_exit:
                    self.scr.addstr(0, 0, "SAVING...")
                else:
                    self.scr.addstr(0, 0, "QUITTING...")
                self.scr.refresh()
                sleep(0.5)
                break 
        
        return self.buf.result()

def main(stdscr, contents: str, *args, **kwargs):
    """
    Content should be a string. String will be split up by newline character

    For full control, you will need to set curses.raw() so all inputs can be
    captured (e.g. ^C, ^Z, etc.):
        ...
        curses.raw()
        mytextpad.edit()
        curses.noraw()
        ...
    """
    curses.use_default_colors()
    window = Window(curses.LINES -1, curses.COLS-1)
    cursor = Cursor()
    buffer = Buffer(contents.split("\n"))

    pad = TextPad(stdscr, window, cursor, buffer, debug=False)
    curses.raw()
    pad.edit()
    curses.noraw()

    return buffer.result()

contents = """Hello,
World

This is a multiline file"""
res = curses.wrapper(main, contents=contents)
print(res)
