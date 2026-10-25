import os
import pathlib
import tempfile
import unittest

from dataset_ancestry import Lineage, hash_dir

EX = pathlib.Path(__file__).resolve().parent.parent / "examples" / "ancestry.json"


class Tests(unittest.TestCase):
    def setUp(self):
        self.lin = Lineage.load(str(EX))

    def test_ancestors_and_sources(self):
        anc = self.lin.ancestors("my-finetune-v3")
        self.assertIn("wiki-dump-2025", anc)
        self.assertEqual(len(anc), len(set(anc)))
        self.assertEqual(
            set(self.lin.sources("my-finetune-v3")),
            {"wiki-dump-2025", "stack-snippets", "public-domain-books", "support-tickets", "academic-qa"},
        )

    def test_obligations(self):
        ob = self.lin.obligations("my-finetune-v3")
        self.assertEqual(ob.non_commercial, ["academic-qa"])
        self.assertEqual(set(ob.share_alike), {"CC-BY-SA"})
        self.assertEqual(len(ob.attribution), 3)
        self.assertTrue(any("proprietary" in c for c in ob.conflicts))

    def test_use_checks(self):
        ok, reasons = self.lin.check("my-finetune-v3", "commercial_training")
        self.assertFalse(ok)
        self.assertTrue(any("non-commercial" in r for r in reasons))
        ok, _ = self.lin.check("instruct-mix", "commercial_training")
        self.assertTrue(ok)
        self.assertTrue(self.lin.check("public-domain-books", "redistribution")[0])

    def test_unknown_use_is_rejected_not_waved_through(self):
        for use in ("Commercial_Training", "commercial-training", "sell it", ""):
            with self.subTest(use=use), self.assertRaises(ValueError):
                self.lin.check("instruct-mix", use)

    def test_validation_and_cycles(self):
        with self.assertRaises(ValueError):
            Lineage({"a": {"parents": ["missing"]}})
        cyc = Lineage({"s": {"license": "MIT"}, "a": {"parents": ["b", "s"]}, "b": {"parents": ["a"]}})
        with self.assertRaises(ValueError):
            cyc.ancestors("a")
        self.assertEqual(Lineage({"x": {"license": "WTFPL-ish"}}).obligations("x").unknown, ["x (WTFPL-ish)"])

    def test_hash_and_verify(self):
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, "a.txt"), "w") as fh:
                fh.write("hello")
            h = hash_dir(d)
            lin = Lineage({"s": {"license": "MIT", "root_hash": h["root"]}})
            self.assertEqual(lin.verify("s", d), (True, "match"))
            with open(os.path.join(d, "b.txt"), "w") as fh:
                fh.write("new")
            self.assertFalse(lin.verify("s", d)[0])

    def test_dot(self):
        dot = self.lin.to_dot("my-finetune-v3")
        self.assertIn('"wiki-clean" -> "instruct-mix"', dot)
        self.assertIn("color=red", dot)


if __name__ == "__main__":
    unittest.main()
