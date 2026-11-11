"""Main window of the JadivCode IDE."""

import os
import sys
import tempfile

from PyQt5.QtCore import QProcess, QProcessEnvironment, QThread, QTimer, Qt, pyqtSignal
from PyQt5.QtGui import QColor, QIcon, QKeySequence, QTextCharFormat, QTextCursor
from PyQt5.QtWidgets import (QAction, QApplication, QDockWidget, QFileDialog, QHBoxLayout,
                             QLabel, QLineEdit, QListWidget, QListWidgetItem, QMainWindow,
                             QMessageBox, QPlainTextEdit, QPushButton, QTabWidget,
                             QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget)

from . import __version__
from .core import CORE_VERSION, FILE_EXTENSION, apply_fixes, check_source, run_environment
from .designer import DesignerDialog
from .editor import SEVERITY_COLORS, CodeEditor
from .reference import sections

STARTER = """// A new JadivCode program
Write = Hello, world!
"""
FILTER = f"JadivCode programs (*{FILE_EXTENSION});;All files (*)"
DOCS_URL = "https://jadivcode.github.io"


class AIWorker(QThread):
    """Asks the optional AI helper without freezing the window."""

    finished_text = pyqtSignal(str, bool)

    def __init__(self, source, parent=None):
        super().__init__(parent)
        self.source = source

    def run(self):
        try:
            from jadivcode.ai import explain
            self.finished_text.emit(explain(self.source), True)
        except Exception as exc:  # noqa: BLE001 - show every failure to the user
            formatter = getattr(exc, "format", None)
            self.finished_text.emit(formatter() if formatter else str(exc), False)


