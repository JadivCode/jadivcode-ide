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

RECIPES = [
    ("A window with a button",
     "Import GUI\n\nGUI Title = My app\nGUI Size = 320x160\n\n"
     "Define Message = GUI Text \"Press the button\" at 20, 20\n"
     "Define Go = GUI Button \"Press me\" at 20, 60\n\n"
     "On Go\n    Set Message = Pressed\nEnd",
     "The smallest window program. Every item has a name; 'On Go' runs when the button "
     "is clicked. The window opens by itself."),
    ("A window that counts clicks",
     "Import GUI\n\nGUI Title = Counter\n"
     "Define Message = GUI Text \"Count: 0\" at 20, 20\n"
     "Define More = GUI Button \"Add one\" at 20, 60\n"
     "Define Count = 0\n\n"
     "On More\n    Set Count = Count + 1\n    Set Message = Count: {Count}\nEnd",
     "Keeps a number in a value and shows it in a text item."),
    ("A text box: read what the user types",
     "Import GUI\n\n"
     "Define Hint = GUI Text \"Type your name and press Enter:\" at 20, 15\n"
     "Define Field = GUI Input at 20, 45 size 200, 28\n"
     "Define Hello = GUI Text \"\" at 20, 90\n\n"
     "On Field\n    Set Hello = Hello, {Event}!\nEnd",
     "'On Field' runs when Enter is pressed. {Event} is the typed text; {Field} gives the "
     "same text at any time."),
    ("A calculator window",
     "Import GUI\nImport Math\n\nGUI Title = Calculator\n"
     "Define Field = GUI Input at 20, 20 size 220, 28\n"
     "Define Result = GUI Text \"Type a calculation and press Enter\" at 20, 60\n\n"
     "On Field\n    Define Answer = {Math Event}\n    If Success = \"None\"\n"
     "        Set Result = That is not a calculation\n    Else\n"
     "        Set Result = {Event} = {Answer}\n    End\nEnd",
     "Math calculates the typed text. Success is \"None\" when the line before failed."),
    ("A checkbox and a slider",
     "Import GUI\n\n"
     "Define Agree = GUI Checkbox \"Switch the lamp\" at 20, 20\n"
     "Define Level = GUI Slider 50 at 20, 60\n"
     "Define Status = GUI Text \"\" at 20, 120\n\n"
     "On Agree\n    Set Status = Lamp is {Agree}\nEnd\n\n"
     "On Level\n    Set Status = Brightness {Event}\nEnd",
     "A checkbox holds ON or OFF, a slider a number from 0 to 100."),
    ("Change how an item looks",
     "Import GUI\n\nDefine Hello = GUI Text \"Hello\" at 20, 20\n"
     "Set Hello Color = red\nSet Hello Size = 18\nWait 2s\nSet Hello = Goodbye\n"
     "Wait 2s\nStop Hello",
     "Properties: Text, Value, Color, Background, Size, Enabled, X, Y, W, H. "
     "'Stop Hello' removes the item."),
    ("Two windows",
     "Import GUI\n\nGUI Title = Main\n"
     "Define Open = GUI Button \"Open settings\" at 20, 20\n"
     "Define Second = GUI Window #2\nSet Second Title = Settings\n"
     "Define Close = GUI Button \"Close\" at 20, 20 on Window #2\n\n"
     "On Open \"Start Second\"\nOn Close \"Stop Second\"",
     "Items go to the first window unless you add 'on Window #2'. Start shows a window, "
     "Stop closes it."),
    ("A web page that switches a lamp",
     "Import WebUI\nImport GPIO\n\nDefine Lamp = GPIO #17\n\n"
     "WebUI Title = Lamp panel\n"
     "Define Status = WebUI Text \"The lamp is OFF\"\n"
     "Define Toggle = WebUI Button \"Toggle lamp\"\n\n"
     "On Toggle\n    If Lamp = ON then Set Lamp = OFF else Set Lamp = ON\n"
     "    Set Status = The lamp is {Lamp}\nEnd",
     "Open http://localhost:8080/ while the program runs. WebUI items work like GUI items."),
    ("A web page for your phone (with a password)",
     "Import WebUI\nImport System\n\nWebUI Title = My panel\nWebUI Host = 0.0.0.0\n"
     "WebUI Password = {System Env \"PAGE_PASSWORD\"}\n\n"
     "Define Hello = WebUI Text \"Hello from JadivCode\"",
     "Host 0.0.0.0 lets other devices connect, so a password is needed. Start the program "
     "with PAGE_PASSWORD set in the environment."),
    ("Blink an LED",
     "Import GPIO\n\nDefine Led = GPIO #17\n\nRepeat 10 times\n    Set Led = ON\n"
     "    Wait 500ms\n    Set Led = OFF\n    Wait 500ms\nEnd",
     "Pins use BCM numbers. Without a Raspberry Pi the pin is simulated."),
    ("A push button switches a lamp",
     "Import GPIO\n\nDefine Button = GPIO Input #4 PullDown\nDefine Lamp = GPIO #17\n\n"
     "On Button Pressed\n    If Lamp = ON then Set Lamp = OFF else Set Lamp = ON\nEnd",
     "Events of an input pin: Pressed, Released, Changed."),
    ("Dim with PWM",
     "Import GPIO\n\nDefine Fan = GPIO PWM #18\n\nFor Speed = 0 to 100 step 20\n"
     "    Set Fan = Speed\n    Wait 1s\nEnd\nSet Fan = OFF",
     "A PWM pin takes a value from 0 to 100."),
    ("Send a webhook (Home Assistant)",
     "Import Web\nImport System\n\nDefine Address = {System Env \"HA_WEBHOOK\"}\n"
     "Web Json Address = state: on, source: jadivcode\n"
     "If Success = \"Full\" then \"Write = sent\" else \"Write = failed: {Error}\"",
     "The address is read from the environment because it works like a password."),
    ("Receive a webhook",
     "Import Web\n\nDefine Server = Web Server #8090\n"
     "Define Hook = Web Read Hook {} on Server #8090\n\n"
     "On Hook \"/lamp\"\n    Write = Received {Event}\nEnd",
     "Try it with: curl -X POST http://localhost:8090/lamp -d '{\"state\": \"on\"}'"),
    ("Read data from the internet",
     "Import Web\n\nDefine Data = {Web Json \"https://api.example.com/data\"}\n"
     "If Success = \"Full\"\n    Write = Temperature: {Data #\"temperature\"}\nElse\n"
     "    Write = Could not read: {Error}\nEnd",
     "Web Json turns the answer into a value; read its fields with #\"name\"."),
    ("Save and read notes in a file",
     "Import File\nImport Time\n\nAsk Note = What do you want to remember?\n"
     "File Append \"notes.txt\" = {Time Date} {Note}\n\n"
     "For each Line in {File Lines \"notes.txt\"}\n    Write = {Line}\nEnd",
     "Append adds a line; Lines reads the file as a list."),
    ("A guessing game",
     "Import Math\n\nDefine Secret = {Math Random 1 20}\nDefine Tries = 0\n\n"
     "Forever\n    Ask Guess = Your guess?\n    Set Tries = Tries + 1\n"
     "    If Guess = Secret\n        Write = Correct after {Tries} tries\n        Break\n"
     "    Else If Guess < Secret\n        Write = Too small\n    Else\n"
     "        Write = Too big\n    End\nEnd",
     "Shows Forever, Break and Else If together."),
    ("Do something every few seconds",
     "Import Time\n\nForever\n    Write = It is {Time Now}\n    Wait 5s\nEnd",
     "An endless loop always needs a Wait."),
]

