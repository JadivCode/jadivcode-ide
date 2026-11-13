"""IDE tests. Run with: QT_QPA_PLATFORM=offscreen python3 -m unittest discover -s tests"""

import os
import sys
import tempfile
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
# Tests must not contact the update server or touch the user's settings.
os.environ["JADIVCODE_NO_UPDATE_CHECK"] = "1"
os.environ["XDG_CONFIG_HOME"] = tempfile.mkdtemp(prefix="jadivcode-ide-test-")
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
        self.assertEqual([{k: v for k, v in item.items() if k != "orig"}
                          for item in parsed["items"]], design["items"])
        self.assertEqual([item["orig"] for item in parsed["items"]],
                         ["Text1", "Button1", "Slider1"])
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


PROGRAM = """// Count and report
Import Math

Define Count = 0
Repeat 3 times
    Set Count = Count + 1
End

If Count >= 3
    Write = big {Count}
Else If Count = 2
    Write = two
Else
    Write = small
End

For I = 1 to 2
    Write = round {I}
End

On Count "Write = one line" Else loop
On Count
    Write = used
End
Forever
    Break
End
Write = done
"""


class BlocksModelTest(unittest.TestCase):
    def setUp(self):
        from jadivcode_ide import blocks_model
        self.blocks = blocks_model

    def test_text_to_blocks_and_back_is_exact(self):
        graph = self.blocks.from_code(PROGRAM)
        text, loose = self.blocks.program_text(graph)
        self.assertEqual(text, PROGRAM)
        self.assertEqual(loose, 0)
        kinds = [b["type"] for b in graph["blocks"]]
        for kind in ("start", "line", "define", "repeat", "set", "if", "write", "group",
                     "event", "forever"):
            self.assertIn(kind, kinds)
        self.assertEqual(kinds.count("if"), 2)      # Else If is a second If block
        self.assertEqual(kinds.count("event"), 1)   # the one-line On stays a line

    def test_layout_is_kept_while_text_is_unchanged(self):
        graph = self.blocks.from_code(PROGRAM)
        graph["blocks"][3]["x"] = 777
        stored, _ = self.blocks.generate_code(graph)
        again = self.blocks.parse_code(stored)
        self.assertEqual(again["blocks"][3]["x"], 777)
        # Editing the text by hand wins over the stored layout.
        edited = stored.replace("Write = done", "Write = finished")
        fresh = self.blocks.parse_code(edited)
        self.assertNotEqual(fresh["blocks"][3]["x"], 777)
        self.assertIn("Write = finished", self.blocks.program_text(fresh)[0])

    def test_editing_blocks_changes_the_text(self):
        blocks = self.blocks
        graph = blocks.from_code("Define A = 1\nWrite = {A}\n")
        define = [b for b in graph["blocks"] if b["type"] == "define"][0]
        write = [b for b in graph["blocks"] if b["type"] == "write"][0]
        define["params"]["value"] = "5"
        extra = blocks.append_code(graph, "If A > 3\n    Write = big\nEnd", define["id"])
        blocks.link(graph, extra[0], "next", write["id"])
        self.assertEqual(blocks.program_text(graph)[0],
                         "Define A = 5\nIf A > 3\n    Write = big\nEnd\nWrite = {A}\n")
        from jadivcode.interpreter import Runtime
        out = []
        Runtime(out=out.append, err=out.append).run_source(blocks.program_text(graph)[0])
        self.assertEqual(out, ["big", "5"])

    def test_links_loops_and_old_format(self):
        blocks = self.blocks
        graph = blocks.from_code("Define A = 1\nWrite = a\n")
        start, define, write = [b["id"] for b in graph["blocks"]]
        self.assertFalse(blocks.link(graph, define, "next", start))
        self.assertFalse(blocks.link(graph, define, "yes", write))
        blocks.link(graph, write, "next", define)
        self.assertIn("goes back to an earlier block", blocks.program_text(graph)[0])
        old = ('// blocks: {"blocks":[{"id":1,"type":"start","x":0,"y":0,"params":{}},'
               '{"id":2,"type":"event","x":300,"y":0,"params":{"name":"Go"}},'
               '{"id":3,"type":"write","x":300,"y":100,"params":{"text":"hi"}}],'
               '"links":[{"from":2,"port":"next","to":3}],"next_id":4}')
        graph = blocks.parse_code("On Go\n    Write = hi\nEnd\n" + old + "\n")
        self.assertEqual(blocks.program_text(graph)[0], "On Go\n    Write = hi\nEnd\n")
        self.assertEqual(blocks.find(graph, 2)["x"], 300)
        self.assertEqual(blocks.program_text(blocks.parse_code(blocks.MARKER + "not json"))[0], "")


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
        self.assertEqual(shown, ["Recipes: complete examples", "Library: GUI",
                                 "Library: WebUI"])
        window.editor.document().setModified(False)
        window.close()

    def test_web_designer(self):
        from jadivcode_ide.designer import DesignerDialog
        dialog = DesignerDialog(None, "", "WebUI")
        dialog.add("Text")
        dialog.add("Button")
        dialog.accept()
        self.assertIsNone(dialog.merged)
        self.assertEqual(dialog.code.splitlines()[:5], [
            "Import WebUI", "", 'WebUI Title = "My app"', "",
            'Define Text1 = WebUI Text "Text"'])
        self.assertIn("On Button1", dialog.code)
        self.assertEqual([d.code for d in check_source(dialog.code) if d.severity == "error"], [])

    def test_designer_updates_the_program_in_place(self):
        from jadivcode_ide.app import MainWindow
        from jadivcode_ide.designer import DesignerDialog
        source = ('// my app\nImport GUI\n\nGUI Title = Counter\nGUI Size = 260x150\n\n'
                  'Define Message = GUI Text "Count: 0" at 20, 20 size 220, 30\n'
                  'Define More = GUI Button "Add one" at 20, 70 size 100, 36\n'
                  'Define Reset = GUI Button "Reset" at 140, 70 size 100, 36\n\n'
                  'Define Count = 0\n\nOn More\n    Set Count = Count + 1\n'
                  '    Set Message = Count: {Count}\nEnd\n\nOn Reset\n    Set Count = 0\nEnd\n')
        window = MainWindow()
        window.editor.setPlainText(source)
        dialog = DesignerDialog(window, window.editor.toPlainText(), "GUI")
        self.assertEqual([i["id"] for i in dialog.design["items"]], ["Message", "More", "Reset"])
        dialog.design["items"][1]["id"] = "Plus"
        dialog.design["items"][1]["x"] = 40
        del dialog.design["items"][2]
        dialog.title_edit.setText("Clicks")
        dialog.accept()
        window.editor.replace_all(dialog.merged)
        text = window.editor.toPlainText()
        self.assertIn('GUI Title = "Clicks"', text)
        self.assertIn('Define Plus = GUI Button "Add one" at 40, 70 size 100, 36', text)
        self.assertIn("On Plus\n    Set Count = Count + 1", text)
        self.assertNotIn("Reset", text)
        self.assertNotIn("More", text)
        self.assertTrue(text.startswith("// my app\nImport GUI\n"))
        self.assertEqual(text.count("Define Message"), 1)
        window.run_check()
        self.assertEqual([d for d in window.diagnostics if d.severity == "error"], [])
        # Opening the designer again reads the updated program.
        again = DesignerDialog(window, text, "GUI")
        self.assertEqual([i["id"] for i in again.design["items"]], ["Message", "Plus"])
        window.editor.document().setModified(False)
        window.close()

    def test_blocks_dialog_is_two_way(self):
        from jadivcode_ide.blocks import BlocksDialog
        dialog = BlocksDialog(None, PROGRAM)
        self.assertEqual(len(dialog.items), len(dialog.graph["blocks"]))
        # Change a block, add one from the palette and one from the help.
        write = [b for b in dialog.graph["blocks"] if b["params"].get("text") == "done"][0]
        dialog.items[write["id"]].setSelected(True)
        dialog.fields["text"].setText("finished")
        dialog.param_changed(dialog.items[write["id"]], "text", "finished")
        dialog.add("wait")
        dialog.help_search.setText("for each")
        tree = dialog.help_tree
        entry = None
        for index in range(tree.topLevelItemCount()):
            top = tree.topLevelItem(index)
            for row in range(top.childCount()):
                if top.child(row).text(0) == "For each" and not top.child(row).isHidden():
                    entry = top.child(row)
        tree.setCurrentItem(entry)
        self.assertTrue(dialog.help_add.isEnabled())
        dialog.add_help_example()
        dialog.accept()
        text = "\n".join(l for l in dialog.code.splitlines() if not l.startswith("// blocks:"))
        self.assertTrue(text.startswith("// Count and report\nImport Math\n"))
        self.assertTrue(text.rstrip().endswith(
            "Write = finished\nWait 1s\nFor each Item in Items\n    Write = {Item}\nEnd"))
        # The text made by the blocks opens as the same blocks again.
        again = BlocksDialog(None, dialog.code)
        self.assertEqual(len(again.items), len(dialog.items))
        self.assertEqual(again.graph["blocks"], dialog.graph["blocks"])

    def test_blocks_help_has_recipes_for_windows(self):
        from jadivcode_ide.blocks import BlocksDialog
        dialog = BlocksDialog(None, "")
        tree = dialog.help_tree
        titles = [tree.topLevelItem(i).text(0) for i in range(tree.topLevelItemCount())]
        self.assertEqual(titles[:2], ["Using blocks", "Recipes: complete examples"])
        for name in ("Library: GUI", "Library: WebUI", "Library: GPIO", "Library: Web"):
            self.assertIn(name, titles)
        recipes = tree.topLevelItem(1)
        entry = [recipes.child(i) for i in range(recipes.childCount())
                 if recipes.child(i).text(0) == "A window with a button"][0]
        tree.setCurrentItem(entry)
        dialog.add_help_example()
        dialog.accept()
        text = "\n".join(l for l in dialog.code.splitlines() if not l.startswith("// blocks:"))
        self.assertIn('Define Go = GUI Button "Press me" at 20, 60', text)
        self.assertIn("On Go\n    Set Message = Pressed\nEnd", text)
        self.assertEqual([d.code for d in check_source(text) if d.severity == "error"], [])
        kinds = [b["type"] for b in dialog.graph["blocks"]]
        self.assertIn("event", kinds)
        self.assertEqual(kinds.count("define"), 2)

    def test_blocks_from_the_main_window(self):
        from jadivcode_ide.app import MainWindow
        from jadivcode_ide import blocks_model
        window = MainWindow()
        window.editor.setPlainText("Define A = 1\nIf A = 1\n    Write = one\nEnd\n")
        graph = blocks_model.parse_code(window.editor.toPlainText())
        self.assertEqual([b["type"] for b in graph["blocks"]], ["start", "define", "if", "write"])
        window.editor.document().setModified(False)
        window.close()


