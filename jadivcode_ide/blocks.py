"""Block editor: build a program by connecting blocks with the mouse."""

from PyQt5.QtCore import QPointF, QRectF, Qt
from PyQt5.QtGui import QBrush, QColor, QFont, QPainter, QPainterPath, QPen
from PyQt5.QtWidgets import (QDialog, QDialogButtonBox, QFormLayout, QGraphicsItem,
                             QGraphicsObject, QGraphicsPathItem, QGraphicsScene,
                             QGraphicsView, QGroupBox, QHBoxLayout, QLabel, QLineEdit,
                             QPlainTextEdit, QPushButton, QTabWidget, QTreeWidget,
                             QTreeWidgetItem, QVBoxLayout, QWidget)

from . import blocks_model as model
from .reference import sections

WIDTH = 200
HEIGHT = 74
PORT = 7


class BlockItem(QGraphicsObject):
    def __init__(self, block, dialog):
        super().__init__()
        self.block = block
        self.dialog = dialog
        self.setFlags(QGraphicsItem.ItemIsMovable | QGraphicsItem.ItemIsSelectable
                      | QGraphicsItem.ItemSendsGeometryChanges)
        self.setPos(block["x"], block["y"])
        self.setZValue(1)

    @property
    def spec(self):
        return model.BLOCKS[self.block["type"]]

    def boundingRect(self):
        return QRectF(-PORT, -PORT, WIDTH + 2 * PORT, HEIGHT + 2 * PORT + 12)

    def input_point(self):
        return QPointF(WIDTH / 2, 0)

    def output_point(self, port):
        outputs = self.spec[3]
        index = outputs.index(port)
        return QPointF(WIDTH * (index + 1) / (len(outputs) + 1), HEIGHT)

    def port_at(self, pos):
        """Name of the output under ``pos`` (item coordinates), or None."""
        for port in self.spec[3]:
            point = self.output_point(port)
            if abs(pos.x() - point.x()) <= PORT + 5 and abs(pos.y() - point.y()) <= PORT + 6:
                return port
        return None

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemPositionHasChanged:
            self.block["x"], self.block["y"] = int(self.x()), int(self.y())
            self.dialog.redraw_links()
        return super().itemChange(change, value)

    def paint(self, painter, option, widget=None):
        title, category, _, outputs, has_input = self.spec
        color = QColor(model.COLORS[category])
        painter.setRenderHint(QPainter.Antialiasing)
        body = QRectF(0, 0, WIDTH, HEIGHT)
        painter.setPen(QPen(QColor("#2f6fed") if self.isSelected() else color.darker(130),
                            3 if self.isSelected() else 1))
        painter.setBrush(QBrush(QColor("#ffffff")))
        painter.drawRoundedRect(body, 8, 8)
        header = QPainterPath()
        header.setFillRule(Qt.WindingFill)
        header.addRoundedRect(QRectF(0, 0, WIDTH, 26), 8, 8)
        header.addRect(QRectF(0, 14, WIDTH, 12))
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(color))
        painter.drawPath(header.simplified())
        font = QFont(painter.font())
        font.setBold(True)
        painter.setFont(font)
        painter.setPen(QColor("#ffffff"))
        painter.drawText(QRectF(10, 0, WIDTH - 20, 26), Qt.AlignVCenter | Qt.AlignLeft, title)
        font.setBold(False)
        painter.setFont(font)
        painter.setPen(QColor("#1c2230"))
        text = painter.fontMetrics().elidedText(model.summary(self.block), Qt.ElideRight,
                                                WIDTH - 20)
        painter.drawText(QRectF(10, 30, WIDTH - 20, 24), Qt.AlignVCenter | Qt.AlignLeft, text)
        painter.setPen(QPen(QColor("#5b6275")))
        if has_input:
            painter.setBrush(QBrush(QColor("#ffffff")))
            painter.drawEllipse(self.input_point(), PORT - 1, PORT - 1)
        small = QFont(font)
        small.setPointSize(max(7, font.pointSize() - 2))
        painter.setFont(small)
        for port in outputs:
            point = self.output_point(port)
            painter.setBrush(QBrush(color))
            painter.setPen(QPen(color.darker(130)))
            painter.drawEllipse(point, PORT, PORT)
            if len(outputs) > 1:
                painter.setPen(QColor("#5b6275"))
                painter.drawText(QRectF(point.x() - 30, HEIGHT - 20, 60, 12), Qt.AlignCenter,
                                 port)


