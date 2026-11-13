"""Pure logic of the block editor (no Qt): blocks, links, text in both directions.

A program is a set of blocks joined by links.  Every block has outputs
("next", and for some blocks "yes"/"no" or "inside"); a link joins one
output to one other block.

``from_code`` turns program text into blocks and ``generate_code`` turns
blocks back into text, so the editor can open any program and write its
changes back.
"""

import json
import re

MARKER = "// blocks: "
VERSION = 2

# type: (title, category, [(parameter, label, default)], [outputs], has_input)
BLOCKS = {
    "start": ("Program starts here", "event", [], ["next"], False),
    "event": ("When this is used", "event",
              [("name", "Item, pin or event", "Button1")], ["inside", "next"], True),
    "write": ("Write", "basic", [("text", "Text to show", "Hello, world!")], ["next"], True),
    "ask": ("Ask", "basic", [("name", "Store the answer as", "Name"),
                             ("text", "Question", "What is your name?")], ["next"], True),
    "define": ("Define", "basic", [("name", "Name", "Count"), ("value", "Value", "0")],
               ["next"], True),
    "set": ("Set", "basic", [("name", "Name", "Count"), ("value", "New value", "Count + 1")],
            ["next"], True),
    "wait": ("Wait", "basic", [("time", "How long (5s, 200ms, 2m)", "1s")], ["next"], True),
    "if": ("If", "flow", [("cond", "Condition", "Count > 3")], ["yes", "no", "next"], True),
    "repeat": ("Repeat", "flow", [("count", "How many times", "3")], ["inside", "next"], True),
    "while": ("While", "flow", [("cond", "Condition", "Count < 10")], ["inside", "next"], True),
    "forever": ("Forever", "flow", [], ["inside", "next"], True),
    "group": ("Block of lines", "other",
              [("text", "First line (For..., Function...)", "For I = 1 to 10")],
              ["inside", "next"], True),
    "line": ("Any line", "other", [("text", "A JadivCode line", "Import GUI")], ["next"], True),
    "stop": ("Stop the program", "flow", [], [], True),
}
PALETTE = ["event", "write", "ask", "define", "set", "wait", "if", "repeat", "while",
           "forever", "group", "line", "stop"]
COLORS = {"event": "#d98b1f", "basic": "#2f6fed", "flow": "#7c3aed", "other": "#5b6275"}

STEP_Y = 114
STEP_X = 250

NAME = r"[^\W\d]\w*"
SIMPLE = [
    ("write", re.compile(r"(?i)^write\s*=\s*(?P<text>.*)$")),
    ("ask", re.compile(rf"(?i)^ask\s+(?P<name>{NAME})\s*=\s*(?P<text>.*)$")),
    ("define", re.compile(rf"(?i)^define\s+(?P<name>{NAME})\s*=\s*(?P<value>.*)$")),
    ("set", re.compile(rf"(?i)^set\s+(?P<name>{NAME}(?:\s+{NAME})?)\s*=\s*(?P<value>.*)$")),
    ("wait", re.compile(r"(?i)^wait\s+(?P<time>.+)$")),
    ("stop", re.compile(r"(?i)^(stop|exit)$")),
]
OPENERS = {
    "if": re.compile(r"(?i)^if\s+(?P<cond>.+)$"),
    "repeat": re.compile(r"(?i)^repeat\s+(?P<count>.+?)(?:\s+times?)?$"),
    "while": re.compile(r"(?i)^while\s+(?P<cond>.+)$"),
    "forever": re.compile(r"(?i)^forever$"),
    "event": re.compile(r"(?i)^on\s+(?P<name>.+?)(?:\s+do)?$"),
    "group": re.compile(r"(?i)^(?P<text>(?:for|function)\b.*)$"),
}


def new_graph():
    graph = {"version": VERSION, "blocks": [], "links": [], "next_id": 1}
    add_block(graph, "start", 40, 30)
    return graph


def add_block(graph, kind, x=40, y=40, params=None):
    spec = BLOCKS[kind][2]
    block = {"id": graph["next_id"], "type": kind, "x": int(x), "y": int(y),
             "params": {name: default for name, _, default in spec}}
    if params:
        block["params"].update({k: str(v) for k, v in params.items() if k in block["params"]})
    graph["next_id"] += 1
    graph["blocks"].append(block)
    return block


