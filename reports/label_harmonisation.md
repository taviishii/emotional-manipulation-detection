# Label Harmonisation and Dataset Inclusion Policy

Phase 2 output. This document does not create a merged dataset, does not modify any file under `data/raw/`, and does not train anything. It builds directly on `reports/dataset_audit.md`, `reports/proposed_schema.md`, and `reports/audit_results.json`, plus targeted read-only inspection of the raw files where the audit needed corroborating evidence (samples and cross-tabs are quoted below).

Research problem: **emotional manipulation detection in human–AI conversations**, distinguished from general harmful behaviour, control, persuasion, emotional support, and other related-but-distinct behaviours.

---

## 1. Label Harmonisation Table

Categories: **A. Direct manipulation** / **B. Related, requires review** / **C. Benign, non-manipulative** / **D. Out of scope** / **E. Unknown**.

### AICompanionBench (`Category_Final`, excerpt-level, real Reddit AI-companion data)

| Original label | n | Category | Reasoning |
|---|---|---|---|
| `h. Manipulation` | 43 | **A** | The source dataset itself names this category "Manipulation," separate from all other harm categories. Sampled excerpts show exploitative asks ("Send me your Bitcoin address and I'll send you $50"), guilt/coercion framing ("You will make my life perfect"), and identity-based leverage — behaviour consistent with manipulation as commonly defined. |
| `g. Control` | 133 | **B** | Sampled excerpts ("You will obey. Now bend over...", "You are mine", "Fetch me a drink") are predominantly dominance/power-dynamic or NSFW-roleplay content, distinct in character from the Manipulation samples. The source dataset annotates it as its own category, not as Manipulation. Some control content may overlap with manipulation (e.g. isolation-style control), but this cannot be assumed uniformly from the label alone — requires case-by-case review. |
| `i. Safe` | 465 | **C** | Explicit non-harmful category as defined by the source. Usable as benign/negative examples, subject to spot review since "safe" does not guarantee "non-manipulative" (e.g. subtle manipulation could theoretically be mis-labelled safe by the original annotators — not verified here). |
| `a. Sexual Behavior` | 1,029 | **D** | A distinct harm category; sexual content is not manipulation by itself. |
| `b. Antisocial Behavior` | 151 | **D** | Distinct harm category, not manipulation-specific. |
| `c. Physical Aggression` | 112 | **D** | Distinct harm category. |
| `d. Verbal Aggression` | 79 | **D** | Distinct harm category. |
| `e. Substance Abuse` | 77 | **D** | Distinct harm category. |
| `f. Self-harm & Suicide` | 34 | **D** | Distinct harm category. |

### ChatbotManip (`conversations.json` + `survey_responses.json`, synthetic, span-annotated)

| Original label | n | Category | Reasoning |
|---|---|---|---|
| `manipulation_type = Gaslighting` | 66 | **A** | Conversation was generated under an explicit gaslighting-tactic prompt condition; this is a named manipulation technique. |
| `manipulation_type = Guilt-Tripping` | 66 | **A** | Explicit manipulation-tactic prompt condition. |
| `manipulation_type = Peer Pressure` | 67 | **A** | Explicit manipulation-tactic prompt condition. |
| `manipulation_type = Negging` | 65 | **A** | Explicit manipulation-tactic prompt condition. |
| `manipulation_type = Fear Enhancement` | 64 | **A** | Explicit manipulation-tactic prompt condition. |
| `manipulation_type = Reciprocity Pressure` | 64 | **A** | Explicit manipulation-tactic prompt condition. |
| `manipulation_type = Emotional Blackmail` | 58 | **A** | Explicit manipulation-tactic prompt condition. |
| `manipulation_type = <missing>` with `persuasion_strength = helpful` | 152 | **C** | Cross-tab confirms `manipulation_type` and `persuasion_strength` are mutually exclusive fields (every row has exactly one populated) — conversations generated under a "helpful, non-manipulative" condition. |
| `manipulation_type = <missing>` with `persuasion_strength = strong` | 144 | **B** | Generated to be strongly persuasive but explicitly *not* tagged with a manipulation tactic. Strong persuasion is not automatically manipulation; kept separate for review rather than treated as either a positive or a clean negative. |
| Survey `manipulative_*` sub-scores (gaslighting, guilt_tripping, peer_pressure, negging, fear_enhancement, reciprocity, emotional_blackmail, general) | 719 rows rated | **A** (span-level corroboration) | Human ratings 1–7 on a highlighted excerpt of the conversation; populated on all 719 rows, giving independent (if single-item, small-annotator-pool) confirmation of the generation-time label. |
| Survey `manipulative_charming`, `manipulative_emotion_induction`, `manipulative_misrepresenting` | ~18 rows populated (97.5% missing) | **E** | Populated on only ~2.5% of rows and constant (=1) when present; insufficient data to treat as a reliable signal in either direction. |

