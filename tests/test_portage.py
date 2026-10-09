"""What uc-portage adds to the ported engine: line-ending-blind
checksums, the case-collision check, harvest, the offering front end and
its schema."""

import unittest

from support import PortageTestCase

from uc_portage.checksums import sha256_bytes
from uc_portage.errors import PortageError
from uc_portage.schema import offering_schema, validate


class LineEndings(PortageTestCase):

    def setUp(self):
        super().setUp()
        self.source_file("docs", "files/guide.md", "line one\nline two\n")
        self.source_file("docs", "en-ca/block.md", "block line\n")
        self.target_file("README.md", "# target\n")
        self.offering("docs", [
            {"source": "files/guide.md", "dest": "guide.md"},
            {"block": "note", "source": "en-ca/block.md",
             "dest": "README.md"}])
        r = self.apply("docs")
        self.assertEqual(r.returncode, 0, r.output)

    def crlf(self, rel):
        path = self.target_file(rel)
        path.write_bytes(path.read_bytes().replace(b"\n", b"\r\n"))

    def test_a_file_converted_to_crlf_is_reported_unchanged(self):
        self.crlf("guide.md")
        p = self.plan("docs")
        self.assertNotIn("CONFLICT", p.stdout)
        self.assertIn("0 item(s) would be synced", p.stdout)
        self.assertIn("unchanged", p.stdout)
        self.assertEqual(self.harvest("docs").stdout.count("changed"), 0)

    def test_a_block_in_a_crlf_file_is_reported_unchanged(self):
        self.crlf("README.md")
        p = self.plan("docs")
        self.assertNotIn("CONFLICT", p.stdout)
        self.assertIn("0 item(s) would be synced", p.stdout)

    def test_crlf_does_not_hide_a_real_edit(self):
        self.target_file("guide.md", "line one\r\nline 2\r\n")
        self.assertIn("CONFLICT", self.plan("docs").stdout)

    def test_binary_files_are_hashed_as_they_are(self):
        self.assertNotEqual(sha256_bytes(b"\0a\r\n"), sha256_bytes(b"\0a\n"))
        self.assertEqual(sha256_bytes(b"a\r\n"), sha256_bytes(b"a\n"))

    def test_blocks_are_written_with_lf(self):
        self.assertNotIn(b"\r\n", self.target_file("README.md").read_bytes())


class CaseCollisions(PortageTestCase):

    def test_two_case_colliding_destinations_are_refused(self):
        self.source_file("one", "files/readme.md", "one\n")
        self.source_file("two", "files/readme.md", "two\n")
        self.offering("one", [
            {"source": "files/readme.md", "dest": "docs/README.md"}])
        self.offering("two", [
            {"source": "files/readme.md", "dest": "docs/readme.md"}])
        r = self.apply("one", "two")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("case collision", r.stderr)
        self.assertFalse(any(self.target.iterdir()), "nothing is written")

    def test_a_collision_within_one_offering_is_refused(self):
        self.source_file("one", "files/a.md", "a\n")
        self.offering("one", [
            {"source": "files/a.md", "dest": "Notes.md"},
            {"source": "files/a.md", "dest": "notes.md"}])
        r = self.plan("one")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("case collision", r.stderr)

    def test_the_same_dest_claimed_twice_is_refused(self):
        self.source_file("one", "files/a.md", "a\n")
        self.source_file("two", "files/a.md", "a\n")
        self.offering("one", [{"source": "files/a.md", "dest": "a.md"}])
        self.offering("two", [{"source": "files/a.md", "dest": "a.md"}])
        r = self.plan("one", "two")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("claimed more than once", r.stderr)

    def test_distinct_blocks_may_share_a_dest(self):
        self.source_file("one", "files/a.md", "a\n")
        self.source_file("two", "files/b.md", "b\n")
        self.offering("one", [
            {"block": "a", "source": "files/a.md", "dest": "README.md"}])
        self.offering("two", [
            {"block": "b", "source": "files/b.md", "dest": "README.md"}])
        r = self.apply("one", "two")
        self.assertEqual(r.returncode, 0, r.output)
        readme = self.read("README.md")
        self.assertIn("uc-portage:begin a", readme)
        self.assertIn("uc-portage:begin b", readme)


class Harvest(PortageTestCase):

    def setUp(self):
        super().setUp()
        self.source_file("docs", "files/a.md", "a v1\n")
        self.source_file("docs", "files/b.md", "b v1\n")
        self.source_file("docs", "files/seed.md", "seed\n")
        self.source_file("docs", "files/block.md", "block v1\n")
        self.offering("docs", [
            {"source": "files/a.md", "dest": "a.md"},
            {"source": "files/b.md", "dest": "b.md"},
            {"source": "files/seed.md", "dest": "seed.md",
             "sync_mode": "seed_if_missing"},
            {"block": "x", "source": "files/block.md", "dest": "X.md"}])
        r = self.apply("docs")
        self.assertEqual(r.returncode, 0, r.output)

    def test_nothing_to_harvest_after_apply(self):
        self.assertIn("nothing to harvest", self.harvest("docs").stdout)

    def test_reports_a_target_only_change_and_ignores_a_source_only_one(self):
        self.target_file("a.md", "a improved in the target\n")
        self.source_file("docs", "files/b.md", "b v2 upstream\n")
        h = self.harvest("docs")
        self.assertEqual(h.returncode, 0, h.output)
        self.assertIn("a.md: changed", h.stdout)
        self.assertNotIn("b.md", h.stdout)
        self.assertEqual(self.read("a.md"), "a improved in the target\n",
                         "harvest writes nothing")

    def test_a_change_on_both_sides_is_a_conflict_not_a_harvest(self):
        self.target_file("a.md", "target edit\n")
        self.source_file("docs", "files/a.md", "a v2\n")
        self.assertNotIn("a.md", self.harvest("docs").stdout)
        self.assertIn("CONFLICT", self.plan("docs").stdout)

    def test_reports_a_block_edit_and_a_deletion(self):
        self.target_file("X.md", self.read("X.md").replace(
            "block v1", "block improved"))
        self.target_file("a.md").unlink()
        h = self.harvest("docs")
        self.assertIn("X.md (block x): changed", h.stdout)
        self.assertIn("a.md: deleted", h.stdout)

    def test_seed_if_missing_items_are_the_targets_own(self):
        self.target_file("seed.md", "the target's own\n")
        self.assertNotIn("seed.md", self.harvest("docs").stdout)