class BlockView(QGraphicsView):
    """Canvas that lets the user drag a wire from an output to another block."""

    def __init__(self, scene, dialog):
        super().__init__(scene)
        self.dialog = dialog
        self.wire = None
        self.wire_from = None
        self.setRenderHint(QPainter.Antialiasing)
        self.setDragMode(QGraphicsView.RubberBandDrag)

    def block_at(self, view_pos):
        for item in self.items(view_pos):
            if isinstance(item, BlockItem):
                return item
        return None

    def mousePressEvent(self, event):
        item = self.block_at(event.pos())
        if item is not None and event.button() == Qt.LeftButton:
            port = item.port_at(item.mapFromScene(self.mapToScene(event.pos())))
            if port is not None:
                self.wire_from = (item, port)
                self.wire = self.scene().addPath(QPainterPath(),
                                                 QPen(QColor("#2f6fed"), 2, Qt.DashLine))
                self.wire.setZValue(2)
                return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.wire is not None:
            item, port = self.wire_from
            self.wire.setPath(wire_path(item.mapToScene(item.output_point(port)),
                                        self.mapToScene(event.pos())))
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self.wire is not None:
            item, port = self.wire_from
            self.scene().removeItem(self.wire)
            self.wire = None
            target = self.block_at(event.pos())
            if target is None or target is item:
                model.unlink(self.dialog.graph, item.block["id"], port)
            else:
                model.link(self.dialog.graph, item.block["id"], port, target.block["id"])
            self.dialog.redraw_links()
            return
        super().mouseReleaseEvent(event)


def wire_path(start, end):
    path = QPainterPath(start)
    bend = max(30.0, abs(end.y() - start.y()) / 2)
    path.cubicTo(QPointF(start.x(), start.y() + bend), QPointF(end.x(), end.y() - bend), end)
    return path


