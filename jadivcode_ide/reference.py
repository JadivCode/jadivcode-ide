"""The complete built-in help shown in the Help panel.

Every entry is (title, text to insert, explanation). Library entries are
read from the interpreter, so the panel always matches what is installed.
"""

from .core import LIBRARIES

LANGUAGE = [
    ("Basics", [
        ("// comment", "// ", "A note for people. JadivCode ignores everything after //."),
        ("Write", "Write = Hello, world!", "Show text. Values in { } are inserted: "
                                           "Write = Count is {Count}"),
        ("Ask", "Ask Name = What is your name?",
         "Show a question and store the answer under a name. Numbers become numbers."),
        ("Define", "Define Count = 0", "Create a named value or thing."),
        ("Set", "Set Count = Count + 1", "Change a value, or switch a thing: Set Lamp = ON"),
        ("Set a property", "Set Hello Color = red",
         "Change one property of a thing (an item, a window, a server)."),
        ("Wait", "Wait 5s", "Pause. Units: ms, s, m, h. Windows and events keep working."),
        ("Stop", "Stop", "End the program. 'Stop Name' stops or removes a thing instead."),
        ("Start", "Start Window", "Start a thing: show a window, start a page or a server."),
        ("Import", "Import Math", "Use a library. Several at once: Import Math, GPIO"),
        ("Strict", "Strict ON", "Stop the program at the first problem instead of continuing."),
    ]),
    ("Values", [
        ("Number", "Define Price = 9.5", "Whole or decimal numbers."),
        ("Text", 'Define Name = "Jan"', "Quotes always mean text. Without quotes, text that "
                                         "is a valid calculation of known names is calculated."),
        ("Switch", "Define Ready = ON", "ON / OFF (also TRUE / FALSE)."),
        ("Nothing", "Define Result = Nothing", "No value."),
        ("Value in text", "Write = Total: {Price * 2}", "Curly braces insert a value into text. "
                                                         "Write {{ and }} for real braces."),
        ("Calculations", "Set Area = Width * Height",
         "+  -  *  /  % (remainder)  ^ (power)  ( ). The + sign also joins text."),
    ]),
    ("Decisions", [
        ("If on one line", "If Count > 3 then Write = big else Write = small",
         "The else part is optional. Statements may be put in quotes."),
        ("If block", "If Count > 3\n    Write = big\nElse If Count = 3\n    Write = three\n"
                     "Else\n    Write = small\nEnd", "Several lines per case. Always close with End."),
        ("Comparing", "If Age >= 18 then Write = adult",
         "=  !=  <  >  <=  >=  is  is not. Text is compared ignoring capitals; == is exact."),
        ("and / or / not", "If Age >= 18 and Age < 65 then Write = working age",
         "Combine conditions."),
    ]),
    ("Loops", [
        ("Repeat", "Repeat 3 times\n    Write = Hello\nEnd", "Run the lines a fixed number of times."),
        ("For", "For I = 1 to 10\n    Write = {I}\nEnd", "Count. Add 'step 2' or 'step -1'."),
        ("For each", "For each Item in Items\n    Write = {Item}\nEnd", "Go through a list."),
        ("While", "While Count < 10\n    Set Count = Count + 1\nEnd",
         "Repeat while the condition is true."),
        ("Forever", "Forever\n    Write = tick\n    Wait 1s\nEnd",
         "Repeat without end. Always put a Wait inside."),
        ("Break", "Break", "Leave the loop."),
        ("Continue", "Continue", "Start the next round of the loop."),
    ]),
    ("Lists", [
        ("Create a list", "Define Colors = List red, green, blue", "An empty list is 'List'."),
        ("Add", "Add yellow to Colors", "Add an item at the end."),
        ("Remove", "Remove green from Colors", "Remove the first matching item."),
        ("Read an item", "Write = {Colors #1}", "Positions start at #1."),
        ("Count", "Write = {Length(Colors)}", "Number of items."),
    ]),
    ("Functions", [
        ("Function", "Function Greet Name\n    Write = Hello, {Name}\nEnd",
         "A named group of lines. The names after the function name receive the values."),
        ("Call", 'Call Greet "Jan"', "Run a function. Separate several values with commas."),
        ("Return", "Function Double N\n    Return N * 2\nEnd", "Hand a value back."),
        ("Use a result", "Write = {Double(21)}", "Functions with a result are used with ( )."),
    ]),
    ("Events", [
        ("On, one line", 'On Go "Write = pressed"',
         "Run a statement when something happens: a click, a pin change, a webhook."),
        ("On, block", "On Go\n    Write = pressed\nEnd", "Several lines per event."),
        ("Event", "Write = {Event}", "Inside On: what happened (typed text, new state, data)."),
        ("Else loop", 'On Go "Write = pressed" Else loop',
         "Optional ending that says 'otherwise keep waiting'."),
    ]),
    ("Problems", [
        ("Success", 'If Success = "Full" then Write = OK',
         'Full: everything worked. None: the line before failed. Partial: an earlier line failed.'),
        ("Error", "Write = {Error}", "Message of the last problem."),
    ]),
    ("Helpers", [
        ("Length(X)", "{Length(X)}", "Characters in text, or items in a list."),
        ("Upper(X) / Lower(X)", "{Upper(X)}", "Text in capital or small letters."),
        ("Trim(X)", "{Trim(X)}", "Text without spaces at both ends."),
        ("Number(X)", "{Number(X)}", "Text turned into a number."),
        ("Text(X)", "{Text(X)}", "A value turned into text."),
        ("Round(X, 2)", "{Round(X, 2)}", "Rounded number; leave out the 2 for a whole number."),
        ("Contains(X, Y)", "{Contains(X, Y)}", "ON when text or a list X contains Y."),
        ("Replace(X, Old, New)", "{Replace(X, Old, New)}", "Replace every Old by New."),
        ("Split(X, \",\")", '{Split(X, ",")}', "Cut text into a list."),
        ("Join(L, \", \")", '{Join(L, ", ")}', "Join a list into text."),
        ("Type(X)", "{Type(X)}", "Number, Text, Switch, List, Map or Nothing."),
        ("Json(X)", "{Json(X)}", "Read JSON text into a value."),
        ("Get(X, Key)", "{Get(X, Key)}", "A field of a map or an item of a list; same as X #Key."),
    ]),
]

