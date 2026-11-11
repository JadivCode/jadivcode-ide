"""The code editor: line numbers, syntax colors and problem markers."""

import re

from PyQt5.QtCore import QRect, QSize, Qt
from PyQt5.QtGui import (QColor, QFont, QFontDatabase, QPainter, QSyntaxHighlighter,
                         QTextCharFormat, QTextCursor, QTextFormat)
from PyQt5.QtWidgets import QPlainTextEdit, QTextEdit, QToolTip, QWidget

from .core import KEYWORDS, LIBRARIES

SEVERITY_COLORS = {"error": "#e5484d", "warning": "#e2a336", "info": "#3b9eff"}

LIGHT = {"keyword": "#7c3aed", "library": "#0f766e", "string": "#b45309", "number": "#be185d",
         "comment": "#6b7280", "brace": "#2563eb", "ref": "#be185d",
         "gutter": "#f1f2f5", "gutter_text": "#8b90a0", "line": "#f3f5fb"}
DARK = {"keyword": "#c4a7ff", "library": "#5eead4", "string": "#fbbf77", "number": "#f9a8d4",
        "comment": "#8a90a2", "brace": "#93c5fd", "ref": "#f9a8d4",
        "gutter": "#22252e", "gutter_text": "#70768a", "line": "#262a35"}

WORD_OPERATORS = ("then", "else", "and", "or", "not", "is", "to", "in", "each", "times",
                  "from", "step", "on", "off", "true", "false", "nothing", "loop", "list")


def is_dark(widget):
    return widget.palette().window().color().lightness() < 128


class Highlighter(QSyntaxHighlighter):
    def __init__(self, document, colors):
        super().__init__(document)
        self.colors = colors
        libs = "|".join(cls.name for cls in LIBRARIES.values())
        words = "|".join(sorted(set(KEYWORDS) | set(WORD_OPERATORS)))
        self.rules = [
            (re.compile(rf"(?<![\w]){'(?:' + words + ')'}(?!\w)", re.I), "keyword"),
            (re.compile(rf"(?<![\w])(?:{libs})(?!\w)", re.I), "library"),
            (re.compile(r"(?<![\w.])\d+(?:\.\d+)?(?:ms|s|m|h)?(?!\w)"), "number"),
            (re.compile(r"#\s*\d+"), "ref"),
            (re.compile(r'"[^"]*"'), "string"),
            (re.compile(r"\{[^{}]*\}"), "brace"),
        ]
        self.comment = re.compile(r"(^\s*//.*$)|(\s//.*$)|(^\s*#\s(?!\d).*$)")

    def fmt(self, name):
        fmt = QTextCharFormat()
        fmt.setForeground(QColor(self.colors[name]))
        if name == "keyword":
            fmt.setFontWeight(QFont.Bold)
        if name == "comment":
            fmt.setFontItalic(True)
        return fmt

    def highlightBlock(self, text):
        for pattern, name in self.rules:
            for match in pattern.finditer(text):
                self.setFormat(match.start(), match.end() - match.start(), self.fmt(name))
        match = self.comment.search(text)
        if match and text[:match.start()].count('"') % 2 == 0:
            self.setFormat(match.start(), match.end() - match.start(), self.fmt("comment"))


class Gutter(QWidget):
    def __init__(self, editor):
        super().__init__(editor)
        self.editor = editor
        self.setMouseTracking(True)

    def sizeHint(self):
        return QSize(self.editor.gutter_width(), 0)

    def paintEvent(self, event):
        self.editor.paint_gutter(event)

    def mouseMoveEvent(self, event):
        line = self.editor.line_at(event.pos().y())
        found = [d for d in self.editor.diagnostics if d.line == line]
        if found:
            QToolTip.showText(event.globalPos(),
                              "\n".join(f"{d.code}: {d.message}" for d in found), self)
        else:
            QToolTip.hideText()


