"""The file-fairy test suite, ported to offerings.

Each test keeps the name of the file-fairy check it ports (from
test_file_fairy.py at commit 4416bcf). Groups became offerings: a
group's sync_mode is now the offering's, and an item's still overrides
it.
"""

import unittest

from support import PortageTestCase


class SyncModes(PortageTestCase):

    def setUp(self):
        super().setUp()
        for name, text in (("mirrored.md", "mirrored v1\n"),
                           ("seeded.md", "seed content\n"),
                           ("owned.md", "owned v1\n"),
                           ("cited.md", "cited\n")):
            self.source_file("conventions", f"files/{name}", text)
        self.offering("conventions", [
            {"source": "files/mirrored.md", "dest": "mirrored.md"},
            {"source": "files/seeded.md", "dest": "seeded.md",
             "sync_mode": "seed_if_missing"},
            {"source": "files/owned.md", "dest": "owned.md",
             "sync_mode": "overwrite"},
            {"source": "files/cited.md", "dest": "cited.md",
             "sync_mode": "reference_only"},
        ])
        r = self.apply("conventions")
        self.assertEqual(r.returncode, 0, r.output)

    def test_first_apply_plants_mirror_seed_and_overwrite_items(self):
        self.assertEqual(self.read("mirrored.md"), "mirrored v1\n")
        self.assertEqual(self.read("seeded.md"), "seed content\n")
        self.assertEqual(self.read("owned.md"), "owned v1\n")

    def test_reference_only_item_is_never_touched(self):
        self.assertFalse(self.target_file("cited.md").exists())

    def test_seed_if_missing_leaves_the_targets_edit_alone(self):
        self.target_file("seeded.md", "the target's own version\n")
        self.source_file("conventions", "files/seeded.md",
                         "seed content v2\n")
        r = self.apply("conventions")
        self.assertEqual(r.returncode, 0, r.output)
        self.assertEqual(self.read("seeded.md"),
                         "the target's own version\n")
        self.assertIn("present", self.plan("conventions").stdout)

    def test_mirror_conflict_is_reported_and_the_local_edit_survives(self):
        self.target_file("mirrored.md", "local hand-edit\n")
        self.source_file("conventions", "files/mirrored.md", "mirrored v2\n")
        r = self.apply("conventions")
        self.assertEqual(r.returncode, 0)
        self.assertIn("conflict", r.output)
        self.assertEqual(self.read("mirrored.md"), "local hand-edit\n")
        self.assertIn("sync_mode: overwrite", r.output,
                      "conflict message points at the standing alternative")
        self.apply("conventions", force=True)
        self.assertEqual(self.read("mirrored.md"), "mirrored v2\n",
                         "--force overwrites the mirror conflict this run")

    def test_overwrite_reclaims_a_local_edit_without_force(self):
        self.target_file("owned.md", "target tries an edit\n")
        r = self.apply("conventions")
        self.assertEqual(r.returncode, 0, r.output)
        self.assertEqual(self.read("owned.md"), "owned v1\n")


class FirstContact(PortageTestCase):

    def test_seed_if_missing_never_clobbers_a_pre_existing_target(self):
        self.source_file("scaffolding", "files/VERSION", "9.9.9\n")
        self.target_file("VERSION", "0.1.0\n")
        self.offering("scaffolding", [
            {"source": "files/VERSION", "dest": "VERSION"}],
            sync_mode="seed_if_missing")
        r = self.apply("scaffolding")
        self.assertEqual(r.returncode, 0, r.output)
        self.assertEqual(self.read("VERSION"), "0.1.0\n")

    def test_offering_mode_inherits_and_item_reference_only_overrides(self):
        self.source_file("styles", "files/a.md", "a\n")
        self.source_file("styles", "files/b.md", "b\n")
        self.offering("styles", [
            {"source": "files/a.md", "dest": "a.md"},
            {"source": "files/b.md", "dest": "b.md",
             "sync_mode": "reference_only"}],
            sync_mode="overwrite")
        r = self.apply("styles")
        self.assertEqual(r.returncode, 0, r.output)
        self.assertTrue(self.target_file("a.md").is_file())
        self.assertFalse(self.target_file("b.md").exists())

    def test_mirror_first_contact(self):
        self.source_file("conventions", "files/same.md", "identical\n")
        self.source_file("conventions", "files/diff.md", "canonical\n")
        self.target_file("same.md", "identical\n")
        self.target_file("diff.md", "the target's variant\n")
        self.offering("conventions", [
            {"source": "files/same.md", "dest": "same.md"},
            {"source": "files/diff.md", "dest": "diff.md"}])
        r = self.apply("conventions")
        self.assertEqual(r.returncode, 0, r.output)
        self.assertIn("conflict", r.output,
                      "a differing dest is a conflict, not a clobber")
        self.assertEqual(self.read("diff.md"), "the target's variant\n")
        self.assertEqual(self.read("same.md"), "identical\n",
                         "an identical dest is adopted")
        r = self.apply("conventions")
        self.assertIn("conflict", r.output,
                      "the unadopted variant stays a conflict on re-apply")


