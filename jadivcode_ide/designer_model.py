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


def ordered_items(design):
    items = list(design["items"])
    if design.get("target", "GUI") != "GUI":
        # A web page flows from top to bottom, so keep the visual order.
        items.sort(key=lambda item: (item["y"], item["x"]))
    return items


def prop_lines(design):
    lib = design.get("target", "GUI")
    lines = [f"{lib} Title = {quote(design['title'])}"]
    if lib == "GUI":
        lines.append(f"GUI Size = {int(design['width'])}x{int(design['height'])}")
    return lines


def item_line(design, item):
    lib = design.get("target", "GUI")
    parts = [f"Define {item['id']} = {lib} {item['kind']}"]
    value = item_value(item)
    if value:
        parts.append(value)
    if lib == "GUI":
        parts.append(f"at {item['x']}, {item['y']} size {item['w']}, {item['h']}")
    return " ".join(parts)


def handler_lines(item):
    return ["", f"On {item['id']}", f"    Write = {item['id']} was pressed", "End"]


def has_import(source, lib):
    return bool(re.search(rf"(?im)^\s*import\b.*\b{lib}\b", source))


def generate_code(design, existing_source=""):
    """Return the JadivCode lines that build the designed window or page."""
    lib = design.get("target", "GUI")
    lines = []
    if not has_import(existing_source, lib):
        lines += [f"Import {lib}", ""]
    lines += prop_lines(design) + [""]
    items = ordered_items(design)
    lines += [item_line(design, item) for item in items]
    if design.get("handlers"):
        for item in items:
            if item["kind"] == "Button":
                lines += handler_lines(item)
    return "\n".join(lines) + "\n"


def _line_target(line):
    """Which library a designer line belongs to, and whether it is an item."""
    match = ITEM_RE.match(line)
    if match:
        return ("WebUI" if match.group(2).lower() == "webui" else "GUI"), "item"
    match = OLD_WRITE_RE.match(line)
    if match:
        return ("WebUI" if (match.group(1) or "").lower() == "webui" else "GUI"), "item"
    match = PROP_RE.match(line)
    if match:
        return ("WebUI" if match.group(1).lower() == "webui" else "GUI"), "prop"
    return None, None


OPENER_RE = re.compile(r"(?i)^\s*(repeat|while|forever|for|function)\b")


def _opens_block(line):
    """True when a line starts a block that needs its own End."""
    if OPENER_RE.match(line):
        return True
    if re.match(r"(?i)^\s*if\b", line):
        return not re.search(r"(?i)\bthen\s+\S", line)
    if re.match(r"(?i)^\s*on\b", line):
        return "=" not in line and not re.search(r"(?i)\belse\s+loop\s*$", line)
    return False


def remove_handlers(lines, names):
    """Drop the ``On <name>`` handlers of items that no longer exist."""
    if not names:
        return lines
    pattern = re.compile(r"(?i)^\s*on\s+(" + "|".join(re.escape(n) for n in names) + r")\b")
    out = []
    index = 0
    while index < len(lines):
        line = lines[index]
        if pattern.match(line):
            if _opens_block(line):
                depth = 1
                index += 1
                while index < len(lines) and depth:
                    if _opens_block(lines[index]):
                        depth += 1
                    elif re.match(r"(?i)^\s*end\s*$", lines[index]):
                        depth -= 1
                    index += 1
            else:
                index += 1
            # Do not leave two blank lines where the handler was.
            if out and not out[-1].strip() and index < len(lines) and not lines[index].strip():
                index += 1
            continue
        out.append(line)
        index += 1
    return out


def apply_to_source(design, source):
    """Write a design back into the program it was read from.

    The lines that define the window or page and its items are replaced in
    place; everything else (handlers, other statements, comments) stays.
    Renamed items are renamed everywhere.  Returns the new program text, or
    None when the program has no designer lines for this target yet.
    """
    lib = design.get("target", "GUI")
    lines = source.splitlines()
    item_at, prop_at = [], []
    for index, line in enumerate(lines):
        target, kind = _line_target(line)
        if target == lib:
            (item_at if kind == "item" else prop_at).append(index)
    if not item_at and not prop_at:
        return None
    managed = set(item_at) | set(prop_at)
    kept = {item["orig"].lower() for item in design["items"] if item.get("orig")}
    removed = []
    for index in item_at:
        match = ITEM_RE.match(lines[index]) or OLD_WRITE_RE.match(lines[index])
        name = match.group(1) if match.re is ITEM_RE else match.group(4)
        if name.lower() not in kept:
            removed.append(name)
    renames = {item["orig"]: item["id"] for item in design["items"]
               if item.get("orig") and item["orig"].lower() != item["id"].lower()}
    items = ordered_items(design)
    new_items = [item_line(design, item) for item in items]
    new_props = prop_lines(design)
    props_index = prop_at[0] if prop_at else (item_at[0] if item_at else None)
    items_index = item_at[0] if item_at else None
    out = []
    for index, line in enumerate(lines):
        if index == props_index:
            out += new_props
            if not prop_at:
                out.append("")
        if index == items_index:
            out += new_items
        if index in managed:
            continue
        for old, new in renames.items():
            line = re.sub(rf"(?i)(?<![\w\"]){re.escape(old)}(?![\w\"])", new, line)
        out.append(line)
    if items_index is None:
        # The program had only Title/Size lines: put the items after them.
        at = out.index(new_props[-1]) + 1
        out[at:at] = [""] + new_items
    text = "\n".join(remove_handlers(out, removed))
    if design.get("handlers"):
        for item in items:
            if item["kind"] == "Button" and not re.search(
                    rf"(?im)^\s*on\s+{re.escape(item['id'])}\b", text):
                text = text.rstrip("\n") + "\n" + "\n".join(handler_lines(item))
    if not has_import(text, lib):
        text = f"Import {lib}\n\n" + text
    return text.rstrip("\n") + "\n"


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
            "kind": kind, "id": name, "orig": name, "text": text, "x": coords.get("x", 20),
            "y": y, "w": coords.get("w", width), "h": coords.get("h", height)})
        flow_y = y + coords.get("h", height) + 10
    if seen_target:
        design["target"] = seen_target
    return design