def find(graph, block_id):
    for block in graph["blocks"]:
        if block["id"] == block_id:
            return block
    return None


def start_of(graph):
    for block in graph["blocks"]:
        if block["type"] == "start":
            return block
    return None


def remove_block(graph, block_id):
    graph["blocks"] = [b for b in graph["blocks"] if b["id"] != block_id]
    graph["links"] = [l for l in graph["links"] if block_id not in (l["from"], l["to"])]


def unlink(graph, block_id, port):
    graph["links"] = [l for l in graph["links"]
                      if not (l["from"] == block_id and l["port"] == port)]


def link(graph, from_id, port, to_id):
    """Join an output to a block. Returns False when the link is not allowed."""
    source, target = find(graph, from_id), find(graph, to_id)
    if source is None or target is None or from_id == to_id:
        return False
    if port not in BLOCKS[source["type"]][3] or not BLOCKS[target["type"]][4]:
        return False
    unlink(graph, from_id, port)
    graph["links"].append({"from": from_id, "port": port, "to": to_id})
    return True


def target_of(graph, block_id, port):
    for item in graph["links"]:
        if item["from"] == block_id and item["port"] == port:
            return item["to"]
    return None


def has_incoming(graph, block_id):
    return any(item["to"] == block_id for item in graph["links"])


def last_in_chain(graph, block_id):
    """Follow 'next' links from a block to the end of its chain."""
    seen = set()
    while block_id not in seen:
        seen.add(block_id)
        nxt = target_of(graph, block_id, "next")
        if nxt is None or "next" not in BLOCKS[find(graph, block_id)["type"]][3]:
            return block_id
        block_id = nxt
    return block_id


def summary(block):
    """Short text shown inside a block."""
    p = block["params"]
    kind = block["type"]
    if kind == "event":
        return p["name"]
    if kind in ("write", "line", "group"):
        return p["text"]
    if kind == "ask":
        return f"{p['name']} = {p['text']}"
    if kind in ("define", "set"):
        return f"{p['name']} = {p['value']}"
    if kind == "wait":
        return p["time"]
    if kind in ("if", "while"):
        return p["cond"]
    if kind == "repeat":
        return f"{p['count']} times"
    return ""


# ----------------------------------------------------------------------
# Blocks -> text
# ----------------------------------------------------------------------
def _line(block):
    p = block["params"]
    kind = block["type"]
    if kind == "write":
        return f"Write = {p['text']}"
    if kind == "ask":
        return f"Ask {p['name']} = {p['text']}"
    if kind == "define":
        return f"Define {p['name']} = {p['value']}"
    if kind == "set":
        return f"Set {p['name']} = {p['value']}"
    if kind == "wait":
        return f"Wait {p['time']}"
    if kind == "line":
        return p["text"]
    return "Stop"


HEADS = {
    "repeat": lambda p: f"Repeat {p['count']} times",
    "while": lambda p: f"While {p['cond']}",
    "forever": lambda p: "Forever",
    "event": lambda p: f"On {p['name']}",
    "group": lambda p: p["text"],
}


def _chain(graph, block_id, indent, active, used, lines):
    pad = "    " * indent
    while block_id is not None:
        block = find(graph, block_id)
        if block is None:
            return
        if block_id in active:
            lines.append(f"{pad}// This link goes back to an earlier block. "
                         "Use a Repeat, While or Forever block to loop.")
            return
        used.add(block_id)
        active = active | {block_id}
        kind = block["type"]
        p = block["params"]
        if block.get("gap") and lines and lines[-1] != "":
            lines.append("")
        if kind == "if":
            word, current = "If", block
            while True:
                lines.append(f"{pad}{word} {current['params']['cond']}")
                _chain(graph, target_of(graph, current["id"], "yes"), indent + 1, active,
                       used, lines)
                other = find(graph, target_of(graph, current["id"], "no"))
                # A lone If in the "no" branch is written as Else If.
                if other is not None and other["type"] == "if" and other["id"] not in active \
                        and target_of(graph, other["id"], "next") is None \
                        and not other.get("gap"):
                    used.add(other["id"])
                    active = active | {other["id"]}
                    word, current = "Else If", other
                    continue
                if other is not None:
                    lines.append(f"{pad}Else")
                    _chain(graph, other["id"], indent + 1, active, used, lines)
                break
            lines.append(f"{pad}End")
        elif kind in HEADS:
            lines.append(pad + HEADS[kind](p))
            _chain(graph, target_of(graph, block_id, "inside"), indent + 1, active, used, lines)
            lines.append(f"{pad}End")
        elif kind == "line" and not p["text"].strip():
            if lines and lines[-1] != "":
                lines.append("")
        else:
            lines.append(pad + _line(block))
        if "next" not in BLOCKS[kind][3]:
            return
        block_id = target_of(graph, block_id, "next")