CHECKER = [
    ("E101", "Text is missing its closing quote."),
    ("E201 / E202", "End without a block / a block that is never closed with End."),
    ("E240", "A line that cannot be understood (often a misspelled word)."),
    ("E301", "A name that is not defined."),
    ("E303", "A value in { } that cannot be understood."),
    ("E320 / E321", "Unknown function / wrong number of values for a function."),
    ("E330 / E331", "A library is used but not imported / does not exist."),
    ("E341", "A Wait time that is not valid."),
    ("E346", "On is used with something that is not an event."),
    ("E437", "A GPIO pin number outside 0 to 27."),
    ("W101", "A value is treated as text because a name in it is not defined."),
    ("W102", "A name is defined but never used."),
    ("W103", "A new name looks like a misspelling of an existing one."),
    ("W110", "An endless loop without a pause."),
    ("S001", "A password, token or key written in the program. Use {System Env \"NAME\"}."),
    ("S002", "Data sent over unencrypted http://. Use https://."),
    ("S003", "A page or server open to the network without a password or token."),
    ("S004", "A value pasted into a command line. Pass it as a separate value."),
    ("S005", "A file name that comes from outside the program. Check it first."),
    ("S006", "A secret printed on screen."),
]


def sections():
    """All help sections: [(section title, [(title, insert text, explanation)])]."""
    result = [("Language: " + title, entries) for title, entries in LANGUAGE]
    for cls in LIBRARIES.values():
        entries = [(f"Import {cls.name}", f"Import {cls.name}", cls.summary)]
        entries += [(command, command, description) for command, description in cls.commands]
        result.append((f"Library: {cls.name}", entries))
    result.append(("Checker findings", [(code, "", text) for code, text in CHECKER]))
    return result