BLOCKS_HELP = [
    ("What a block is", "",
     "One block is one line of the program. Blocks joined from top to bottom run in "
     "that order."),
    ("Joining blocks", "",
     "Drag from a coloured dot at the bottom of a block onto the block that comes next. "
     "Drag a dot to empty space to remove the link."),
    ("The dots of If", "",
     "yes: blocks to run when the condition is true. no: blocks to run otherwise. "
     "next: what happens after the If, in both cases."),
    ("The inside dot", "",
     "Repeat, While, Forever, 'When this is used' and 'Block of lines' contain other "
     "blocks. Join the first contained block to the inside dot, and the block that "
     "follows the whole thing to next."),
    ("When this is used", "On Go\n    Write = pressed\nEnd",
     "Runs its inside blocks when a button is clicked, a pin changes or a webhook "
     "arrives. Type the name of the item, pin or event into the block."),
    ("Any line", "Import GUI",
     "Holds one line of JadivCode exactly as written. Use it for Import, library "
     "commands, Call, Add, Break and anything else without its own block."),
    ("Block of lines", "For I = 1 to 10\n    Write = {I}\nEnd",
     "A For loop or a Function: its first line is typed into the block and the lines "
     "it contains are joined to the inside dot."),
    ("Windows and web pages in blocks", "Define Go = GUI Button \"Press me\" at 20, 60",
     "Each item is a Define block. React to it with a 'When this is used' block that "
     "carries the item's name. The Recipes section has complete examples; the designers "
     "in the Tools menu place items with the mouse."),
    ("Blocks and text are the same program", "",
     "Opening Blocks reads the program text. 'Update the program' writes the blocks "
     "back as text. Edit whichever is easier."),
    ("Tidy up", "", "Arranges all joined blocks in neat columns."),
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


def sections(blocks=False):
    """All help sections: [(section title, [(title, insert text, explanation)])].

    With ``blocks=True`` the list starts with help for the block editor.
    """
    result = [("Using blocks", BLOCKS_HELP)] if blocks else []
    result.append(("Recipes: complete examples", RECIPES))
    result += [("Language: " + title, entries) for title, entries in LANGUAGE]
    for cls in LIBRARIES.values():
        entries = [(f"Import {cls.name}", f"Import {cls.name}", cls.summary)]
        entries += [(command, command, description) for command, description in cls.commands]
        result.append((f"Library: {cls.name}", entries))
    result.append(("Checker findings", [(code, "", text) for code, text in CHECKER]))
    return result
