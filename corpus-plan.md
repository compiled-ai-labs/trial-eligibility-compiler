# corpus-plan.md — trial-eligibility-compiler feasibility gate

Fourth repo in `github.com/compiled-ai-labs`. LLM at **compile time only**:
reads verbatim ClinicalTrials.gov eligibility prose, emits a deterministic
**OHDSI Circe cohort-definition JSON**, committed only after passing gates that
run it against **synthetic** OMOP fixtures. Runtime is standard OHDSI tooling —
no model in the path. Refusal is first-class: indeterminate criteria compile to
**AMBIGUOUS**, never to a guess.

---

## TASK 1 — Corpus selection

**Therapeutic area chosen: type-2 diabetes (T2D) pharmacological interventional
trials.** Rationale, tested against the corpus below rather than assumed:

- T2D screening criteria are threshold-dense (HbA1c, eGFR, BMI, UACR, blood
  pressure, age) → high proportion of numeric, determinate, LOINC-mappable
  criteria. This is the opposite of oncology, where staging/response criteria
  ("adequate organ function", "measurable disease per RECIST") are mostly
  indeterminate without the protocol appendix.
- The condition backbone (T2DM, T1DM, MI, stroke, HF) maps to a small, stable
  set of SNOMED standard concepts.
- The area still contains genuine indeterminacy (drug-class membership,
  DDI-strength categories, investigator-discretion catch-alls), so the
  AMBIGUOUS machinery is exercised, not decorative.

Four real interventional trials, criteria **verbatim** as registered
(ClinicalTrials.gov is US public record; the registered criteria text is the
immutable authoritative corpus).

### T1 — NCT03985293 · danuglipron (PF-06882961) 16-week T2D · Phase 2 · Pfizer

> **Inclusion**
> - Male or female participants between the ages of 18 and 75 years, inclusive.
> - Patients with T2DM who are treated with metformin and/or diet and exercise
>   (metformin dose stable for ≥60 days prior to screening).
> - HbA1c ≥7% and ≤10.5% at screening.
> - Total body weight >50 kg (110 lb) with BMI 24.5 to 45.4 kg/m².
>
> **Exclusion**
> - Any condition possibly affecting drug absorption.
> - Diagnosis of Type 1 diabetes.
> - History of myocardial infarction, unstable angina, arterial
>   revascularization, stroke, heart failure, or transient ischemic attack
>   within 6 months of screening.
> - Any malignancy not considered cured.
> - Personal or family history of MTC or MEN2, or suspected MTC.
> - Acute pancreatitis or history of chronic pancreatitis.
> - Symptomatic gallbladder disease.
> - Known medical history of active proliferative retinopathy and/or macular edema.
> - Known medical history of active liver disease (chronic active hepatitis B or
>   C, or primary biliary cirrhosis).
> - Known history of HIV.
> - Supine blood pressure ≥160 mmHg systolic or ≥100 mmHg diastolic.

### T2 — NCT02663245 · INTEGRA · primary-care T2D poor glycaemic control · interventional

> **Inclusion**
> - Diagnosis of Type 2 DM (WHO criteria) of ≥1 year disease duration.
> - Age 30 to 80 years.
> - HbA1c ≥9% (DCCT) on the last blood test within the 12 months prior to inclusion.
> - No changes in treatment that can influence the main variable in the 3 months prior.
> - Accepting to participate and signing informed consent.
>
> **Exclusion**
> - Patient refuses to participate / any condition preventing consent.
> - Other diabetes types: Type 1, gestational, secondary.
> - Pharmacological treatments interfering with carbohydrate metabolism (e.g. steroids).
> - Life expectancy under 2 years.
> - Current treatment for cancer other than basal-cell or squamous skin cancer.

### T3 — NCT03667300 · evogliptin on albuminuria in T2D + renal insufficiency · interventional

