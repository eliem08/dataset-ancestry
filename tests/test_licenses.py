import unittest

from dataset_ancestry.core import Lineage
from dataset_ancestry.licenses import lookup


def lineage(**sources):
    ds = {name: {"license": lic} for name, lic in sources.items()}
    ds["out"] = {"parents": list(sources)}
    return Lineage(ds)


class LookupTests(unittest.TestCase):
    def test_names_as_people_write_them(self):
        self.assertEqual(lookup("cc by-sa 3.0")[0], "CC-BY-SA-3.0")
        self.assertEqual(lookup("CC-BY-NC-ND-2.0-fr")[1], {"by": True, "nc": True, "nd": True})
        self.assertEqual(lookup("Apache 2.0")[0], "Apache-2.0")
        self.assertEqual(lookup("MIT License")[0], "MIT")
        self.assertEqual(lookup("Llama 3.1 Community License")[0], "Llama-3.1")
        self.assertEqual(lookup("CC-BY-ND")[0], "CC-BY-ND")  # no version is not assumed to be 4.0
        self.assertIsNone(lookup("made-up-licence"))
        self.assertIsNone(lookup(""))


class ObligationTests(unittest.TestCase):
    def test_old_cc_versions_are_checked_not_unknown(self):
        ok, why = lineage(a="CC-BY-NC-3.0").check("out", "commercial_training")
        self.assertFalse(ok)
        self.assertTrue(any("non-commercial" in r for r in why))

    def test_cc_by_sa_4_and_gplv3_combine_one_way(self):
        ok, why = lineage(a="CC-BY-SA-4.0", b="GPL-3.0-only").check("out", "commercial_redistribution")
        self.assertTrue(ok, why)
        self.assertTrue(any("GPLv3" in r for r in why))
        ok, _ = lineage(a="CC-BY-SA-3.0", b="GPL-3.0-only").check("out", "commercial_redistribution")
        self.assertFalse(ok)  # 3.0 has no such compatibility
        ok, _ = lineage(a="GPL-2.0-only", b="GPL-3.0-only").check("out", "commercial_redistribution")
        self.assertFalse(ok)

    def test_ai_model_licences_carry_their_terms(self):
        ok, why = lineage(a="Llama 2").check("out", "commercial_training")
        self.assertTrue(ok)
        text = " ".join(why)
        for phrase in ("other than Llama 2", "acceptable-use", "700 million"):
            self.assertIn(phrase, text)
        ok, why = lineage(a="Llama-3.1").check("out", "commercial_training")
        self.assertIn("licensor's name", " ".join(why))
        ok, why = lineage(a="CreativeML-OpenRAIL-M").check("out", "research")
        self.assertTrue(ok)
        self.assertIn("acceptable-use", " ".join(why))

    def test_weak_copyleft_is_a_note_not_a_block(self):
        ok, why = lineage(a="MPL-2.0", b="proprietary-owned").check("out", "commercial_training")
        self.assertTrue(ok)
        self.assertIn("weak copyleft", " ".join(why))


if __name__ == "__main__":
    unittest.main()
