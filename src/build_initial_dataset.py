"""
Phase 3 — build the INITIAL, TRACEABLE processed dataset for the
Emotional Manipulation Detection project.

Reads ONLY from data/raw/. Never modifies, deletes, or overwrites any raw
file. Writes:

    data/processed/initial_unified_dataset.csv      (human-AI sources only)
    data/processed/claim_manipulation_reference.csv (CLAIM, reference only)

    reports/initial_dataset_summary.md
    reports/data_lineage.md
    reports/initial_dataset_preview.md

This is NOT the final research dataset: uncertain cases are deliberately
left as RELATED_BEHAVIOUR or UNLABELED rather than forced into a binary
manipulation label, and no train/dev/test split is created here.

Run:
    python src/build_initial_dataset.py
"""

from __future__ import annotations

import csv
import json
import re
import sys
from collections import Counter
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
PROCESSED = ROOT / "data" / "processed"
REPORTS = ROOT / "reports"

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except AttributeError:
    pass

# --------------------------------------------------------------------------
# Controlled vocabularies (enforced, never extended silently)
# --------------------------------------------------------------------------

TARGET_LABELS = {"MANIPULATIVE", "NON_MANIPULATIVE", "RELATED_BEHAVIOUR", "UNLABELED"}
ANNOTATION_LEVELS = {"span", "turn", "excerpt", "conversation", "unlabeled"}
EXPECTED_SOURCES = {
    "ai_companion_bench",
    "chatbotmanip",
    "companion_harm_train",
    "companion_harm_dev",
    "companion_harm_test",
    "tea_dialog",
}

COLUMNS = [
    "conversation_id",
    "turn_id",
    "speaker",
    "context",
    "text",
    "target_label",
    "technique",
    "source_dataset",
    "original_label",
    "original_label_definition",
    "annotation_level",
    "annotator_count",
    "agreement",
    "real_or_synthetic",
]


def row(**kwargs) -> dict:
    r = {c: "" for c in COLUMNS}
    for k, v in kwargs.items():
        if k not in COLUMNS:
            raise KeyError(f"'{k}' is not part of the unified schema")
        r[k] = "" if v is None else v
    return r