def program_text(graph):
    """Return (program text without the marker line, number of loose blocks)."""
    lines = []
    used = set()
    ordered = sorted(graph["blocks"], key=lambda b: (b["y"], b["x"]))
    for block in ordered:
        if block["type"] == "start":
            used.add(block["id"])
            _chain(graph, target_of(graph, block["id"], "next"), 0, {block["id"]}, used, lines)
    # "When this is used" blocks that hang free still belong to the program.
    for block in ordered:
        if block["type"] == "event" and block["id"] not in used \
                and not has_incoming(graph, block["id"]):
            if lines and lines[-1] != "":
                lines.append("")
            _chain(graph, block["id"], 0, set(), used, lines)
    while lines and lines[-1] == "":
        lines.pop()
    loose = len([b for b in graph["blocks"] if b["id"] not in used])
    return "\n".join(lines) + ("\n" if lines else ""), loose


def generate_code(graph):
    """Return (program text with the layout marker, number of loose blocks)."""
    text, loose = program_text(graph)
    graph["version"] = VERSION
    stored = json.dumps(graph, separators=(",", ":"), sort_keys=True)
    return text + ("\n" if text else "") + MARKER + stored + "\n", loose


# ----------------------------------------------------------------------
# Text -> blocks
# ----------------------------------------------------------------------
def strip_marker(source):
    return "\n".join(line for line in source.splitlines() if not line.startswith(MARKER))


def _one_line(kind, text):
    """True when an If or On line carries its statement on the same line."""
    if kind == "if":
        return bool(re.search(r"(?i)\bthen\s+\S", text))
    if kind == "event":
        return "=" in text or text.rstrip().endswith('"') and text.count('"') >= 2 \
            and bool(re.search(r'"\s*[^\W\d]\w*(\s|=)[^"]*"\s*$', text)) \
            or bool(re.search(r"(?i)\belse\s+loop\s*$", text))
    return False


def _classify(text):
    """Return (kind, params, opens_block) for one program line."""
    for kind, pattern in OPENERS.items():
        match = pattern.match(text)
        if match and not _one_line(kind, text):
            return kind, match.groupdict(), True
    for kind, pattern in SIMPLE:
        match = pattern.match(text)
        if match:
            return kind, match.groupdict(), False
    return "line", {"text": text}, False


def append_code(graph, source, after_id=None, port="next"):
    """Add the lines of ``source`` as blocks after a block. Returns new ids."""
    created = []
    # Each frame: where the next block of that level gets linked from.
    frames = [{"from": after_id, "port": port, "owner": None, "extra": 0}]
    gap = False
    for raw in source.splitlines():
        text = raw.strip()
        if raw.startswith(MARKER):
            continue
        if not text:
            gap = True
            continue
        word = text.split(None, 1)[0].lower()
        if word == "end" and len(text) == 3 and len(frames) > 1:
            frame = frames.pop()
            for _ in range(frame["extra"]):
                frames.pop()
            owner = frame.get("outer", frame["owner"])
            if "next" in BLOCKS[find(graph, owner)["type"]][3]:
                frames[-1].update({"from": owner, "port": "next"})
            else:
                frames[-1].update({"from": None, "port": "next"})
            continue
        if word == "else" and len(frames) > 1 \
                and find(graph, frames[-1]["owner"])["type"] == "if":
            owner = frames[-1]["owner"]
            rest = text[4:].strip()
            if not rest:
                frames[-1].update({"from": owner, "port": "no"})
                continue
            nested = OPENERS["if"].match(rest)
            if nested and not _one_line("if", rest):
                # Else If: an If block inside the "no" branch.
                block = add_block(graph, "if", params=nested.groupdict())
                created.append(block["id"])
                link(graph, owner, "no", block["id"])
                frames[-1].update({"from": None, "port": "next"})
                frames.append({"from": block["id"], "port": "yes", "owner": block["id"],
                               "outer": frames[-1].get("outer", owner),
                               "extra": frames[-1]["extra"] + 1})
                continue
        kind, params, opens = _classify(text)
        block = add_block(graph, kind, params=params)
        if gap and created:
            block["gap"] = True
        gap = False
        created.append(block["id"])
        frame = frames[-1]
        if frame["from"] is not None:
            link(graph, frame["from"], frame["port"], block["id"])
        if opens:
            frame.update({"from": None, "port": "next"})
            frames.append({"from": block["id"],
                           "port": "yes" if kind == "if" else "inside",
                           "owner": block["id"], "extra": 0})
        elif "next" in BLOCKS[kind][3]:
            frame.update({"from": block["id"], "port": "next"})
        else:
            frame.update({"from": None, "port": "next"})
    return created