class CodeEditor(QPlainTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.diagnostics = []
        font = QFontDatabase.systemFont(QFontDatabase.FixedFont)
        font.setPointSize(max(font.pointSize(), 11))
        self.setFont(font)
        self.setLineWrapMode(QPlainTextEdit.NoWrap)
        self.setTabStopDistance(self.fontMetrics().horizontalAdvance(" ") * 4)
        self.colors = DARK if is_dark(self) else LIGHT
        self.highlighter = Highlighter(self.document(), self.colors)
        self.gutter = Gutter(self)
        self.blockCountChanged.connect(self.update_margins)
        self.updateRequest.connect(self.on_update_request)
        self.cursorPositionChanged.connect(self.refresh_selections)
        self.update_margins()
        self.refresh_selections()

    # -- gutter ----------------------------------------------------------
    def gutter_width(self):
        digits = max(2, len(str(self.blockCount())))
        return 22 + self.fontMetrics().horizontalAdvance("9") * digits

    def update_margins(self, *_):
        self.setViewportMargins(self.gutter_width(), 0, 0, 0)

    def on_update_request(self, rect, dy):
        if dy:
            self.gutter.scroll(0, dy)
        else:
            self.gutter.update(0, rect.y(), self.gutter.width(), rect.height())

    def resizeEvent(self, event):
        super().resizeEvent(event)
        rect = self.contentsRect()
        self.gutter.setGeometry(QRect(rect.left(), rect.top(), self.gutter_width(),
                                      rect.height()))

    def line_at(self, y):
        block = self.firstVisibleBlock()
        while block.isValid():
            top = self.blockBoundingGeometry(block).translated(self.contentOffset()).top()
            if top <= y < top + self.blockBoundingRect(block).height():
                return block.blockNumber() + 1
            block = block.next()
        return 0

    def paint_gutter(self, event):
        painter = QPainter(self.gutter)
        painter.fillRect(event.rect(), QColor(self.colors["gutter"]))
        worst = {}
        order = {"error": 0, "warning": 1, "info": 2}
        for diag in self.diagnostics:
            if diag.line not in worst or order[diag.severity] < order[worst[diag.line]]:
                worst[diag.line] = diag.severity
        block = self.firstVisibleBlock()
        height = self.fontMetrics().height()
        while block.isValid():
            top = int(self.blockBoundingGeometry(block).translated(self.contentOffset()).top())
            if top > event.rect().bottom():
                break
            if block.isVisible():
                number = block.blockNumber() + 1
                painter.setPen(QColor(self.colors["gutter_text"]))
                painter.drawText(0, top, self.gutter.width() - 6, height,
                                 Qt.AlignRight | Qt.AlignVCenter, str(number))
                if number in worst:
                    painter.setRenderHint(QPainter.Antialiasing)
                    painter.setPen(Qt.NoPen)
                    painter.setBrush(QColor(SEVERITY_COLORS[worst[number]]))
                    painter.drawEllipse(4, top + height // 2 - 4, 8, 8)
            block = block.next()

    # -- problems --------------------------------------------------------
    def set_diagnostics(self, diagnostics):
        self.diagnostics = list(diagnostics)
        self.refresh_selections()
        self.gutter.update()

    def refresh_selections(self):
        selections = []
        current = QTextEdit.ExtraSelection()
        current.format.setBackground(QColor(self.colors["line"]))
        current.format.setProperty(QTextFormat.FullWidthSelection, True)
        current.cursor = self.textCursor()
        current.cursor.clearSelection()
        selections.append(current)
        for diag in self.diagnostics:
            block = self.document().findBlockByNumber(diag.line - 1)
            if not block.isValid():
                continue
            text = block.text()
            start = len(text) - len(text.lstrip())
            selection = QTextEdit.ExtraSelection()
            selection.format.setUnderlineStyle(QTextCharFormat.WaveUnderline)
            selection.format.setUnderlineColor(QColor(SEVERITY_COLORS[diag.severity]))
            selection.format.setToolTip(f"{diag.code}: {diag.message}")
            cursor = QTextCursor(block)
            cursor.setPosition(block.position() + start)
            cursor.setPosition(block.position() + max(len(text), start + 1)
                               if text.strip() else block.position(), QTextCursor.KeepAnchor)
            selection.cursor = cursor
            selections.append(selection)
        self.setExtraSelections(selections)

    def go_to_line(self, line):
        block = self.document().findBlockByNumber(max(0, line - 1))
        if block.isValid():
            cursor = QTextCursor(block)
            self.setTextCursor(cursor)
            self.centerCursor()
            self.setFocus()

    def replace_all(self, text):
        """Replace the whole text as one undo step, keeping the cursor line."""
        line = self.textCursor().blockNumber()
        cursor = self.textCursor()
        cursor.beginEditBlock()
        cursor.select(QTextCursor.Document)
        cursor.insertText(text)
        cursor.endEditBlock()
        self.go_to_line(line + 1)

    # -- typing helpers --------------------------------------------------
    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Return, Qt.Key_Enter) and not event.modifiers():
            text = self.textCursor().block().text()
            indent = text[:len(text) - len(text.lstrip())]
            word = text.strip().split(" ")[0].lower() if text.strip() else ""
            opens = word in ("repeat", "while", "forever", "for", "function", "else") or \
                (word == "if" and not re.search(r"(?i)\bthen\s+\S", text)) or \
                (word == "on" and not text.rstrip().endswith(('"', "loop")))
            super().keyPressEvent(event)
            self.insertPlainText(indent + ("    " if opens else ""))
            return
        if event.key() == Qt.Key_Tab and not event.modifiers():
            self.insertPlainText("    ")
            return
        super().keyPressEvent(event)