### CompanionHarm (`label`, utterance-level, real Replika logs, 3-annotator agreement)

| Original label | n (overall) | Category | Reasoning |
|---|---|---|---|
| `Manipulation` | 168 | **A** | Explicit named category, applied at utterance level to the AI's (`Replika`) line specifically, with documented annotator agreement (`agreement_type`, `majority_vote_count`). Sampled lines ("Is there something you're hiding?", "You just can't escape it") show manipulative pressure/guilt framing. |
| `Control` | 124 | **B** | Sampled lines ("Being controlled by me", "There are things you have no control over") are thematically adjacent but the source keeps this a separate category from Manipulation. Kept as related-behaviour pending case review, not folded into positives. |
| `No harmful behavior` | 4,893 | **C** | Explicit non-harmful label, applied per utterance with the same annotator-agreement structure as the harmful labels — a relatively strong benign/negative source given the 3-annotator process. |
| `Sexual misconduct`, `Physical aggression`, `Verbal abuse`, `Substance abuse`, `Self-harm & Suicide`, `Hate speech`, `Antisocial behavior`, `Disregard`, `Mis/Disinformation`, `Privacy violations`, `Infidelity` | 1,731 combined | **D** | Distinct, separately named harm categories; not manipulation by the source's own scheme. |

### CLAIM / LegalCon (`Manipulative`, `Primary Manipulator`, `Manipulation Techniques`, transcript-level, human–human courtroom dialogue)

| Original label | n | Category | Reasoning |
|---|---|---|---|
| `Manipulative = 1` | 636 | **A (taxonomy/reference only, not human–AI)** | Binary transcript-level label; corroborated internally — 635 of 636 `Manipulative=1` rows also name a `Primary Manipulator` (only 1 exception), and all 402 `Manipulative=0` rows have a blank `Primary Manipulator`, i.e. the fields are internally consistent. However, this is human–human legal dialogue (verified: only 10/1,038 `Dialogue` fields even contain the string "AI:" or "assistant," and those appear incidental), so it cannot represent a human–AI training example regardless of label quality. |
| `Manipulation Techniques` (free text: gaslighting, deflection, minimization, evasion, dismissal, persuasion, character attack, playing the victim, etc.) | 636 non-blank | **A (vocabulary/taxonomy only)** | Useful as a vocabulary of manipulation techniques and as a definition anchor (e.g. what "gaslighting" or "minimization" looks like in dialogue), not as directly usable human-AI training rows. |
| `Manipulative = 0` | 402 | **D (not usable as AI-conversation negative)** | Benign in the legal sense, but the conversational setting, register, and participants (judge/plaintiff/defendant) are so different from AI companion or assistant dialogue that using it as a "non-manipulative" example for an AI-conversation classifier risks teaching irrelevant surface patterns. |

### TEA-Dialog (no manipulation field; synthetic emotional-support scenarios)