def layout(graph, block_id=None, x=40, y=30):
    """Place a chain of blocks top to bottom, branches to the right."""
    if block_id is None:
        start = start_of(graph)
        if start is None:
            return y
        block_id = start["id"]
    seen = set()

    def place(current, left, top):
        width = 0
        while current is not None and current not in seen:
            seen.add(current)
            block = find(graph, current)
            block["x"], block["y"] = left, top
            bottom = top + STEP_Y
            offset = left + STEP_X
            for branch in BLOCKS[block["type"]][3]:
                if branch == "next":
                    continue
                target = target_of(graph, current, branch)
                if target is not None and target not in seen:
                    end, used = place(target, offset, top + STEP_Y // 2)
                    bottom = max(bottom, end)
                    offset += used + STEP_X
                    width = max(width, offset - left - STEP_X)
            top = bottom
            current = target_of(graph, current, "next") \
                if "next" in BLOCKS[block["type"]][3] else None
        return top, width

    end, _ = place(block_id, x, y)
    return end


def from_code(source):
    """Build a graph from program text."""
    graph = new_graph()
    append_code(graph, strip_marker(source), start_of(graph)["id"], "next")
    layout(graph)
    return graph


def _stored_graph(source):
    for line in source.splitlines():
        if not line.startswith(MARKER):
            continue
        try:
            graph = json.loads(line[len(MARKER):])
        except ValueError:
            return None
        if not isinstance(graph, dict) or not isinstance(graph.get("blocks"), list) \
                or not isinstance(graph.get("links"), list):
            return None
        old = graph.get("version") != VERSION
        blocks = []
        for block in graph["blocks"]:
            if not isinstance(block, dict) or block.get("type") not in BLOCKS \
                    or not isinstance(block.get("id"), int):
                continue
            params = block.get("params") if isinstance(block.get("params"), dict) else {}
            clean = {name: str(params.get(name, default))
                     for name, _, default in BLOCKS[block["type"]][2]}
            entry = {"id": block["id"], "type": block["type"], "params": clean,
                     "x": int(block.get("x", 40) or 0), "y": int(block.get("y", 40) or 0)}
            if block.get("gap"):
                entry["gap"] = True
            blocks.append(entry)
        result = {"version": VERSION, "blocks": blocks, "links": [],
                  "next_id": max([b["id"] for b in blocks], default=0) + 1}
        for item in graph["links"]:
            if not isinstance(item, dict):
                continue
            port = item.get("port")
            source_block = find(result, item.get("from"))
            if old and source_block is not None and source_block["type"] == "event" \
                    and port == "next":
                port = "inside"  # version 1 stored an event's body under "next"
            link(result, item.get("from"), port, item.get("to"))
        return result
    return None


def normalize(text):
    """Program text reduced to what matters for comparing two versions."""
    return [line.strip() for line in strip_marker(text).splitlines() if line.strip()]


def parse_code(source):
    """Blocks for a program: the stored layout when it still matches the text,
    otherwise blocks built from the text itself."""
    stored = _stored_graph(source)
    if stored is not None and start_of(stored) is not None:
        if normalize(program_text(stored)[0]) == normalize(source):
            return stored
    return from_code(source)
