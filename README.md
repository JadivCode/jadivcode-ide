# JadivCode IDE

A desktop editor for the [JadivCode](https://github.com/JadivCode/jadivcode)
programming language on Linux.

- **Editor** with syntax colors, line numbers and automatic indenting.
- **Live checking**: mistakes and unsafe code are underlined while you
  type, with a "Did you mean ...?" hint and one-click fixes.
- **Run** and **Run simulated** (no hardware or screen needed), with an
  input line for `Ask` questions.
- **Help panel**: recipes for complete programs, the whole language, every
  command of every library and every checker finding, with a search box.
  Double-click inserts an example.
- **Blocks**: see and edit the program as connected blocks instead of
  text. Blocks and text stay the same program in both directions.
- **Window designer** and **Web page designer**: place texts, buttons,
  inputs, checkboxes and sliders with the mouse. They read the window that
  is already in the program and write changes back in place.
- **AI helper** (optional): explains problems in plain words. Your program
  is sent to the Claude API only when you ask for it.
- **Updates**: the IDE can update itself and JadivCode.

## Install

Install JadivCode first, then the IDE:

```bash
curl -fsSL https://raw.githubusercontent.com/JadivCode/jadivcode/main/install.sh | bash
```

```bash
curl -fsSL https://raw.githubusercontent.com/JadivCode/jadivcode-ide/main/install.sh | bash
```

The IDE needs PyQt5:

```bash
sudo apt install python3-pyqt5
```

Start it from the application menu or with:

```bash
jadivcode-ide
```

Remove it with `bash install.sh --uninstall`.

## Keys

| Key | Action |
|---|---|
| F5 | Run |
| Shift+F5 | Run simulated |
| Ctrl+F5 | Stop |
| Ctrl+Shift+F | Apply every automatic fix |
| Ctrl+B | Blocks |
| Ctrl+D | Window designer |
| Ctrl+Shift+D | Web page designer |
| F1 | Documentation |

## Blocks

Open **Tools → Blocks**. The whole program appears as blocks joined from
top to bottom. Add blocks from the left, then drag from a coloured dot at
the bottom of a block to the block that comes next. Drag a dot to empty
space to remove its link. Select a block to edit it on the right.

- **Program starts here** begins the program.
- **When this is used** runs its blocks when an item, pin or event is used.
- **If** has three dots: `yes`, `no` and `next`.
- **Repeat**, **While**, **Forever** and **Block of lines** (a `For` loop
  or a `Function`) have an `inside` dot for the blocks they contain.
- **Any line** holds one line of JadivCode for everything else.

Blocks and text are two views of the same program:

- Opening Blocks reads the program text, including changes typed by hand.
- **Update the program** writes the blocks back as text.
- The positions of the blocks are stored in the last line of the program
  (`// blocks: ...`) and reused while the text still matches them.

The **Help** tab inside Blocks has the same searchable help as the main
window, plus a guide to using blocks and **recipes**: complete examples
(windows, web pages, pins, webhooks, files) that are added as a whole set
of blocks with one click.

## Designers

Open **Tools → Window designer** or **Web page designer**. Add items from
the left, drag them into place, edit the name, text and size on the right.

The designers work in both directions:

- They read the window or page that is already in the program.
- **Update the program** changes those lines in place. Other lines,
  comments and your handlers stay as they are.
- Renaming an item renames it everywhere in the program.
- Removing an item also removes its `On` handler.

In a program without a window or page yet, the button reads **Insert
code** and adds new lines at the cursor.

Items snap to a 5 pixel grid. A web page places items from top to bottom
in the order you arrange them; exact positions are used only for windows.

## Updates

**Help → Check for updates** looks for a newer JadivCode and JadivCode IDE
and, after you agree, installs both by running their installers. The IDE
also looks once at start, in the background; switch that off with
**Help → Check for updates at start**.

- An update is offered when the version number on the `main` branch of the
  repository is higher than the installed one.
- The check downloads two small files from `raw.githubusercontent.com`.
  Nothing about you or your programs is sent.
- If you say no to an update, the check at start does not ask about the
  same version again.
- A copy that was not installed with the installer (a git folder, Code
  Master) is only reported; update it the way you installed it.
- Restart the IDE after an update.

## Development

```bash
python3 main.py
QT_QPA_PLATFORM=offscreen python3 -m unittest discover -s tests
```

The IDE finds the interpreter in `~/.local/share/jadivcode`, on the Python
path, or in the folder named by the `JADIVCODE_HOME` environment variable.

## License

MIT License. See [LICENSE](LICENSE).
