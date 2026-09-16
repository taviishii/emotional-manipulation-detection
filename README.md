# Emotional Manipulation Detection in Human-AI Conversations

## Project Status

Phase 1 — Dataset audit: COMPLETE
Phase 2 — Label harmonisation: COMPLETE
Phase 3 — Initial processed dataset: COMPLETE
Phase 4 — Manual boundary-case annotation: NEXT

## Research Problem

This project studies emotional manipulation detection in human-AI
conversations: identifying when an AI's conversational behaviour is
emotionally manipulative, while explicitly distinguishing that from
general harmful behaviour, control, persuasion, emotional support,
validation, and companionship.

## Datasets Currently Available

- **AICompanionBench** — real, Reddit-sourced AI companion conversation
  excerpts with excerpt-level harm/behaviour labels (including Manipulation,
  Control, Safe).
- **ChatbotManip** — synthetic, LLM-generated conversations with an explicit
  manipulation-tactic taxonomy (7 techniques) at conversation level, plus
  human span-level manipulation ratings.
- **CompanionHarm** — real Replika conversation logs with utterance-level
  harm labels (including Manipulation, Control, No harmful behavior) and
  documented multi-annotator agreement.
- **CLAIM / LegalCon** — human-human courtroom dialogue with transcript-level
  manipulation labels; used only as a manipulation taxonomy/reference source,
  never as human-AI training data.
- **TEA-Dialog** — synthetic emotional-support scenarios with no manipulation
  annotation; used only as unlabelled reference material.
- **Illusions of Intimacy** — documentation only; no local dataset file
  exists, so it contributes no rows anywhere.

See `reports/dataset_audit.md` for the full audit and
`reports/label_harmonisation.md` for how each source's labels were mapped
(or deliberately not mapped) to the project's target concept.

## Why Multiple Datasets Are Being Used

No single available dataset combines all of: real human-AI conversation,
explicit manipulation labelling, and utterance-level granularity. Combining
sources lets the project draw on real manipulation-labelled AI dialogue
(AICompanionBench, CompanionHarm), a controlled manipulation-technique
taxonomy (ChatbotManip, CLAIM), and benign reference material (TEA-Dialog),
while keeping each source's provenance and label definition explicit rather
than assuming they are equivalent.

## Why Provenance Is Retained

Every row in the processed dataset (`data/processed/initial_unified_dataset.csv`)
keeps its `source_dataset`, original identifiers, `original_label`, and
`annotation_level` (span / turn / excerpt / conversation / unlabeled). The
datasets differ in annotation granularity, in whether they are real or
synthetic, and in how each source itself defines terms like "Manipulation"
or "Control" — collapsing that provenance would make it impossible to later
audit, correct, or selectively reuse any part of the dataset. See
`reports/data_lineage.md` for the exact source-to-row mapping.

## Why This Is an INITIAL Dataset, Not the Final One

Several categories are deliberately left as `RELATED_BEHAVIOUR` or
`UNLABELED` rather than forced into a manipulation/non-manipulation binary:
Control (AICompanionBench, CompanionHarm), strong persuasion (ChatbotManip),
and all of TEA-Dialog. These require manual review against
`reports/annotation_guidelines_v0.md` (itself marked Version 0, pending
review) before they can be confidently labelled. No train/dev/test split has
been created, and no model has been trained. See
`reports/initial_dataset_summary.md` for exact counts and
`reports/label_harmonisation.md` for the reasoning behind each decision.