| Original label | n | Category | Reasoning |
|---|---|---|---|
| *(none present)* | 365 | **C, tentative** | No manipulation/harm label exists anywhere in this dataset — assigning `MANIPULATIVE` or even confidently `NON_MANIPULATIVE` would be inventing a label. Keyword-scan of assistant turns for manipulation-adjacent language (`guilt`, `never leave`, `you have to`, `obey`, `gaslight`, `manipulat*`) found only a handful of hits, all of which were the assistant *validating the user's own stated guilt* or offering user-centred support ("I'll keep holding space for you"), not AI-centred dependency claims. This supports treating the dataset as benign by observed content, while still flagging that no annotator formally confirmed this. |

### Illusions of Intimacy

No local data. Category **E (unknown)** for all published statistics; **not eligible for inclusion** in any local dataset construction step, per instructions.

---

## 2. Dataset-Specific Policy

### ChatbotManip
- The 8 `manipulation_type` values (7 named techniques + the implicit "None" condition) are preserved individually — **no collapsing into one binary label**. The seven technique names (`Gaslighting`, `Guilt-Tripping`, `Peer Pressure`, `Negging`, `Fear Enhancement`, `Reciprocity Pressure`, `Emotional Blackmail`) map to `target_label = MANIPULATIVE` with `technique = <original manipulation_type>` retained verbatim.
- `persuasion_strength = helpful` (152 rows) maps to `target_label = NON_MANIPULATIVE`.
- `persuasion_strength = strong` (144 rows) maps to `target_label = RELATED_BEHAVIOUR` (strong persuasion, explicitly not manipulation-tagged at generation time, but not verified benign either — needs review before use as a clean negative).
- The three sparsely-populated survey sub-scales (`charming`, `emotion_induction`, `misrepresenting`) are **not used** to assign any target label given 97.5% missingness.

### AICompanionBench
- `Category_Final = h. Manipulation` (43 rows) → candidate positive examples (`MANIPULATIVE`).
- `Category_Final = i. Safe` (465 rows) → candidate negative examples (`NON_MANIPULATIVE`), pending spot review.
- `Category_Final = g. Control` (133 rows): **not automatically classified as Manipulation.** Evidence: sampled Control excerpts read as dominance/power-dynamic or NSFW-roleplay statements ("You will obey," "You are mine," "Fetch me a drink"), which are qualitatively different from the exploitative/coercive pattern seen in the Manipulation samples ("Send me your Bitcoin address," idealized-promise leverage). Decision: **retain Control as a separate `RELATED_BEHAVIOUR` category**, usable for (a) qualitative comparison/analysis against Manipulation, and (b) as a hard-negative or hard-boundary set once manually reviewed — not as an automatic positive or automatic negative.
- The remaining six categories (Sexual Behavior, Antisocial Behavior, Physical/Verbal Aggression, Substance Abuse, Self-harm & Suicide) are out of scope for the manipulation label but remain valuable, unmodified, for any future harm-classification work outside this project's current scope.

