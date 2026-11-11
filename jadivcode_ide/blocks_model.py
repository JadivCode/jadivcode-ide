"""Pure logic of the block editor (no Qt): blocks, links and code generation.

A program is a set of blocks joined by links.  Every block has outputs
("next", and for some blocks "yes"/"no" or "inside"); a link joins one
output to one other block.
"""

import json

MARKER = "// blocks: "

# type: (title, category, [(parameter, label, default)], [outputs], has_input)
BLOCKS = {
    "start": ("When the program starts", "event", [], ["next"], False),
    "event": ("When this is used", "event",
              [("name", "Item, pin or event name", "Button1")], ["next"], False),
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
    "forever": ("Forever", "flow", [], ["inside"], True),
    "line": ("Any line", "other", [("text", "A JadivCode line", "Import GUI")], ["next"], True),
    "stop": ("Stop the program", "flow", [], [], True),
}
PALETTE = ["start", "event", "write", "ask", "define", "set", "wait", "if", "repeat",
           "while", "forever", "line", "stop"]
COLORS = {"event": "#d98b1f", "basic": "#2f6fed", "flow": "#7c3aed", "other": "#5b6275"}


def new_graph():
    graph = {"blocks": [], "links": [], "next_id": 1}
    add_block(graph, "start", 40, 30)
    return graph


def add_block(graph, kind, x=40, y=40):
    _, _, params, _, _ = BLOCKS[kind]
    block = {"id": graph["next_id"], "type": kind, "x": int(x), "y": int(y),
             "params": {name: default for name, _, default in params}}
    graph["next_id"] += 1
    graph["blocks"].append(block)
    return block


def find(graph, block_id):
    for block in graph["blocks"]:
        if block["id"] == block_id:
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


def summary(block):
    """Short text shown inside a block."""
    p = block["params"]
    kind = block["type"]
    if kind == "event":
        return f"When {p['name']} is used"
    if kind in ("write", "line"):
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
        if kind == "if":
            lines.append(f"{pad}If {p['cond']}")
            _chain(graph, target_of(graph, block_id, "yes"), indent + 1, active, used, lines)
            if target_of(graph, block_id, "no") is not None:
                lines.append(f"{pad}Else")
                _chain(graph, target_of(graph, block_id, "no"), indent + 1, active, used, lines)
            lines.append(f"{pad}End")
        elif kind in ("repeat", "while", "forever"):
            head = {"repeat": f"Repeat {p.get('count', '')} times",
                    "while": f"While {p.get('cond', '')}", "forever": "Forever"}[kind]
            lines.append(pad + head)
            _chain(graph, target_of(graph, block_id, "inside"), indent + 1, active, used, lines)
            lines.append(f"{pad}End")
        else:
            lines.append(pad + _line(block))
        block_id = target_of(graph, block_id, "next")


def generate_code(graph):
    """Return (code, number of blocks that are not connected to anything)."""
    lines = []
    used = set()
    ordered = sorted(graph["blocks"], key=lambda b: (b["y"], b["x"]))
    for block in ordered:
        if block["type"] == "start":
            used.add(block["id"])
            _chain(graph, target_of(graph, block["id"], "next"), 0, {block["id"]}, used, lines)
    for block in ordered:
        if block["type"] == "event":
            used.add(block["id"])
            if lines and lines[-1] != "":
                lines.append("")
            lines.append(f"On {block['params']['name']}")
            _chain(graph, target_of(graph, block["id"], "next"), 1, {block["id"]}, used, lines)
            lines.append("End")
    loose = len([b for b in graph["blocks"] if b["id"] not in used])
    lines += ["", MARKER + json.dumps(graph, separators=(",", ":"), sort_keys=True)]
    return "\n".join(lines).lstrip("\n") + "\n", loose


def parse_code(source):
    """Return the graph stored in program text, or None."""
    for line in source.splitlines():
        if line.startswith(MARKER):
            try:
                graph = json.loads(line[len(MARKER):])
            except ValueError:
                return None
            if not isinstance(graph, dict) or not isinstance(graph.get("blocks"), list) \
                    or not isinstance(graph.get("links"), list):
                return None
            blocks = []
            for block in graph["blocks"]:
                if not isinstance(block, dict) or block.get("type") not in BLOCKS \
                        or not isinstance(block.get("id"), int):
                    continue
                params = block.get("params") if isinstance(block.get("params"), dict) else {}
                clean = {name: str(params.get(name, default))
                         for name, _, default in BLOCKS[block["type"]][2]}
                blocks.append({"id": block["id"], "type": block["type"], "params": clean,
                               "x": int(block.get("x", 40) or 0), "y": int(block.get("y", 40) or 0)})
            result = {"blocks": blocks, "links": [],
                      "next_id": max([b["id"] for b in blocks], default=0) + 1}
            for item in graph["links"]:
                if isinstance(item, dict):
                    link(result, item.get("from"), item.get("port"), item.get("to"))
            return result
    return None
