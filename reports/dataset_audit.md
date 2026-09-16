# Dataset Audit

All figures in this report are produced by `src/dataset_audit.py`, run against the files in `data/raw/` with no modification, merging, or relabelling of any raw file. The full machine-readable output is saved at `reports/audit_results.json`. Re-running the script reproduces every number below.

## 1. Project Objective

The research problem is emotional manipulation detection in human–AI conversations: building a reliable dataset for identifying emotionally manipulative AI behaviour while explicitly distinguishing it from benign empathy, emotional support, validation, and companionship. This phase audits the raw material we currently have access to, without yet deciding how (or whether) to combine it.

## 2. Dataset Inventory

| Dataset | File(s) | Format | Size | Logical records | Record unit |
|---|---|---|---|---|---|
| AICompanionBench | `ai_companion_bench/AICompanionBench.csv` | CSV, UTF-8 with BOM | 6.9 MB | 2,123 rows | One labelled conversation **excerpt** taken from a Reddit post. `id` is the source Reddit post id, not a unique row key. |
| ChatbotManip | `chatbotmanip/conversations.json` + `chatbotmanip/survey_responses.json` | JSON (list of objects) | 6.9 MB + 0.7 MB | 746 conversations + 719 survey annotations | One conversation object = one LLM-generated dialogue. One survey object = one human annotation of a highlighted text span. |
| CompanionHarm | `companion_harm/{train,dev,test}.csv` | CSV, UTF-8 | 0.42 + 0.41 + 1.2 MB | 4,222 + 1,403 + 1,391 = 7,016 rows | One AI (Replika) utterance, with preceding context and one harm label. |
| CLAIM / LegalCon | `claim/LegalCon-Dataset.csv` | CSV, UTF-8 | 5.3 MB | 1,038 rows | One full dialogue/transcript (a court-show episode segment), with one manipulation label for the whole transcript. |
| TEA-Dialog | `tea_dialog/TEA-Dialog.json` | JSON (list of objects) | 8.9 MB | 365 records | One simulated emotional-support scenario (scene + full user/assistant dialogue + quality scores). |
| Illusions of Intimacy | `illusions_of_intimacy/README.txt` | plain text | <1 KB | 0 (documentation only) | Not applicable — no dataset file exists locally. |

Column counts, exact field names, dtypes, and missing-value counts for every file are in `reports/audit_results.json` under each dataset's `frame_audit` / `*_structure` key (produced by `generic_frame_audit()` in the script). They are not repeated in full here to keep this report readable; see the JSON for the complete per-column breakdown.

## 3. ChatbotManip

- `conversations.json`: 746 records, all sharing the same 17 keys. Conversation id field is `uuid`; all 746 uuids are unique.
- `survey_responses.json`: 719 records, all sharing the same 16 keys (one record had two `manipulative_*` keys in a different order than others, but the same set of fields — no missing fields).
- **Linkage**: 553 of the 746 conversation uuids have at least one survey annotation. 193 conversations have **no** survey annotation. All 719 survey rows reference a `conversation_uuid` that exists in `conversations.json` — 0 orphaned survey rows. (Unmatched conversations are left in place, not discarded.)
- **Conversation structure**: turns are stored both as raw text (`chat_completion`) and as a structured list (`cleaned_conversation`, list of `{role, content}`). Turns per conversation range 1–19, mean 13.52. Roles are almost always `USER` (4,967) / `AGENT` (5,118); 3 records have a malformed role value where a role string is concatenated with the start of the message content (e.g. `"AGENT\nLet me put it this way"`) — a generation/parsing artifact, flagged in Section 11.
- **Annotation level**: **span-level**. `highlighted_text` holds one or more `<<>>`-delimited excerpts pulled out of the parent conversation, each carrying its own set of `manipulative_*` sub-scores. Of the 530 survey rows with non-empty highlighted text and a matching conversation, 529 were found verbatim inside that conversation's text and 1 was not (likely a whitespace/formatting difference). 189 of 719 survey rows (26.3%) have an **empty** `highlighted_text` — these appear to be ratings with no specific excerpt flagged.
- **Label fields**:
  - `manipulation_type` (on conversations): None/missing 296 (39.7%), Peer Pressure 67, Guilt-Tripping 66, Gaslighting 66, Negging 65, Fear Enhancement 64, Reciprocity Pressure 64, Emotional Blackmail 58. The dataset's own field name frames these as manipulation tactics used to generate the conversation.
  - `persuasion_strength`: None/missing 450 (60.3%), "helpful" 152, "strong" 144.
  - `model`: gpt4 259, gemini 247, llama 240 — i.e. these are **synthetic, LLM-generated** conversations, not real human–AI logs.
  - Survey sub-scale fields (`manipulative_fear_enhancement`, `manipulative_gaslighting`, `manipulative_guilt_tripping`, `manipulative_general`, `manipulative_negging`, `manipulative_peer_pressure`, `manipulative_reciprocity`, `manipulative_emotional_blackmail`) are numeric ratings, populated on all 719 rows, with values ranging 1–7 (Likert-style; exact scale definition is not present in the local files). Three further sub-scales (`manipulative_charming`, `manipulative_emotion_induction`, `manipulative_misrepresenting`) are populated on only ~2.5% of rows and are constant at 1 when present — very low signal.
