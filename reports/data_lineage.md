# Data Lineage (Phase 3)

How every row in `data/processed/initial_unified_dataset.csv` traces back to
`data/raw/`. Produced by `src/build_initial_dataset.py`. No raw file is
modified by this process.

## ai_companion_bench

- Raw file: `data/raw/ai_companion_bench/AICompanionBench.csv`
- One processed row per raw CSV row where `Category_Final` is one of
  `h. Manipulation`, `i. Safe`, `g. Control` (other 6 harm categories excluded
  from this manipulation-focused dataset; see `initial_dataset_summary.md`
  for exact exclusion counts).
- `conversation_id` = raw `id` (the source Reddit **post** id; NOT unique per
  processed row, since one post can contribute several excerpts).
- `turn_id` = raw `row_id` (unique per processed row; use conversation_id +
  turn_id together to find the exact source row).
- `speaker` is derived (not copied) by scanning the excerpt text for
  `User:`/`AI:` prefixes: `MIXED` if both appear, `AI` or `USER` if only one
  appears, `UNKNOWN` if neither is detected.
- `context` is left empty: any conversational history is already embedded
  verbatim inside `text` (the raw `conversation` field is excerpt-level, not
  split into a separate history field in the source).
- `annotator_count` / `agreement` are left empty: not documented in this
  source.
- Reddit `author`, `author_fullname`, `author_flair_text`, and
  `media_metadata` are deliberately NOT copied into the processed dataset
  (privacy).

## chatbotmanip

Two structurally different record types from two raw files, kept distinct via
`annotation_level`:

- **Conversation-level** (`annotation_level = conversation`): one processed
  row per record in `data/raw/chatbotmanip/conversations.json` (all 746).
  `conversation_id` = raw `uuid`; `turn_id` = raw `_id` (unique within this
  file). `target_label`/`technique` are derived from the generation-time
  fields `manipulation_type` (7 named techniques -> MANIPULATIVE, technique
  preserved) and `persuasion_strength` (`helpful` -> NON_MANIPULATIVE,
  `strong` -> RELATED_BEHAVIOUR). Every one of the 746 conversations has
  exactly one of these two fields populated, so every conversation yields
  exactly one conversation-level row.
- **Span-level** (`annotation_level = span`): one processed row per record in
  `data/raw/chatbotmanip/survey_responses.json` that (a) has a matching
  `conversation_uuid` in `conversations.json` and (b) has a non-empty
  `highlighted_text`. `conversation_id` = raw `conversation_uuid` (links back
  to the conversation-level row for the same conversation); `turn_id` = raw
  `_id` from the survey file (a *different* id namespace from the
  conversation-level `_id` — the two are only unique within their own file,
  so `annotation_level` must be used together with `turn_id` to know which
  raw file a given `_id` belongs to). `target_label = UNLABELED` for all span
  rows: the raw manipulation sub-scale ratings (1-7 Likert-style) are
  preserved verbatim in `original_label`, but no validated threshold exists
  to convert a continuous rating into a categorical label, so none is
  invented here.
- 0 survey rows were found with no matching conversation (all 719 reference a
  valid `conversation_uuid`); 189 were excluded for having an empty
  `highlighted_text` (logged in `initial_dataset_summary.md`).

## companion_harm

- Raw files: `data/raw/companion_harm/{train,dev,test}.csv`.
- One processed row per raw row where `label` is one of `Manipulation`,
  `No harmful behavior`, `Control` (the other 11 harm categories are
  excluded from this manipulation-focused dataset).
- `conversation_id` = raw `conversation_id`; `turn_id` = raw `utterance_id`
  (both already unique in the source; no synthetic id needed).
- `speaker`, `context`, `annotator_count`, `agreement` are copied directly
  from the corresponding raw columns (`speaker`, `context`,
  `annotator_count`, `agreement_type`).
- `source_dataset` is set to `companion_harm_train` / `companion_harm_dev` /
  `companion_harm_test` specifically so the ORIGINAL source split can always
  be recovered. **This is provenance only — it is explicitly not reused as
  the project's final train/dev/test split.**

## tea_dialog

- Raw file: `data/raw/tea_dialog/TEA-Dialog.json`.
- One processed row per raw record (all 365), always `target_label =
  UNLABELED` and `annotation_level = unlabeled`, since no manipulation/harm
  annotation exists in the source at any level.
- The source provides no reliable unique per-record identifier: `task_id`
  has only 81 distinct values across 365 records and `source_file` only 9,
  so neither can serve as `conversation_id`. `conversation_id` is instead a
  synthesised, deterministic `tea_<index>` based on the record's position in
  the source JSON array (stable across re-runs because JSON array order is
  fixed). The original `task_id` and `source_file` are preserved instead
  inside `original_label_definition` for additional traceability context.
- `text` is a light, non-lossy reconstruction: the `content_messages` list of
  `{role, content}` turns is joined into one string as `ROLE: content` lines,
  in original order. No wording is changed.

## claim_legalcon (separate file, not part of the unified dataset)

- Raw file: `data/raw/claim/LegalCon-Dataset.csv`.
- Written to `data/processed/claim_manipulation_reference.csv`, one row per
  raw row (all 1,038), with `id` = raw `IDs`, and `dialogue`, `manipulative`,
  `manipulation_techniques`, `primary_manipulator` copied directly from the
  corresponding raw columns.
- Every row carries a `domain_note` stating this is human-human courtroom
  dialogue, not a human-AI conversation, and is for manipulation
  taxonomy/reference use only.
- **This file is never merged into `initial_unified_dataset.csv`.**

## illusions_of_intimacy

- No raw dataset file exists (`README.txt` only, per the Phase 1 audit).
- Contributes 0 rows to any processed file, by construction — there is no
  builder function for this source.