class Retraction(PortageTestCase):

    def setUp(self):
        super().setUp()
        self.target_file("orphan.md", "superseded copy\n")
        self.offering("retired", [
            {"state": "absent", "dest": "orphan.md"},
            {"state": "absent", "dest": "never-existed.md"}])

    def test_plan_shows_retract_and_retired_in_their_own_sections(self):
        p = self.plan("retired")
        self.assertIn("RETRACT", p.stdout)
        self.assertIn("retired", p.stdout)

    def test_absent_deletes_the_dest_and_re_apply_is_a_no_op(self):
        r = self.apply("retired")
        self.assertEqual(r.returncode, 0, r.output)
        self.assertFalse(self.target_file("orphan.md").exists())
        self.assertIn("retracted: orphan.md", r.stdout)
        r = self.apply("retired")
        self.assertEqual(r.returncode, 0, r.output)
        self.assertIn("nothing to apply", r.stdout)

    def test_absent_works_under_any_inherited_sync_mode(self):
        self.target_file("also-gone.md", "x\n")
        self.offering("retired-seed", [
            {"state": "absent", "dest": "also-gone.md"}],
            sync_mode="seed_if_missing")
        r = self.apply("retired-seed")
        self.assertEqual(r.returncode, 0, r.output)
        self.assertFalse(self.target_file("also-gone.md").exists())


BEGIN = "<!-- uc-portage:begin license -->"
END = "<!-- uc-portage:end license -->"


class ManagedBlocks(PortageTestCase):

    def setUp(self):
        super().setUp()
        self.source_file("blocks", "en-ca/license-block.md",
                         "## License\n\nv1 of the block.\n")
        self.target_file("README.md", "# target\n\nThe target's own prose.\n")
        self.offering("blocks", [
            {"block": "license", "source": "en-ca/license-block.md",
             "dest": "README.md"}])

    def test_block_lifecycle(self):
        r = self.apply("blocks")
        readme = self.read("README.md")
        self.assertEqual(r.returncode, 0, r.output)
        self.assertIn(BEGIN, readme)
        self.assertIn("v1 of the block.", readme)
        self.assertTrue(readme.startswith(
            "# target\n\nThe target's own prose.\n"),
            "block inserts at EOF; target prose untouched")

        r = self.apply("blocks")
        self.assertIn("nothing to apply", r.stdout,
                      "unchanged block re-apply is a no-op")

        # Source changes; edits outside the markers survive.
        self.source_file("blocks", "en-ca/license-block.md",
                         "## License\n\nv2 of the block.\n")
        self.target_file("README.md", self.read("README.md").replace(
            "The target's own prose.",
            "The target's own prose, edited locally."))
        r = self.apply("blocks")
        readme = self.read("README.md")
        self.assertIn("v2 of the block.", readme, r.output)
        self.assertIn("edited locally.", readme)

        # A local edit inside the markers: mirror protects it.
        self.target_file("README.md", self.read("README.md").replace(
            "v2 of the block.", "hand-edited region"))
        self.source_file("blocks", "en-ca/license-block.md",
                         "## License\n\nv3.\n")
        r = self.apply("blocks")
        self.assertIn("conflict", r.output)
        self.assertIn("hand-edited region", self.read("README.md"))

        # --force reclaims the region; outside edits still intact.
        self.apply("blocks", force=True)
        readme = self.read("README.md")
        self.assertIn("v3.", readme)
        self.assertIn("edited locally.", readme)

    def test_missing_dest_is_created_holding_only_the_block(self):
        self.offering("blocks", [
            {"block": "license", "source": "en-ca/license-block.md",
             "dest": "CLAUDE.md"}])
        r = self.apply("blocks")
        claude = self.read("CLAUDE.md")
        self.assertEqual(r.returncode, 0, r.output)
        self.assertTrue(claude.startswith(BEGIN))
        self.assertTrue(claude.rstrip().endswith(END))

    def test_anchor_bof_inserts_the_block_at_the_top(self):
        self.target_file("notes.md", "existing first line\n")
        self.offering("blocks", [
            {"block": "license", "source": "en-ca/license-block.md",
             "dest": "notes.md", "anchor": "BOF"}])
        r = self.apply("blocks")
        notes = self.read("notes.md")
        self.assertEqual(r.returncode, 0, r.output)
        self.assertTrue(notes.startswith(BEGIN))
        self.assertTrue(notes.rstrip().endswith("existing first line"))


