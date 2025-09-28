
LETTERS = ["a", "b", "c", "d", "e", "f", "g", "h", "i", "j", "k", "l", "m",
           "n", "o", "p", "q", "r", "s", "t", "u", "v", "w", "x", "y", "z"]

NUMBERS = ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9"]

FUNCTION_KEYS = ["f1", "f2", "f3", "f4", "f5", "f6", "f7", "f8", "f9", "f10", "f11", "f12"]

NAVIGATION_KEYS = ["up", "down", "left", "right", "page_up", "page_down", "home", "end"]

SPECIAL_KEYS = ["tab", "enter", "escape", "space", "backspace", "delete"]

SYMBOLS = ["+", "-", "=", "[", "]", ";", "'", ",", ".", "/", "\\", "`",
           "?", "!", '"', "(", ")", "{", "}", "_", "|", ":", "~",
           "@", "#", "$", "%", "^", "&", "*"]

MODIFIERS = ["ctrl", "cmd", "alt", "shift"]


ALL_VALID_KEYS = set(LETTERS + NUMBERS + FUNCTION_KEYS + NAVIGATION_KEYS + SPECIAL_KEYS + SYMBOLS)

KEYS_BY_CATEGORY = {
    "Letters": LETTERS,
    "Numbers": NUMBERS,
    "Function Keys": FUNCTION_KEYS,
    "Navigation": NAVIGATION_KEYS,
    "Special Keys": SPECIAL_KEYS,
    "Symbols": SYMBOLS,
    "Modifiers": MODIFIERS
}


SHORTCUT_MAPPINGS = {
    # common shortcuts
    "copy": "ctrl+c",
    "paste": "ctrl+v", 
    "cut": "ctrl+x",
    "undo": "ctrl+z",
    "redo": "ctrl+y",
    "save": "ctrl+s",
    "select all": "ctrl+a",
    "find": "ctrl+f",
    "new": "ctrl+n",
    "open": "ctrl+o",
    "print": "ctrl+p",
    "quit": "ctrl+q",
    "refresh": "ctrl+r",
    "bold": "ctrl+b",
    "italic": "ctrl+i",
    "underline": "ctrl+u",
    "zoom in": "ctrl++",
    "zoom out": "ctrl+-",
    
    # Navigation and special keys
    "tab": "tab",
    "enter": "enter",
    "return": "enter",
    "escape": "escape",
    "esc": "escape",
    "backspace": "backspace",
    "delete": "delete",
    "space": "space",
    "spacebar": "space",
    "up": "up",
    "down": "down", 
    "left": "left",
    "right": "right",
    "up arrow": "up",
    "down arrow": "down",
    "left arrow": "left", 
    "right arrow": "right",
    "page up": "page_up",
    "page down": "page_down",
    "home": "home",
    "end": "end",
    
    "letter a": "a", "letter b": "b", "letter c": "c", "letter d": "d",
    "letter e": "e", "letter f": "f", "letter g": "g", "letter h": "h",
    "letter i": "i", "letter j": "j", "letter k": "k", "letter l": "l",
    "letter m": "m", "letter n": "n", "letter o": "o", "letter p": "p",
    "letter q": "q", "letter r": "r", "letter s": "s", "letter t": "t",
    "letter u": "u", "letter v": "v", "letter w": "w", "letter x": "x",
    "letter y": "y", "letter z": "z",

    "f1": "f1", "f2": "f2", "f3": "f3", "f4": "f4", "f5": "f5", "f6": "f6",
    "f7": "f7", "f8": "f8", "f9": "f9", "f10": "f10", "f11": "f11", "f12": "f12",
    "function 1": "f1", "function 2": "f2", "function 3": "f3", "function 4": "f4",
    "function 5": "f5", "function 6": "f6", "function 7": "f7", "function 8": "f8",
    "function 9": "f9", "function 10": "f10", "function 11": "f11", "function 12": "f12",
    
    "0": "0", "1": "1", "2": "2", "3": "3", "4": "4", 
    "5": "5", "6": "6", "7": "7", "8": "8", "9": "9",
    "zero": "0", "one": "1", "two": "2", "three": "3", "four": "4",
    "five": "5", "six": "6", "seven": "7", "eight": "8", "nine": "9",
    "number 0": "0", "number 1": "1", "number 2": "2", "number 3": "3", "number 4": "4",
    "number 5": "5", "number 6": "6", "number 7": "7", "number 8": "8", "number 9": "9",
    
    "period": ".", "dot": ".", "comma": ",", "semicolon": ";", "colon": ":",
    "question mark": "?", "exclamation": "!", "exclamation mark": "!",
    "apostrophe": "'", "quote": "'", "double quote": '"', 
    "left parenthesis": "(", "right parenthesis": ")", "open paren": "(", "close paren": ")",
    "left bracket": "[", "right bracket": "]", "open bracket": "[", "close bracket": "]",
    "left brace": "{", "right brace": "}", "open brace": "{", "close brace": "}",
    "plus": "+", "minus": "-", "dash": "-", "hyphen": "-",
    "equals": "=", "equal": "=", "equals sign": "=",
    "underscore": "_", "pipe": "|", "backslash": "\\", "forward slash": "/", "slash": "/",
    "tilde": "~", "backtick": "`", "grave": "`",
    "at": "@", "at sign": "@", "hash": "#", "hashtag": "#", "pound": "#",
    "dollar": "$", "dollar sign": "$", "percent": "%", "percent sign": "%",
    "caret": "^", "ampersand": "&", "asterisk": "*", "star": "*"
}

KEY_NORMALIZATIONS = {
    "control": "ctrl",
    "command": "cmd",
    "alt": "alt",
    "shift": "shift",
    "option": "alt",
    "plus": "+",
    "minus": "-",
    "equals": "=",
    "semicolon": ";",
    "quote": "'",
    "comma": ",",
    "period": ".",
    "slash": "/",
    "backslash": "\\",
    "left bracket": "[",
    "right bracket": "]",
    "backtick": "`",
}

