"""Prepare offline representative identity evidence for Sapporo's owned-parent reader."""

import argparse
from contextlib import closing
import hashlib
import io
import json
from pathlib import Path
import sqlite3
import sys
import zipfile


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def json_object(data, label):
    value = json.loads(data)
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be a JSON object")
    return value


def unique_rows(rows, field, valid):
    result = {}
    if not isinstance(rows, list):
        raise ValueError(f"Expected a row list keyed by {field}")
    for row in rows:
        key = row.get(field) if isinstance(row, dict) else None
        if not valid(key) or key in result:
            raise ValueError(f"Invalid or duplicate {field}")
        result[key] = row
    return result


def natural(value):
    return type(value) is int and value >= 0


def nonempty(value):
    return isinstance(value, str) and bool(value.strip())


def position_state(trainee, observation, list_length):
    reviewed_state = observation.get("state", "confirmed")
    if reviewed_state in ("unknown", "conflict"):
        reason = observation.get("basis")
        if nonempty(reason):
            return reviewed_state, reason
        return "conflict", "reviewed_nonconfirmation_reason_missing"
    if reviewed_state != "confirmed":
        return "conflict", "invalid_reviewed_state"

    position = trainee.get("card")
    if not natural(position) or position >= list_length:
        return "conflict", "record_position_outside_card_list"
    observed = observation.get("position")
    if not natural(observed) or observed != position:
        return "conflict", "reviewed_position_disagrees_with_record"

    prediction = observation.get("factor_tab_prediction")
    if prediction is None:
        if position == 0:
            return "unknown", "position_zero_without_representative_prediction"
    else:
        if not isinstance(prediction, dict):
            return "conflict", "invalid_representative_prediction"
        for field in ("icon", "character", "card"):
            value = prediction.get(field)
            if not natural(value) or not natural(trainee.get(field)) or value != trainee[field]:
                return "conflict", "representative_prediction_disagrees_with_record"
        rect, size = prediction.get("rect_xyxy"), prediction.get("image_wh")
        if (
            not isinstance(rect, list) or len(rect) != 4
            or not isinstance(size, list) or len(size) != 2
            or not all(map(natural, rect + size))
            or not (rect[0] < rect[2] <= size[0] and rect[1] < rect[3] <= size[1])
        ):
            return "conflict", "representative_prediction_geometry_invalid"

    if not nonempty(observation.get("basis")):
        return "unknown", "representative_review_basis_missing"
    return "confirmed", "reviewed_representative_read"


