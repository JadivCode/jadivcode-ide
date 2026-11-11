"""IDE tests. Run with: QT_QPA_PLATFORM=offscreen python3 -m unittest discover -s tests"""

import os
import sys
import tempfile
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from jadivcode_ide import designer_model as model  # noqa: E402
from jadivcode_ide.core import check_source  # noqa: E402


class DesignerModelTest(unittest.TestCase):
    def design(self):
        design = model.new_design()
        design["title"] = 'My "best" app'
        model.add_item(design, "Text", 22, 18)
        button = model.add_item(design, "Button", 20, 60)
        button["text"] = "Press {me}"
        model.add_item(design, "Slider", 20, 110)
        return design

    def test_ids_and_snapping(self):
        design = self.design()
        self.assertEqual([i["id"] for i in design["items"]], ["T01", "B01", "S01"])
        self.assertEqual((design["items"][0]["x"], design["items"][0]["y"]), (20, 20))
        self.assertEqual(model.add_item(design, "Button")["id"], "B02")

    def test_generated_code_is_valid(self):
        code = model.generate_code(self.design())
        self.assertTrue(code.startswith("Import GUI\n"))
        self.assertEqual([d.code for d in check_source(code) if d.severity == "error"], [])
        self.assertNotIn("Import GUI", model.generate_code(self.design(), "import gui\n"))

    def test_round_trip(self):
        design = self.design()
        parsed = model.parse_code(model.generate_code(design))
        self.assertEqual(parsed["title"], "My 'best' app")
        self.assertEqual((parsed["width"], parsed["height"]), (400, 300))
        self.assertEqual(parsed["items"], design["items"])

    def test_generated_code_runs(self):
        from jadivcode.interpreter import Runtime
        os.environ["JADIVCODE_GUI"] = "headless"
        out = []
        code = model.generate_code(self.design()) + 'GUI Press "B01" on Window #1\nWait 10ms\n'
        runtime = Runtime(out=out.append, err=out.append)
        runtime.run_source(code)
        self.assertIn("B01 was pressed", out)
        window = runtime.libs["gui"].surfaces[1]
        self.assertEqual(window.widgets["b01"].text, "Press {me}")
        self.assertEqual(window.props["title"], "My 'best' app")


class WindowTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from PyQt5.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    def test_check_fix_and_designer(self):
        from jadivcode_ide.app import MainWindow
        from jadivcode_ide.designer import DesignerDialog
        window = MainWindow()
        window.editor.setPlainText("Import Mth\nWrte = hi\n")
        window.run_check()
        self.assertEqual(window.problems.count(), 2)
        self.assertEqual(len(window.editor.extraSelections()), 3)
        window.fix_all()
        self.assertEqual(window.editor.toPlainText(), "Import Math\nWrite = hi\n")
        self.assertEqual(window.problems.count(), 0)

        dialog = DesignerDialog(window, window.editor.toPlainText())
        dialog.add("Button")
        dialog.add("Input")
        dialog.text_edit.setText("typed")
        dialog.item_changed()
        dialog.accept()
        self.assertIn('WindowWrite Input "X = 20, Y = 60, W = 180, H = 28" "I01" = "typed"',
                      dialog.code)
        window.insert_line(dialog.code.rstrip("\n"))
        window.run_check()
        self.assertEqual([d for d in window.diagnostics if d.severity == "error"], [])
        window.editor.document().setModified(False)
        window.close()

    def test_run_program(self):
        from PyQt5.QtCore import QEventLoop, QTimer
        from jadivcode_ide.app import MainWindow
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "t.jdv")
            with open(path, "w", encoding="utf-8") as handle:
                handle.write("Ask Name = Who?\nWrite = Hello {Name}\n")
            window = MainWindow(path)
            window.run_program(True)
            loop = QEventLoop()
            QTimer.singleShot(700, lambda: (window.input_line.setText("Jan"),
                                            window.send_input()))
            window.process.finished.connect(lambda *_: QTimer.singleShot(100, loop.quit))
            QTimer.singleShot(15000, loop.quit)
            loop.exec_()
            text = window.output.toPlainText()
            self.assertIn("Hello Jan", text)
            self.assertIn("Finished (code 0)", text)
            window.close()


if __name__ == "__main__":
    unittest.main()