class UpdaterTest(unittest.TestCase):
    def setUp(self):
        from jadivcode_ide import updater
        self.updater = updater

    def fetch(self, versions):
        def fake(url):
            for key, version in versions.items():
                if f"/{key}/main/" in url and url.endswith("__init__.py"):
                    return f'"""doc"""\n\n__version__ = "{version}"\n'
            return "#!/usr/bin/env bash\n# JadivCode installer\n"
        return fake

    def test_version_comparison(self):
        newer = self.updater.is_newer
        self.assertTrue(newer("0.2.0", "0.1.0"))
        self.assertTrue(newer("0.10.0", "0.9.9"))
        self.assertTrue(newer("1.0", "0.9.9"))
        self.assertFalse(newer("0.2.0", "0.2.0"))
        self.assertFalse(newer("0.2", "0.2.0"))
        self.assertFalse(newer("0.1.9", "0.2.0"))
        self.assertFalse(newer("garbage", "0.2.0"))
        self.assertEqual(self.updater.parse_version("1.2.3-beta4"), (1, 2, 3))

    def test_check_reports_what_is_newer_and_who_manages_it(self):
        with tempfile.TemporaryDirectory() as data:
            os.makedirs(os.path.join(data, "jadivcode"))
            previous = os.environ.get("XDG_DATA_HOME")
            os.environ["XDG_DATA_HOME"] = data
            try:
                results = self.updater.check(
                    {"JadivCode": ("0.1.0", os.path.join(data, "jadivcode")),
                     "JadivCode IDE": ("0.2.0", "/somewhere/else")},
                    self.fetch({"jadivcode": "0.3.0", "jadivcode-ide": "0.2.0"}))
            finally:
                if previous is None:
                    del os.environ["XDG_DATA_HOME"]
                else:
                    os.environ["XDG_DATA_HOME"] = previous
        core, ide = results
        self.assertEqual((core["newer"], core["managed"], core["latest"]), (True, True, "0.3.0"))
        self.assertEqual((ide["newer"], ide["managed"]), (False, False))
        self.assertEqual(self.updater.summary(results),
                         "Update available: JadivCode 0.3.0 (you have 0.1.0).")
        self.assertEqual(self.updater.summary([ide]), "JadivCode and the IDE are up to date.")

    def test_bad_downloads_are_refused(self):
        updater = self.updater
        with self.assertRaises(updater.UpdateError):
            updater.download("http://example.com/install.sh")
        with self.assertRaises(updater.UpdateError):
            updater.remote_version("JadivCode", lambda url: "no version here")
        with self.assertRaises(updater.UpdateError):
            updater.installer_script("JadivCode", lambda url: "<html>Not found</html>")
        self.assertTrue(updater.installer_script("JadivCode", self.fetch({})).startswith("#!"))


class UpdateWindowTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from PyQt5.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    def window(self):
        from PyQt5.QtWidgets import QMessageBox
        from jadivcode_ide import app as ide
        self.shown = []
        self.answer = QMessageBox.No
        self.patches = (QMessageBox.information, QMessageBox.question, QMessageBox.warning)
        QMessageBox.information = staticmethod(
            lambda parent, title, text, *a: self.shown.append(("info", text)))
        QMessageBox.warning = staticmethod(
            lambda parent, title, text, *a: self.shown.append(("warning", text)))

        def question(parent, title, text, *a):
            self.shown.append(("question", text))
            return self.answer
        QMessageBox.question = staticmethod(question)
        self.addCleanup(self.restore)
        window = ide.MainWindow()
        window.settings.clear()
        return window

    def restore(self):
        from PyQt5.QtWidgets import QMessageBox
        QMessageBox.information, QMessageBox.question, QMessageBox.warning = self.patches

    def result(self, managed=True):
        return [{"name": "JadivCode", "installed": "0.1.0", "latest": "0.3.0", "newer": True,
                 "managed": managed},
                {"name": "JadivCode IDE", "installed": "0.2.0", "latest": "0.2.0",
                 "newer": False, "managed": True}]

    def close(self, window):
        window.editor.document().setModified(False)
        window.close()

    def test_menu_and_setting(self):
        window = self.window()
        self.assertTrue(window.act_auto_update.isChecked())
        window.act_auto_update.setChecked(False)
        self.assertFalse(window.settings.value("check_updates_at_start", True, type=bool))
        window.act_auto_update.setChecked(True)
        self.close(window)

    def test_up_to_date_and_errors(self):
        window = self.window()
        window.update_silent = False
        window.updates_checked([self.result()[1]], "")
        self.assertEqual(self.shown, [("info", "JadivCode and the IDE are up to date.")])
        self.shown.clear()
        window.update_silent = True          # the check made at start stays quiet
        window.updates_checked([self.result()[1]], "")
        window.updates_checked([], "Cannot reach the update server")
        self.assertEqual(self.shown, [])
        window.update_silent = False
        window.updates_checked([], "Cannot reach the update server")
        self.assertEqual(self.shown[0][0], "warning")
        self.close(window)

    def test_declined_update_is_not_offered_again_at_start(self):
        window = self.window()
        window.update_silent = True
        window.updates_checked(self.result(), "")
        self.assertEqual(self.shown[0][0], "question")
        self.assertIn("JadivCode: 0.1.0  ->  0.3.0", self.shown[0][1])
        self.shown.clear()
        window.updates_checked(self.result(), "")      # same update, same start check
        self.assertEqual(self.shown, [])
        window.update_silent = False                    # asking by hand offers it again
        window.updates_checked(self.result(), "")
        self.assertEqual(self.shown[0][0], "question")
        self.close(window)

    def test_copy_not_from_the_installer_is_only_reported(self):
        window = self.window()
        window.update_silent = False
        window.updates_checked(self.result(managed=False), "")
        self.assertEqual(self.shown[0][0], "info")
        self.assertIn("was not installed with the JadivCode installer", self.shown[0][1])
        self.close(window)

    def test_installers_run_one_after_another(self):
        from PyQt5.QtCore import QEventLoop, QTimer
        window = self.window()
        folder = tempfile.mkdtemp()
        scripts = []
        for name in ("JadivCode", "JadivCode IDE"):
            path = os.path.join(folder, name.replace(" ", "-") + ".sh")
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(f"#!/bin/sh\necho installed {name}\n")
            scripts.append((name, path))
        loop = QEventLoop()
        window.updates_prepared(scripts, "")
        timer = QTimer()
        timer.timeout.connect(lambda: loop.quit() if self.shown else None)
        timer.start(50)
        QTimer.singleShot(15000, loop.quit)
        loop.exec_()
        text = window.output.toPlainText()
        self.assertIn("installed JadivCode\n", text)
        self.assertIn("installed JadivCode IDE", text)
        self.assertLess(text.index("installed JadivCode\n"), text.index("installed JadivCode IDE"))
        self.assertIn("Close and start the IDE again", self.shown[-1][1])
        self.assertFalse(os.path.exists(scripts[0][1]))
        self.assertTrue(window.act_update.isEnabled())
        self.close(window)

    def test_failed_installer_is_reported(self):
        from PyQt5.QtCore import QEventLoop, QTimer
        window = self.window()
        path = os.path.join(tempfile.mkdtemp(), "bad.sh")
        with open(path, "w", encoding="utf-8") as handle:
            handle.write("#!/bin/sh\necho broken\nexit 3\n")
        loop = QEventLoop()
        window.updates_prepared([("JadivCode", path), ("JadivCode IDE", path)], "")
        timer = QTimer()
        timer.timeout.connect(lambda: loop.quit() if self.shown else None)
        timer.start(50)
        QTimer.singleShot(15000, loop.quit)
        loop.exec_()
        self.assertEqual(self.shown[-1][0], "warning")
        self.assertIn("ended with code 3", window.output.toPlainText())
        self.assertEqual(window.output.toPlainText().count("broken"), 1)
        self.close(window)
