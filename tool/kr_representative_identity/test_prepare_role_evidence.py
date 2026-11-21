from argparse import Namespace
from contextlib import closing, redirect_stdout
from io import StringIO
import json
from pathlib import Path
import sqlite3
from tempfile import TemporaryDirectory
import unittest
import zipfile

from prepare_role_evidence import natural, position_state, prepare, sha256, unique_rows


class PositionTest(unittest.TestCase):
    def setUp(self):
        self.trainee = {"icon": 0, "character": 0, "card": 0}
        self.prediction = {**self.trainee, "rect_xyxy": [1, 2, 10, 12], "image_wh": [20, 30]}
        self.observation = {"position": 0, "basis": "Reviewed representative factor-tab prediction"}

    def test_position_zero_requires_an_actual_prediction(self):
        self.assertEqual(position_state(self.trainee, self.observation, 272),
                         ("unknown", "position_zero_without_representative_prediction"))
        self.observation["factor_tab_prediction"] = self.prediction
        self.assertEqual(position_state(self.trainee, self.observation, 272)[0], "confirmed")

    def test_prediction_disagreement_and_bad_geometry_are_conflicts(self):
        self.observation["factor_tab_prediction"] = {**self.prediction, "card": 1}
        self.assertEqual(position_state(self.trainee, self.observation, 272),
                         ("conflict", "representative_prediction_disagrees_with_record"))
        self.observation["factor_tab_prediction"] = {**self.prediction, "rect_xyxy": [1, 2, 21, 12]}
        self.assertEqual(position_state(self.trainee, self.observation, 272),
                         ("conflict", "representative_prediction_geometry_invalid"))

    def test_nonzero_position_can_use_a_reviewed_portrait_receipt(self):
        self.assertEqual(position_state({**self.trainee, "card": 22},
                                        {"position": 22, "basis": "Reviewed source portrait"}, 272)[0], "confirmed")

    def test_wrong_position_and_boolean_indices_are_rejected(self):
        self.assertEqual(position_state(self.trainee, {**self.observation, "position": 1}, 272)[0], "conflict")
        for rows in ([{"position": True}], [{"position": 0}, {"position": 0}]):
            with self.assertRaises(ValueError):
                unique_rows(rows, "position", natural)


class EvidenceTest(unittest.TestCase):
    def test_only_the_positively_observed_zero_reaches_the_reader(self):
        with TemporaryDirectory() as work:
            root = Path(work)

            def write(name, value):
                path = root / name
                path.write_text(json.dumps(value), encoding="utf-8")
                return path

            trainee = {"icon": 0, "character": 0, "card": 0}
            records = root / "records.zip"
            capture_keys = []
            with zipfile.ZipFile(records, "w") as archive:
                for index in range(2):
                    data = json.dumps({"trainee": trainee, "fixture": index}).encode()
                    archive.writestr(f"{index}.json", data)
                    capture_keys.append("sha256:" + sha256(data))
            scout_data = {"entries": [{"capture_key": key} for key in capture_keys]}
            scout = write("scout.json", scout_data)
            card_list = write("list.json", [{}])
            lookup = root / "lookup.sqlite3"
            with closing(sqlite3.connect(lookup)) as db:
                db.executescript("""
                    CREATE TABLE character_card(card_id, chara_id);
                    CREATE TABLE character(chara_id, name_ko);
                    CREATE TABLE card_profile(card_id, outfit_name_ko);
                    INSERT INTO character_card VALUES (100001, 1000);
                    INSERT INTO character VALUES (1000, 'character');
                    INSERT INTO card_profile VALUES (100001, 'outfit');
                """)
            lookup_hash, list_hash = sha256(lookup.read_bytes()), sha256(card_list.read_bytes())
            input_hash = sha256(json.dumps(scout_data, sort_keys=True, separators=(",", ":")).encode())
            baseline = write("baseline.json", {
                "event": "kr-sapporo-loh-2600", "target": "106803", "style": "escape",
                "build": "kitasan-falcon-30210", "source": "owned", "mode": "direct_parent",
                "master_id": "sha256:" + lookup_hash, "input_hash": input_hash, "unavailable": [],
                "entries": [{"candidate_id": "owned-instance:" + key,
                             "source_evidence": {"capture_key": key}} for key in capture_keys],
            })
            bridge = write("bridge.json", {
                "schema_version": 1, "card_list_sha256": list_hash, "kr_lookup_sha256": lookup_hash,
                "entries": [{"position": 0, "card_id": 100001, "chara_id": 1000, "basis": "reviewed mapping"}],
            })
            observations = write("observations.json", {
                "schema_version": 1, "card_list_sha256": list_hash, "records_sha256": sha256(records.read_bytes()),
                "entries": [
                    {"capture_key": capture_keys[0], "position": 0, "basis": "reviewed",
                     "factor_tab_prediction": {**trainee, "rect_xyxy": [1, 2, 10, 12], "image_wh": [20, 30]}},
                    {"capture_key": capture_keys[1], "position": 0, "basis": "no representative prediction"},
                ],
            })
            output = root / "output"
            args = Namespace(scout_input=scout, baseline=baseline, records=records, card_list=card_list,
                             kr_lookup=lookup, bridge=bridge, observations=observations, output=output)
            with redirect_stdout(StringIO()):
                prepare(args)
            evidence = json.loads((output / "role-evidence.json").read_bytes())["direct_parent_identity"]
            receipt = json.loads((output / "identity-receipt.json").read_bytes())
            self.assertEqual(evidence["input_hash"], input_hash)
            self.assertEqual(list(evidence["candidates"]), ["owned-instance:" + capture_keys[0]])
            self.assertEqual([row["state"] for row in receipt["entries"]], ["confirmed", "unknown"])



if __name__ == "__main__":
    unittest.main()
