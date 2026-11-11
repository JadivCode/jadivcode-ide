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
    def design(self, target="GUI"):
        design = model.new_design(target)
        design["title"] = 'My "best" app'
        model.add_item(design, "Text", 22, 18)
        button = model.add_item(design, "Button", 20, 60)
        button["text"] = "Press {me}"
        model.add_item(design, "Slider", 20, 110)
        return design

    def test_names_and_snapping(self):
        design = self.design()
        self.assertEqual([i["id"] for i in design["items"]], ["Text1", "Button1", "Slider1"])
        self.assertEqual((design["items"][0]["x"], design["items"][0]["y"]), (20, 20))
        self.assertEqual(model.add_item(design, "Button")["id"], "Button2")
        self.assertFalse(model.valid_name(design, "button1"))
        self.assertFalse(model.valid_name(design, "1st"))
        self.assertTrue(model.valid_name(design, "Go"))

    def test_generated_code_is_valid(self):
        for target in ("GUI", "WebUI"):
            code = model.generate_code(self.design(target))
            self.assertTrue(code.startswith(f"Import {target}\n"))
            self.assertEqual([d.code for d in check_source(code) if d.severity == "error"], [])
        self.assertNotIn("Import GUI", model.generate_code(self.design(), "import gui\n"))
        self.assertIn('Define Button1 = GUI Button "Press {{me}}" at 20, 60 size 110, 32',
                      model.generate_code(self.design()))
        self.assertIn('Define Button1 = WebUI Button "Press {{me}}"\n',
                      model.generate_code(self.design("WebUI")))

    def test_round_trip(self):
        design = self.design()
        parsed = model.parse_code(model.generate_code(design))
        self.assertEqual(parsed["title"], "My 'best' app")
        self.assertEqual((parsed["width"], parsed["height"]), (400, 300))
        self.assertEqual(parsed["items"], design["items"])
        web = model.parse_code(model.generate_code(self.design("WebUI")))
        self.assertEqual(web["target"], "WebUI")
        self.assertEqual([i["id"] for i in web["items"]], ["Text1", "Button1", "Slider1"])
        old = model.parse_code('WindowWrite Button "X = 10, Y = 20" "B01" = "Go"\n')
        self.assertEqual((old["items"][0]["id"], old["items"][0]["x"], old["items"][0]["text"]),
                         ("B01", 10, "Go"))

    def test_generated_code_runs(self):
        from jadivcode.interpreter import Runtime
        os.environ["JADIVCODE_GUI"] = "headless"
        out = []
        code = model.generate_code(self.design()) + 'GUI Press "Button1"\nWait 10ms\n'
        runtime = Runtime(out=out.append, err=out.append)
        runtime.run_source(code)
        self.assertIn("Button1 was pressed", out)
        window = runtime.libs["gui"].surfaces[1]
        self.assertEqual(window.widgets["button1"].text, "Press {me}")
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
        self.assertIn('Define Input1 = GUI Input "typed" at 20, 60 size 180, 28', dialog.code)
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


class BlocksModelTest(unittest.TestCase):
    def graph(self):
        from jadivcode_ide import blocks_model as blocks
        graph = blocks.new_graph()
        start = graph["blocks"][0]["id"]
        define = blocks.add_block(graph, "define", 40, 150)
        repeat = blocks.add_block(graph, "repeat", 40, 270)
        change = blocks.add_block(graph, "set", 300, 390)
        check = blocks.add_block(graph, "if", 40, 510)
        yes = blocks.add_block(graph, "write", 40, 630)
        no = blocks.add_block(graph, "write", 300, 630)
        event = blocks.add_block(graph, "event", 600, 30)
        shout = blocks.add_block(graph, "write", 600, 150)
        blocks.add_block(graph, "wait", 900, 900)
        yes["params"]["text"] = "big {Count}"
        no["params"]["text"] = "small"
        check["params"]["cond"] = "Count >= 3"
        event["params"]["name"] = "Count"
        self.assertTrue(blocks.link(graph, start, "next", define["id"]))
        blocks.link(graph, define["id"], "next", repeat["id"])
        blocks.link(graph, repeat["id"], "inside", change["id"])
        blocks.link(graph, repeat["id"], "next", check["id"])
        blocks.link(graph, check["id"], "yes", yes["id"])
        blocks.link(graph, check["id"], "no", no["id"])
        blocks.link(graph, event["id"], "next", shout["id"])
        self.assertFalse(blocks.link(graph, define["id"], "next", start))
        self.assertFalse(blocks.link(graph, define["id"], "yes", repeat["id"]))
        return blocks, graph

    def test_generated_program(self):
        blocks, graph = self.graph()
        code, loose = blocks.generate_code(graph)
        self.assertEqual(loose, 1)
        expected = ["Define Count = 0", "Repeat 3 times", "    Set Count = Count + 1", "End",
                    "If Count >= 3", "    Write = big {Count}", "Else", "    Write = small",
                    "End", "", "On Count", "    Write = Hello, world!", "End"]
        self.assertEqual(code.splitlines()[:len(expected)], expected)
        from jadivcode.interpreter import Runtime
        out = []
        Runtime(out=out.append, err=out.append).run_source(
            code.replace("On Count\n    Write = Hello, world!\nEnd\n", ""))
        self.assertEqual(out, ["big 3"])

    def test_round_trip_and_cycles(self):
        blocks, graph = self.graph()
        code, _ = blocks.generate_code(graph)
        again = blocks.parse_code(code)
        self.assertEqual(blocks.generate_code(again)[0], code)
        ids = {b["type"]: b["id"] for b in graph["blocks"]}
        blocks.link(graph, ids["set"], "next", ids["repeat"])
        self.assertIn("goes back to an earlier block", blocks.generate_code(graph)[0])
        self.assertIsNone(blocks.parse_code("Write = hi\n"))
        self.assertIsNone(blocks.parse_code(blocks.MARKER + "not json"))


class NewToolsWindowTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from PyQt5.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    def test_help_panel_search(self):
        from jadivcode_ide.app import MainWindow
        window = MainWindow()
        tree = window.help_tree
        total = sum(tree.topLevelItem(i).childCount() for i in range(tree.topLevelItemCount()))
        self.assertGreater(total, 150)
        window.help_search.setText("slider")
        shown = [tree.topLevelItem(i).text(0) for i in range(tree.topLevelItemCount())
                 if not tree.topLevelItem(i).isHidden()]
        self.assertEqual(shown, ["Library: GUI", "Library: WebUI"])
        window.editor.document().setModified(False)
        window.close()

    def test_web_designer_and_blocks_dialog(self):
        from jadivcode_ide.blocks import BlocksDialog
        from jadivcode_ide.designer import DesignerDialog
        dialog = DesignerDialog(None, "", "WebUI")
        dialog.add("Text")
        dialog.add("Button")
        dialog.accept()
        self.assertEqual(dialog.code.splitlines()[:5], [
            "Import WebUI", "", 'WebUI Title = "My app"', "",
            'Define Text1 = WebUI Text "Text"'])
        self.assertIn("On Button1", dialog.code)
        self.assertEqual([d.code for d in check_source(dialog.code) if d.severity == "error"], [])

        blocks = BlocksDialog(None, "")
        blocks.items[1].setSelected(True)
        blocks.add("write")
        blocks.add("wait")
        blocks.accept()
        self.assertTrue(blocks.replace)
        self.assertEqual(blocks.code.splitlines()[:2], ["Write = Hello, world!", "Wait 1s"])
        reopened = BlocksDialog(None, blocks.code)
        self.assertEqual(len(reopened.items), 3)