class MainWindow(QMainWindow):
    def __init__(self, path=None):
        super().__init__()
        self.path = None
        self.process = None
        self.temp_file = None
        self.ai_worker = None
        self.diagnostics = []
        self.resize(1180, 760)

        self.editor = CodeEditor()
        self.setCentralWidget(self.editor)
        self.editor.textChanged.connect(self.schedule_check)
        self.editor.document().modificationChanged.connect(self.update_title)
        self.editor.cursorPositionChanged.connect(self.update_status)

        self.check_timer = QTimer(self)
        self.check_timer.setSingleShot(True)
        self.check_timer.setInterval(400)
        self.check_timer.timeout.connect(self.run_check)

        self.build_actions()
        self.build_bottom()
        self.build_library_dock()
        self.position_label = QLabel()
        self.problem_label = QLabel()
        self.statusBar().addPermanentWidget(self.problem_label)
        self.statusBar().addPermanentWidget(self.position_label)
        self.statusBar().addPermanentWidget(
            QLabel(f"JadivCode {CORE_VERSION}  |  IDE {__version__}"))

        if path:
            self.load(path)
        else:
            self.editor.setPlainText(STARTER)
            self.editor.document().setModified(False)
        self.update_title()
        self.update_status()
        self.run_check()

    # ------------------------------------------------------------------
    # Building the window
    # ------------------------------------------------------------------
    def action(self, text, slot, shortcut=None, tip=None):
        action = QAction(text, self)
        action.triggered.connect(lambda _checked=False: slot())
        if shortcut:
            action.setShortcut(QKeySequence(shortcut))
        action.setToolTip(f"{tip or text}" + (f" ({shortcut})" if shortcut else ""))
        return action

    def build_actions(self):
        self.act_new = self.action("New", self.new_file, "Ctrl+N")
        self.act_open = self.action("Open...", self.open_file, "Ctrl+O")
        self.act_save = self.action("Save", self.save, "Ctrl+S")
        self.act_save_as = self.action("Save as...", self.save_as, "Ctrl+Shift+S")
        self.act_run = self.action("Run", self.run_program, "F5", "Run the program")
        self.act_sim = self.action("Run simulated", lambda: self.run_program(True), "Shift+F5",
                                   "Run with simulated pins and windows")
        self.act_stop = self.action("Stop", self.stop_program, "Ctrl+F5", "Stop the program")
        self.act_fix = self.action("Fix all", self.fix_all, "Ctrl+Shift+F",
                                   "Apply every automatic fix")
        self.act_designer = self.action("Window designer", self.open_designer, "Ctrl+D",
                                        "Design a desktop window with the mouse")
        self.act_web_designer = self.action("Web page designer",
                                            lambda: self.open_designer("WebUI"), "Ctrl+Shift+D",
                                            "Design a web page with the mouse")
        self.act_blocks = self.action("Blocks", self.open_blocks, "Ctrl+B",
                                      "Build a program by connecting blocks")
        self.act_ai = self.action("Ask AI...", self.ask_ai, None,
                                  "Explain the problems with the optional AI helper")
        self.act_docs = self.action("Documentation", self.open_docs, "F1")
        self.act_stop.setEnabled(False)

        menu = self.menuBar().addMenu("&File")
        for action in (self.act_new, self.act_open, self.act_save, self.act_save_as):
            menu.addAction(action)
        menu.addSeparator()
        menu.addAction(self.action("Quit", self.close, "Ctrl+Q"))
        menu = self.menuBar().addMenu("&Edit")
        menu.addAction(self.action("Undo", self.editor.undo, "Ctrl+Z"))
        menu.addAction(self.action("Redo", self.editor.redo, "Ctrl+Shift+Z"))
        menu.addSeparator()
        menu.addAction(self.act_fix)
        menu = self.menuBar().addMenu("&Run")
        for action in (self.act_run, self.act_sim, self.act_stop):
            menu.addAction(action)
        menu = self.menuBar().addMenu("&Tools")
        menu.addAction(self.act_blocks)
        menu.addAction(self.act_designer)
        menu.addAction(self.act_web_designer)
        menu.addAction(self.act_ai)
        menu = self.menuBar().addMenu("&Help")
        menu.addAction(self.act_docs)
        menu.addAction(self.action("About", self.about))

        bar = self.addToolBar("Main")
        bar.setMovable(False)
        bar.setToolButtonStyle(Qt.ToolButtonTextOnly)
        for action in (self.act_new, self.act_open, self.act_save, None, self.act_run,
                       self.act_sim, self.act_stop, None, self.act_fix, self.act_blocks,
                       self.act_designer, self.act_web_designer, self.act_ai):
            if action is None:
                bar.addSeparator()
            else:
                bar.addAction(action)

    def build_bottom(self):
        self.output = QPlainTextEdit()
        self.output.setReadOnly(True)
        self.output.setFont(self.editor.font())
        self.output.setMaximumBlockCount(5000)
        self.input_line = QLineEdit()
        self.input_line.setPlaceholderText("Type an answer for Ask here and press Enter")
        self.input_line.returnPressed.connect(self.send_input)
        self.input_line.setEnabled(False)
        output_page = QWidget()
        layout = QVBoxLayout(output_page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.output)
        layout.addWidget(self.input_line)

        self.problems = QListWidget()
        self.problems.itemDoubleClicked.connect(self.jump_to_problem)
        self.problems.currentRowChanged.connect(self.problem_selected)
        self.fix_button = QPushButton("Apply fix")
        self.fix_button.clicked.connect(self.fix_selected)
        self.fix_button.setEnabled(False)
        fix_all_button = QPushButton("Fix all")
        fix_all_button.clicked.connect(self.fix_all)
        self.hint_label = QLabel()
        self.hint_label.setWordWrap(True)
        self.hint_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        row = QHBoxLayout()
        row.addWidget(self.hint_label, 1)
        row.addWidget(self.fix_button)
        row.addWidget(fix_all_button)
        problems_page = QWidget()
        layout = QVBoxLayout(problems_page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.problems)
        layout.addLayout(row)

        self.ai_view = QPlainTextEdit()
        self.ai_view.setReadOnly(True)
        self.ai_view.setPlaceholderText(
            "The optional AI helper explains problems in plain words.\n"
            "Use Tools > Ask AI. Your program is sent to the Claude API only when you do.")

        self.tabs = QTabWidget()
        self.tabs.addTab(problems_page, "Problems")
        self.tabs.addTab(output_page, "Output")
        self.tabs.addTab(self.ai_view, "AI helper")
        dock = QDockWidget("Results", self)
        dock.setObjectName("results")
        dock.setWidget(self.tabs)
        dock.setFeatures(QDockWidget.DockWidgetMovable)
        self.addDockWidget(Qt.BottomDockWidgetArea, dock)

    def build_library_dock(self):
        """The Help panel: the whole language and every library, searchable."""
        self.help_search = QLineEdit()
        self.help_search.setPlaceholderText("Search the help (for example: button, loop, wait)")
        self.help_search.setClearButtonEnabled(True)
        self.help_search.textChanged.connect(self.filter_help)
        tree = QTreeWidget()
        tree.setHeaderHidden(True)
        for title, entries in sections():
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
        tree.itemDoubleClicked.connect(
            lambda item, _column: self.insert_line(item.data(0, Qt.UserRole)))
        self.help_tree = tree
        self.help_text = QPlainTextEdit()
        self.help_text.setReadOnly(True)
        self.help_text.setFont(self.editor.font())
        self.help_text.setMaximumHeight(130)
        self.help_text.setPlaceholderText(
            "Select an entry to see what it does.\nDouble-click to insert it into the program.")
        insert_button = QPushButton("Insert into program")
        insert_button.clicked.connect(lambda: self.insert_line(
            tree.currentItem().data(0, Qt.UserRole) if tree.currentItem() else None))
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.addWidget(self.help_search)
        layout.addWidget(tree, 1)
        layout.addWidget(self.help_text)
        layout.addWidget(insert_button)
        dock = QDockWidget("Help", self)
        dock.setObjectName("help")
        dock.setWidget(page)
        dock.setFeatures(QDockWidget.DockWidgetMovable | QDockWidget.DockWidgetClosable)
        self.addDockWidget(Qt.RightDockWidgetArea, dock)
        self.menuBar().addMenu("&View").addAction(dock.toggleViewAction())
        self.resizeDocks([dock], [380], Qt.Horizontal)

    def show_help(self, item, _previous=None):
        if item is None or item.childCount():
            self.help_text.setPlainText("")
            return
        insert = item.data(0, Qt.UserRole) or ""
        explanation = item.data(0, Qt.UserRole + 1) or ""
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

    # ------------------------------------------------------------------
    # Files
    # ------------------------------------------------------------------
    def update_title(self, *_):
        name = os.path.basename(self.path) if self.path else "untitled" + FILE_EXTENSION
        star = "*" if self.editor.document().isModified() else ""
        self.setWindowTitle(f"{name}{star} - JadivCode IDE")

    def update_status(self):
        cursor = self.editor.textCursor()
        self.position_label.setText(
            f"Line {cursor.blockNumber() + 1}, column {cursor.positionInBlock() + 1}")

    def confirm_discard(self):
        if not self.editor.document().isModified():
            return True
        answer = QMessageBox.question(
            self, "Unsaved changes", "Save the changes to this program first?",
            QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel, QMessageBox.Save)
        if answer == QMessageBox.Save:
            return self.save()
        return answer == QMessageBox.Discard

    def new_file(self):
        if not self.confirm_discard():
            return
        self.path = None
        self.editor.setPlainText(STARTER)
        self.editor.document().setModified(False)
        self.update_title()

    def open_file(self):
        if not self.confirm_discard():
            return
        start = os.path.dirname(self.path) if self.path else os.path.expanduser("~")
        path, _ = QFileDialog.getOpenFileName(self, "Open a program", start, FILTER)
        if path:
            self.load(path)

    def load(self, path):
        try:
            with open(path, encoding="utf-8") as handle:
                text = handle.read()
        except (OSError, UnicodeDecodeError) as exc:
            QMessageBox.warning(self, "Cannot open", f"{path}\n\n{exc}")
            return False
        self.path = os.path.abspath(path)
        self.editor.setPlainText(text)
        self.editor.document().setModified(False)
        self.update_title()
        return True

    def save(self):
        if not self.path:
            return self.save_as()
        return self.write(self.path)

    def save_as(self):
        start = self.path or os.path.join(os.path.expanduser("~"), "program" + FILE_EXTENSION)
        path, _ = QFileDialog.getSaveFileName(self, "Save the program", start, FILTER)
        if not path:
            return False
        if not os.path.splitext(path)[1]:
            path += FILE_EXTENSION
        if self.write(path):
            self.path = os.path.abspath(path)
            self.update_title()
            return True
        return False

    def write(self, path):
        text = self.editor.toPlainText()
        if text and not text.endswith("\n"):
            text += "\n"
        try:
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(text)
        except OSError as exc:
            QMessageBox.warning(self, "Cannot save", f"{path}\n\n{exc}")
            return False
        self.editor.document().setModified(False)
        self.statusBar().showMessage(f"Saved {path}", 3000)
        return True

    def closeEvent(self, event):
        if not self.confirm_discard():
            event.ignore()
            return
        self.stop_program()
        if self.temp_file:
            try:
                os.remove(self.temp_file)
            except OSError:
                pass
        event.accept()

    # ------------------------------------------------------------------
    # Checking
    # ------------------------------------------------------------------
    def schedule_check(self):
        self.check_timer.start()

    def run_check(self):
        try:
            self.diagnostics = check_source(self.editor.toPlainText())
        except Exception as exc:  # noqa: BLE001 - never let the checker break typing
            self.diagnostics = []
            self.statusBar().showMessage(f"Checker problem: {exc}", 5000)
        self.editor.set_diagnostics(self.diagnostics)
        selected = self.problems.currentRow()
        self.problems.clear()
        for diag in self.diagnostics:
            item = QListWidgetItem(f"Line {diag.line}   {diag.code}   {diag.message}"
                                   + ("   [fix available]" if diag.fix else ""))
            item.setForeground(QColor(SEVERITY_COLORS[diag.severity]))
            item.setToolTip(diag.hint or diag.message)
            self.problems.addItem(item)
        if 0 <= selected < self.problems.count():
            self.problems.setCurrentRow(selected)
        errors = sum(d.severity == "error" for d in self.diagnostics)
        warnings = sum(d.severity == "warning" for d in self.diagnostics)
        self.problem_label.setText(f"{errors} error(s), {warnings} warning(s)")
        self.tabs.setTabText(0, f"Problems ({len(self.diagnostics)})")
        self.act_fix.setEnabled(any(d.fix for d in self.diagnostics))
        self.problem_selected(self.problems.currentRow())

    def problem_selected(self, row):
        diag = self.diagnostics[row] if 0 <= row < len(self.diagnostics) else None
        self.fix_button.setEnabled(bool(diag and diag.fix))
        self.fix_button.setText(diag.fix["title"] if diag and diag.fix else "Apply fix")
        self.hint_label.setText(diag.hint or "" if diag else "")

    def jump_to_problem(self, item):
        row = self.problems.row(item)
        if 0 <= row < len(self.diagnostics):
            self.editor.go_to_line(self.diagnostics[row].line)

    def apply(self, diagnostics):
        fixed, count = apply_fixes(self.editor.toPlainText(), diagnostics)
        if count:
            self.editor.replace_all(fixed)
            self.run_check()
            self.statusBar().showMessage(f"Applied {count} fix(es). Undo with Ctrl+Z.", 4000)

    def fix_selected(self):
        row = self.problems.currentRow()
        if 0 <= row < len(self.diagnostics):
            self.apply([self.diagnostics[row]])

    def fix_all(self):
        self.apply(self.diagnostics)

    # ------------------------------------------------------------------
    # Running
    # ------------------------------------------------------------------
    def append_output(self, text, color=None):
        cursor = self.output.textCursor()
        cursor.movePosition(QTextCursor.End)
        fmt = QTextCharFormat()
        if color:
            fmt.setForeground(QColor(color))
        cursor.insertText(text, fmt)
        self.output.setTextCursor(cursor)
        self.output.ensureCursorVisible()

    def program_path(self):
        """The file to run: the saved file, or a temporary copy."""
        if self.path and not self.editor.document().isModified():
            return self.path
        if self.path:
            return self.path if self.save() else None
        if self.temp_file is None:
            handle, self.temp_file = tempfile.mkstemp(suffix=FILE_EXTENSION, prefix="untitled-")
            os.close(handle)
        with open(self.temp_file, "w", encoding="utf-8") as handle:
            handle.write(self.editor.toPlainText())
        return self.temp_file

    def run_program(self, simulate=False):
        if self.process is not None:
            return
        path = self.program_path()
        if path is None:
            return
        self.output.clear()
        self.tabs.setCurrentIndex(1)
        self.append_output(f"Running {os.path.basename(path)}"
                           + (" (simulated)" if simulate else "") + "\n", "#8a90a2")
        process = QProcess(self)
        env = QProcessEnvironment()
        for key, value in run_environment(simulate).items():
            env.insert(key, value)
        process.setProcessEnvironment(env)
        process.setWorkingDirectory(os.path.dirname(path))
        process.readyReadStandardOutput.connect(
            lambda: self.append_output(bytes(process.readAllStandardOutput()).decode(
                "utf-8", "replace")))
        process.readyReadStandardError.connect(
            lambda: self.append_output(bytes(process.readAllStandardError()).decode(
                "utf-8", "replace"), SEVERITY_COLORS["error"]))
        process.finished.connect(self.program_finished)
        process.errorOccurred.connect(self.program_error)
        self.process = process
        self.set_running(True)
        process.start(sys.executable, ["-u", "-m", "jadivcode", "run", path])

    def set_running(self, running):
        self.act_run.setEnabled(not running)
        self.act_sim.setEnabled(not running)
        self.act_stop.setEnabled(running)
        self.input_line.setEnabled(running)
        if running:
            self.input_line.setFocus()

    def program_error(self, _error):
        if self.process is not None and self.process.state() == QProcess.NotRunning:
            self.append_output("The program could not be started.\n", SEVERITY_COLORS["error"])
            self.process = None
            self.set_running(False)

    def program_finished(self, code, _status):
        if self.process is None:
            return
        self.append_output(f"\nFinished (code {code}).\n", "#8a90a2")
        self.process.deleteLater()
        self.process = None
        self.set_running(False)

    def stop_program(self):
        process = self.process
        if process is None:
            return
        process.terminate()
        if not process.waitForFinished(1500):
            process.kill()
            process.waitForFinished(1500)

    def send_input(self):
        if self.process is None:
            return
        text = self.input_line.text()
        self.input_line.clear()
        self.append_output(text + "\n", "#3b9eff")
        self.process.write((text + "\n").encode("utf-8"))

    # ------------------------------------------------------------------
    # Tools
    # ------------------------------------------------------------------
    def insert_line(self, text):
        if not text:
            return
        cursor = self.editor.textCursor()
        cursor.beginEditBlock()
        if cursor.block().text().strip():
            cursor.movePosition(QTextCursor.EndOfBlock)
            cursor.insertText("\n")
        cursor.insertText(text)
        cursor.endEditBlock()
        self.editor.setTextCursor(cursor)
        self.editor.setFocus()

    def open_designer(self, target="GUI"):
        dialog = DesignerDialog(self, self.editor.toPlainText(), target)
        if dialog.exec_() == DesignerDialog.Accepted and dialog.code:
            self.insert_line(dialog.code.rstrip("\n"))

    def open_blocks(self):
        from .blocks import BlocksDialog
        dialog = BlocksDialog(self, self.editor.toPlainText())
        if dialog.exec_() == BlocksDialog.Accepted and dialog.code:
            if dialog.replace:
                self.editor.replace_all(dialog.code)
            else:
                self.insert_line(dialog.code.rstrip("\n"))

    def ask_ai(self):
        if self.ai_worker is not None:
            return
        answer = QMessageBox.question(
            self, "Ask the AI helper",
            "This sends the whole program to the Claude API (Anthropic) using your own "
            "API key. Remove passwords and other secrets first.\n\nSend it now?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if answer != QMessageBox.Yes:
            return
        self.tabs.setCurrentIndex(2)
        self.ai_view.setPlainText("Asking the AI helper...")
        self.act_ai.setEnabled(False)
        self.ai_worker = AIWorker(self.editor.toPlainText(), self)
        self.ai_worker.finished_text.connect(self.ai_done)
        self.ai_worker.start()

    def ai_done(self, text, ok):
        self.ai_view.setPlainText(text if ok else "The AI helper is not available.\n\n" + text)
        self.act_ai.setEnabled(True)
        self.ai_worker.wait()
        self.ai_worker = None

    def open_docs(self):
        from PyQt5.QtCore import QUrl
        from PyQt5.QtGui import QDesktopServices
        QDesktopServices.openUrl(QUrl(DOCS_URL))

    def about(self):
        QMessageBox.about(
            self, "About JadivCode IDE",
            f"JadivCode IDE {__version__}\nJadivCode {CORE_VERSION}\n\n"
            f"Documentation: {DOCS_URL}\nLicensed under the MIT License.")


def main(argv=None):
    argv = list(sys.argv if argv is None else argv)
    app = QApplication(argv)
    app.setApplicationName("JadivCode IDE")
    icon = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "assets", "jadivcode-ide.svg")
    if os.path.exists(icon):
        app.setWindowIcon(QIcon(icon))
    path = next((a for a in argv[1:] if not a.startswith("-")), None)
    window = MainWindow(path)
    window.show()
    return app.exec_()