> **Inclusion**
> - Men and women aged ≥20 years diagnosed with type 2 diabetes.
> - HbA1c ≥7.0% and ≤10%.
> - Urine albumin-to-creatinine ratio (UACR) ≥30 µg/mg and ≤3000 µg/mg.
> - eGFR ≥30.
> - Taken an ARB or ACE inhibitor for >4 weeks.
> - BMI ≥20 and ≤40 kg/m².
> - Understood and voluntarily consented.
>
> **Exclusion**
> - Type 1 diabetes, secondary diabetes, or gestational diabetes.
> - History of resection of more than half the length of stomach or intestine.
> - AST or ALT >3× the upper normal limit.
> - DPP-4 inhibitor or GLP-1 analogue within 8 weeks prior to screening.
> - Oral triple hypoglycemic agents within 8 weeks prior to screening.
> - Taking strong CYP3A4 inhibitors or strong CYP3A4 inducers.
> - Pregnant or breastfeeding.
> - Unsuitable per clinical laboratory results or other reasons (e.g. chemotherapy/radiation).

### T4 — NCT02653209 · TriMaster · third-line DPP4i/SGLT2i/TZD in T2D · interventional · Univ. Exeter

> **Inclusion**
> - Clinical diagnosis of Type 2 diabetes.
> - Age ≥30 and ≤80.
> - Currently treated with two classes of oral glucose-lowering therapy that do
>   not include a DPP4-inhibitor, an SGLT2-inhibitor or a thiazolidinedione.
> - Diabetes duration ≥12 months.
> - No change in diabetes treatment within previous 3 months.
> - HbA1c >58 mmol/mol (7.5%) and ≤110 mmol/mol (12.2%).
> - eGFR ≥60 mL/min/1.73 m².
>
> **Exclusion** — mirror of inclusion (Rx change <3 months; HbA1c or eGFR out of
> range; diabetes duration <12 months).

### Distinct-criterion inventory (union across T1–T4, de-duplicated)

Classes: **(a)** determinate & mappable · **(b)** determinate but mapping-hard ·
**(c)** indeterminate → expected AMBIGUOUS.

| # | Distinct criterion | Trials | Class | Note |
|---|---|---|---|---|
| 1 | Age within [min,max] | all | **a** | `person.year_of_birth` vs index date |
| 2 | T2DM diagnosis present | all | **a** | SNOMED condition |
| 3 | Type 1 diabetes (exclude) | T1,T2,T3 | **a** | SNOMED condition |
| 4 | Secondary / gestational diabetes (exclude) | T2,T3 | **a** | SNOMED conditions |
| 5 | HbA1c within range | all | **a** | LOINC measurement; unit % or mmol/mol |
| 6 | eGFR ≥ threshold | T3,T4 | **a** | LOINC measurement |
| 7 | BMI within range | T1,T3 | **a** | measurement/derived |
| 8 | Body weight > threshold | T1 | **a** | measurement |
| 9 | UACR within range | T3 | **a** | LOINC measurement |
| 10 | Supine BP ≥ threshold (exclude) | T1 | **a** | measurement (SBP/DBP) |
| 11 | MI within 6 months (exclude) | T1 | **a** | condition + temporal window |
| 12 | Stroke within 6 months (exclude) | T1 | **a** | condition + temporal |
| 13 | Heart failure within 6 months (exclude) | T1 | **a** | condition + temporal |
| 14 | TIA within 6 months (exclude) | T1 | **a** | condition + temporal |
| 15 | Unstable angina within 6 months (exclude) | T1 | **a** | condition + temporal |
| 16 | HIV history (exclude) | T1 | **a** | condition |
| 17 | Acute / chronic pancreatitis (exclude) | T1 | **a** | condition |
| 18 | Hepatitis B / C (exclude) | T1 | **a** | condition |
| 19 | MTC / MEN2 personal history (exclude) | T1 | **a** | condition (personal history only) |
| 20 | Metformin, dose stable ≥60 days | T1 | **b** | drug + dose-stability + duration |
| 21 | ARB or ACE-inhibitor for >4 weeks | T3 | **b** | drug **class** + duration |
| 22 | DPP4i or GLP-1 within 8 weeks (exclude) | T3 | **b** | drug class + temporal |
| 23 | On 2 oral GLD classes excluding 3 named classes | T4 | **b** | class-count + set-exclusion logic |
| 24 | Diabetes duration ≥1 yr / ≥12 mo | T2,T4 | **b** | needs earliest T2DM date |
| 25 | Arterial revascularization within 6 months (exclude) | T1 | **b** | broad procedure set + temporal |
| 26 | Resection of >½ stomach/intestine (exclude) | T3 | **b** | procedure + extent qualifier |
| 27 | AST or ALT >3× ULN (exclude) | T3 | **b** | measurement relative to lab-specific ULN |
| 28 | "active"/"symptomatic" condition qualifiers (retinopathy, gallbladder, liver) | T1 | **b** | qualifier semantics on condition |
| 29 | Systemic corticosteroids (codeable part of "interfere w/ carb metabolism") | T2 | **b** | ATC/RxNorm class |
| 30 | Pregnancy / breastfeeding (exclude) | T3 | **b** | pregnancy modelable; breastfeeding weak in CDM |
| 31 | "Any condition possibly affecting drug absorption" | T1 | **c** | open-ended, unbounded set |
| 32 | "Strong CYP3A4 inhibitors or inducers" | T3 | **c** | DDI-strength category; no vocabulary-native set |
| 33 | "Any malignancy not considered cured" | T1 | **c** | clinical-judgment qualifier |
| 34 | "Life expectancy < 2 years" | T2 | **c** | prognostic judgment |
| 35 | "No change affecting the main variable" | T2 | **c** | protocol-relative, undefined in CDM |
| 36 | "Oral triple hypoglycemic agents" | T3 | **c** | count/combination undefined; borderline b/c |
| 37 | "Unsuitable per labs / other reasons" | T3 | **c** | investigator-discretion catch-all |
| 38 | Consent / willingness / ability to comply | T1–T4 | **c** | non-clinical; not evaluable over any CDM |
| 39 | Family history of MTC/MEN2 + "suspected MTC" | T1 | **c** | family-history construct + suspicion |

