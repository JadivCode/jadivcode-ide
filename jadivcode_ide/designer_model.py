"""Pure logic of the window designer: no Qt here, so it is easy to test."""

import re

KINDS = {
    # kind: (id prefix, default text, default width, default height)
    "Text": ("T", "Text", 160, 24),
    "Button": ("B", "Button", 110, 32),
    "Input": ("I", "", 180, 28),
    "Checkbox": ("C", "Checkbox", 160, 24),
    "Slider": ("S", "50", 180, 40),
}
GRID = 5

WRITE_RE = re.compile(
    r'(?i)^\s*(?:GUI\s+Write|[^\W\d]\w*)\s+(Text|Button|Input|Checkbox|Slider)\s+'
    r'"([^"]*)"\s+"([^"]*)"(?:\s+on\s+[^=]*?)?\s*=\s*(.*?)\s*$')
TITLE_RE = re.compile(r'(?i)^\s*(?:GUI\s+Set|[^\W\d]\w*)\s+Title(?:\s+on\s+[^=]*?)?\s*=\s*(.*?)\s*$')
SIZE_RE = re.compile(r'(?i)^\s*(?:GUI\s+Set|[^\W\d]\w*)\s+Size(?:\s+on\s+[^=]*?)?\s*=\s*"?(\d+)\s*x\s*(\d+)"?\s*$')
COORD_RE = re.compile(r"(?i)\b([xywh])\s*[=:]?\s*(-?\d+)")


def snap(value):
    return int(round(value / GRID) * GRID)


def new_design():
    return {"title": "My app", "width": 400, "height": 300, "items": [], "handlers": True}


def next_id(design, kind):
    prefix = KINDS[kind][0]
    used = {item["id"].lower() for item in design["items"]}
    number = 1
    while f"{prefix}{number:02d}".lower() in used:
        number += 1
    return f"{prefix}{number:02d}"


def add_item(design, kind, x=20, y=20):
    prefix, text, width, height = KINDS[kind]
    item = {"kind": kind, "id": next_id(design, kind), "text": text,
            "x": snap(x), "y": snap(y), "w": width, "h": height}
    design["items"].append(item)
    return item


def quote(text):
    """Quote text so JadivCode always reads it as text."""
    clean = str(text).replace('"', "'").replace("{", "{{").replace("}", "}}")
    return f'"{clean}"'


def unquote(text):
    text = text.strip()
    if len(text) >= 2 and text[0] == '"' and text[-1] == '"':
        text = text[1:-1]
    return text.replace("{{", "{").replace("}}", "}")


def generate_code(design, existing_source=""):
    """Return the JadivCode lines that build the designed window."""
    lines = []
    if not re.search(r"(?im)^\s*import\b.*\bgui\b", existing_source):
        lines += ["Import GUI", ""]
    lines += [
        "Define Window = GUI Window #1",
        "Define WindowWrite = GUI Write {} on Window #1",
        "Define WindowSet = GUI Set {} on Window #1",
        "",
        f"WindowSet Title = {quote(design['title'])}",
        f"WindowSet Size = {int(design['width'])}x{int(design['height'])}",
        "",
    ]
    for item in design["items"]:
        position = f"X = {item['x']}, Y = {item['y']}, W = {item['w']}, H = {item['h']}"
        if item["kind"] == "Slider":
            try:
                value = str(int(float(item["text"])))
            except ValueError:
                value = "0"
        else:
            value = quote(item["text"])
        lines.append(f'WindowWrite {item["kind"]} "{position}" "{item["id"]}" = {value}')
    lines += ["", "Start Window"]
    buttons = [item for item in design["items"] if item["kind"] == "Button"]
    if design.get("handlers") and buttons:
        lines += ["", "Define ButtonPress = GUI Read Button {} on Window #1"]
        for item in buttons:
            lines += ["", f'On ButtonPress "{item["id"]}"',
                      f"    Write = {item['id']} was pressed", "End"]
    return "\n".join(lines) + "\n"


def parse_code(source):
    """Read a design back from program text (best effort)."""
    design = new_design()
    for line in source.splitlines():
        match = WRITE_RE.match(line)
        if match:
            kind = match.group(1).capitalize()
            coords = {m.group(1).lower(): int(m.group(2))
                      for m in COORD_RE.finditer(match.group(2))}
            _, _, width, height = KINDS[kind]
            design["items"].append({
                "kind": kind, "id": match.group(3), "text": unquote(match.group(4)),
                "x": coords.get("x", 20), "y": coords.get("y", 20),
                "w": coords.get("w", width), "h": coords.get("h", height)})
            continue
        match = SIZE_RE.match(line)
        if match:
            design["width"], design["height"] = int(match.group(1)), int(match.group(2))
            continue
        match = TITLE_RE.match(line)
        if match:
            design["title"] = unquote(match.group(1))
    return design