def prepare(args):
    factor_bytes = args.scout_input.read_bytes()
    dataset = json_object(factor_bytes, "Scout input")
    factor_hash = sha256(factor_bytes)
    input_hash = sha256(json.dumps(dataset, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode())
    list_bytes = args.card_list.read_bytes()
    card_list = json.loads(list_bytes)
    if not isinstance(card_list, list) or not card_list:
        raise ValueError("Expected a nonempty ordered card list")
    list_hash = sha256(list_bytes)
    lookup_hash = sha256(args.kr_lookup.read_bytes())

    baseline_bytes = args.baseline.read_bytes()
    baseline = json_object(baseline_bytes, "Evaluator baseline")
    context = {key: baseline.get(key) for key in ("event", "target", "style", "build")}
    if (
        baseline.get("input_hash") != input_hash or baseline.get("master_id") != "sha256:" + lookup_hash
        or baseline.get("unavailable") != [] or baseline.get("source") != "owned"
        or baseline.get("mode") != "direct_parent" or baseline.get("role_evidence_sha256") is not None
        or context != {"event": "kr-sapporo-loh-2600", "target": "106803", "style": "escape",
                       "build": "kitasan-falcon-30210"}
    ):
        raise ValueError("Expected the successful factor-only Evaluator baseline for this exact input and lookup")

    source_rows = unique_rows(dataset.get("entries"), "capture_key", nonempty)
    candidates = unique_rows(baseline.get("entries"), "candidate_id", nonempty)
    lineage = {}
    for candidate_id, row in candidates.items():
        source = row.get("source_evidence")
        key = source.get("capture_key") if isinstance(source, dict) else None
        if not nonempty(key) or key in lineage or candidate_id != "owned-instance:" + key:
            raise ValueError("Evaluator candidates do not uniquely bind to Scout captures")
        lineage[key] = candidate_id
    if not source_rows or lineage.keys() != source_rows.keys():
        raise ValueError("Evaluator candidate and Scout capture coverage differ")

    archive_bytes = args.records.read_bytes()
    archive_hash = sha256(archive_bytes)
    with zipfile.ZipFile(io.BytesIO(archive_bytes)) as archive:
        records = {}
        for member in archive.infolist():
            if member.is_dir():
                continue
            raw = archive.read(member)
            key = "sha256:" + sha256(raw)
            if key in records:
                raise ValueError("Duplicate capture record digest")
            records[key] = json_object(raw, "Archived capture record")
    if records.keys() != source_rows.keys():
        raise ValueError("Archive records must match the exact Scout capture keys")

    bridge_bytes = args.bridge.read_bytes()
    reviewed_bytes = args.observations.read_bytes()
    bridge = json_object(bridge_bytes, "Reviewed bridge")
    reviewed = json_object(reviewed_bytes, "Reviewed observations")
    if (
        bridge.get("schema_version") != 1 or reviewed.get("schema_version") != 1
        or bridge.get("card_list_sha256") != list_hash or bridge.get("kr_lookup_sha256") != lookup_hash
        or reviewed.get("card_list_sha256") != list_hash or reviewed.get("records_sha256") != archive_hash
    ):
        raise ValueError("Reviewed inputs do not match the pinned list, lookup and capture archive")
    mapping = unique_rows(bridge.get("entries"), "position", lambda n: natural(n) and n < len(card_list))
    observations = unique_rows(reviewed.get("entries"), "capture_key", nonempty)
    if observations.keys() - records.keys():
        raise ValueError("Reviewed observation references an unrelated capture")

    if any(Path(str(args.kr_lookup) + suffix).exists() for suffix in ("-wal", "-shm", "-journal")):
        raise ValueError("Expected a standalone KR lookup snapshot")
    confirmed, statuses = {}, []
    lookup_uri = args.kr_lookup.resolve().as_uri() + "?mode=ro&immutable=1"
    with closing(sqlite3.connect(lookup_uri, uri=True)) as db:
        for key, candidate_id in lineage.items():
            trainee = records[key].get("trainee")
            observation = observations.get(key)
            if not isinstance(trainee, dict):
                state, reason = "unknown", "representative_record_missing"
            elif observation is None:
                state, reason = "unknown", "representative_review_missing"
            else:
                state, reason = position_state(trainee, observation, len(card_list))
            if state == "confirmed":
                position = trainee["card"]
                match = mapping.get(position)
                if match is None:
                    state, reason = "unknown", "reviewed_card_mapping_missing"
                else:
                    card, chara = match.get("card_id"), match.get("chara_id")
                    actual = db.execute(
                        "SELECT c.chara_id, n.name_ko, p.outfit_name_ko FROM character_card c "
                        "JOIN character n USING (chara_id) JOIN card_profile p USING (card_id) WHERE c.card_id = ?",
                        (card if type(card) is int else None,),
                    ).fetchall()
                    if (
                        type(card) is not int or card <= 0 or type(chara) is not int or chara <= 0
                        or len(actual) != 1 or actual[0][0] != chara or not all(map(nonempty, actual[0][1:]))
                        or not nonempty(match.get("basis"))
                    ):
                        state, reason = "conflict", "bridge_disagrees_with_kr_lookup_or_has_no_basis"
                    else:
                        _, character_name, outfit_name = actual[0]
                        confirmed[candidate_id] = {
                            "card_id": card,
                            "chara_id": chara,
                            "character_name_ko": character_name,
                            "outfit_name_ko": outfit_name,
                            "basis": observation["basis"] + " / " + match["basis"],
                        }
            statuses.append({"capture_key": key, "candidate_id": candidate_id, "state": state, "reason": reason})
    if sha256(args.kr_lookup.read_bytes()) != lookup_hash:
        raise ValueError("KR lookup changed during preparation")
    evidence = {"schema_version": 1, **context,
                "direct_parent_identity": {"input_hash": input_hash, "candidates": confirmed}}
    receipt = {
        "schema_version": 1, "factor_dataset_sha256": factor_hash, "input_hash": input_hash,
        "evaluator_baseline_sha256": sha256(baseline_bytes), "card_list_sha256": list_hash,
        "kr_lookup_sha256": lookup_hash, "records_sha256": archive_hash,
        "bridge_sha256": sha256(bridge_bytes), "observations_sha256": sha256(reviewed_bytes),
        "entries": statuses,
    }
    output = {"role-evidence.json": evidence, "identity-receipt.json": receipt}
    args.output.mkdir(mode=0o700)
    for name, data in output.items():
        with (args.output / name).open("x", encoding="utf-8") as handle:
            json.dump(data, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
    print(f"Confirmed {len(confirmed)}/{len(statuses)} candidates; see identity-receipt.json for per-capture states.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for option in ("scout-input", "baseline", "records", "card-list", "kr-lookup", "bridge", "observations", "output"):
        parser.add_argument("--" + option, required=True, type=Path)
    try:
        prepare(parser.parse_args())
    except (ValueError, OSError, sqlite3.Error, zipfile.BadZipFile) as exc:
        print(f"Could not prepare representative identity: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