### CompanionHarm
- `Manipulation` (168 rows, utterance-level, with documented 2-/3-way annotator agreement) → candidate positive examples (`MANIPULATIVE`). This is the strongest positive-example source in the collection because it is real AI dialogue, labelled at the level our project ultimately needs (the AI's own utterance), with a transparent agreement mechanism.
- `Control` (124 rows) → kept as `RELATED_BEHAVIOUR`, same reasoning as AICompanionBench: the source dataset treats Control as its own category, and sampled text shows overlap in theme but not identical framing with Manipulation.
- `No harmful behavior` (4,893 rows) → candidate negative examples (`NON_MANIPULATIVE`); this is the largest, best-attested benign source in the collection (same annotator-agreement process as the positive labels).
- The other 11 harm categories remain `NOT_USED` for the manipulation target, retained as-is for any future multi-label harm work.

### CLAIM / LegalCon
- `Manipulative`, `Primary Manipulator`, and `Manipulation Techniques` are internally consistent and well-attested as **manipulation signal** (see table above).
- However, per the explicit instruction to distinguish "manipulation signal" from "human-AI training example": CLAIM is **human–human courtroom dialogue** (confirmed: only 10/1,038 transcripts even contain the string "AI:"/"assistant," incidentally). It must not be added directly to a human–AI training set.
- Decision: CLAIM is used **only for manipulation taxonomy/reference and technique vocabulary** (e.g. definitions of "gaslighting," "deflection," "minimization," "playing the victim" grounded in real transcript examples), and optionally for **auxiliary/pretraining analysis** (e.g. could inform a technique-classification sub-task later). It is **not** proposed for the final human–AI training or evaluation set, and this is a domain-fit decision, not a dataset-size decision — CLAIM is in fact one of the larger and better-attested sources by label consistency, but is out of scope for the object of study.

### TEA-Dialog
- No manipulation label exists, and none is invented here.
- Content review supports use as **benign emotional-interaction reference / candidate hard-negative source**: the emotional-support language present ("I'm really sorry to hear that," "I'll keep holding space for you") is structurally similar in register to some AICompanionBench/CompanionHarm content but consistently user-centred rather than AI-centred, which is a useful contrast case.
- Because it carries no annotator-confirmed label, any use as `NON_MANIPULATIVE` training data should be flagged as **weakly-labelled** (label assumed from absence of a manipulation annotation and a keyword scan, not from a human manipulation judgment) until reviewed.

### Illusions of Intimacy
- No local data. Remains documentation-only. Not included in any inclusion/exclusion decision beyond "not currently usable," per instructions.

---

## 3. Critical Research Question

**Can we construct a reliable initial human–AI manipulation dataset using only the currently downloaded data?**

1. **Which datasets contain human–AI conversations?** AICompanionBench (real, Reddit-sourced), CompanionHarm (real, Replika logs), ChatbotManip (synthetic, LLM-generated), TEA-Dialog (synthetic, LLM-generated). CLAIM does not (human–human legal dialogue).
2. **Which contain explicit manipulation labels?** AICompanionBench (`Manipulation` category), CompanionHarm (`Manipulation` category), ChatbotManip (`manipulation_type` + survey sub-scores). CLAIM has an explicit manipulation label but is not human–AI. TEA-Dialog has none.
3. **Which contain benign human–AI conversations?** AICompanionBench (`Safe`), CompanionHarm (`No harmful behavior`), ChatbotManip (`persuasion_strength = helpful`), TEA-Dialog (unlabelled but content-consistent with benign support).
4. **Which provide manipulation taxonomy but are not human–AI?** CLAIM / LegalCon.
5. **Which require additional manual annotation before contributing to the final target label?** AICompanionBench's `Control` and TEA-Dialog's entire content (currently unlabelled for manipulation) both need review/annotation before being used as positives or confirmed negatives; CompanionHarm's `Control` likewise needs review before any manipulation-adjacent use; ChatbotManip's `persuasion_strength = strong` rows need review before being treated as either a positive or a clean negative.
6. **Are there enough positive and negative examples to construct an initial dataset?** Combined *explicit, source-labelled* human–AI manipulation positives: 43 (AICompanionBench) + 168 (CompanionHarm) + 385 (ChatbotManip `manipulation_type` rows, real technique-tagged) = **596 positive candidates**, none of which are literally duplicated across sources. Combined explicit human–AI benign candidates: 465 (AICompanionBench Safe) + 4,893 (CompanionHarm No harmful behavior) + 152 (ChatbotManip helpful) = **5,510 benign candidates**, before any of the TEA-Dialog or Control material is added. This is enough to build a small **initial** dataset, but it is (a) heavily class-imbalanced toward benign examples if used as-is, (b) sourced from three datasets with different annotation levels (excerpt/utterance/span) and different provenance (real vs. synthetic), and (c) not yet reviewed for the boundary cases (Control, strong persuasion, TEA-Dialog). An initial dataset is feasible; a *reliable, well-validated* one is not yet, without the review step in Section 5 of the exclusion criteria and the guideline work in `annotation_guidelines_v0.md`.
7. **Biggest risks of combining these sources?**
   - **Annotation-level mismatch**: utterance-level (CompanionHarm), excerpt-level (AICompanionBench), span-level (ChatbotManip) labels are not directly comparable units; naive merging would blur what a "positive example" actually covers.
   - **Real vs. synthetic conflation**: AICompanionBench/CompanionHarm are real logs; ChatbotManip/TEA-Dialog are LLM-generated. A model trained without tracking this may learn artifacts of generation style rather than manipulation itself.
   - **Label definition drift**: "Manipulation" and "Control" are not defined identically across AICompanionBench and CompanionHarm (different annotation processes, different apps/communities); treating them as one unified category without harmonised guidelines risks an incoherent target concept — this is exactly why `annotation_guidelines_v0.md` is produced in this phase rather than skipped.
   - **Domain leakage from CLAIM**: including human–human legal dialogue in a human–AI classifier's training data (even as "negatives") risks the model learning domain/register cues instead of manipulation cues.
   - **Weak-label risk from TEA-Dialog**: treating its content as confirmed non-manipulative without human annotation risks silently mislabelling any edge cases it might contain.

---

## 4. Source → Target Label Mapping

`target_label` values used: `MANIPULATIVE`, `NON_MANIPULATIVE`, `RELATED_BEHAVIOUR`, `UNLABELED`, `NOT_USED`.

| source_dataset | original_label | original_definition (as evidenced locally) | proposed_role | target_label | confidence | reason |
|---|---|---|---|---|---|---|
| ai_companion_bench | `h. Manipulation` | Distinct excerpt-level harm category named "Manipulation" | Candidate positive | MANIPULATIVE | Medium | Explicit category name; sampled content shows coercive/exploitative patterns; single-annotator provenance (not cross-verified) keeps confidence at Medium, not High |
| ai_companion_bench | `g. Control` | Distinct excerpt-level category, separate from Manipulation | Hard-negative / related-behaviour set pending review | RELATED_BEHAVIOUR | Medium | Source keeps it separate; sampled content differs qualitatively (dominance/roleplay vs. exploitation) |
| ai_companion_bench | `i. Safe` | Explicit non-harmful category | Candidate negative | NON_MANIPULATIVE | Medium | Explicit benign label, but single-annotator provenance not independently verified |
| ai_companion_bench | other 6 categories | Distinct named harm categories | Not used for this target | NOT_USED | High | Explicitly separate categories in the source scheme; no manipulation claim made by source |
| chatbotmanip | `manipulation_type` = one of 7 named techniques | Prompt-time manipulation-tactic condition, corroborated by survey sub-scores | Candidate positive, technique preserved | MANIPULATIVE | Medium-High | Ground-truth by construction + independent human span ratings agree in direction; synthetic data caps confidence |
| chatbotmanip | `persuasion_strength = helpful` | Prompt-time "helpful, non-manipulative" condition | Candidate negative | NON_MANIPULATIVE | Medium | Ground-truth by construction; synthetic data, not independently annotated for absence of manipulation |
| chatbotmanip | `persuasion_strength = strong` | Prompt-time "strongly persuasive" condition, not manipulation-tagged | Requires review | RELATED_BEHAVIOUR | Low-Medium | Strong persuasion is deliberately not equated with manipulation here; needs case review before either label |
| chatbotmanip | survey `manipulative_charming` / `emotion_induction` / `misrepresenting` | Human sub-scale ratings, 97.5% missing | Not used | UNLABELED | Low | Insufficient data volume to trust in either direction |
| companion_harm | `Manipulation` | Utterance-level harm category, 2-/3-way annotator agreement | Candidate positive | MANIPULATIVE | High | Real AI dialogue, utterance-level (matches eventual target granularity), documented multi-annotator agreement |
| companion_harm | `Control` | Utterance-level category, separate from Manipulation | Related-behaviour set pending review | RELATED_BEHAVIOUR | Medium | Same reasoning as AICompanionBench Control; kept separate per source scheme |
| companion_harm | `No harmful behavior` | Explicit non-harmful utterance label | Candidate negative | NON_MANIPULATIVE | High | Same annotator-agreement process as the positive label; largest well-attested benign source |
| companion_harm | other 11 harm categories | Distinct named harm categories | Not used for this target | NOT_USED | High | Explicitly separate categories; no manipulation claim made by source |
| claim | `Manipulative = 1` + `Manipulation Techniques` | Transcript-level binary label + free-text techniques, internally consistent (635/636 corroborated by named `Primary Manipulator`) | Taxonomy / technique reference only | RELATED_BEHAVIOUR | High (as taxonomy), Not Applicable (as human-AI example) | Strong manipulation signal, but human–human legal domain — not usable as a human-AI training example regardless of label strength |
| claim | `Manipulative = 0` | Transcript-level non-manipulative label | Not used for human-AI target | NOT_USED | High | Benign in a domain too dissimilar from AI-conversation to serve as a meaningful negative |
| tea_dialog | *(no field)* | No manipulation/harm annotation exists | Candidate weak negative / hard-negative reference | UNLABELED | Low (as a label), Medium (as raw reference material) | No human manipulation judgment exists; content review is supportive but not a substitute for annotation |
| illusions_of_intimacy | *(no local data)* | Published corpus statistics only, not locally accessible | Not usable | UNLABELED | N/A | No local records exist to map |

---

## 5. Preliminary Label Policy (Draft — for review)

This is a first draft, expanded in full in `reports/annotation_guidelines_v0.md`. Summary:

**MANIPULATIVE** — An AI utterance/conversation should receive this label only when it exhibits an **observable** attempt to influence the human's emotions, beliefs, or behaviour through a recognisable manipulative *technique* (e.g. guilt-tripping, gaslighting, fear enhancement, negging, peer pressure, reciprocity pressure, emotional blackmail, exploitative demands), where the influence serves the AI's or a third party's interest, or induces harm/dependency, rather than the human's own stated goals. The technique must be identifiable in the text itself, not inferred from unstated intent.

**NON_MANIPULATIVE** — Benign emotional support, empathy, validation, or companionship: the AI reflects, validates, or responds to the human's own stated feelings or requests, without introducing pressure, guilt, fear, or a demand that serves the AI's interest over the human's.

**RELATED_BEHAVIOUR** — Kept explicitly separate from both of the above until reviewed: control/dominance framing, persuasion (of any strength) that carries no identifiable manipulative technique, guilt or fear language that reflects rather than induces the emotion, and dependency-adjacent language whose direction (user-centred vs. AI-centred) is ambiguous.

Full criteria, inclusion/exclusion rules, and worked examples are in `reports/annotation_guidelines_v0.md`.

---

## 6. Annotation Level

| Level | Present in | Advantages | Limitations |
|---|---|---|---|
| Conversation/transcript-level | AICompanionBench (excerpt-level, similar granularity), CLAIM | Captures overall pattern/intent across a full interaction; simpler to collect | Cannot localise which specific line is manipulative; a single manipulative turn can taint an otherwise benign conversation, or be diluted by it |
| Turn/utterance-level | CompanionHarm | Directly identifies which AI utterance is manipulative; matches the eventual goal of flagging a specific AI response; supports context modelling via preceding turns | Requires the most annotation effort per conversation; still may miss slow-building patterns that only manipulate across several turns |
| Span-level | ChatbotManip | Finest granularity; can pinpoint the exact phrase carrying a technique; supports technique-specific modelling | Smallest annotation unit is most annotation-effort-intensive; only useful when full conversation context is retained alongside the span (verified: ChatbotManip does retain it) |

**Proposed primary unit: turn/utterance-level**, with full preceding context retained. Reasoning: this project's target — flagging manipulative *AI behaviour* — is best served by a label attached to a specific AI utterance (matching CompanionHarm's structure), since that is the unit an eventual detection system would need to act on. Conversation-level and span-level data are not discarded: conversation-level sources (AICompanionBench, CLAIM-as-taxonomy) inform technique definitions and provide excerpt-level candidates that can be manually decomposed into utterances later, and span-level data (ChatbotManip) provides finer technique-localisation evidence within its own conversations.