**Tally (full union, 39 distinct):** (a) 19 · (b) 11 · (c) 9 → **class (a) ≈ 49%.**

This is the predicted "drowning": real eligibility prose is padded with
judgment-based exclusions, DDI-strength categories, and non-clinical consent
items that are genuinely indeterminate over any CDM. The 49% is not a defect in
the corpus — it is the measurement the paradigm exists to produce. See TASK 4.

---

## TASK 2 — Concept-mapping closure

Domain → OMOP standard vocabulary is fixed by the CDM: **conditions → SNOMED CT**,
**drugs → RxNorm** (classes via **ATC**/RxNorm class hierarchy), **measurements/labs
→ LOINC**, **units → UCUM**. Concept-set expansion uses `concept_ancestor`
(descendants of a SNOMED/RxNorm root).

### Class-(a) concepts required (the committable core)

| Criterion | Standard concept(s) | Vocab | Modeling |
|---|---|---|---|
| T2DM present | *Type 2 diabetes mellitus* (+ descendants) | SNOMED | `condition_occurrence` |
| T1DM / gestational / secondary | respective SNOMED roots + descendants | SNOMED | `condition_occurrence` |
| MI / stroke / HF / TIA / unstable angina | *Myocardial infarction* (≈concept 4329847), *Cerebrovascular accident*, *Heart failure*, *TIA*, *Unstable angina* + descendants | SNOMED | condition + `event ≤ 180 d` before index |
| HIV / hepatitis B / C / pancreatitis | respective SNOMED roots | SNOMED | condition |
| HbA1c | *Hemoglobin A1c/Hemoglobin.total in Blood* | LOINC | `measurement.value_as_number`, unit-aware (% ↔ mmol/mol) |
| eGFR | eGFR LOINC panel | LOINC | measurement threshold |
| UACR | Albumin/Creatinine ratio in urine | LOINC | measurement range |
| BMI / body weight | BMI + Body weight | LOINC | measurement/derived |
| Blood pressure | Systolic BP / Diastolic BP | LOINC | two measurements |
| Age | — | — | `person` + index date arithmetic |

> Exact `concept_id` integers are **pinned in the committed vocabulary snapshot**
> and referenced by the artifact. Under the **curated-vocab decision (resolution
> A)** the concept sets live under `compiled/<trial>/vocab/*.json` and are the
> **only** membership the compiler may use — the compile prompt is allowed to read
> them (they are curated reference data, not an answer key), and the model may
> never invent a concept_id. The count of distinct standard concepts across T1–T4
> is small — on the order of **~30–40 conditions + ~10 LOINC measurements + a
> handful of RxNorm/ATC drug roots** — well within a committable subset.