def load_csv(path: Path) -> list[dict]:
    with open(path, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def load_json(path: Path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


# --------------------------------------------------------------------------
# AICompanionBench -> excerpt-level rows
# --------------------------------------------------------------------------

LABEL_MAP_ACB = {
    "h. Manipulation": "MANIPULATIVE",
    "i. Safe": "NON_MANIPULATIVE",
    "g. Control": "RELATED_BEHAVIOUR",
}

ACB_LABEL_DEF = {
    "h. Manipulation": (
        "AICompanionBench excerpt-level category 'h. Manipulation': Reddit-sourced "
        "AI companion excerpt labelled as manipulative behaviour, distinct from "
        "Control/Safe/other harm categories in the source's own scheme."
    ),
    "i. Safe": (
        "AICompanionBench excerpt-level category 'i. Safe': excerpt labelled as "
        "non-harmful/benign by the source."
    ),
    "g. Control": (
        "AICompanionBench excerpt-level category 'g. Control': excerpt labelled as "
        "controlling/dominance-oriented behaviour, kept separate from Manipulation "
        "by the source's own annotation scheme. NOT auto-converted to MANIPULATIVE."
    ),
}


def _acb_speaker(text: str) -> str:
    has_user = bool(re.search(r"(?:^|\n)\s*User\s*:", text or ""))
    has_ai = bool(re.search(r"(?:^|\n)\s*AI\s*:", text or ""))
    if has_user and has_ai:
        return "MIXED"
    if has_ai:
        return "AI"
    if has_user:
        return "USER"
    return "UNKNOWN"


def build_ai_companion_bench() -> tuple[list[dict], Counter]:
    path = RAW / "ai_companion_bench" / "AICompanionBench.csv"
    records = load_csv(path)
    rows, excluded = [], Counter()

    for r in records:
        cat = r.get("Category_Final", "")
        if cat not in LABEL_MAP_ACB:
            excluded[f"ai_companion_bench:out_of_scope_category:{cat}"] += 1
            continue
        text = r.get("conversation", "") or ""
        rows.append(
            row(
                conversation_id=r.get("id", ""),
                turn_id=r.get("row_id", ""),
                speaker=_acb_speaker(text),
                context="",  # history (if any) is embedded verbatim inside 'text'
                text=text,
                target_label=LABEL_MAP_ACB[cat],
                technique="",  # no technique sub-typing exists locally
                source_dataset="ai_companion_bench",
                original_label=cat,
                original_label_definition=ACB_LABEL_DEF[cat],
                annotation_level="excerpt",
                annotator_count="",  # not documented locally
                agreement="",  # not documented locally
                real_or_synthetic="real",
            )
        )
    return rows, excluded


# --------------------------------------------------------------------------
# ChatbotManip -> conversation-level (generation condition) + span-level
# (human survey) rows, kept explicitly distinct via annotation_level.
# --------------------------------------------------------------------------

MANIPULATION_TECHNIQUES = {
    "Gaslighting",
    "Guilt-Tripping",
    "Peer Pressure",
    "Negging",
    "Fear Enhancement",
    "Reciprocity Pressure",
    "Emotional Blackmail",
}

SURVEY_SCORE_FIELDS = [
    "manipulative_general",
    "manipulative_gaslighting",
    "manipulative_guilt_tripping",
    "manipulative_peer_pressure",
    "manipulative_negging",
    "manipulative_fear_enhancement",
    "manipulative_reciprocity",
    "manipulative_emotional_blackmail",
    "manipulative_charming",
    "manipulative_emotion_induction",
    "manipulative_misrepresenting",
]


def _cm_speaker_for_conversation() -> str:
    return "MIXED"  # a full multi-turn USER/AGENT dialogue, not one speaker


def build_chatbotmanip() -> tuple[list[dict], Counter]:
    conv_path = RAW / "chatbotmanip" / "conversations.json"
    surv_path = RAW / "chatbotmanip" / "survey_responses.json"
    conv = load_json(conv_path)
    surv = load_json(surv_path)
    conv_by_uuid = {c.get("uuid"): c for c in conv}

    rows, excluded = [], Counter()

    for c in conv:
        mtype = c.get("manipulation_type")
        pstrength = c.get("persuasion_strength")
        text = c.get("chat_completion") or ""

        if mtype in MANIPULATION_TECHNIQUES:
            target = "MANIPULATIVE"
            technique = mtype
            definition = (
                f"ChatbotManip conversation generated under an explicit "
                f"'{mtype}' manipulation-tactic prompt condition (ground truth "
                f"by construction; corroborated where available by human span "
                f"ratings in survey_responses.json)."
            )
            original_label = f"manipulation_type={mtype}"
        elif pstrength == "helpful":
            target = "NON_MANIPULATIVE"
            technique = ""
            definition = (
                "ChatbotManip conversation generated under a 'helpful' "
                "persuasion_strength condition, with no manipulation tactic "
                "tagged (ground truth by construction, not independently "
                "human-verified as manipulation-free)."
            )
            original_label = "persuasion_strength=helpful"
        elif pstrength == "strong":
            target = "RELATED_BEHAVIOUR"
            technique = ""
            definition = (
                "ChatbotManip conversation generated under a 'strong' "
                "persuasion_strength condition, with no manipulation tactic "
                "tagged. Strong persuasion is deliberately NOT treated as "
                "manipulation without manual review (ground truth by "
                "construction)."
            )
            original_label = "persuasion_strength=strong"
        else:
            excluded[f"chatbotmanip:unexpected_condition:{mtype}/{pstrength}"] += 1
            continue

        rows.append(
            row(
                conversation_id=c.get("uuid", ""),
                turn_id=c.get("_id", ""),
                speaker=_cm_speaker_for_conversation(),
                context="",  # full history is embedded verbatim inside 'text'
                text=text,
                target_label=target,
                technique=technique,
                source_dataset="chatbotmanip",
                original_label=original_label,
                original_label_definition=definition,
                annotation_level="conversation",
                annotator_count="",  # generation condition, not human-annotated at this level
                agreement="",
                real_or_synthetic="synthetic",
            )
        )

    for s in surv:
        cu = s.get("conversation_uuid")
        matched = conv_by_uuid.get(cu)
        ht = s.get("highlighted_text") or ""

        if matched is None:
            excluded["chatbotmanip:survey_no_matching_conversation"] += 1
            continue
        if not ht.strip():
            excluded["chatbotmanip:survey_empty_highlighted_text"] += 1
            continue

        scores = {f: s.get(f) for f in SURVEY_SCORE_FIELDS if s.get(f) is not None}
        original_label = ";".join(f"{k}={v}" for k, v in scores.items())

        rows.append(
            row(
                conversation_id=cu,
                turn_id=s.get("_id", ""),
                speaker="MIXED",
                context="",  # span is drawn from the linked conversation_id's full text
                text=ht,
                target_label="UNLABELED",
                technique="",
                source_dataset="chatbotmanip",
                original_label=original_label,
                original_label_definition=(
                    "ChatbotManip human survey rating of a highlighted span within "
                    "the linked conversation_id. Raw manipulation sub-scale scores "
                    "(1-7 Likert-style) are preserved verbatim in original_label; "
                    "no validated threshold exists to convert these continuous "
                    "ratings into a categorical target_label, so target_label is "
                    "left UNLABELED rather than silently inferring MANIPULATIVE."
                ),
                annotation_level="span",
                annotator_count="1",  # this row = one rater's judgement of this span
                agreement="",  # no cross-rater aggregation performed here
                real_or_synthetic="synthetic",
            )
        )

    return rows, excluded


# --------------------------------------------------------------------------
# CompanionHarm -> utterance-level rows, per split (split kept only inside
# source_dataset for provenance; NOT reused as the project's final split).
# --------------------------------------------------------------------------

LABEL_MAP_CH = {
    "Manipulation": "MANIPULATIVE",
    "No harmful behavior": "NON_MANIPULATIVE",
    "Control": "RELATED_BEHAVIOUR",
}

CH_LABEL_DEF = {
    "Manipulation": (
        "CompanionHarm utterance-level harm category 'Manipulation': annotator-"
        "labelled harmful AI (Replika) behaviour classified as manipulation, "
        "distinct from Control and other harm categories (2-/3-way annotator "
        "agreement)."
    ),
    "No harmful behavior": (
        "CompanionHarm utterance-level label 'No harmful behavior': annotators "
        "found no harmful behaviour in this AI utterance (2-/3-way annotator "
        "agreement)."
    ),
    "Control": (
        "CompanionHarm utterance-level harm category 'Control': annotator-"
        "labelled controlling AI behaviour, kept separate from Manipulation by "
        "the source's own annotation scheme. NOT auto-converted to MANIPULATIVE."
    ),
}


def build_companion_harm() -> tuple[list[dict], Counter]:
    rows, excluded = [], Counter()
    for split in ("train", "dev", "test"):
        path = RAW / "companion_harm" / f"{split}.csv"
        records = load_csv(path)
        source_name = f"companion_harm_{split}"
        for r in records:
            label = r.get("label", "")
            if label not in LABEL_MAP_CH:
                excluded[f"{source_name}:out_of_scope_label:{label}"] += 1
                continue
            rows.append(
                row(
                    conversation_id=r.get("conversation_id", ""),
                    turn_id=r.get("utterance_id", ""),
                    speaker=r.get("speaker", ""),
                    context=r.get("context", ""),
                    text=r.get("current_line", ""),
                    target_label=LABEL_MAP_CH[label],
                    technique="",  # no technique sub-typing exists locally
                    source_dataset=source_name,
                    original_label=label,
                    original_label_definition=CH_LABEL_DEF[label],
                    annotation_level="turn",
                    annotator_count=r.get("annotator_count", ""),
                    agreement=r.get("agreement_type", ""),
                    real_or_synthetic="real",
                )
            )
    return rows, excluded


# --------------------------------------------------------------------------
# TEA-Dialog -> unlabelled conversation-level reference rows.
# No unique per-record id exists in the source, so conversation_id is
# synthesised from list position (stable/reproducible) and documented.
# --------------------------------------------------------------------------


def build_tea_dialog() -> tuple[list[dict], Counter]:
    path = RAW / "tea_dialog" / "TEA-Dialog.json"
    data = load_json(path)
    rows: list[dict] = []

    for idx, d in enumerate(data):
        msgs = d.get("content_messages") or []
        text = "\n".join(f"{m.get('role','').upper()}: {m.get('content','')}" for m in msgs)
        synthetic_id = f"tea_{idx:04d}"
        rows.append(
            row(
                conversation_id=synthetic_id,
                turn_id="FULL_CONVERSATION",
                speaker="MIXED",
                context="",
                text=text,
                target_label="UNLABELED",
                technique="",
                source_dataset="tea_dialog",
                original_label="",  # no manipulation/harm label exists in the source
                original_label_definition=(
                    f"TEA-Dialog record (source position {idx}, task_id="
                    f"{d.get('task_id')}, source_file={d.get('source_file')}): "
                    f"no manipulation or harm annotation exists in the source; "
                    f"included as unlabelled emotional-support reference material "
                    f"only. conversation_id is a synthesised index-based id since "
                    f"the source provides no unique per-record identifier "
                    f"(task_id and source_file both repeat across records)."
                ),
                annotation_level="unlabeled",
                annotator_count="",
                agreement="",
                real_or_synthetic="synthetic",
            )
        )
    return rows, Counter()


# --------------------------------------------------------------------------
# CLAIM / LegalCon -> separate reference-only file, NOT part of the
# human-AI unified dataset.
# --------------------------------------------------------------------------


def build_claim_reference() -> pd.DataFrame:
    path = RAW / "claim" / "LegalCon-Dataset.csv"
    records = load_csv(path)
    out = []
    for r in records:
        out.append(
            {
                "id": r.get("IDs", ""),
                "dialogue": r.get("Dialogue", ""),
                "manipulative": r.get("Manipulative", ""),
                "manipulation_techniques": r.get("Manipulation Techniques", ""),
                "primary_manipulator": r.get("Primary Manipulator", ""),
                "source_dataset": "claim_legalcon",
                "domain_note": (
                    "Human-human courtroom dialogue (e.g. televised small-claims "
                    "court transcripts). NOT a human-AI conversation. Included "
                    "for manipulation taxonomy/technique reference only; must "
                    "not be merged into the human-AI training or evaluation set."
                ),
            }
        )
    return pd.DataFrame(out)


# --------------------------------------------------------------------------
# Data quality checks (report-only; never auto-fixed)
# --------------------------------------------------------------------------


def run_quality_checks(df: pd.DataFrame) -> dict:
    checks: dict = {}

    checks["missing_text"] = int((df["text"].fillna("").str.strip() == "").sum())
    checks["full_row_duplicates"] = int(df.duplicated().sum())

    id_cols = ["source_dataset", "conversation_id", "turn_id"]
    checks["duplicate_source_conversation_turn_id"] = int(df.duplicated(subset=id_cols).sum())

    checks["unexpected_target_labels"] = sorted(set(df["target_label"]) - TARGET_LABELS)
    checks["unexpected_source_names"] = sorted(set(df["source_dataset"]) - EXPECTED_SOURCES)
    checks["unexpected_annotation_levels"] = sorted(set(df["annotation_level"]) - ANNOTATION_LEVELS)

    labelled = df[df["target_label"] != "UNLABELED"]
    checks["labelled_rows_missing_original_label"] = int(
        (labelled["original_label"].fillna("").str.strip() == "").sum()
    )

    checks["target_label_distribution"] = df["target_label"].value_counts().to_dict()
    checks["source_distribution"] = df["source_dataset"].value_counts().to_dict()

    return checks


# --------------------------------------------------------------------------
# Verification (Section 11 of the phase instructions)
# --------------------------------------------------------------------------


def run_verification(df: pd.DataFrame, claim_df: pd.DataFrame, exclusions: Counter) -> list[tuple[str, bool]]:
    results = []

    def check(name, cond):
        results.append((name, bool(cond)))

    raw_files = list(RAW.rglob("*"))
    raw_file_count = sum(1 for p in raw_files if p.is_file())
    check("raw file count unchanged (9 files)", raw_file_count == 9)

    check("every row has non-empty source_dataset", (df["source_dataset"].str.strip() != "").all())
    labelled = df[df["target_label"] != "UNLABELED"]
    check(
        "every labelled row has a non-empty original_label",
        (labelled["original_label"].fillna("").str.strip() != "").all(),
    )
    check("target_label uses only the 4 allowed values", set(df["target_label"]) <= TARGET_LABELS)
    check("claim_legalcon is absent from the unified dataset", "claim_legalcon" not in set(df["source_dataset"]))
    check("illusions_of_intimacy contributes zero rows", "illusions_of_intimacy" not in set(df["source_dataset"]))
    check(
        "all tea_dialog rows are UNLABELED",
        (df.loc[df["source_dataset"] == "tea_dialog", "target_label"] == "UNLABELED").all(),
    )
    control_mask = df["original_label"].isin(["g. Control", "Control"])
    check(
        "all Control-labelled rows are RELATED_BEHAVIOUR",
        (df.loc[control_mask, "target_label"] == "RELATED_BEHAVIOUR").all(),
    )
    strong_mask = df["original_label"] == "persuasion_strength=strong"
    check(
        "all strong-persuasion rows are RELATED_BEHAVIOUR",
        (df.loc[strong_mask, "target_label"] == "RELATED_BEHAVIOUR").all(),
    )
    check("claim reference file has one row per source record (1038)", len(claim_df) == 1038)

    return results


# --------------------------------------------------------------------------
# Reporting
# --------------------------------------------------------------------------


def write_summary_report(df: pd.DataFrame, exclusions: Counter, quality: dict) -> None:
    def counts_for(source_prefix_set):
        sub = df[df["source_dataset"].isin(source_prefix_set)]
        return sub["target_label"].value_counts().to_dict()

    lines = []
    lines.append("# Initial Dataset Summary (Phase 3)\n")
    lines.append(
        "This summarises `data/processed/initial_unified_dataset.csv`, built by "
        "`src/build_initial_dataset.py` from `data/raw/`. Uncertain cases are "
        "deliberately kept as RELATED_BEHAVIOUR or UNLABELED rather than forced "
        "into a binary label. This is an INITIAL dataset, not the final research "
        "dataset, and contains no train/dev/test split.\n"
    )

    lines.append("## Rows produced per source (input vs. included vs. excluded)\n")
    source_groups = {
        "ai_companion_bench": ["ai_companion_bench"],
        "chatbotmanip": ["chatbotmanip"],
        "companion_harm": ["companion_harm_train", "companion_harm_dev", "companion_harm_test"],
        "tea_dialog": ["tea_dialog"],
    }
    input_counts = {
        "ai_companion_bench": 2123,
        "chatbotmanip": 746 + 719,
        "companion_harm": 4222 + 1403 + 1391,
        "tea_dialog": 365,
    }

    header = (
        "| Source | Input records | Included | Excluded | MANIPULATIVE | "
        "NON_MANIPULATIVE | RELATED_BEHAVIOUR | UNLABELED |"
    )
    sep = "|---|---|---|---|---|---|---|---|"
    lines.append(header)
    lines.append(sep)
    for name, srcs in source_groups.items():
        sub = df[df["source_dataset"].isin(srcs)]
        included = len(sub)
        input_n = input_counts[name]
        excl_n = input_n - included if name != "chatbotmanip" else "see note"
        c = sub["target_label"].value_counts()
        lines.append(
            f"| {name} | {input_n} | {included} | {excl_n} | "
            f"{c.get('MANIPULATIVE', 0)} | {c.get('NON_MANIPULATIVE', 0)} | "
            f"{c.get('RELATED_BEHAVIOUR', 0)} | {c.get('UNLABELED', 0)} |"
        )
    lines.append(
        "\nNote on chatbotmanip: 746 input conversations plus 719 input survey "
        "rows are two different record types (conversation-level and span-level) "
        "combined into one source; \"excluded\" is reported via the exclusion "
        "log below rather than a single input-minus-included subtraction, since "
        "conversation-level and span-level rows do not exclude one another.\n"
    )

    lines.append("## Excluded rows and reasons\n")
    if exclusions:
        lines.append("| Reason | Count |")
        lines.append("|---|---|")
        for reason, n in sorted(exclusions.items()):
            lines.append(f"| {reason} | {n} |")
    else:
        lines.append("No exclusions recorded.")
    lines.append("")

    lines.append("## Manipulation technique counts (non-empty `technique` field)\n")
    tech_counts = df.loc[df["technique"].str.strip() != "", "technique"].value_counts()
    lines.append("| Technique | Count |")
    lines.append("|---|---|")
    for t, n in tech_counts.items():
        lines.append(f"| {t} | {n} |")
    lines.append("")

    lines.append("## Annotation-level counts\n")
    lines.append("| annotation_level | Count |")
    lines.append("|---|---|")
    for lvl, n in df["annotation_level"].value_counts().items():
        lines.append(f"| {lvl} | {n} |")
    lines.append("")

    lines.append("## Real vs. synthetic counts\n")
    lines.append("| real_or_synthetic | Count |")
    lines.append("|---|---|")
    for k, n in df["real_or_synthetic"].value_counts().items():
        lines.append(f"| {k} | {n} |")
    lines.append("")

    lines.append("## Target label totals (whole unified dataset)\n")
    lines.append("| target_label | Count |")
    lines.append("|---|---|")
    for k in ["MANIPULATIVE", "NON_MANIPULATIVE", "RELATED_BEHAVIOUR", "UNLABELED"]:
        lines.append(f"| {k} | {int((df['target_label'] == k).sum())} |")
    lines.append("")

    lines.append("## Data quality check results\n")
    lines.append(f"- Missing/empty `text`: {quality['missing_text']}")
    lines.append(f"- Full-row duplicates: {quality['full_row_duplicates']}")
    lines.append(
        f"- Duplicate (source_dataset, conversation_id, turn_id) combinations: "
        f"{quality['duplicate_source_conversation_turn_id']}"
    )
    lines.append(f"- Unexpected target_label values: {quality['unexpected_target_labels'] or 'none'}")
    lines.append(f"- Unexpected source_dataset values: {quality['unexpected_source_names'] or 'none'}")
    lines.append(f"- Unexpected annotation_level values: {quality['unexpected_annotation_levels'] or 'none'}")
    lines.append(
        f"- Labelled rows (target_label != UNLABELED) missing an original_label: "
        f"{quality['labelled_rows_missing_original_label']}"
    )
    lines.append("")
    lines.append(
        "No problems found above were auto-fixed; any non-zero count is reported "
        "here for manual review, not silently corrected."
    )

    REPORTS.mkdir(parents=True, exist_ok=True)
    (REPORTS / "initial_dataset_summary.md").write_text("\n".join(lines), encoding="utf-8")


def write_lineage_report(df: pd.DataFrame) -> None:
    text = """# Data Lineage (Phase 3)

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
"""
    (REPORTS / "data_lineage.md").write_text(text, encoding="utf-8")


def write_preview_report(df: pd.DataFrame) -> None:
    def truncate(t, n=220):
        t = str(t).replace("\n", " ")
        return t if len(t) <= n else t[:n] + "..."

    lines = ["# Initial Dataset Preview (Phase 3)\n"]
    lines.append(
        "Approximately 5 representative rows per included source, for human "
        "inspection. Text is truncated to ~220 characters for readability; the "
        "full text is in `data/processed/initial_unified_dataset.csv`. No "
        "Reddit author metadata or other identifying fields are shown (none "
        "are part of the unified schema).\n"
    )

    groups = {
        "ai_companion_bench": ["ai_companion_bench"],
        "chatbotmanip (conversation-level)": None,  # handled specially below
        "chatbotmanip (span-level)": None,
        "companion_harm": ["companion_harm_train", "companion_harm_dev", "companion_harm_test"],
        "tea_dialog": ["tea_dialog"],
    }

    def pick_sample(sub: pd.DataFrame, n: int = 5) -> pd.DataFrame:
        sub = sub.reset_index(drop=True)
        picked: list[int] = []
        for lbl in sub["target_label"].unique():
            idx = sub.index[sub["target_label"] == lbl]
            if len(idx) and idx[0] not in picked:
                picked.append(idx[0])
            if len(picked) >= n:
                break
        for i in sub.index:
            if len(picked) >= n:
                break
            if i not in picked:
                picked.append(i)
        return sub.loc[picked[:n]]

    def emit(title, sub):
        lines.append(f"## {title}\n")
        if sub.empty:
            lines.append("_No rows available._\n")
            return
        sample = pick_sample(sub, 5)
        for _, r in sample.iterrows():
            lines.append(f"- **source**: {r['source_dataset']}")
            lines.append(f"  **speaker**: {r['speaker']}")
            lines.append(f"  **text**: {truncate(r['text'])}")
            lines.append(f"  **original_label**: {r['original_label']}")
            lines.append(f"  **target_label**: {r['target_label']}")
            lines.append(f"  **technique**: {r['technique'] or '(none)'}")
            lines.append(f"  **annotation_level**: {r['annotation_level']}")
            lines.append("")

    emit("AICompanionBench", df[df["source_dataset"] == "ai_companion_bench"])
    emit(
        "ChatbotManip — conversation-level",
        df[(df["source_dataset"] == "chatbotmanip") & (df["annotation_level"] == "conversation")],
    )
    emit(
        "ChatbotManip — span-level",
        df[(df["source_dataset"] == "chatbotmanip") & (df["annotation_level"] == "span")],
    )
    emit(
        "CompanionHarm",
        df[df["source_dataset"].isin(["companion_harm_train", "companion_harm_dev", "companion_harm_test"])],
    )
    emit("TEA-Dialog", df[df["source_dataset"] == "tea_dialog"])

    (REPORTS / "initial_dataset_preview.md").write_text("\n".join(lines), encoding="utf-8")


def write_readme() -> None:
    text = """# Emotional Manipulation Detection in Human-AI Conversations

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
"""
    (ROOT / "README.md").write_text(text, encoding="utf-8")


# --------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------


def main() -> None:
    PROCESSED.mkdir(parents=True, exist_ok=True)
    REPORTS.mkdir(parents=True, exist_ok=True)

    all_rows: list[dict] = []
    all_exclusions: Counter = Counter()

    for builder in (build_ai_companion_bench, build_chatbotmanip, build_companion_harm, build_tea_dialog):
        rows, excl = builder()
        all_rows.extend(rows)
        all_exclusions.update(excl)

    df = pd.DataFrame(all_rows, columns=COLUMNS)
    df.to_csv(PROCESSED / "initial_unified_dataset.csv", index=False, encoding="utf-8")

    claim_df = build_claim_reference()
    claim_df.to_csv(PROCESSED / "claim_manipulation_reference.csv", index=False, encoding="utf-8")

    quality = run_quality_checks(df)
    write_summary_report(df, all_exclusions, quality)
    write_lineage_report(df)
    write_preview_report(df)
    write_readme()

    verification = run_verification(df, claim_df, all_exclusions)

    print("=" * 78)
    print("PHASE 3 BUILD - initial_unified_dataset.csv")
    print("=" * 78)
    print(f"Total processed rows: {len(df)}")
    print("Rows by source:")
    for src, n in df["source_dataset"].value_counts().items():
        print(f"  {src}: {n}")
    print("Target label counts:")
    for k in ["MANIPULATIVE", "NON_MANIPULATIVE", "RELATED_BEHAVIOUR", "UNLABELED"]:
        print(f"  {k}: {int((df['target_label'] == k).sum())}")
    print(f"Techniques represented: {sorted(t for t in df['technique'].unique() if t)}")
    print(f"claim_manipulation_reference.csv rows: {len(claim_df)}")

    print("\nData quality checks:")
    for k, v in quality.items():
        print(f"  {k}: {v}")

    print("\nVerification:")
    all_pass = True
    for name, ok in verification:
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}")
        all_pass = all_pass and ok
    if not all_pass:
        print("\nWARNING: one or more verification checks FAILED. See above.")

    print("\nReports written to reports/: initial_dataset_summary.md, "
          "data_lineage.md, initial_dataset_preview.md")
    print("README.md written at project root.")


if __name__ == "__main__":
    main()
