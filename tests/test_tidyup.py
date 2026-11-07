import os
import sys
import tempfile
import time
import unittest
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import tidyup  # noqa: E402

OLD = time.time() - 3600 * 24  # a day ago


def make(folder, name, age=OLD, content="x"):
    path = os.path.join(folder, name)
    with open(path, "w") as handle:
        handle.write(content)
    os.utime(path, (age, age))
    return path


class TidyupTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = self.tmp.name

    def tearDown(self):
        self.tmp.cleanup()

    def test_categories(self):
        self.assertEqual(tidyup.category_for("photo.JPG"), "Images")
        self.assertEqual(tidyup.category_for("report.pdf"), "Documents")
        self.assertEqual(tidyup.category_for("part.STL"), "Design & CAD")
        self.assertEqual(tidyup.category_for("weird.xyz"), "Other")
        self.assertEqual(tidyup.category_for("noextension"), "Other")

    def test_preview_changes_nothing(self):
        make(self.dir, "a.png")
        moves, _ = tidyup.plan(self.dir)
        self.assertEqual([m.dst for m in moves], [os.path.join("Images", "a.png")])
        self.assertTrue(os.path.exists(os.path.join(self.dir, "a.png")))

    def test_apply_moves_files(self):
        make(self.dir, "a.png")
        make(self.dir, "b.pdf")
        moves, _ = tidyup.plan(self.dir)
        self.assertEqual(tidyup.apply_moves(self.dir, moves), 2)
        self.assertTrue(os.path.exists(os.path.join(self.dir, "Images", "a.png")))
        self.assertTrue(os.path.exists(os.path.join(self.dir, "Documents", "b.pdf")))
        self.assertFalse(os.path.exists(os.path.join(self.dir, "a.png")))

    def test_recent_hidden_and_partial_files_are_skipped(self):
        make(self.dir, "new.png", age=time.time())
        make(self.dir, ".secret.txt")
        make(self.dir, "movie.mp4.crdownload")
        make(self.dir, "ok.png")
        moves, skipped = tidyup.plan(self.dir)
        self.assertEqual([m.src for m in moves], ["ok.png"])
        self.assertEqual(len(skipped), 3)

    def test_never_overwrites(self):
        os.makedirs(os.path.join(self.dir, "Images"))
        make(os.path.join(self.dir, "Images"), "a.png", content="old")
        make(self.dir, "a.png", content="new")
        moves, _ = tidyup.plan(self.dir)
        self.assertEqual(moves[0].dst, os.path.join("Images", "a (1).png"))
        tidyup.apply_moves(self.dir, moves)
        with open(os.path.join(self.dir, "Images", "a.png")) as handle:
            self.assertEqual(handle.read(), "old")

    def test_collisions_inside_one_plan_get_unique_names(self):
        make(self.dir, "a.png")
        make(self.dir, "a.PNG")  # on case-sensitive systems these are two files
        moves, _ = tidyup.plan(self.dir)
        self.assertEqual(len({m.dst for m in moves}), len(moves))

    def test_by_date_groups_by_month(self):
        stamp = datetime(2025, 3, 15).timestamp()
        make(self.dir, "a.png", age=stamp)
        moves, _ = tidyup.plan(self.dir, by_date=True)
        self.assertEqual(moves[0].dst, os.path.join("Images", "2025-03", "a.png"))

    def test_undo_restores_everything_and_removes_empty_folders(self):
        make(self.dir, "a.png")
        make(self.dir, "b.pdf")
        moves, _ = tidyup.plan(self.dir, by_date=True)
        tidyup.apply_moves(self.dir, moves)
        restored, problems = tidyup.undo_last(self.dir)
        self.assertEqual((restored, problems), (2, []))
        self.assertEqual(sorted(os.listdir(self.dir)), ["a.png", "b.pdf"])

    def test_undo_with_nothing_to_undo(self):
        restored, problems = tidyup.undo_last(self.dir)
        self.assertEqual(restored, 0)
        self.assertTrue(problems)

    def test_undo_skips_when_original_name_is_taken(self):
        make(self.dir, "a.png", content="first")
        moves, _ = tidyup.plan(self.dir)
        tidyup.apply_moves(self.dir, moves)
        make(self.dir, "a.png", content="newcomer")
        restored, problems = tidyup.undo_last(self.dir)
        self.assertEqual(restored, 0)
        self.assertEqual(len(problems), 1)
        with open(os.path.join(self.dir, "a.png")) as handle:
            self.assertEqual(handle.read(), "newcomer")

    def test_cli_preview_then_apply(self):
        make(self.dir, "a.png")
        self.assertEqual(tidyup.main([self.dir]), 0)
        self.assertTrue(os.path.exists(os.path.join(self.dir, "a.png")))
        self.assertEqual(tidyup.main([self.dir, "--apply"]), 0)
        self.assertTrue(os.path.exists(os.path.join(self.dir, "Images", "a.png")))
        self.assertEqual(tidyup.main([self.dir, "--undo"]), 0)
        self.assertTrue(os.path.exists(os.path.join(self.dir, "a.png")))

    def test_summary_counts(self):
        moves = [tidyup.Move("a", os.path.join("Images", "a")), tidyup.Move("b", os.path.join("Images", "b")),
                 tidyup.Move("c", os.path.join("Documents", "c"))]
        self.assertEqual(tidyup.summarize(moves), {"Images": 2, "Documents": 1})


if __name__ == "__main__":
    unittest.main()