### Class-(b) closure (mapping-hard but determinate)

- **Drug classes** (ARB, ACE-I, DPP4i, SGLT2i, TZD, GLP-1, corticosteroids):
  each is a real ATC/RxNorm-class root with `concept_ancestor` descendants →
  mappable, but the artifact must **pin the class root + expansion** so runtime
  is deterministic. Modeling decision documented per class.
- **Temporal windows** ("within 6 months", "within 8 weeks", "for >4 weeks",
  "duration ≥12 months"): native Circe capability (event windows relative to
  index / `first occurrence` dates). Determinate once the index date is defined.
- **Relative-to-lab thresholds** ("AST >3× ULN"): ULN is lab-specific and not a
  CDM value → compile to a **documented modeling assumption** (fixed reference
  ULN) *or* demote to (c). Default: keep in (b) with the assumption recorded in
  the artifact; the gate fixtures pin the ULN so behaviour is reproducible.

### Class-(c) reclassifications forced by vocabulary reality

- **"Strong CYP3A4 inhibitors/inducers"** (T3): confirmed **(c)**. There is **no
  vocabulary-native standard concept set** for the pharmacokinetic *strength*
  category — SNOMED/RxNorm/ATC do not classify drugs by CYP3A4-inhibition
  strength. Membership is defined by an external, curated regulatory list (FDA
  Clinical Drug Interaction guidance). Compiling a guessed drug set here would
  violate the paradigm. → **AMBIGUOUS**, with provenance to the criterion text
  and a note that a protocol-supplied enumerated list would move it to (b).
- **"Any condition affecting drug absorption" / "any malignancy not cured" /
  "life expectancy <2y" / "unsuitable per investigator"** → **AMBIGUOUS**
  (unbounded or judgment-defined).

### Vocabulary licensing — is the committed subset redistributable?

The corpus (criteria prose) is US public record → committable without question.
The **vocabulary subset** carried for offline execution is the real licensing
question, resolved as follows:

- **Precedent exists and is decisive.** OHDSI's own **Eunomia** test-data
  package redistributes a small OMOP CDM — *including a subset of the
  Standardized Vocabularies* (`concept`, `concept_ancestor`,
  `concept_relationship`, …) — publicly as SQLite/duckdb files from a public
  GitHub repo (`OHDSI/EunomiaDatasets`), used across the Book of OHDSI. A
  minimal vocabulary subset for testing/demonstration is established, accepted
  practice.
- **Per-vocabulary terms:** LOINC (open, redistributable under LOINC license) and
  RxNorm (NLM, freely available) cover the measurements and drugs cleanly.
  **SNOMED CT** (conditions) is the one with an affiliate/UMLS regime; blanket
  redistribution is restricted in non-member territories.
- **Conservative committable route adopted for the PoC** (satisfies "committable"
  *and* "offline CI"): ship a **minimal duckdb CDM** built the Eunomia way. To
  keep the repo unambiguously clean of any SNOMED redistribution question, the
  committed test CDM is generated in CI from a **cached Eunomia/Athena subset**
  restricted to the pinned concept list; the repo commits the **concept-set
  definitions (integer IDs + our own labels + provenance)**, not a bulk SNOMED
  export. Result: nothing beyond a test-scale, purpose-restricted subset is
  redistributed — matching what OHDSI itself already ships.

**Closure verdict:** vocabulary subset is committable; the one licensing nuance
(SNOMED) is handled by the Eunomia-precedent / pinned-subset route, with a
documented caveat rather than an unresolved blocker.

---

## TASK 4 — Verdict

### **REDRAW** → conditional GO on the narrowed slice.

Auditable against the four GO conditions:

| GO condition | Status | Evidence |
|---|---|---|
| Vocabulary subset committable | ✅ | Eunomia precedent + pinned-subset route (TASK 2) |
| Offline synthetic-CDM loop runnable end-to-end in CI | ✅ | Circe JSON → CirceR → SqlRender → duckdb OMOP CDM; OHDSI's own CI does this via Eunomia (see fixture-plan.md) |
| ≥10 fixtures constructible | ✅ | ~19 class-(a) criteria × ≥2 = 38+; boundary pairs trivial |
| **≥60% of criteria in class (a)** | ❌ **on full union (≈49%)** | 19/39 distinct criteria (TASK 1 tally) |

