"""Pure logic of the window and web page designer (no Qt, easy to test)."""

import re

KINDS = {
    # kind: (default text, default width, default height)
    "Text": ("Text", 160, 24),
    "Button": ("Button", 110, 32),
    "Input": ("", 180, 28),
    "Checkbox": ("Checkbox", 160, 24),
    "Slider": ("50", 180, 40),
}
TARGETS = {"GUI": "window", "WebUI": "web page"}
GRID = 5

NAME_RE = re.compile(r"^[^\W\d]\w*$")
ITEM_RE = re.compile(
    r'(?i)^\s*Define\s+([^\W\d]\w*)\s*=\s*(GUI|WebUI)\s+(Text|Button|Input|Checkbox|Slider)\b(.*)$')
PROP_RE = re.compile(r"(?i)^\s*(GUI|WebUI)\s+(Title|Size)\s*=\s*(.*?)\s*$")
OLD_WRITE_RE = re.compile(
    r'(?i)^\s*(?:(GUI|WebUI)\s+Write|[^\W\d]\w*)\s+(Text|Button|Input|Checkbox|Slider)\s+'
    r'"([^"]*)"\s+"([^"]*)"(?:\s+on\s+[^=]*?)?\s*=\s*(.*?)\s*$')
COORD_RE = re.compile(r"(?i)\b([xywh])\s*[=:]?\s*(-?\d+)")
PAIR_RE = r"\s+(-?\d+)\s*,?\s*(-?\d+)"


def snap(value):
    return int(round(value / GRID) * GRID)


def new_design(target="GUI"):
    return {"target": target, "title": "My app", "width": 400, "height": 300, "items": [],
            "handlers": True}


def next_name(design, kind):
    used = {item["id"].lower() for item in design["items"]}
    number = 1
    while f"{kind}{number}".lower() in used:
        number += 1
    return f"{kind}{number}"


def valid_name(design, name, item=None):
    """A usable item name: a JadivCode name that no other item has."""
    if not NAME_RE.match(name or ""):
        return False
    return all(other is item or other["id"].lower() != name.lower()
               for other in design["items"])


def add_item(design, kind, x=20, y=20):
    text, width, height = KINDS[kind]
    item = {"kind": kind, "id": next_name(design, kind), "text": text,
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


def item_value(item):
    if item["kind"] == "Slider":
        try:
            return str(int(float(item["text"])))
        except ValueError:
            return "0"
    if item["kind"] == "Input" and not item["text"]:
        return ""
    return quote(item["text"])


def generate_code(design, existing_source=""):
    """Return the JadivCode lines that build the designed window or page."""
    lib = design.get("target", "GUI")
    lines = []
    if not re.search(rf"(?im)^\s*import\b.*\b{lib}\b", existing_source):
        lines += [f"Import {lib}", ""]
    lines.append(f"{lib} Title = {quote(design['title'])}")
    items = list(design["items"])
    if lib == "GUI":
        lines.append(f"GUI Size = {int(design['width'])}x{int(design['height'])}")
    else:
        # A web page flows from top to bottom, so keep the visual order.
        items.sort(key=lambda item: (item["y"], item["x"]))
    lines.append("")
    for item in items:
        parts = [f"Define {item['id']} = {lib} {item['kind']}"]
        value = item_value(item)
        if value:
            parts.append(value)
        if lib == "GUI":
            parts.append(f"at {item['x']}, {item['y']} size {item['w']}, {item['h']}")
        lines.append(" ".join(parts))
    buttons = [item for item in items if item["kind"] == "Button"]
    if design.get("handlers") and buttons:
        for item in buttons:
            lines += ["", f"On {item['id']}", f"    Write = {item['id']} was pressed", "End"]
    return "\n".join(lines) + "\n"


def _split_value(rest):
    """Split '"text" at 1, 2 size 3, 4' into (value, coordinates)."""
    coords = {}
    for word, keys in (("at", ("x", "y")), ("size", ("w", "h"))):
        match = re.search(rf"(?i)\b{word}{PAIR_RE}", rest)
        if match:
            coords[keys[0]], coords[keys[1]] = int(match.group(1)), int(match.group(2))
            rest = rest[:match.start()] + rest[match.end():]
    rest = re.sub(r"(?i)\s+on\s+\w+\s*#\s*\d+\s*$", "", rest)
    return unquote(rest.strip()), coords


def parse_code(source):
    """Read a design back from program text (best effort)."""
    design = new_design()
    seen_target = None
    flow_y = 20
    for line in source.splitlines():
        match = ITEM_RE.match(line)
        old = OLD_WRITE_RE.match(line) if not match else None
        if match:
            name, lib, kind, rest = match.group(1), match.group(2), match.group(3), match.group(4)
            text, coords = _split_value(rest)
            target = "WebUI" if lib.lower() == "webui" else "GUI"
        elif old:
            kind, name, text = old.group(2), old.group(4), unquote(old.group(5))
            coords = {m.group(1).lower(): int(m.group(2)) for m in COORD_RE.finditer(old.group(3))}
            target = "WebUI" if (old.group(1) or "").lower() == "webui" else "GUI"
        else:
            prop = PROP_RE.match(line)
            if prop:
                if prop.group(2).lower() == "title":
                    design["title"] = unquote(prop.group(3))
                else:
                    size = re.match(r'"?(\d+)\s*x\s*(\d+)"?$', prop.group(3))
                    if size:
                        design["width"], design["height"] = int(size.group(1)), int(size.group(2))
            continue
        kind = kind.capitalize()
        seen_target = seen_target or target
        _, width, height = KINDS[kind]
        if not NAME_RE.match(name) or not valid_name(design, name):
            name = next_name(design, kind)
        y = coords.get("y", flow_y)
        design["items"].append({
            "kind": kind, "id": name, "text": text, "x": coords.get("x", 20), "y": y,
            "w": coords.get("w", width), "h": coords.get("h", height)})
        flow_y = y + coords.get("h", height) + 10
    if seen_target:
        design["target"] = seen_target
    return design
