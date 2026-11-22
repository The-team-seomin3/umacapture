# Offline representative identity

The Recognition Team prepares a companion evidence file for the existing Sapporo
Engine 1 owned-parent reader, target `106803`. This tool uses reviewed capture
evidence and an approved card-position bridge. It does not generate a bridge or
prove which module the capture loaded. Keep the inputs and detailed receipt private.

1. Run the pinned Evaluator `rank-sapporo-parents` with the final Scout
   `--owned-input`, its `--factor-lookup`, and the bound master and mapping arguments.
   Save the successful JSON output without `--role-evidence`.
2. Prepare the reviewed inputs. The record ZIP must contain the exact JSON
   records corresponding to Scout's `sha256:…` capture keys. Use the actual
   ordered `character_card_info.json` bytes from the reviewed list. The bridge
   is a JSON object with `schema_version: 1`, `card_list_sha256`,
   `kr_lookup_sha256` and `entries` containing unique `position`, `card_id`,
   `chara_id` and review `basis`. Use SHA-256 of the exact file bytes in hex.
   A reviewed bridge can cover only part of the list.
3. Supply reviewed observations as a JSON object with `schema_version: 1`,
   `records_sha256` for the record ZIP, `card_list_sha256` and `entries`.
   Each row has a `capture_key`, stored `position` and review `basis` describing
   how the representative was bound to the record and list. A reviewer can
   report `state: "unknown"` or `"conflict"` with a reason in `basis`.
   For position 0, a confirmed observation also requires a normalized
   `factor_tab_prediction` from the reviewed representative `character` entry.
   Copy its `icon`, `character` (native `chara`) and `card`, and provide
   `rect_xyxy: [left, top, right, bottom]` and `image_wh: [width, height]`
   in original image pixels. An anchor miss leaves no such prediction and a
   default zero is withheld. A prediction mismatch or invalid rectangle is a
   conflict. The reviewer must associate the prediction with the record and
   source image before supplying it.
4. Prepare the sidecar in a new private directory.

   ```sh
   python3 -B tool/kr_representative_identity/prepare_role_evidence.py \
     --scout-input owned-parent-factors.json --baseline evaluator-baseline.json \
     --records captures.zip --card-list character_card_info.json \
     --kr-lookup master.sqlite3 --bridge bridge.json --observations observations.json \
     --output new-evidence
   ```

5. Rerun the **same Evaluator invocation** with
   `--role-evidence new-evidence/role-evidence.json`. Confirm the expected
   character restriction and unchanged factor terms and scores. Use
   `identity-receipt.json` to account for every candidate, including unknown and
   conflict rows. A successful preparation can produce partial identity coverage.
   A batch is fully identity-ready only after all intended identities are
   confirmed and the reader succeeds.

The tool reads existing artifacts offline and does not alter capture records,
factor rows, or the reviewed KR export. Recognition-time evidence retention and
archive verification are separate work under [#48](https://github.com/The-team-seomin3/umacapture/issues/48).

Run the focused tests with
`python3 -B -m unittest discover -s tool/kr_representative_identity -v`.