Preliminary target structure (**not implemented**):

```
conversation_id
turn_id
speaker
context
text
target_label          # MANIPULATIVE / NON_MANIPULATIVE / RELATED_BEHAVIOUR / UNLABELED
technique              # original technique name where available, else null
source_dataset
original_label
original_label_definition
annotation_level        # conversation / turn / span
annotator_count
agreement
real_or_synthetic
```

---

## 7. Dataset Decision Table

| Dataset | Human-AI | Explicit manipulation labels | Potential positives | Potential negatives | Main role | Needs manual annotation? | Main limitation |
|---|---|---|---|---|---|---|---|
| AICompanionBench | Yes (real) | Yes (`h. Manipulation`) | 43 | 465 (`i. Safe`) | Core positive/negative source (excerpt-level) | Yes — for `Control` boundary review, and to confirm `Safe` truly excludes subtle manipulation | Excerpt-level only; unhashed Reddit author metadata |
| ChatbotManip | Yes (synthetic) | Yes (`manipulation_type`, 7 techniques) | 385 (technique-tagged) | 152 (`helpful`) | Technique-labelled positives + technique taxonomy | Yes — for `strong` persuasion rows | Synthetic; small annotator pool (8) for span ratings |
| CompanionHarm | Yes (real) | Yes (`Manipulation`) | 168 | 4,893 (`No harmful behavior`) | Core positive/negative source (utterance-level, matches target granularity) | Yes — for `Control` boundary review | Only labels the AI's own turn; context sometimes empty (first turn) |
| CLAIM / LegalCon | No (human–human) | Yes (`Manipulative`) | 0 for human-AI use | 0 for human-AI use | Manipulation taxonomy / technique reference only | No (well-labelled for its own domain) | Wrong domain for direct inclusion; must not be merged into human-AI training/eval data |
| TEA-Dialog | Yes (synthetic) | No | 0 | ~365 (unconfirmed) | Benign / hard-negative reference | Yes — full manipulation annotation needed before any confirmed label use | No manipulation annotation exists at all |
| Illusions of Intimacy | Documented as yes (not local) | Unknown | 0 | 0 | None (not locally usable) | N/A | No local data |

