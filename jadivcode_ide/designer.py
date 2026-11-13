"""Visual designer: place GUI items with the mouse, get JadivCode lines."""

from PyQt5.QtCore import QRectF, Qt, pyqtSignal
from PyQt5.QtGui import QBrush, QColor, QPainter, QPen
from PyQt5.QtWidgets import (QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFormLayout, QGraphicsItem,
                             QGraphicsObject, QGraphicsScene, QGraphicsView, QGroupBox,
                             QHBoxLayout, QLabel, QLineEdit, QPushButton, QSpinBox,
                             QVBoxLayout, QWidget)

from . import designer_model as model


class DesignItem(QGraphicsObject):
    """One item on the canvas. Keeps its dictionary in sync while dragged."""

    moved = pyqtSignal()

    def __init__(self, data):
        super().__init__()
        self.data_ = data
        self.setFlags(QGraphicsItem.ItemIsMovable | QGraphicsItem.ItemIsSelectable
                      | QGraphicsItem.ItemSendsGeometryChanges)
        self.setPos(data["x"], data["y"])
        self.setCursor(Qt.SizeAllCursor)

    def boundingRect(self):
        return QRectF(0, 0, self.data_["w"], self.data_["h"])

    def resized(self):
        self.prepareGeometryChange()
        self.update()

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemPositionChange and self.scene():
            rect = self.scene().sceneRect()
            x = min(max(model.snap(value.x()), 0), max(0, rect.width() - self.data_["w"]))
            y = min(max(model.snap(value.y()), 0), max(0, rect.height() - self.data_["h"]))
            value.setX(x)
            value.setY(y)
            self.data_["x"], self.data_["y"] = int(x), int(y)
            self.moved.emit()
            return value
        return super().itemChange(change, value)

    def paint(self, painter, option, widget=None):
        data = self.data_
        rect = self.boundingRect().adjusted(0.5, 0.5, -0.5, -0.5)
        kind = data["kind"]
        painter.setRenderHint(QPainter.Antialiasing)
        ink = QColor("#1c2230")
        if kind == "Button":
            painter.setPen(QPen(QColor("#8b93a7")))
            painter.setBrush(QBrush(QColor("#e4e7ee")))
            painter.drawRoundedRect(rect, 4, 4)
            painter.setPen(ink)
            painter.drawText(rect, Qt.AlignCenter, data["text"])
        elif kind == "Input":
            painter.setPen(QPen(QColor("#8b93a7")))
            painter.setBrush(QBrush(QColor("#ffffff")))
            painter.drawRect(rect)
            painter.setPen(ink)
            painter.drawText(rect.adjusted(5, 0, -5, 0), Qt.AlignVCenter | Qt.AlignLeft,
                             data["text"])
        elif kind == "Checkbox":
            box = QRectF(1, rect.height() / 2 - 7, 14, 14)
            painter.setPen(QPen(QColor("#8b93a7")))
            painter.setBrush(QBrush(QColor("#ffffff")))
            painter.drawRect(box)
            painter.setPen(ink)
            painter.drawText(rect.adjusted(22, 0, 0, 0), Qt.AlignVCenter | Qt.AlignLeft,
                             data["text"])
        elif kind == "Slider":
            middle = rect.height() / 2
            painter.setPen(QPen(QColor("#8b93a7"), 3))
            painter.drawLine(int(6), int(middle), int(rect.width() - 6), int(middle))
            try:
                share = min(max(float(data["text"]) / 100.0, 0.0), 1.0)
            except ValueError:
                share = 0.0
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(QColor("#2f6fed")))
            painter.drawEllipse(QRectF(6 + share * (rect.width() - 24), middle - 7, 14, 14))
        else:
            painter.setPen(ink)
            painter.drawText(rect, Qt.AlignVCenter | Qt.AlignLeft, data["text"])
        if self.isSelected():
            painter.setBrush(Qt.NoBrush)
            painter.setPen(QPen(QColor("#2f6fed"), 1, Qt.DashLine))
            painter.drawRect(rect)