class BlockFirstContact(PortageTestCase):

    def setUp(self):
        super().setUp()
        self.source_file("blocks", "files/b.md", "canonical body\n")
        self.target_file("doc.md",
                         "<!-- uc-portage:begin b -->\nsomebody else's body\n"
                         "<!-- uc-portage:end b -->\n")

    def blocks(self, **fields):
        self.offering("blocks", [
            {"block": "b", "source": "files/b.md", "dest": "doc.md"}],
            **fields)

    def test_first_contact_with_a_differing_region_is_a_conflict(self):
        self.blocks()
        r = self.apply("blocks")
        self.assertEqual(r.returncode, 0, r.output)
        self.assertIn("conflict", r.output)
        self.assertIn("somebody else's body", self.read("doc.md"))

    def test_seed_if_missing_leaves_a_present_block_alone(self):
        self.blocks(sync_mode="seed_if_missing")
        r = self.apply("blocks")
        self.assertEqual(r.returncode, 0, r.output)
        self.assertIn("somebody else's body", self.read("doc.md"))

    def test_overwrite_block_reclaims_the_region_without_force(self):
        self.blocks(sync_mode="overwrite")
        r = self.apply("blocks")
        self.assertEqual(r.returncode, 0, r.output)
        self.assertIn("canonical body", self.read("doc.md"))

    def test_malformed_markers_are_an_error_never_a_guess(self):
        self.target_file("bad.md", "<!-- uc-portage:begin b -->\nno end\n")
        self.offering("blocks", [
            {"block": "b", "source": "files/b.md", "dest": "bad.md"}])
        r = self.apply("blocks")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("malformed", r.stderr)


class Refusals(PortageTestCase):

    def setUp(self):
        super().setUp()
        self.source_file("broken", "files/a.md", "a\n")

    def test_substitute_refuses_as_scheduled_not_unknown(self):
        self.offering("broken", [
            {"block": "b", "source": "files/a.md", "dest": "doc.md",
             "substitute": True}], valid=False)
        r = self.apply("broken")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("scheduled", r.stderr)

    def test_state_directory_refuses_as_scheduled_not_unknown(self):
        self.offering("broken", [
            {"state": "directory", "dest": "somewhere/"}], valid=False)
        r = self.apply("broken")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("scheduled but", r.stderr)

    def test_unknown_state_is_an_offering_error(self):
        self.offering("broken", [
            {"state": "vapor", "dest": "x.md"}], valid=False)
        r = self.apply("broken")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("unknown state", r.stderr)

    def test_unknown_sync_mode_is_an_offering_error_not_a_default(self):
        self.offering("broken", [
            {"source": "files/a.md", "dest": "a.md"}],
            valid=False, sync_mode="yolo")
        r = self.apply("broken")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("unknown sync_mode", r.stderr)
        self.assertIn("yolo", r.stderr)


if __name__ == "__main__":
    unittest.main()