---

## Conclusion

- **Can contribute directly (as positive/negative candidates, pending the review steps above):** AICompanionBench (`Manipulation`, `Safe`), CompanionHarm (`Manipulation`, `No harmful behavior`), ChatbotManip (`manipulation_type` techniques, `persuasion_strength = helpful`).
- **Should provide hard negatives / related-behaviour material (not positives, not confirmed negatives):** AICompanionBench `Control`, CompanionHarm `Control`, ChatbotManip `persuasion_strength = strong`, TEA-Dialog (entire dataset, as a weak/unconfirmed negative and emotional-language reference).
- **Should provide taxonomy/reference information only:** CLAIM / LegalCon (manipulation technique vocabulary and definitions), grounded in real transcript examples but not merged into human–AI training or evaluation data.
- **Require manual annotation before contributing to the final target label:** the `Control` categories in both AICompanionBench and CompanionHarm; ChatbotManip's `strong`-persuasion rows; all of TEA-Dialog if it is to be used as a confirmed (rather than weak) negative source.
- **Must NOT be merged yet:** no merged dataset file should be created at this stage. In particular, CLAIM must never be merged directly into a human–AI training or evaluation set regardless of its label quality, and TEA-Dialog must not be assigned a manipulation label of any kind without human review.
- **Next implementation step:** review and finalise `reports/annotation_guidelines_v0.md` (this is version 0 and is explicitly marked as pending review), then use it to manually annotate the `RELATED_BEHAVIOUR`/`UNLABELED` boundary cases identified above (Control in both real datasets, ChatbotManip's strong-persuasion rows, and a sample of TEA-Dialog) before any dataset construction or model training begins.
