"""Block editor: build a program by connecting blocks with the mouse."""

from PyQt5.QtCore import QPointF, QRectF, Qt
from PyQt5.QtGui import QBrush, QColor, QFont, QPainter, QPainterPath, QPen
from PyQt5.QtWidgets import (QCheckBox, QDialog, QDialogButtonBox, QFormLayout,
                             QGraphicsItem, QGraphicsObject, QGraphicsPathItem, QGraphicsScene,
                             QGraphicsView, QGroupBox, QHBoxLayout, QLabel, QLineEdit,
                             QPushButton, QVBoxLayout, QWidget)

from . import blocks_model as model

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
    """Dialog returning generated code in ``self.code`` when accepted."""

    def __init__(self, parent=None, source=""):
        super().__init__(parent)
        self.setWindowTitle("Blocks")
        self.resize(1100, 680)
        self.code = ""
        self.replace = False
        stored = model.parse_code(source)
        self.had_blocks = stored is not None
        self.graph = stored or model.new_graph()
        self.items = {}
        self.link_items = []
        self.fields = {}

        self.scene = QGraphicsScene(self)
        self.scene.setSceneRect(0, 0, 3000, 2000)
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
        palette.setFixedWidth(240)

        self.form_box = QGroupBox("Selected block")
        self.form = QFormLayout(self.form_box)
        help_text = QLabel(
            "How it works\n\n"
            "1. Add blocks from the left.\n"
            "2. Drag from a coloured dot at the bottom of a block to the block that comes "
            "next.\n"
            "3. Drag a dot to empty space to remove its link.\n"
            "4. Select a block to edit it here. Press Delete to remove it.\n\n"
            "If has three dots: yes, no, and next (what happens afterwards). Repeat, While "
            "and Forever have an 'inside' dot for the blocks they repeat.")
        help_text.setWordWrap(True)
        self.replace_box = QCheckBox("Replace the whole program")
        self.replace_box.setChecked(self.had_blocks or not source.strip()
                                    or source.strip().count("\n") <= 1)
        side = QWidget()
        side_layout = QVBoxLayout(side)
        side_layout.setContentsMargins(0, 0, 0, 0)
        side_layout.addWidget(self.form_box)
        side_layout.addWidget(help_text)
        side_layout.addStretch(1)
        side_layout.addWidget(self.replace_box)
        side.setFixedWidth(300)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Ok).setText("Make the program")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        row = QHBoxLayout()
        row.addWidget(palette)
        row.addWidget(self.view, 1)
        row.addWidget(side)
        layout = QVBoxLayout(self)
        layout.addLayout(row, 1)
        layout.addWidget(buttons)

        for block in self.graph["blocks"]:
            self.place(block)
        self.redraw_links()
        self.show_selected()
        self.view.centerOn(200, 150)

    # -- canvas ----------------------------------------------------------
    def place(self, block):
        item = BlockItem(block, self)
        self.items[block["id"]] = item
        self.scene.addItem(item)
        return item

    def add(self, kind):
        selected = self.selected()
        if selected is not None:
            x, y = selected.block["x"], selected.block["y"] + model_height()
        else:
            lowest = max((b["y"] for b in self.graph["blocks"]), default=0)
            x, y = 40, lowest + model_height()
        block = model.add_block(self.graph, kind, x, y)
        item = self.place(block)
        # Join the new block to the selected one when its first output is free.
        if selected is not None and model.BLOCKS[kind][4]:
            for port in model.BLOCKS[selected.block["type"]][3]:
                if model.target_of(self.graph, selected.block["id"], port) is None:
                    model.link(self.graph, selected.block["id"], port, block["id"])
                    break
        self.scene.clearSelection()
        item.setSelected(True)
        self.view.ensureVisible(item)
        self.redraw_links()

    def selected(self):
        items = [i for i in self.scene.selectedItems() if isinstance(i, BlockItem)]
        return items[0] if len(items) == 1 else None

    def delete_selected(self):
        for item in [i for i in self.scene.selectedItems() if isinstance(i, BlockItem)]:
            model.remove_block(self.graph, item.block["id"])
            self.items.pop(item.block["id"], None)
            self.scene.removeItem(item)
            item.deleteLater()
        self.redraw_links()

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
            self.form.addRow(label, edit)
            self.fields[name] = edit
        remove = QPushButton("Remove block")
        remove.clicked.connect(self.delete_selected)
        self.form.addRow(remove)

    def param_changed(self, item, name, text):
        item.block["params"][name] = text.replace("\n", " ")
        item.update()

    def accept(self):
        self.code, _loose = model.generate_code(self.graph)
        self.replace = self.replace_box.isChecked()
        super().accept()


def model_height():
    return HEIGHT + 40