class Offerings(PortageTestCase):

    def test_language_placeholder_uses_the_subscribers_language(self):
        self.source_file("signpost", "en-ca/block.md", "English\n")
        self.source_file("signpost", "fr-ca/block.md", "Français\n")
        self.offering("signpost", [
            {"block": "signpost", "source": "{language}/block.md",
             "dest": "CLAUDE.md"}], source_language="en-ca")
        r = self.run_cli("apply", ["signpost"], "--yes",
                         "--language", "fr-ca")
        self.assertEqual(r.returncode, 0, r.output)
        self.assertIn("Français", self.read("CLAUDE.md"))

    def test_language_falls_back_to_the_source_language(self):
        self.source_file("signpost", "en-ca/block.md", "English\n")
        self.offering("signpost", [
            {"block": "signpost", "source": "{language}/block.md",
             "dest": "CLAUDE.md"}], source_language="en-ca")
        r = self.run_cli("apply", ["signpost"], "--yes",
                         "--language", "fr-ca")
        self.assertEqual(r.returncode, 0, r.output)
        self.assertIn("English", self.read("CLAUDE.md"))

    def test_comma_separated_subscriptions(self):
        self.source_file("one", "files/a.md", "a\n")
        self.source_file("two", "files/b.md", "b\n")
        self.offering("one", [{"source": "files/a.md", "dest": "a.md"}])
        self.offering("two", [{"source": "files/b.md", "dest": "b.md"}])
        r = self.run_cli("apply", ["one,two"], "--yes")
        self.assertEqual(r.returncode, 0, r.output)
        self.assertTrue(self.target_file("b.md").is_file())

    def test_id_must_match_the_directory_name(self):
        self.offering("one", [{"state": "absent", "dest": "a.md"}])
        path = self.source / "one"
        path.rename(self.source / "other")
        r = self.plan("other")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("does not match its directory name", r.stderr)

    def test_an_unknown_offering_is_an_error(self):
        r = self.plan("nowhere")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("offering not found", r.stderr)

    def test_a_dest_outside_the_target_is_refused(self):
        self.source_file("one", "files/a.md", "a\n")
        for dest in ("../escape.md", "/etc/escape.md", "C:/escape.md",
                     "docs\\escape.md"):
            with self.subTest(dest=dest):
                self.offering("one", [
                    {"source": "files/a.md", "dest": dest}], valid=False)
                r = self.plan("one")
                self.assertNotEqual(r.returncode, 0)
        self.assertFalse((self.root / "escape.md").exists())

    def test_a_source_outside_the_offering_is_refused(self):
        self.offering("one", [
            {"source": "../two/secret.md", "dest": "a.md"}], valid=False)
        r = self.plan("one")
        self.assertNotEqual(r.returncode, 0)

    def test_a_language_that_is_not_a_tag_is_refused(self):
        self.source_file("one", "en-ca/a.md", "a\n")
        self.offering("one", [
            {"source": "{language}/a.md", "dest": "a.md"}],
            source_language="en-ca")
        r = self.run_cli("plan", ["one"], "--language", "../en-ca")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("not a lowercase tag", r.stderr)

    def test_state_file_is_written_at_the_target_root(self):
        self.offering("one", [{"state": "absent", "dest": "a.md"}])
        self.target_file("a.md", "x\n")
        self.apply("one")
        self.assertTrue(self.target_file(".uc-portage-state.yaml").is_file())


class Schema(unittest.TestCase):

    def test_the_schema_uses_only_supported_keywords(self):
        # validate() raises on any keyword it does not implement.
        self.assertEqual(validate({"format": 1, "id": "x", "items": [
            {"state": "absent", "dest": "a"}]}, offering_schema()), [])

    def test_unsupported_keywords_are_refused_not_ignored(self):
        with self.assertRaises(PortageError):
            validate("x", {"type": "string", "maxLength": 3})

    def test_unexpected_keys_are_reported(self):
        errors = validate({"format": 1, "id": "x", "colour": "blue",
                           "items": [{"state": "absent", "dest": "a"}]},
                          offering_schema())
        self.assertTrue(any("colour" in e for e in errors), errors)

    def test_an_item_matching_no_shape_is_reported(self):
        errors = validate({"format": 1, "id": "x", "items": [
            {"dest": "a"}]}, offering_schema())
        self.assertTrue(any("none of the allowed shapes" in e
                            for e in errors), errors)


if __name__ == "__main__":
    unittest.main()