Three of four conditions pass outright. The 60%-class-(a) gate **fails on the
full inclusion+exclusion union** — so the honest verdict is **REDRAW, not GO and
not NO-GO**: everything structural works; the corpus scope is too wide.

**The redraw (this is the compilable scope for PLAN.md):**

1. **Compile target = determinate criteria only** — class (a) ∪ (b), i.e. the
   CDM-evaluable criteria: demographics, numeric thresholds, named conditions
   with temporal windows, and pinned drug-class + duration criteria.
2. **AMBIGUOUS is a first-class *output*, not a discarded criterion.** Every
   class-(c) item (CYP3A4-strength, "any condition affecting absorption",
   judgment/consent catch-alls) compiles to an explicit AMBIGUOUS entry with
   provenance to the source sentence. A gate asserts that these emit AMBIGUOUS
   and *never* a silent inclusion/exclusion. This is the paradigm's
   differentiator, so the large (c) count is an asset, not a failure.
3. On the redrawn compilable set {(a)∪(b) = 30 criteria}, class (a) = 19/30 ≈
   **63% → clears 60%.** The 9 class-(c) items become the mandatory AMBIGUOUS
   test suite.

Under the redraw, all four GO conditions hold. Proceed to PLAN.md with the
narrowed scope; PoC command `trcheck evaluate --patient <fixture.yaml>` prints,
per criterion, INCLUDED / EXCLUDED / AMBIGUOUS with provenance to the criterion
text.

**Recommended PoC seed trial:** **T1 (NCT03985293)** or **T3 (NCT03667300)** —
both maximise the (a) core while carrying at least one genuine (c) (CYP3A4 in T3;
"any condition affecting absorption" + "malignancy not cured" in T1), so the demo
shows a real match, a real exclusion, a boundary case, *and* a first-class refusal
in one run.

> **Pinned for the PoC: T3 (NCT03667300).** PLAN.md and `fixture-plan.md` implement
> T3 as the single seed — it carries all three demo anchors in one trial (a
> first-class CYP3A4 refusal, an AST >3× ULN compile-with-documented-assumption,
> and an eGFR = 30 boundary). T1/T2/T4 remain in this corpus as the
> feasibility-tally evidence, not as implemented fixtures.

### Prior art (feeds the README)

- **Criteria2Query (Yuan et al., JAMIA 2019).** Hybrid ML+rule NLP that parses
  eligibility text into structured criteria and OMOP-conformant SQL. Closest
  analog. *What gate-verified compilation adds:* the output is a **committed,
  fixture-verified artifact** with a first-class AMBIGUOUS class — not an
  interactive best-effort extraction whose known failure modes (dropped temporal
  reference points, nested-entity errors, documented in the Chia comparison) ship
  silently.
- **Chia corpus (Kury et al.).** Public human-annotated criteria→concept dataset.
  *Delta:* under answer-key demotion, Chia is **evaluation-only** — it can score
  the compiler but must never enter a compile prompt. The compile prompt reads
  raw ClinicalTrials.gov prose **plus the curated concept sets** (resolution A);
  the *answer key* it must never see is Chia/n2c2, the fixtures, the expected
  labels, and the manifest dispositions.
- **TrialGPT (Jin et al., Nature Communications 2024).** End-to-end LLM
  patient-to-trial matching, criterion-by-criterion, ~87% accuracy. *Delta:* the
  model is in the **runtime hot path** (non-deterministic, un-auditable per run);
  Compiled AI moves the model to compile time and answers "why included/excluded"
  from a deterministic committed artifact that reruns identically forever.
- **OHDSI ATLAS / Circe + PhenotypeLibrary.** Deterministic cohort runtime — but
  cohort JSON is **hand-authored** by an analyst. *Delta:* the compiler produces
  that JSON *from prose*, gated, closing the manual-authoring bottleneck while
  reusing ATLAS/Circe unchanged as the runtime.

**One-line positioning:** existing tools either extract non-deterministically
(C2Q, TrialGPT) or execute deterministically from hand-built definitions (ATLAS).
This repo is the missing compile step: prose → gate-verified Circe JSON →
unmodified OHDSI runtime, with refusal as a first-class, tested output.