class DesignerDialog(QDialog):
    """Dialog returning generated code in ``self.code`` when accepted."""

    def __init__(self, parent=None, source="", target=None):
        super().__init__(parent)
        self.setWindowTitle("Designer")
        self.resize(980, 600)
        self.source = source
        self.code = ""
        self.merged = None
        self.loading = False
        self.design = model.parse_code(source)
        if not self.design["items"]:
            self.design = model.new_design(target or "GUI")
        elif target and self.design["target"] != target:
            self.design = model.new_design(target)

        self.scene = QGraphicsScene(self)
        self.view = QGraphicsView(self.scene)
        self.view.setRenderHint(QPainter.Antialiasing)
        self.view.setBackgroundBrush(QBrush(QColor("#9aa1b2")))
        self.view.setAlignment(Qt.AlignCenter)
        self.scene.selectionChanged.connect(self.show_selected)

        palette = QGroupBox("Add an item")
        palette_layout = QVBoxLayout(palette)
        for kind in model.KINDS:
            button = QPushButton(kind)
            button.clicked.connect(lambda _checked=False, k=kind: self.add(k))
            palette_layout.addWidget(button)
        palette_layout.addStretch(1)
        hint = QLabel("Drag items to move them.\nPress Delete to remove\nthe selected item.")
        hint.setWordWrap(True)
        palette_layout.addWidget(hint)

        self.target_box = QComboBox()
        self.target_box.addItem("Desktop window (GUI)", "GUI")
        self.target_box.addItem("Web page (WebUI)", "WebUI")
        self.target_box.setCurrentIndex(1 if self.design["target"] == "WebUI" else 0)
        self.target_box.currentIndexChanged.connect(self.window_changed)
        self.title_edit = QLineEdit(self.design["title"])
        self.width_spin = self.spin(120, 3000, self.design["width"])
        self.height_spin = self.spin(80, 3000, self.design["height"])
        self.handlers_box = QCheckBox("Add click handlers for buttons")
        self.handlers_box.setChecked(True)
        window_box = QGroupBox("Window or page")
        window_form = QFormLayout(window_box)
        window_form.addRow("Make a", self.target_box)
        window_form.addRow("Title", self.title_edit)
        window_form.addRow("Width", self.width_spin)
        window_form.addRow("Height", self.height_spin)
        window_form.addRow(self.handlers_box)
        self.title_edit.textChanged.connect(self.window_changed)
        self.width_spin.valueChanged.connect(self.window_changed)
        self.height_spin.valueChanged.connect(self.window_changed)

        self.id_edit = QLineEdit()
        self.text_edit = QLineEdit()
        self.x_spin = self.spin(0, 3000, 0)
        self.y_spin = self.spin(0, 3000, 0)
        self.w_spin = self.spin(10, 3000, 100)
        self.h_spin = self.spin(10, 3000, 30)
        self.delete_button = QPushButton("Remove item")
        self.delete_button.clicked.connect(self.delete_selected)
        self.item_box = QGroupBox("Selected item")
        item_form = QFormLayout(self.item_box)
        item_form.addRow("Name", self.id_edit)
        item_form.addRow("Text / value", self.text_edit)
        item_form.addRow("X", self.x_spin)
        item_form.addRow("Y", self.y_spin)
        item_form.addRow("Width", self.w_spin)
        item_form.addRow("Height", self.h_spin)
        item_form.addRow(self.delete_button)
        for widget in (self.id_edit, self.text_edit):
            widget.textEdited.connect(self.item_changed)
        for widget in (self.x_spin, self.y_spin, self.w_spin, self.h_spin):
            widget.valueChanged.connect(self.item_changed)

        self.web_note = QLabel("A web page places items from top to bottom, in the order "
                               "you arrange them here. Exact positions are not used.")
        self.web_note.setWordWrap(True)
        self.web_note.setVisible(self.design["target"] == "WebUI")
        side = QWidget()
        side_layout = QVBoxLayout(side)
        side_layout.setContentsMargins(0, 0, 0, 0)
        side_layout.addWidget(window_box)
        side_layout.addWidget(self.web_note)
        side_layout.addWidget(self.item_box)
        side_layout.addStretch(1)
        side.setFixedWidth(290)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        existing = bool(self.design["items"]) and self.design.get("target") == (
            target or self.design.get("target"))
        buttons.button(QDialogButtonBox.Ok).setText(
            "Update the program" if existing else "Insert code")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        row = QHBoxLayout()
        row.addWidget(palette)
        row.addWidget(self.view, 1)
        row.addWidget(side)
        layout = QVBoxLayout(self)
        layout.addLayout(row, 1)
        layout.addWidget(buttons)

        self.rebuild()
        self.show_selected()

    @staticmethod
    def spin(low, high, value):
        box = QSpinBox()
        box.setRange(low, high)
        box.setSingleStep(model.GRID)
        box.setValue(int(value))
        return box

    # -- canvas ----------------------------------------------------------
    def rebuild(self):
        self.scene.clear()
        width, height = self.design["width"], self.design["height"]
        self.scene.setSceneRect(0, 0, width, height)
        background = self.scene.addRect(0, 0, width, height, QPen(QColor("#5b6275")),
                                        QBrush(QColor("#f4f5f7")))
        background.setZValue(-1)
        for data in self.design["items"]:
            self.place(data)

    def place(self, data):
        item = DesignItem(data)
        item.moved.connect(self.show_selected)
        self.scene.addItem(item)
        return item

    def selected(self):
        items = [i for i in self.scene.selectedItems() if isinstance(i, DesignItem)]
        return items[0] if items else None

    def add(self, kind):
        items = self.design["items"]
        below = max((d["y"] + d["h"] for d in items), default=10) + 10
        height = model.KINDS[kind][2]
        if below + height > self.design["height"]:
            below = 20
        data = model.add_item(self.design, kind, 20, below)
        item = self.place(data)
        self.scene.clearSelection()
        item.setSelected(True)

    def delete_selected(self):
        item = self.selected()
        if item is not None:
            self.design["items"].remove(item.data_)
            self.scene.removeItem(item)
            item.deleteLater()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Delete and not isinstance(self.focusWidget(), QLineEdit):
            self.delete_selected()
            return
        super().keyPressEvent(event)

    # -- forms -----------------------------------------------------------
    def window_changed(self):
        self.design["target"] = self.target_box.currentData()
        web = self.design["target"] == "WebUI"
        self.web_note.setVisible(web)
        self.design["title"] = self.title_edit.text()
        self.design["width"] = self.width_spin.value()
        self.design["height"] = self.height_spin.value()
        self.scene.setSceneRect(0, 0, self.design["width"], self.design["height"])
        for item in self.scene.items():
            if not isinstance(item, DesignItem):
                item.setRect(0, 0, self.design["width"], self.design["height"])

    def show_selected(self):
        item = self.selected()
        self.item_box.setEnabled(item is not None)
        if item is None:
            return
        self.loading = True
        data = item.data_
        self.item_box.setTitle(f"Selected item ({data['kind']})")
        if not self.id_edit.hasFocus():
            self.id_edit.setText(data["id"])
        if not self.text_edit.hasFocus():
            self.text_edit.setText(str(data["text"]))
        self.x_spin.setValue(data["x"])
        self.y_spin.setValue(data["y"])
        self.w_spin.setValue(data["w"])
        self.h_spin.setValue(data["h"])
        self.loading = False

    def item_changed(self, *_):
        item = self.selected()
        if item is None or self.loading:
            return
        data = item.data_
        new_id = self.id_edit.text().strip()
        if model.valid_name(self.design, new_id, data):
            data["id"] = new_id
        data["text"] = self.text_edit.text()
        data["w"], data["h"] = self.w_spin.value(), self.h_spin.value()
        item.resized()
        item.setPos(self.x_spin.value(), self.y_spin.value())

    def accept(self):
        self.design["handlers"] = self.handlers_box.isChecked()
        # When the program already contains this window or page, the design
        # is written back into it; otherwise new lines are produced.
        self.merged = model.apply_to_source(self.design, self.source)
        self.code = model.generate_code(self.design, self.source)
        super().accept()