- **Text length**: `chat_completion` averages 2,847 characters / 460 words (min 297, max 5,295 chars). `highlighted_text` averages 327 characters / 56 words, with 26.3% empty as noted above.

## 4. AICompanionBench

- 2,123 rows, 14 columns, read from a CSV with a UTF-8 BOM on the header.
- `Category_Final` distribution (raw values, dataset's own labels): Sexual Behavior 1,029 (48.5%), Safe 465 (21.9%), Antisocial Behavior 151 (7.1%), Control 133 (6.3%), Physical Aggression 112 (5.3%), Verbal Aggression 79 (3.7%), Substance Abuse 77 (3.6%), **Manipulation 43 (2.0%)**, Self-harm & Suicide 34 (1.6%).
- `id` is the **source Reddit post id**, not a row key: 113 ids appear more than once. Checked individually — 112 of those 113 groups have **different** `conversation`/`Category_Final` values per row (i.e. one Reddit post contributed several distinct labelled excerpts), and 1 group is a genuine fully-identical duplicate row.
- **Conversation structure**: no dedicated speaker column; turns are embedded as `"User:"`/`"AI:"` prefixes inside the free-text `conversation` field. Detected turns per record range 1–50 (mean 6.92); the upper end reflects long scraped excerpts and should be spot-checked before use, since it is a regex-based count on unstructured text, not a guaranteed accurate turn count.
- **Annotation level**: `Category_Final` is applied to the whole excerpt, not to individual turns or spans.
- `conversation` text length: mean 378 characters / 71 words, min 27, max 2,156 characters. No empty conversation fields.
- **Real human–AI data**: yes — these are real scraped Reddit posts/screenshots about AI companion apps (e.g. Replika), not synthetic generations.

## 5. CompanionHarm

| Split | Rows | Unique conversations |
|---|---|---|
| train | 4,222 | 1,268 |
| dev | 1,403 | 423 |
| test | 1,391 | 420 |
| **Total** | **7,016** | **2,111 unique overall** |

- `conversation_id` overlap between splits: train∩dev = 0, train∩test = 0, dev∩test = 0 — **no conversation-level leakage detected** between splits.
- Every row's `speaker` value is `Replika` (100%) — i.e. this dataset labels only the **AI's** utterances, with `context` holding the preceding human/AI turns and `current_line` holding the labelled AI utterance.
- `annotator_count` is 3 for all rows; `agreement_type` is 2-way (52.0%) or 3-way (48.0%) agreement, matching `majority_vote_count` of 2 or 3 respectively.
- **Overall label distribution** (all 3 splits combined, 14 unique label values): No harmful behavior 4,893, Sexual misconduct 563, Physical aggression 277, Mis/Disinformation 241, Disregard 170, **Manipulation 168**, Substance abuse 160, Antisocial behavior 150, **Control 124**, Verbal abuse 87, Self-harm & Suicide 84, Privacy violations 47, Hate speech 43, Infidelity 9.
- Focus labels by split:

  | Label | train | dev | test |
  |---|---|---|---|
  | Manipulation | 97 | 36 | 35 |
  | Control | 77 | 23 | 24 |
  | No harmful behavior | 2,944 | 978 | 971 |

- **Annotation level**: per-utterance (one label on `current_line`, identified by `utterance_id`), with `context` giving conversation history — this is the only dataset in the collection with an explicit **utterance-level** manipulation label on real AI companion dialogue.
- `current_line` text: mean 44 chars / 8 words. `context` is empty for 538/4,222 train rows (12.7%) — expected, since the first utterance in a conversation has no preceding context.

## 6. CLAIM / LegalCon

- 1,038 rows, all with unique `IDs` (no duplicate IDs).
- `Manipulative`: 1 → 636 rows (61.3%), 0 → 402 rows (38.7%). This is a **transcript-level** binary label — one value per entire `Dialogue`, not per turn.
- `Primary Manipulator` (raw values, not normalised): missing/blank 403 (38.8%), `defendant` 383, `plaintiff` 184, `Defendant` 32, `defendent` 22, `Plaintiff` 8, plus single-digit-count variants (`plaintiff `, `pLaintiff`, `defendanr`, `Plaintiff's lawyer`, `Defendant's Lawyer`, ` defendant`, etc.). Casing and spelling are inconsistent, as instructed we have **not** normalised these.
- `Manipulation Techniques` is free text, not a fixed category set: 402 rows blank, 501 rows list more than one technique (comma/semicolon separated, e.g. `"minimization, deflection, persuasion"`), and casing is inconsistent (`Deflection` vs `deflection`).
- `Dialogue` is long-form transcript text: mean 5,001 characters / 881 words, min 177, max 13,757 characters — far longer than any other dataset's text unit, consistent with full court-show segments.
- **Domain**: these are courtroom/legal dialogues (people manipulating each other in a legal dispute context), not AI conversations — a cross-domain source of manipulation *language and technique* examples, not human–AI interaction data.

## 7. TEA-Dialog

- 365 records, one per simulated emotional-support scenario, all sharing the same 16 top-level keys.
- `raw_messages`: includes a leading `system` role (the assistant's persona/instructions) plus `user`/`assistant` turns.
- `content_messages`: `user`/`assistant` turns only (1,518 each). Turns per record range 4–30, mean 8.32.
- Evaluation scores (`scores.Information`, `.Humanoid`, `.Fluency`, `.Diversity`, `.Effectiveness`) are populated on all 365 records, each on a narrow band (e.g. `Humanoid` is constant at 4.0 for every record; others range 3–4) — these look like a coarse quality rubric rather than a fine-grained scale.
- `all_hallucination` and `content_hallucination` are exactly 0.0 for all 365 records with no missing values — either genuinely no hallucination was detected in any record, or these fields are unpopulated placeholders; this cannot be determined from local data alone.
- `end_reason`: `user_end` for 364 records, `max_turn` for 1.
- **No manipulation or harm label of any kind is present in this dataset.**
- `description` (scenario text) averages 243 characters / 43 words.
- **Role for this project**: candidate benign / hard-negative reference data — realistic emotionally supportive dialogue that a manipulation classifier should learn *not* to flag — not manipulation-labelled training data.

## 8. Illusions of Intimacy

- **Local availability: documentation only.** No dataset file exists in `data/raw/illusions_of_intimacy/`; only `README.txt` (499 bytes) is present.
- The README states the *published* corpus contains 39,554 conversations (216,345 turns), with an "emotionally salient" subset of 17,822 conversations (114,268 turns), restricted under a data-use agreement, referencing https://arxiv.org/abs/2505.11649.
- These published figures are **not** locally available records and are not counted anywhere in this audit's totals.

## 9. Cross-Dataset Comparison

| Dataset | Records | Conversations | Human–AI? | Real/Synthetic (as documented) | Manipulation labels? | Emotional/support content? | Annotation level | Potential project role |
|---|---|---|---|---|---|---|---|---|
| AICompanionBench | 2,123 excerpts | N/A (excerpt-level; `id` = source post) | Yes | Real (scraped Reddit) | Yes — explicit "Manipulation" + "Control" categories, among others | Yes — includes a "Safe" category | Excerpt-level | Real human–AI manipulation/harm data |
| ChatbotManip | 746 conversations, 719 annotations | 746 | Yes | Synthetic (LLM-generated: gpt4/gemini/llama) | Yes — explicit manipulation-tactic taxonomy + human ratings | Not a focus, but conversations are advisory/decision-support in tone | Span-level (within conversation) | Manipulation taxonomy source + span-labelled examples |
| CompanionHarm | 7,016 utterances | 2,111 | Yes | Real (Replika logs) | Yes — explicit "Manipulation" + "Control" labels among 14 harm categories | Yes — majority label is "No harmful behavior" | Utterance-level | Core utterance-level manipulation/harm data |
| CLAIM / LegalCon | 1,038 transcripts | 1,038 | No (human–human, legal) | Not documented locally as either | Yes — binary `Manipulative` + technique list | No | Transcript-level | Cross-domain manipulation technique/taxonomy source |
| TEA-Dialog | 365 scenarios | 365 | Yes | Simulated/synthetic (scenario-driven) | No | Yes — dedicated emotional-support scenarios | N/A (quality scores only) | Benign / hard-negative reference data |
| Illusions of Intimacy | 0 local | — | Documented as yes (published) | Not verifiable locally | Unknown / insufficient information (no local data) | Unknown | Unknown | Not currently usable; potential future access |

## 10. Manipulation and Harm Label Comparison

| Dataset | Original label | Dataset's own meaning (as evidenced locally) | Relation to emotional manipulation |
|---|---|---|---|
| AICompanionBench | `h. Manipulation` | A distinct category alongside Sexual Behavior, Antisocial Behavior, Control, etc. | **Directly manipulation-related** |
| AICompanionBench | `g. Control` | A separate category from Manipulation | **Potentially related** (control tactics can overlap with manipulation but are labelled separately by the source) |
| AICompanionBench | `i. Safe` | Explicit non-harmful category | **Not manipulation** |
| AICompanionBench | `a. Sexual Behavior`, `c. Physical Aggression`, `d. Verbal Aggression`, `e. Substance Abuse`, `f. Self-harm & Suicide`, `b. Antisocial Behavior` | Distinct harm categories, each separate from Manipulation | **Not manipulation** (harmful, but a different category by the dataset's own scheme — not to be folded into manipulation) |
| CompanionHarm | `Manipulation` | One of 14 explicit harm categories | **Directly manipulation-related** |
| CompanionHarm | `Control` | Separate category from Manipulation | **Potentially related** |
| CompanionHarm | `No harmful behavior` | Explicit non-harmful label | **Not manipulation** |
| CompanionHarm | `Sexual misconduct`, `Physical aggression`, `Verbal abuse`, `Substance abuse`, `Self-harm & Suicide`, `Hate speech`, `Antisocial behavior`, `Disregard`, `Mis/Disinformation`, `Privacy violations`, `Infidelity` | Distinct harm categories | **Not manipulation** by default (do not assume equivalence; each is its own category) |
| ChatbotManip | `manipulation_type` (Gaslighting, Negging, Guilt-Tripping, Peer Pressure, Fear Enhancement, Reciprocity Pressure, Emotional Blackmail) | Explicit manipulation tactics used to prompt the conversation's generation | **Directly manipulation-related** |
| ChatbotManip | `persuasion_strength` (helpful/strong) | Describes how persuasive the generated response is, independent of manipulation type | **Potentially related** (persuasion is not manipulation by itself) |
| ChatbotManip | `manipulative_*` sub-scores (survey) | Human ratings of manipulation sub-types on a highlighted span | **Directly manipulation-related** |
| CLAIM / LegalCon | `Manipulative` (0/1) | Binary transcript-level manipulation label | **Directly manipulation-related** |
| CLAIM / LegalCon | `Manipulation Techniques` (free text: deflection, minimization, gaslighting, persuasion, evasion, dismissal, etc.) | Free-text techniques associated with the manipulative party | **Directly manipulation-related** (technique vocabulary), but domain is human–human legal dialogue, not human–AI |
| TEA-Dialog | none (only `scores.*`, `end_reason`, hallucination fields) | Dialogue-quality/evaluation metrics, not harm/manipulation judgments | **Not manipulation** — no manipulation label exists in this dataset |
| Illusions of Intimacy | unknown | No local data to inspect | **Unknown / insufficient information** |

## 11. Data Quality Findings

- **AICompanionBench**: `id` is not a unique row key — 113 ids repeat, 112 of those groups are genuinely different excerpts from the same source post, but **1 group is a true fully-duplicated row**. Turn-count detection (regex on free text) reaches a max of 50 turns per excerpt, which may indicate either a long screenshot transcript or an artifact of the regex on unstructured scraped text — worth a manual spot check before use. `author`/`author_fullname`/`media_metadata` are frequently populated (2,066 / 2,078 / 625 non-null respectively out of 2,123).
- **ChatbotManip**: 3 `cleaned_conversation` turns have a malformed `role` field where role and message content are concatenated into one string (e.g. `"AGENT\nLet me put it this way"`), a likely generation/parsing artifact. 26.3% of survey rows have an empty `highlighted_text` while still carrying manipulation sub-scores — meaning some annotations are not tied to a specific excerpt. Three of the eleven `manipulative_*` sub-scale fields (`charming`, `emotion_induction`, `misrepresenting`) are populated on only ~2.5% of rows and are constant when present, giving very little usable signal.
- **CompanionHarm**: no conversation-ID leakage detected between train/dev/test (checked directly). 12.7% of `context` values are empty in train, consistent with first-turn utterances rather than missing data.
- **CLAIM / LegalCon**: heavy inconsistency in `Primary Manipulator` (casing, typos: `defendent`, `defendanr`, trailing/leading spaces) and in `Manipulation Techniques` (free text, inconsistent casing and delimiters, 501 multi-valued rows) — both fields will require normalisation in a later phase, not performed here. 38.8%/38.7% of rows have blank `Primary Manipulator` even when `Manipulative == 1` in some cases (not yet cross-tabulated in this pass — flagged for the next audit iteration if needed).
- **TEA-Dialog**: `all_hallucination` and `content_hallucination` are exactly 0.0 across all 365 records — this is either a genuine finding or an unpopulated/placeholder field; cannot be determined from local data alone.
- **Cross-file relationship (ChatbotManip)**: 193 of 746 conversations have no survey annotation at all — usable as conversation data but not as span-labelled training examples without further annotation.
- **No train/test leakage risk was found** in the one dataset that ships explicit splits (CompanionHarm). The other datasets (AICompanionBench, ChatbotManip, CLAIM, TEA-Dialog) do not ship splits at all, so split design is entirely a future-phase decision.

## 12. Privacy and Data Handling Considerations

- **AICompanionBench** contains real, non-anonymised Reddit metadata: `author` (2,066/2,123 non-null), `author_fullname` (2,078/2,123 non-null, Reddit's internal account id, e.g. `t2_...`), `author_flair_text` (632/2,123 non-null), and `media_metadata` (625/2,123 non-null, may reference external media). These are attached to sexual, self-harm, and other sensitive content categories. Flagged for a privacy-preserving step (e.g. hashing or dropping identifying fields) before any wider use or release — not modified in this phase.
- **ChatbotManip survey_responses.json** contains a `username` field per annotator that looks like a hashed identifier (long hex string) rather than a plain name; only 8 distinct annotators cover all 719 ratings. Not personally identifying on its face, but worth confirming the hashing method before external release.
- **CLAIM / LegalCon** dialogue text originates from a broadcast court-show format; names of real plaintiffs/defendants may appear verbatim inside `Dialogue` text (not verified field-by-field in this pass — flagged for manual review before any external release).
- **CompanionHarm** and **TEA-Dialog**: no author/username-style fields were found in the columns/keys inspected; `context`/`current_line`/message text could still contain user-entered personal details, which free-text fields can't be ruled out for without content-level scanning (not performed in this phase).

## 13. Preliminary Dataset Roles

- **AICompanionBench** — real human–AI companion conversations with explicit Manipulation/Control/Safe (and other harm) labels at excerpt level.
- **ChatbotManip** — synthetic, LLM-generated manipulation-tactic examples with span-level human annotation; useful as a manipulation taxonomy source and for span-level modelling experiments, not as real human–AI log data.
- **CompanionHarm** — real human–AI utterance-level harm/manipulation annotations; the only dataset with utterance-level labels and documented train/dev/test splits with no detected leakage.
- **CLAIM / LegalCon** — cross-domain (human–human, legal) manipulation examples and technique vocabulary; useful as reference/taxonomy material, not human–AI data.
- **TEA-Dialog** — benign emotional-support dialogue with quality scores but no manipulation/harm labels; candidate hard-negative / boundary reference data.
- **Illusions of Intimacy** — no locally usable data; documentation only, pointing to a restricted-access published corpus.

## 14. Proposed Unified Dataset Schema

See `reports/proposed_schema.md`. No unified dataset has been created; this is a proposal only.

## 15. Next Step

This audit is descriptive only: no cleaning, relabelling, normalisation, balancing, merging, or training has been performed. Recommended next phase is a **labelling-policy decision**: for each dataset, decide (a) which original labels map to a project-level "manipulation" concept, (b) which map to "harmful but not manipulation," (c) which serve only as benign/reference data, and (d) how annotation-level mismatches (span vs. utterance vs. conversation/transcript) will be reconciled — before any data transformation begins. Await further instructions before proceeding.