class BlocksDialog(QDialog):
    """The program as connected blocks.

    The dialog reads the program text into blocks when it opens and returns
    the whole program as text in ``self.code`` when it is accepted, so
    blocks and text always describe the same program.
    """

    def __init__(self, parent=None, source=""):
        super().__init__(parent)
        self.setWindowTitle("Blocks")
        self.resize(1180, 720)
        self.code = ""
        self.graph = model.parse_code(source)
        self.items = {}
        self.link_items = []
        self.fields = {}

        self.scene = QGraphicsScene(self)
        self.scene.setBackgroundBrush(QBrush(QColor("#eef0f4")))
        self.view = BlockView(self.scene, self)
        self.scene.selectionChanged.connect(self.show_selected)

        palette = QGroupBox("Add a block")
        palette_layout = QVBoxLayout(palette)
        for kind in model.PALETTE:
            button = QPushButton(model.BLOCKS[kind][0])
            button.clicked.connect(lambda _checked=False, k=kind: self.add(k))
            palette_layout.addWidget(button)
        palette_layout.addStretch(1)
        tidy = QPushButton("Tidy up")
        tidy.setToolTip("Arrange all connected blocks neatly")
        tidy.clicked.connect(self.tidy)
        palette_layout.addWidget(tidy)
        palette.setFixedWidth(240)

        self.form_box = QGroupBox("Selected block")
        self.form = QFormLayout(self.form_box)
        how = QLabel(
            "How it works\n\n"
            "1. Add blocks from the left. A new block is joined to the selected one.\n"
            "2. Drag from a coloured dot at the bottom of a block to the block that comes "
            "next.\n"
            "3. Drag a dot to empty space to remove its link.\n"
            "4. Select a block to edit it here. Press Delete to remove it.\n\n"
            "If has three dots: yes, no, and next (what happens afterwards). Blocks that "
            "contain other blocks have an 'inside' dot.\n\n"
            "The blocks always show the whole program. Changes you make in the text "
            "appear here the next time you open Blocks, and the other way round.")
        how.setWordWrap(True)
        block_page = QWidget()
        block_layout = QVBoxLayout(block_page)
        block_layout.addWidget(self.form_box)
        block_layout.addWidget(how)
        block_layout.addStretch(1)

        tabs = QTabWidget()
        tabs.addTab(block_page, "Block")
        tabs.addTab(self.build_help(), "Help")
        tabs.setFixedWidth(340)
        self.tabs = tabs

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Ok).setText("Update the program")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        row = QHBoxLayout()
        row.addWidget(palette)
        row.addWidget(self.view, 1)
        row.addWidget(tabs)
        layout = QVBoxLayout(self)
        layout.addLayout(row, 1)
        layout.addWidget(buttons)

        self.rebuild()
        self.show_selected()
        self.view.ensureVisible(0, 0, 10, 10)

    # -- help ------------------------------------------------------------
    def build_help(self):
        """The same help as in the main window, searchable."""
        self.help_search = QLineEdit()
        self.help_search.setPlaceholderText("Search the help (button, loop, wait...)")
        self.help_search.setClearButtonEnabled(True)
        self.help_search.textChanged.connect(self.filter_help)
        tree = QTreeWidget()
        tree.setHeaderHidden(True)
        for title, entries in sections(blocks=True):
            top = QTreeWidgetItem([title])
            font = top.font(0)
            font.setBold(True)
            top.setFont(0, font)
            for name, insert, explanation in entries:
                child = QTreeWidgetItem([name])
                child.setData(0, Qt.UserRole, insert)
                child.setData(0, Qt.UserRole + 1, explanation)
                child.setToolTip(0, explanation)
                top.addChild(child)
            tree.addTopLevelItem(top)
        tree.currentItemChanged.connect(self.show_help)
        tree.itemDoubleClicked.connect(lambda _item, _column: self.add_help_example())
        self.help_tree = tree
        self.help_text = QPlainTextEdit()
        self.help_text.setReadOnly(True)
        self.help_text.setMaximumHeight(150)
        self.help_text.setPlaceholderText(
            "Select an entry to see what it does.\nDouble-click to add its example as blocks.")
        self.help_add = QPushButton("Add the example as blocks")
        self.help_add.clicked.connect(self.add_help_example)
        self.help_add.setEnabled(False)
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addWidget(self.help_search)
        layout.addWidget(tree, 1)
        layout.addWidget(self.help_text)
        layout.addWidget(self.help_add)
        return page

    def show_help(self, item, _previous=None):
        insert = (item.data(0, Qt.UserRole) or "") if item is not None else ""
        explanation = (item.data(0, Qt.UserRole + 1) or "") if item is not None else ""
        usable = bool(insert) and item is not None and not item.childCount()
        self.help_add.setEnabled(usable)
        if item is None or item.childCount():
            self.help_text.setPlainText("")
            return
        self.help_text.setPlainText(explanation + ("\n\nExample:\n" + insert if insert else ""))

    def filter_help(self, text):
        words = text.lower().split()
        for index in range(self.help_tree.topLevelItemCount()):
            top = self.help_tree.topLevelItem(index)
            shown = 0
            for row in range(top.childCount()):
                child = top.child(row)
                haystack = " ".join([top.text(0), child.text(0),
                                     child.data(0, Qt.UserRole) or "",
                                     child.data(0, Qt.UserRole + 1) or ""]).lower()
                match = all(word in haystack for word in words)
                child.setHidden(not match)
                shown += match
            top.setHidden(shown == 0)
            top.setExpanded(bool(words) and shown > 0)

    def add_help_example(self):
        item = self.help_tree.currentItem()
        example = item.data(0, Qt.UserRole) if item is not None else None
        if not example or item.childCount():
            return
        if example.startswith("{") and example.endswith("}"):
            example = "Write = " + example  # a value on its own is not a line
        self.attach(lambda: model.append_code(self.graph, example))

    # -- canvas ----------------------------------------------------------
    def rebuild(self, select=None):
        """Draw every block of the graph again."""
        self.scene.blockSignals(True)
        self.scene.clear()
        self.items = {}
        self.link_items = []
        for block in self.graph["blocks"]:
            item = BlockItem(block, self)
            self.items[block["id"]] = item
            self.scene.addItem(item)
        self.scene.blockSignals(False)
        self.redraw_links()
        self.fit_scene()
        if select in self.items:
            self.items[select].setSelected(True)
            self.view.ensureVisible(self.items[select])
        self.show_selected()

    def fit_scene(self):
        right = max((b["x"] for b in self.graph["blocks"]), default=0) + WIDTH + 400
        bottom = max((b["y"] for b in self.graph["blocks"]), default=0) + HEIGHT + 400
        self.scene.setSceneRect(0, 0, max(right, 1200), max(bottom, 900))

    def selected(self):
        items = [i for i in self.scene.selectedItems() if isinstance(i, BlockItem)]
        return items[0] if len(items) == 1 else None

    def anchor(self):
        """(block id, output) where new blocks are attached."""
        item = self.selected()
        if item is not None:
            block = item.block
            outputs = model.BLOCKS[block["type"]][3]
            for port in outputs:
                if model.target_of(self.graph, block["id"], port) is None:
                    return block["id"], port
            if "next" in outputs:
                return block["id"], "next"
            return None, None
        start = model.start_of(self.graph)
        if start is None:
            return None, None
        return model.last_in_chain(self.graph, start["id"]), "next"

    def attach(self, make):
        """Create blocks with ``make()`` and join them at the anchor."""
        anchor_id, port = self.anchor()
        created = make()
        if not created:
            return
        first = created[0]
        base = model.find(self.graph, anchor_id) if anchor_id is not None else None
        if base is not None and port in model.BLOCKS[base["type"]][3]:
            following = model.target_of(self.graph, anchor_id, port)
            if model.link(self.graph, anchor_id, port, first) and following is not None:
                tail = model.last_in_chain(self.graph, first)
                if "next" in model.BLOCKS[model.find(self.graph, tail)["type"]][3]:
                    model.link(self.graph, tail, "next", following)
            x = base["x"] + (model.STEP_X if port != "next" else 0)
            y = base["y"] + (model.STEP_Y if port == "next" else model.STEP_Y // 2)
        else:
            x = 40
            y = max((b["y"] for b in self.graph["blocks"] if b["id"] not in created),
                    default=0) + model.STEP_Y
        self.place_new(created, x, y)
        self.rebuild(select=first)

    def place_new(self, created, x, y):
        """Lay out new blocks without moving the blocks that follow them."""
        ids = set(created)
        saved = {b["id"]: (b["x"], b["y"]) for b in self.graph["blocks"] if b["id"] not in ids}
        model.layout(self.graph, created[0], x, y)
        for block in self.graph["blocks"]:
            if block["id"] in saved:
                block["x"], block["y"] = saved[block["id"]]

    def add(self, kind):
        self.attach(lambda: [model.add_block(self.graph, kind)["id"]])

    def tidy(self):
        model.layout(self.graph)
        self.rebuild()

    def delete_selected(self):
        removed = False
        for item in [i for i in self.scene.selectedItems() if isinstance(i, BlockItem)]:
            if item.block["type"] == "start":
                continue  # a program always has a beginning
            model.remove_block(self.graph, item.block["id"])
            removed = True
        if removed:
            self.rebuild()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Delete and not isinstance(self.focusWidget(), QLineEdit):
            self.delete_selected()
            return
        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            return  # Enter in a field must not close the dialog
        super().keyPressEvent(event)

    def redraw_links(self):
        for path in self.link_items:
            self.scene.removeItem(path)
        self.link_items = []
        for item in self.graph["links"]:
            source, target = self.items.get(item["from"]), self.items.get(item["to"])
            if source is None or target is None:
                continue
            path = QGraphicsPathItem(wire_path(source.mapToScene(source.output_point(item["port"])),
                                               target.mapToScene(target.input_point())))
            path.setPen(QPen(QColor("#5b6275"), 2))
            path.setZValue(0)
            self.scene.addItem(path)
            self.link_items.append(path)

    # -- form ------------------------------------------------------------
    def show_selected(self):
        while self.form.rowCount():
            self.form.removeRow(0)
        self.fields = {}
        item = self.selected()
        if item is None:
            self.form_box.setTitle("Selected block")
            self.form.addRow(QLabel("Select one block to edit it."))
            return
        title, _, params, _, _ = item.spec
        self.form_box.setTitle(title)
        if not params:
            self.form.addRow(QLabel("This block has nothing to set."))
        for name, label, _ in params:
            edit = QLineEdit(item.block["params"].get(name, ""))
            edit.textEdited.connect(
                lambda text, n=name, i=item: self.param_changed(i, n, text))
            caption = QLabel(label)
            caption.setWordWrap(True)
            self.form.addRow(caption)
            self.form.addRow(edit)
            self.fields[name] = edit
        if item.block["type"] != "start":
            remove = QPushButton("Remove block")
            remove.clicked.connect(self.delete_selected)
            self.form.addRow(remove)

    def param_changed(self, item, name, text):
        item.block["params"][name] = text.replace("\n", " ")
        item.update()

    def accept(self):
        self.code, self.loose = model.generate_code(self.graph)
        super().accept()
