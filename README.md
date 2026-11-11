# JadivCode IDE

A desktop editor for the [JadivCode](https://github.com/JadivCode/jadivcode)
programming language on Linux.

- **Editor** with syntax colors, line numbers and automatic indenting.
- **Live checking**: mistakes and unsafe code are underlined while you
  type, with a "Did you mean ...?" hint and one-click fixes.
- **Run** and **Run simulated** (no hardware or screen needed), with an
  input line for `Ask` questions.
- **Window designer**: place buttons, texts, inputs, checkboxes and sliders
  with the mouse; the IDE writes the `GUI` lines for you.
- **Library browser**: every command of every library, inserted with a
  double-click.
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
| Ctrl+D | Window designer |
| F1 | Documentation |

## Window designer

Open **Tools → Window designer**. Add items from the left, drag them into
place, edit the id, text and size on the right, then choose **Insert
code**. The designer reads `WindowWrite ...` lines that are already in the
program, so you can reopen a design and continue.

Items snap to a 5 pixel grid.

## Development

```bash
python3 main.py examples.jdv
QT_QPA_PLATFORM=offscreen python3 -m unittest discover -s tests
```

The IDE finds the interpreter in `~/.local/share/jadivcode`, on the Python
path, or in the folder named by the `JADIVCODE_HOME` environment variable.

## License

Apache License 2.0. See [LICENSE](LICENSE).
