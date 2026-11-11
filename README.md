# JadivCode IDE

A desktop editor for the [JadivCode](https://github.com/JadivCode/jadivcode)
programming language on Linux.

- **Editor** with syntax colors, line numbers and automatic indenting.
- **Live checking**: mistakes and unsafe code are underlined while you
  type, with a "Did you mean ...?" hint and one-click fixes.
- **Run** and **Run simulated** (no hardware or screen needed), with an
  input line for `Ask` questions.
- **Help panel**: the whole language, every command of every library and
  every checker finding, with a search box. Double-click inserts an example.
- **Blocks**: build a program by connecting blocks with the mouse instead
  of typing. Good for people who think in pictures.
- **Window designer** and **Web page designer**: place texts, buttons,
  inputs, checkboxes and sliders with the mouse; the IDE writes the lines.
- **AI helper** (optional): explains problems in plain words. Your program
  is sent to the Claude API only when you ask for it.

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

Open **Tools → Blocks**. Add blocks from the left, then drag from a
coloured dot at the bottom of a block to the block that comes next. Drag a
dot to empty space to remove its link. Select a block to edit it on the
right.

- **When the program starts** begins the main program.
- **When this is used** runs its blocks when an item, pin or event is used.
- **If** has three dots: `yes`, `no` and `next`.
- **Repeat**, **While** and **Forever** have an `inside` dot for the blocks
  they repeat.
- **Any line** holds one line of JadivCode for everything else.

**Make the program** writes the JadivCode text. The blocks are stored in
the last line of the program (`// blocks: ...`), so opening Blocks again
continues where you stopped. Changes typed into the text are not read back
into the blocks.

## Designers

Open **Tools → Window designer** or **Web page designer**. Add items from
the left, drag them into place, edit the name, text and size on the right,
then choose **Insert code**. The designer reads items that are already in
the program, so you can reopen a design and continue.

Items snap to a 5 pixel grid. A web page places items from top to bottom
in the order you arrange them; exact positions are used only for windows.

## Development

```bash
python3 main.py
QT_QPA_PLATFORM=offscreen python3 -m unittest discover -s tests
```

The IDE finds the interpreter in `~/.local/share/jadivcode`, on the Python
path, or in the folder named by the `JADIVCODE_HOME` environment variable.

## License

MIT License. See [LICENSE](LICENSE).
