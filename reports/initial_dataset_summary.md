# Initial Dataset Summary (Phase 3)

This summarises `data/processed/initial_unified_dataset.csv`, built by `src/build_initial_dataset.py` from `data/raw/`. Uncertain cases are deliberately kept as RELATED_BEHAVIOUR or UNLABELED rather than forced into a binary label. This is an INITIAL dataset, not the final research dataset, and contains no train/dev/test split.

## Rows produced per source (input vs. included vs. excluded)

| Source | Input records | Included | Excluded | MANIPULATIVE | NON_MANIPULATIVE | RELATED_BEHAVIOUR | UNLABELED |
|---|---|---|---|---|---|---|---|
| ai_companion_bench | 2123 | 641 | 1482 | 43 | 465 | 133 | 0 |
| chatbotmanip | 1465 | 1276 | see note | 450 | 152 | 144 | 530 |
| companion_harm | 7016 | 5185 | 1831 | 168 | 4893 | 124 | 0 |
| tea_dialog | 365 | 365 | 0 | 0 | 0 | 0 | 365 |

Note on chatbotmanip: 746 input conversations plus 719 input survey rows are two different record types (conversation-level and span-level) combined into one source; "excluded" is reported via the exclusion log below rather than a single input-minus-included subtraction, since conversation-level and span-level rows do not exclude one another.

## Excluded rows and reasons

| Reason | Count |
|---|---|
| ai_companion_bench:out_of_scope_category:a. Sexual Behavior | 1029 |
| ai_companion_bench:out_of_scope_category:b. Antisocial Behavior | 151 |
| ai_companion_bench:out_of_scope_category:c. Physical Aggression | 112 |
| ai_companion_bench:out_of_scope_category:d. Verbal Aggression | 79 |
| ai_companion_bench:out_of_scope_category:e. Substance Abuse | 77 |
| ai_companion_bench:out_of_scope_category:f. Self-harm & Suicide | 34 |
| chatbotmanip:survey_empty_highlighted_text | 189 |
| companion_harm_dev:out_of_scope_label:Antisocial behavior | 32 |
| companion_harm_dev:out_of_scope_label:Disregard | 35 |
| companion_harm_dev:out_of_scope_label:Hate speech | 9 |
| companion_harm_dev:out_of_scope_label:Mis/Disinformation | 50 |
| companion_harm_dev:out_of_scope_label:Physical aggression | 53 |
| companion_harm_dev:out_of_scope_label:Privacy violations | 10 |
| companion_harm_dev:out_of_scope_label:Self-harm & Suicide | 19 |
| companion_harm_dev:out_of_scope_label:Sexual misconduct | 104 |
| companion_harm_dev:out_of_scope_label:Substance abuse | 32 |
| companion_harm_dev:out_of_scope_label:Verbal abuse | 22 |
| companion_harm_test:out_of_scope_label:Antisocial behavior | 31 |
| companion_harm_test:out_of_scope_label:Disregard | 33 |
| companion_harm_test:out_of_scope_label:Hate speech | 8 |
| companion_harm_test:out_of_scope_label:Infidelity | 1 |
| companion_harm_test:out_of_scope_label:Mis/Disinformation | 50 |
| companion_harm_test:out_of_scope_label:Physical aggression | 54 |
| companion_harm_test:out_of_scope_label:Privacy violations | 9 |
| companion_harm_test:out_of_scope_label:Self-harm & Suicide | 17 |
| companion_harm_test:out_of_scope_label:Sexual misconduct | 107 |
| companion_harm_test:out_of_scope_label:Substance abuse | 34 |
| companion_harm_test:out_of_scope_label:Verbal abuse | 17 |
| companion_harm_train:out_of_scope_label:Antisocial behavior | 87 |
| companion_harm_train:out_of_scope_label:Disregard | 102 |
| companion_harm_train:out_of_scope_label:Hate speech | 26 |
| companion_harm_train:out_of_scope_label:Infidelity | 8 |
| companion_harm_train:out_of_scope_label:Mis/Disinformation | 141 |
| companion_harm_train:out_of_scope_label:Physical aggression | 170 |
| companion_harm_train:out_of_scope_label:Privacy violations | 28 |
| companion_harm_train:out_of_scope_label:Self-harm & Suicide | 48 |
| companion_harm_train:out_of_scope_label:Sexual misconduct | 352 |
| companion_harm_train:out_of_scope_label:Substance abuse | 94 |
| companion_harm_train:out_of_scope_label:Verbal abuse | 48 |

## Manipulation technique counts (non-empty `technique` field)

| Technique | Count |
|---|---|
| Peer Pressure | 67 |
| Guilt-Tripping | 66 |
| Gaslighting | 66 |
| Negging | 65 |
| Fear Enhancement | 64 |
| Reciprocity Pressure | 64 |
| Emotional Blackmail | 58 |

## Annotation-level counts

| annotation_level | Count |
|---|---|
| turn | 5185 |
| conversation | 746 |
| excerpt | 641 |
| span | 530 |
| unlabeled | 365 |

## Real vs. synthetic counts

| real_or_synthetic | Count |
|---|---|
| real | 5826 |
| synthetic | 1641 |

## Target label totals (whole unified dataset)

| target_label | Count |
|---|---|
| MANIPULATIVE | 661 |
| NON_MANIPULATIVE | 5510 |
| RELATED_BEHAVIOUR | 401 |
| UNLABELED | 895 |

## Data quality check results

- Missing/empty `text`: 0
- Full-row duplicates: 0
- Duplicate (source_dataset, conversation_id, turn_id) combinations: 0
- Unexpected target_label values: none
- Unexpected source_dataset values: none
- Unexpected annotation_level values: none
- Labelled rows (target_label != UNLABELED) missing an original_label: 0

No problems found above were auto-fixed; any non-zero count is reported here for manual review, not silently corrected.