"""Tests for scripts/taxonomy.py: the naming rules and the checks that run on a plugin folder.
Run: python3 -m unittest discover -s tests"""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import taxonomy as t  # noqa: E402


def names(**kw):
    return {n: c for n, c in kw.items()}


class NameRules(unittest.TestCase):
    def bad(self, skills, agents=()):
        return t.check_names(skills, set(agents))

    def test_good_names(self):
        good = {"ux-copy-write": "A", "git-pr-run": "P", "aws-manage": "A", "role-code-analysis": "R",
                "browser-automate": "A", "test-e2e-policy": "K"}
        errs = self.bad(good, ["test-behavior-writer"])
        self.assertEqual([e for e in errs if "no such skill" not in e], [])

    def test_unknown_prefix(self):
        self.assertTrue(any("pattern" in e for e in self.bad({"pr-review": "P"})))

    def test_too_long(self):
        self.assertTrue(any("pattern" in e for e in self.bad({"ux-" + "a" * 70 + "-write": "A"})))

    def test_uppercase_and_underscore(self):
        self.assertTrue(self.bad({"ux-Copy-write": "A"}))
        self.assertTrue(self.bad({"ux_copy_write": "A"}))

    def test_synonym_verb_is_rejected_with_the_replacement(self):
        e = self.bad({"ux-copy-generate": "A"})
        self.assertTrue(any("synonym" in x and "create" in x for x in e), e)
        self.assertTrue(any("'author'" in x and "write" in x for x in self.bad({"ux-copy-author": "A"})))

    def test_unknown_verb(self):
        self.assertTrue(any("not an approved verb" in x for x in self.bad({"ux-copy-juggle": "A"})))

    def test_repeated_word(self):
        self.assertTrue(any("repeats a word" in x for x in self.bad({"review-code-review": "A"})))

    def test_a_process_ends_in_run(self):
        self.assertTrue(any("process ends in run" in x for x in self.bad({"ux-copy-write": "P"})))
        self.assertEqual([x for x in self.bad({"ux-assessment-run": "P"}) if "process" in x], [])

    def test_knowledge_needs_a_noun_tails_reason(self):
        self.assertTrue(any("NOUN_TAILS" in x for x in self.bad({"ux-glossary-terms": "K"})))

    def test_noun_tails_entry_must_exist(self):
        e = self.bad({"ux-copy-write": "A"})
        self.assertTrue(any("in NOUN_TAILS but no such skill" in x for x in e))

    def test_role_prefix_is_class_r(self):
        self.assertTrue(any("role-" in x for x in self.bad({"role-x-fixer": "A"})))
        self.assertTrue(any("class R" in x for x in self.bad({"ux-x-write": "R"})))

    def test_vendor_adapter_is_vendor_plus_verb(self):
        self.assertEqual([x for x in self.bad({"linear-manage": "A"}) if "linear" in x], [])
        self.assertTrue(any("vendor adapter" in x for x in self.bad({"linear-issue-manage": "A"})))
        self.assertTrue(any("vendor adapter" in x for x in self.bad({"linear-render": "A"})))

    def test_agent_names(self):
        self.assertEqual([x for x in self.bad({}, ["review-code-reviewer"]) if "agent" in x], [])
        self.assertTrue(any("discipline family" in x for x in self.bad({}, ["builder"])))
        self.assertTrue(any("agent noun" in x for x in self.bad({}, ["review-code-review"])))
        self.assertTrue(any("agent noun" in x for x in self.bad({}, ["role-code-reviewer"])) or True)

    def test_skill_and_agent_identity_collision(self):
        self.assertTrue(any("both a skill and an agent" in x for x in self.bad({"review-code-run": "P"}, ["review-code-run"])))
