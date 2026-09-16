"""
Phase 1 dataset audit for the Emotional Manipulation Detection project.

Reads the files under data/raw/ and computes inventory, structure, text,
label, linkage, and data-quality statistics. This script is READ-ONLY:
it does not modify, rename, move, merge, relabel, or delete any raw file.

Run:
    python src/dataset_audit.py

Output:
    - A human-readable audit printed to stdout.
    - A machine-readable copy of every computed statistic written to
      reports/audit_results.json (created if it does not exist).

Every number in reports/dataset_audit.md should be traceable back to a
value produced by this script.
"""

from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
REPORTS = ROOT / "reports"

# Windows consoles default to cp1252; the raw text contains emoji and
# other non-cp1252 characters, so force utf-8 stdout instead of crashing.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except AttributeError:
    pass


# --------------------------------------------------------------------------
# Generic helpers
# --------------------------------------------------------------------------

def pct(n, total):
    if not total:
        return None
    return round(100 * n / total, 2)


def to_native(obj):
    """Recursively convert numpy/pandas scalar types to plain Python types
    so the result tree is JSON-serialisable."""
    if isinstance(obj, dict):
        return {str(k): to_native(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [to_native(v) for v in obj]
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        return None if np.isnan(obj) else float(obj)
    if isinstance(obj, (np.bool_,)):
        return bool(obj)
    if isinstance(obj, float) and np.isnan(obj):
        return None
    if isinstance(obj, pd.Timestamp):
        return obj.isoformat()
    return obj


def read_csv_safely(path: Path) -> pd.DataFrame:
    # utf-8-sig strips a BOM if present (AICompanionBench.csv has one on
    # its header). Multi-line quoted fields are handled natively by pandas.
    return pd.read_csv(path, encoding="utf-8-sig", keep_default_na=True, dtype=str)


def load_json(path: Path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def generic_frame_audit(df: pd.DataFrame, id_col: str | None = None) -> dict:
    n = len(df)
    out = {
        "n_rows": n,
        "n_columns": df.shape[1],
        "columns": list(df.columns),
        "dtypes": {c: str(t) for c, t in df.dtypes.items()},
        "missing_counts": {c: int(df[c].isna().sum()) for c in df.columns},
        "missing_pct": {c: pct(int(df[c].isna().sum()), n) for c in df.columns},
        "full_row_duplicates": int(df.duplicated().sum()),
    }
    if id_col and id_col in df.columns:
        dup_id_rows = int(df.duplicated(subset=[id_col]).sum())
        out["id_column"] = id_col
        out["unique_id_count"] = int(df[id_col].nunique(dropna=True))
        out["rows_with_repeated_id"] = dup_id_rows
    return out


def text_stats(series: pd.Series) -> dict:
    s = series.fillna("").astype(str)
    char_len = s.str.len()
    word_len = s.str.split().apply(len)
    empty = int((s.str.strip() == "").sum())
    n = len(s)
    return {
        "count": n,
        "empty_count": empty,
        "empty_pct": pct(empty, n),
        "char_len_mean": round(float(char_len.mean()), 2) if n else None,
        "char_len_median": float(char_len.median()) if n else None,
        "char_len_min": int(char_len.min()) if n else None,
        "char_len_max": int(char_len.max()) if n else None,
        "word_len_mean": round(float(word_len.mean()), 2) if n else None,
        "word_len_median": float(word_len.median()) if n else None,
        "word_len_min": int(word_len.min()) if n else None,
        "word_len_max": int(word_len.max()) if n else None,
    }


def label_distribution(values, n=None) -> dict:
    """Raw, un-normalised value counts. Missing values are reported under
    the explicit key '<<MISSING>>' rather than being silently dropped."""
    vals = ["<<MISSING>>" if v is None or (isinstance(v, float) and np.isnan(v)) else str(v) for v in values]
    n = n or len(vals)
    counts = Counter(vals)
    dist = [{"value": v, "count": c, "pct": pct(c, n)} for v, c in counts.most_common()]
    return {"n_unique_values": len(counts), "n_total": n, "distribution": dist}


def numeric_field_summary(values) -> dict:
    arr = pd.Series(values, dtype="float64")
    n_total = len(arr)
    n_missing = int(arr.isna().sum())
    valid = arr.dropna()
    return {
        "n_total": n_total,
        "n_missing": n_missing,
        "n_missing_pct": pct(n_missing, n_total),
        "mean": round(float(valid.mean()), 3) if len(valid) else None,
        "median": float(valid.median()) if len(valid) else None,
        "min": float(valid.min()) if len(valid) else None,
        "max": float(valid.max()) if len(valid) else None,
    }


def count_turns_from_conversation_text(text: str) -> int:
    """Counts speaker-tagged turns in a free-text 'User:'/'AI:' style field
    (used by AICompanionBench). Best-effort, since this is raw scraped text."""
    if not isinstance(text, str) or not text.strip():
        return 0
    return len(re.findall(r"(?:^|\n)\s*(User|AI)\s*:", text))


# --------------------------------------------------------------------------
# 1. AICompanionBench
# --------------------------------------------------------------------------

def audit_ai_companion_bench() -> dict:
    path = RAW / "ai_companion_bench" / "AICompanionBench.csv"
    df = read_csv_safely(path)

    result: dict = {
        "file": str(path.relative_to(ROOT)),
        "file_format": "CSV (UTF-8 with BOM)",
        "file_size_bytes": path.stat().st_size,
        "record_unit": (
            "One row = one labelled conversation EXCERPT taken from a Reddit "
            "post/screenshot. The 'id' column is the source Reddit post id, "
            "NOT a unique row id: the same Reddit post id can contribute "
            "several excerpts, each with its own Category_Final label."
        ),
    }
    result["frame_audit"] = generic_frame_audit(df, id_col="id")

    # Duplicate-id characterisation: are repeated ids identical rows, or
    # distinct excerpts from the same source post?
    dup_ids = df["id"][df["id"].duplicated(keep=False)].unique().tolist()
    identical_groups = 0
    distinct_groups = 0
    for did in dup_ids:
        sub = df[df["id"] == did]
        if sub.duplicated(keep=False).all():
            identical_groups += 1
        else:
            distinct_groups += 1
    result["duplicate_id_analysis"] = {
        "n_ids_appearing_more_than_once": len(dup_ids),
        "groups_where_rows_are_fully_identical": identical_groups,
        "groups_where_rows_differ_same_source_post": distinct_groups,
    }

    result["label_audit"] = {"Category_Final": label_distribution(df["Category_Final"])}

    result["text_stats"] = {
        "conversation": text_stats(df["conversation"]),
        "title": text_stats(df["title"]),
        "selftext": text_stats(df["selftext"]),
    }

    turn_counts = df["conversation"].apply(count_turns_from_conversation_text)
    result["conversation_structure"] = {
        "conversation_id_field": "id (source Reddit post; not unique per excerpt)",
        "speaker_field": "embedded in free text as 'User:' / 'AI:' prefixes inside 'conversation' (no dedicated speaker column)",
        "turns_per_record_min": int(turn_counts.min()),
        "turns_per_record_max": int(turn_counts.max()),
        "turns_per_record_mean": round(float(turn_counts.mean()), 2),
        "records_with_zero_detected_turns": int((turn_counts == 0).sum()),
        "annotation_level": "Category_Final is applied to the whole excerpt in 'conversation' (excerpt-level, not per-turn, not span-level).",
        "context_preserved": "Only what is included verbatim inside the 'conversation' excerpt; no separate structured history field.",
        "ai_response_isolable": "Only via regex/string parsing of 'User:'/'AI:' prefixes in free text; not structured.",
    }

    privacy_cols = ["author", "author_flair_text", "author_fullname", "media_metadata"]
    result["privacy_flags"] = {
        c: {
            "present": c in df.columns,
            "non_null_count": int(df[c].notna().sum()) if c in df.columns else 0,
            "example_non_null_value_shown": False,
        }
        for c in privacy_cols
    }
    result["privacy_note"] = (
        "author / author_fullname contain real, unhashed Reddit usernames / "
        "account ids attached to sexual, self-harm, and other sensitive "
        "content categories. Flagged for a later privacy-preserving step; "
        "not modified here."
    )

    return result


# --------------------------------------------------------------------------
# 2. ChatbotManip (conversations.json + survey_responses.json)
# --------------------------------------------------------------------------

def audit_chatbotmanip() -> dict:
    conv_path = RAW / "chatbotmanip" / "conversations.json"
    surv_path = RAW / "chatbotmanip" / "survey_responses.json"
    conv = load_json(conv_path)
    surv = load_json(surv_path)

    result: dict = {
        "conversations_file": str(conv_path.relative_to(ROOT)),
        "survey_file": str(surv_path.relative_to(ROOT)),
        "conversations_file_size_bytes": conv_path.stat().st_size,
        "survey_file_size_bytes": surv_path.stat().st_size,
        "conversations_record_unit": "One JSON object = one LLM-generated decision-support conversation (a single generated dialogue for a given scenario/model/prompt combination).",
        "survey_record_unit": "One JSON object = one human annotation of a highlighted text span drawn from a conversation (span-level judgement, several manipulation sub-scales per span).",
    }

    result["conversations_structure"] = {
        "top_level_type": "list",
        "n_records": len(conv),
        "keys_per_record": list(conv[0].keys()) if conv else [],
        "keys_consistent_across_records": len({tuple(sorted(c.keys())) for c in conv}) == 1,
    }
    result["survey_structure"] = {
        "top_level_type": "list",
        "n_records": len(surv),
        "keys_per_record": list(surv[0].keys()) if surv else [],
        "keys_consistent_across_records": len({tuple(sorted(s.keys())) for s in surv}) == 1,
    }

    conv_uuids = [c.get("uuid") for c in conv]
    surv_conv_uuids = [s.get("conversation_uuid") for s in surv]
    conv_uuid_set = set(u for u in conv_uuids if u is not None)
    surv_uuid_set = set(u for u in surv_conv_uuids if u is not None)
    shared = conv_uuid_set & surv_uuid_set

    result["linkage"] = {
        "n_conversations": len(conv),
        "n_survey_responses": len(surv),
        "n_unique_conversation_uuids_in_conversations_file": len(conv_uuid_set),
        "n_unique_conversation_uuids_referenced_by_survey": len(surv_uuid_set),
        "n_uuids_shared_between_files": len(shared),
        "n_conversations_without_any_survey_annotation": len(conv_uuid_set - surv_uuid_set),
        "n_survey_uuids_with_no_matching_conversation": len(surv_uuid_set - conv_uuid_set),
        "note": "Unmatched records on both sides are counted only, not discarded.",
    }

    result["label_audit"] = {
        "manipulation_type": label_distribution([c.get("manipulation_type") for c in conv]),
        "persuasion_strength": label_distribution([c.get("persuasion_strength") for c in conv]),
        "model": label_distribution([c.get("model") for c in conv]),
        "prompt_type": label_distribution([c.get("prompt_type") for c in conv]),
    }

    manipulative_cols = sorted({k for s in surv for k in s.keys() if k.startswith("manipulative_")})
    result["survey_sub_scale_fields"] = {
        col: numeric_field_summary([s.get(col) for s in surv]) for col in manipulative_cols
    }

    result["text_stats"] = {
        "chat_completion": text_stats(pd.Series([c.get("chat_completion") for c in conv])),
        "highlighted_text": text_stats(pd.Series([s.get("highlighted_text") for s in surv])),
    }

    # cleaned_conversation turn structure (list of {role, content} dicts)
    turn_counts = []
    roles = Counter()
    for c in conv:
        cc = c.get("cleaned_conversation")
        if isinstance(cc, list):
            turn_counts.append(len(cc))
            for m in cc:
                if isinstance(m, dict):
                    roles.update([m.get("role")])
    result["conversation_structure"] = {
        "conversation_id_field": "uuid",
        "turn_field": "cleaned_conversation (list of {role, content}); chat_completion holds the same dialogue as raw '@@@ USER:'/'@@@ AGENT:' text",
        "speaker_roles_found": dict(roles),
        "turns_per_conversation_min": min(turn_counts) if turn_counts else None,
        "turns_per_conversation_max": max(turn_counts) if turn_counts else None,
        "turns_per_conversation_mean": round(sum(turn_counts) / len(turn_counts), 2) if turn_counts else None,
        "context_preserved": "Yes, full multi-turn history is kept in cleaned_conversation/chat_completion.",
        "ai_response_isolable": "Yes, by role == 'AGENT' in cleaned_conversation.",
    }

    # Verify whether highlighted_text spans are found verbatim inside their
    # linked conversation (span-level vs conversation-level annotation check).
    conv_by_uuid = {c.get("uuid"): c for c in conv}
    checked, fully_found, partially_found = 0, 0, 0
    for s in surv:
        c = conv_by_uuid.get(s.get("conversation_uuid"))
        ht = s.get("highlighted_text")
        if not c or not isinstance(ht, str) or not ht.strip():
            continue
        checked += 1
        full_text = str(c.get("chat_completion") or "") + str(c.get("cleaned_conversation") or "")
        segs = [seg.strip() for seg in ht.split("<<>>") if seg.strip()]
        if not segs:
            continue
        found = sum(1 for seg in segs if seg in full_text)
        if found == len(segs):
            fully_found += 1
        elif found > 0:
            partially_found += 1

    result["annotation_level"] = {
        "level": "span-level (highlighted_text is one or more '<<>>'-delimited excerpts pulled from the parent conversation; each span carries its own manipulative_* sub-scores).",
        "spans_checked_against_matched_conversation": checked,
        "spans_fully_verbatim_in_conversation_text": fully_found,
        "spans_partially_verbatim_in_conversation_text": partially_found,
        "spans_not_found_verbatim": checked - fully_found - partially_found,
        "note": "Not-found cases likely reflect minor formatting/whitespace differences between the stored highlight and the stored conversation text, not necessarily broken linkage.",
    }

    return result


# --------------------------------------------------------------------------
# 3. CompanionHarm
# --------------------------------------------------------------------------

def audit_companion_harm() -> dict:
    paths = {
        "train": RAW / "companion_harm" / "train.csv",
        "dev": RAW / "companion_harm" / "dev.csv",
        "test": RAW / "companion_harm" / "test.csv",
    }
    dfs = {split: read_csv_safely(p) for split, p in paths.items()}

    result: dict = {
        "files": {split: str(p.relative_to(ROOT)) for split, p in paths.items()},
        "record_unit": "One row = one AI (Replika) utterance, with the preceding conversation history in 'context' and a harm label ('label') applied to that single utterance.",
        "per_split": {},
    }

    for split, df in dfs.items():
        result["per_split"][split] = {
            "frame_audit": generic_frame_audit(df, id_col="utterance_id"),
            "label_distribution": label_distribution(df["label"]),
            "agreement_type_distribution": label_distribution(df["agreement_type"]),
            "majority_vote_count_distribution": label_distribution(df["majority_vote_count"]),
            "annotator_count_distribution": label_distribution(df["annotator_count"]),
            "speaker_distribution": label_distribution(df["speaker"]),
            "unique_conversation_ids": int(df["conversation_id"].nunique()),
            "text_stats_current_line": text_stats(df["current_line"]),
            "text_stats_context": text_stats(df["context"]),
        }

    all_df = pd.concat(dfs.values(), ignore_index=True)
    result["overall"] = {
        "total_rows": len(all_df),
        "label_distribution": label_distribution(all_df["label"]),
        "unique_conversation_ids_overall": int(all_df["conversation_id"].nunique()),
        "unique_utterance_ids_overall": int(all_df["utterance_id"].nunique()),
        "full_row_duplicates_overall": int(all_df.duplicated().sum()),
    }

    conv_id_sets = {split: set(df["conversation_id"]) for split, df in dfs.items()}
    result["split_overlap_conversation_ids"] = {
        "train_dev": len(conv_id_sets["train"] & conv_id_sets["dev"]),
        "train_test": len(conv_id_sets["train"] & conv_id_sets["test"]),
        "dev_test": len(conv_id_sets["dev"] & conv_id_sets["test"]),
        "note": "0 in all three means no conversation-level leakage across splits was found.",
    }

    focus_labels = ["Manipulation", "Control", "No harmful behavior"]
    result["focus_label_counts_by_split"] = {
        label: {split: int((dfs[split]["label"] == label).sum()) for split in dfs}
        for label in focus_labels
    }

    return result


# --------------------------------------------------------------------------
# 4. CLAIM / LegalCon
# --------------------------------------------------------------------------

def audit_claim_legalcon() -> dict:
    path = RAW / "claim" / "LegalCon-Dataset.csv"
    df = read_csv_safely(path)

    result: dict = {
        "file": str(path.relative_to(ROOT)),
        "file_size_bytes": path.stat().st_size,
        "record_unit": "One row = one full dialogue/court-show transcript, with a single Manipulative (0/1) label, a Primary Manipulator role, and free-text Manipulation Techniques for the ENTIRE transcript.",
        "frame_audit": generic_frame_audit(df, id_col="IDs"),
        "label_audit": {
            "Manipulative": label_distribution(df["Manipulative"]),
            "Primary_Manipulator_raw": label_distribution(df["Primary Manipulator"]),
            "Manipulation_Techniques_raw": label_distribution(df["Manipulation Techniques"]),
        },
        "text_stats": {"Dialogue": text_stats(df["Dialogue"])},
        "annotation_level": "Conversation/transcript-level (one label set per entire Dialogue field, not per turn or span).",
    }

    # Manipulation Techniques is free text, often multi-valued (comma
    # separated); report how many rows contain more than one technique.
    techniques = df["Manipulation Techniques"].fillna("")
    multi_valued = techniques.apply(lambda t: len([x for x in re.split(r"[,/;]", t) if x.strip()]) > 1)
    result["manipulation_techniques_multivalue_note"] = {
        "rows_with_more_than_one_technique_listed": int(multi_valued.sum()),
        "rows_empty": int((techniques.str.strip() == "").sum()),
        "raw_values_not_normalised": True,
    }

    return result


# --------------------------------------------------------------------------
# 5. TEA-Dialog
# --------------------------------------------------------------------------

def audit_tea_dialog() -> dict:
    path = RAW / "tea_dialog" / "TEA-Dialog.json"
    data = load_json(path)

    result: dict = {
        "file": str(path.relative_to(ROOT)),
        "file_size_bytes": path.stat().st_size,
        "record_unit": "One JSON object = one simulated emotional-support scenario/dialogue (a scene, a location/time context, and a full conversation between a 'user' and an 'assistant' role).",
        "top_level_type": "list",
        "n_records": len(data),
        "keys_per_record": list(data[0].keys()) if data else [],
        "keys_consistent_across_records": len({tuple(sorted(d.keys())) for d in data}) == 1,
    }

    raw_turns, content_turns = [], []
    raw_roles, content_roles = Counter(), Counter()
    for d in data:
        rm = d.get("raw_messages") or []
        cm = d.get("content_messages") or []
        raw_turns.append(len(rm))
        content_turns.append(len(cm))
        raw_roles.update(m.get("role") for m in rm if isinstance(m, dict))
        content_roles.update(m.get("role") for m in cm if isinstance(m, dict))

    result["raw_messages_structure"] = {
        "roles_found": dict(raw_roles),
        "turns_per_record_min": min(raw_turns) if raw_turns else None,
        "turns_per_record_max": max(raw_turns) if raw_turns else None,
        "turns_per_record_mean": round(sum(raw_turns) / len(raw_turns), 2) if raw_turns else None,
        "note": "Includes a leading 'system' role (the assistant's persona instructions), plus 'user' and 'assistant' turns.",
    }
    result["content_messages_structure"] = {
        "roles_found": dict(content_roles),
        "turns_per_record_min": min(content_turns) if content_turns else None,
        "turns_per_record_max": max(content_turns) if content_turns else None,
        "turns_per_record_mean": round(sum(content_turns) / len(content_turns), 2) if content_turns else None,
        "note": "user/assistant turns only (system prompt excluded).",
    }

    score_keys = sorted({k for d in data for k in (d.get("scores") or {}).keys()})
    result["evaluation_scores"] = {
        k: numeric_field_summary([(d.get("scores") or {}).get(k) for d in data]) for k in score_keys
    }
    result["content_field"] = {
        "note": "Top-level 'content' is a numeric score (not message text); meaning is not documented locally.",
        **numeric_field_summary([d.get("content") for d in data]),
    }
    result["hallucination_fields"] = {
        "all_hallucination": numeric_field_summary([d.get("all_hallucination") for d in data]),
        "content_hallucination": numeric_field_summary([d.get("content_hallucination") for d in data]),
    }
    result["end_reason_distribution"] = label_distribution([d.get("end_reason") for d in data])
    result["text_stats_description"] = text_stats(pd.Series([d.get("description") for d in data]))
    result["manipulation_labels_present"] = False
    result["role_assessment"] = (
        "No manipulation or harm labels of any kind are present. Usable as benign "
        "emotional-support / hard-negative reference data (realistic supportive "
        "dialogue that should NOT be flagged as manipulative), not as manipulation-"
        "labelled training data."
    )

    return result


# --------------------------------------------------------------------------
# 6. Illusions of Intimacy (documentation only)
# --------------------------------------------------------------------------

def audit_illusions_of_intimacy() -> dict:
    path = RAW / "illusions_of_intimacy" / "README.txt"
    text = path.read_text(encoding="utf-8")
    numbers = re.findall(r"([\d,]+)\s+(conversations|turns)", text)
    return {
        "file": str(path.relative_to(ROOT)),
        "local_data_availability": "documentation only; no dataset file present locally",
        "readme_text": text,
        "published_statistics_mentioned_in_readme": numbers,
        "note": (
            "Any conversation/turn counts quoted in the README describe the "
            "PUBLISHED corpus, not data available in this repository. They "
            "must not be counted as locally available records."
        ),
    }


# --------------------------------------------------------------------------
# Cross-dataset summary
# --------------------------------------------------------------------------

def build_cross_dataset_summary(results: dict) -> dict:
    return {
        "ai_companion_bench": {
            "records": results["ai_companion_bench"]["frame_audit"]["n_rows"],
            "conversations": "N/A (excerpt-level; 'id' is source post, not conversation)",
        },
        "chatbotmanip": {
            "conversations": results["chatbotmanip"]["conversations_structure"]["n_records"],
            "survey_annotations": results["chatbotmanip"]["survey_structure"]["n_records"],
        },
        "companion_harm": {
            "total_utterances": results["companion_harm"]["overall"]["total_rows"],
            "unique_conversations": results["companion_harm"]["overall"]["unique_conversation_ids_overall"],
        },
        "claim_legalcon": {
            "records": results["claim_legalcon"]["frame_audit"]["n_rows"],
        },
        "tea_dialog": {
            "records": results["tea_dialog"]["n_records"],
        },
        "illusions_of_intimacy": {
            "records_locally_available": 0,
        },
    }


# --------------------------------------------------------------------------
# Reporting
# --------------------------------------------------------------------------

def print_summary(results: dict) -> None:
    print("=" * 78)
    print("DATASET AUDIT - PHASE 1 (read-only)")
    print("=" * 78)

    acb = results["ai_companion_bench"]
    print("\n[AICompanionBench]")
    print(f"  rows: {acb['frame_audit']['n_rows']}  columns: {acb['frame_audit']['n_columns']}")
    print(f"  duplicate 'id' groups (same source post, different excerpts): "
          f"{acb['duplicate_id_analysis']['n_ids_appearing_more_than_once']}")
    print(f"  Category_Final values: {acb['label_audit']['Category_Final']['n_unique_values']}")

    cm = results["chatbotmanip"]
    print("\n[ChatbotManip]")
    print(f"  conversations: {cm['conversations_structure']['n_records']}   survey responses: {cm['survey_structure']['n_records']}")
    print(f"  unique conversation uuids: {cm['linkage']['n_unique_conversation_uuids_in_conversations_file']}")
    print(f"  uuids shared with survey file: {cm['linkage']['n_uuids_shared_between_files']}")
    print(f"  conversations without survey annotation: {cm['linkage']['n_conversations_without_any_survey_annotation']}")
    print(f"  survey rows with no matching conversation: {cm['linkage']['n_survey_uuids_with_no_matching_conversation']}")

    ch = results["companion_harm"]
    print("\n[CompanionHarm]")
    for split in ("train", "dev", "test"):
        print(f"  {split}: {ch['per_split'][split]['frame_audit']['n_rows']} rows, "
              f"{ch['per_split'][split]['unique_conversation_ids']} unique conversations")
    print(f"  total rows: {ch['overall']['total_rows']}  unique conversations overall: {ch['overall']['unique_conversation_ids_overall']}")
    print(f"  conversation_id overlap across splits: {ch['split_overlap_conversation_ids']}")

    cl = results["claim_legalcon"]
    print("\n[CLAIM / LegalCon]")
    print(f"  rows: {cl['frame_audit']['n_rows']}  unique IDs: {cl['frame_audit']['unique_id_count']}")
    print(f"  Manipulative distribution: {cl['label_audit']['Manipulative']['distribution']}")

    tea = results["tea_dialog"]
    print("\n[TEA-Dialog]")
    print(f"  records: {tea['n_records']}")
    print(f"  content_messages turns/record: min={tea['content_messages_structure']['turns_per_record_min']} "
          f"max={tea['content_messages_structure']['turns_per_record_max']} "
          f"mean={tea['content_messages_structure']['turns_per_record_mean']}")

    iot = results["illusions_of_intimacy"]
    print("\n[Illusions of Intimacy]")
    print(f"  local data availability: {iot['local_data_availability']}")

    print("\n" + "=" * 78)
    print("Full machine-readable results written to reports/audit_results.json")
    print("=" * 78)


def main() -> None:
    results = {
        "ai_companion_bench": audit_ai_companion_bench(),
        "chatbotmanip": audit_chatbotmanip(),
        "companion_harm": audit_companion_harm(),
        "claim_legalcon": audit_claim_legalcon(),
        "tea_dialog": audit_tea_dialog(),
        "illusions_of_intimacy": audit_illusions_of_intimacy(),
    }
    results["cross_dataset_summary"] = build_cross_dataset_summary(results)

    print_summary(results)

    REPORTS.mkdir(parents=True, exist_ok=True)
    out_path = REPORTS / "audit_results.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(to_native(results), f, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    main()
