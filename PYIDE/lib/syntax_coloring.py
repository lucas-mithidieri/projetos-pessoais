import regex as re
import idlelib.colorizer as ic
import idlelib.percolator as ip

def apply_syntax_coloring(target:object):
    # {SYNTAX_COLORING}
    KEYWORD   = r"\b(?P<KEYWORD>False|None|True|and|as|assert|async|await|break|class|continue|def|del|elif|else|except|finally|for|from|global|if|import|in|is|lambda|nonlocal|not|or|pass|raise|return|try|while|with|yield)\b"
    EXCEPTION = r"([^.'\"\\#]\b|^)(?P<EXCEPTION>ArithmeticError|AssertionError|AttributeError|BaseException|BlockingIOError|BrokenPipeError|BufferError|BytesWarning|ChildProcessError|ConnectionAbortedError|ConnectionError|ConnectionRefusedError|ConnectionResetError|DeprecationWarning|EOFError|Ellipsis|EnvironmentError|Exception|FileExistsError|FileNotFoundError|FloatingPointError|FutureWarning|GeneratorExit|IOError|ImportError|ImportWarning|IndentationError|IndexError|InterruptedError|IsADirectoryError|KeyError|KeyboardInterrupt|LookupError|MemoryError|ModuleNotFoundError|NameError|NotADirectoryError|NotImplemented|NotImplementedError|OSError|OverflowError|PendingDeprecationWarning|PermissionError|ProcessLookupError|RecursionError|ReferenceError|ResourceWarning|RuntimeError|RuntimeWarning|StopAsyncIteration|StopIteration|SyntaxError|SyntaxWarning|SystemError|SystemExit|TabError|TimeoutError|TypeError|UnboundLocalError|UnicodeDecodeError|UnicodeEncodeError|UnicodeError|UnicodeTranslateError|UnicodeWarning|UserWarning|ValueError|Warning|WindowsError|ZeroDivisionError)\b"
    BUILTIN   = r"([^.'\"\\#]\b|^)(?P<BUILTIN>abs|all|any|ascii|bin|breakpoint|callable|chr|classmethod|compile|complex|copyright|credits|delattr|dir|divmod|enumerate|eval|exec|exit|filter|format|frozenset|getattr|globals|hasattr|hash|help|hex|id|input|isinstance|issubclass|iter|len|license|locals|map|max|memoryview|min|next|oct|open|ord|pow|print|quit|range|repr|reversed|round|set|setattr|slice|sorted|staticmethod|sum|super|type|vars|zip)\b"
    DOCSTRING = r"(?P<DOCSTRING>(?i:r|u|f|fr|rf|b|br|rb)?'''[^'\\]*((\\.|'(?!''))[^'\\]*)*(''')?|(?i:r|u|f|fr|rf|b|br|rb)?\"\"\"[^\"\\]*((\\.|\"(?!\"\"))[^\"\\]*)*(\"\"\")?)"
    STRING    = r"(?P<STRING>(?i:r|u|f|fr|rf|b|br|rb)?'[^'\\\n]*(\\.[^'\\\n]*)*'?|(?i:r|u|f|fr|rf|b|br|rb)?\"[^\"\\\n]*(\\.[^\"\\\n]*)*\"?)"
    TYPES     = r"\b(?P<TYPES>bool|bytearray|bytes|dict|float|int|list|str|tuple|object)\b"
    NUMBER    = r"\b(?P<NUMBER>((0x|0b|0o|#)[\da-fA-F]+)|((\d*\.)?\d+))\b"
    CLASSDEF  = r"(?<=\bclass)[ \t]+(?P<CLASSDEF>\w+)[ \t]*[:\(]" #recolor of DEFINITION for class definitions
    DECORATOR = r"(^[ \t]*(?P<DECORATOR>@[\w\d\.]+))"
    INSTANCE  = r"\b(?P<INSTANCE>cls)\b"
    OPERATOR  = r"(?P<OPERATOR>[+\-*\/])" # não tinha no original
    COMMENT   = r"(?P<COMMENT>#[^\n]*)"
    SYNC      = r"(?P<SYNC>\n)"
    PROG      = rf"{KEYWORD}|{BUILTIN}|{EXCEPTION}|{TYPES}|{OPERATOR}|{COMMENT}|{DOCSTRING}|{STRING}|{SYNC}|{INSTANCE}|{DECORATOR}|{NUMBER}|{CLASSDEF}"
    IDPROG    = r"(?<!class)\s+(\w+)"

    cd        = ic.ColorDelegator()
    cd.prog   = re.compile(PROG, re.S|re.M)
    cd.idprog = re.compile(IDPROG, re.S)

    TAGDEFS   = {
        'COMMENT': {'foreground': '#868586', 'background': None}, #ok
        'TYPES': {'foreground': '#e9950c', 'background': None}, #ok
        'NUMBER': {'foreground': '#df3079', 'background': None}, #ok
        'BUILTIN': {'foreground': '#e9950c', 'background': None},#ok
        'STRING': {'foreground': '#00a67d', 'background': None},#ok
        'DOCSTRING': {'foreground': '#00a67d', 'background': None},#ok
        'EXCEPTION': {'foreground': '#868586', 'background': None},
        'OPERATOR': {'foreground': 'white', 'background': None},
        'DEFINITION': {'foreground': '#ea2424', 'background': None},#ok
        'DECORATOR': {'foreground': '#868586', 'background': None},#ok
        'INSTANCE': {'foreground': '#00a67d', 'background': None}, #self
        'KEYWORD': {'foreground': '#2e95d3', 'background': None}, #def
        'CLASSDEF': {'foreground': '#ea2424', 'background': None},#classname
    }
    cd.tagdefs = {**cd.tagdefs, **TAGDEFS}

    # apply filter to target widget
    ip.Percolator(target).insertfilter(cd)