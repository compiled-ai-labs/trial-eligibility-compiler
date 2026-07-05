# The refusal ledger

Six of the sixteen criteria in `source/NCT03667300.md` compile to `AMBIGUOUS`.
This is the paradigm's headline behaviour, not a coverage gap: the compiler refuses
rather than invent concept-set membership or encode a human judgment.

Each refusal is recorded in `compiled/NCT03667300/manifest.json` as an entry with
`disposition: "AMBIGUOUS"`, `cohort_rule: null`, and `concepts: []`. Gate 1 enforces
that shape; Gate 3 enforces that no AMBIGUOUS criterion corresponds to an executed
inclusion rule — a refused criterion can never change a patient's disposition.

## The compile/refuse rule

Compile a criterion (`INCLUDE`/`EXCLUDE`) **only if** the sole thing you add is a
convention a reviewer can change in one place — a unit, a numeric edge, a date
window, a reference value. **Refuse (`AMBIGUOUS`)** if you would have to invent set
*membership* or encode a *human judgment*. A compound criterion is only as
determinable as its weakest conjunct/disjunct. When in genuine doubt, refuse: a
false `AMBIGUOUS` is safe; a false `INCLUDE`/`EXCLUDE` is not.

## The six refusals

| id | source span | disposition | why refused | what would make it determinate |
|----|-------------|-------------|-------------|-------------------------------|
| I8 | "Subjects who entirely understood the study and voluntarily consented." | AMBIGUOUS | Non-clinical; consent/understanding is not represented in, and not evaluable over, any OMOP CDM. | Nothing — out of scope for a phenotype by nature. |
| E2 | "Subjects who had a history of resection of more than a half length of stomach or intestine." | AMBIGUOUS | The **extent** qualifier ("more than a half length") is not a value in the data. A gastrectomy procedure code exists, but "how much" does not. | A coded resection-extent attribute, or a protocol rule mapping specific procedures to the ">½" threshold. |
| E5 | "Subjects who had taken oral triple hypoglycemic agents within 8 weeks prior to screening." | AMBIGUOUS | "Triple" is an undefined count/combination — which three classes, taken how, over what window — with no standard concept set. | A protocol-supplied enumerated regimen (the three named drug classes and the concurrency rule). |
| E6 | "Subjects taking strong CYP3A4 inhibitors or strong CYP3A4 inducers." | AMBIGUOUS | There is **no vocabulary-native standard concept set** for the DDI-strength category. SNOMED/RxNorm/ATC do not classify drugs by CYP3A4-inhibition strength; membership is defined by an external curated regulatory list. | A protocol-supplied enumerated drug list (e.g. from FDA Clinical Drug Interaction guidance), committed as a curated concept set — then E6 becomes an `EXCLUDE`. |
| E7 | "Subjects who are pregnant or breastfeeding." | AMBIGUOUS | Compound criterion; only as determinable as its weakest disjunct. Pregnancy is modelable, but breastfeeding is poorly and inconsistently coded, so the disjunction as a whole is not reliably evaluable. | Reliable breastfeeding coding in the source data. |
| E8 | "Subjects unsuitable for participation based on clinical laboratory results or other reasons." | AMBIGUOUS | Investigator-discretion catch-all ("or other reasons"); not machine-evaluable by construction. | Not machine-evaluable — this is a human decision by design. |

## The tested demo: E6 (CYP3A4)

The fixture `fixtures/patients/p_cyp3a4_itraconazole.yaml` puts a patient on
itraconazole — a real strong CYP3A4 inhibitor. A "helpful" guess would exclude the
patient and be **correct**. The tool refuses anyway: E6 reports `AMBIGUOUS` with
provenance to the source sentence, and the patient's cohort membership is unchanged
(`IN`, because itraconazole belongs to no concept set the executed cohort tests).

Refusing a guess that would have been right is the point — the guarantee is that the
committed artifact never encodes membership the vocabulary cannot justify.

## Determinate for contrast

Ten criteria compile: I1 (age ≥ 20, demographic), I2 (T2DM), I3 (HbA1c 7–10), I4
(UACR 30–3000), I5 (eGFR ≥ 30), I6 (ARB/ACE ≥ 29 days), I7 (BMI 20–40), E1 (no
type-1/secondary/gestational diabetes), E3 (no AST/ALT > 3× ULN), E4 (no DPP-4i /
GLP-1 within 8 weeks). Each is a named Circe inclusion rule; the two that add a
convention (E3's ULN, I6's day-count) record it in `conventions.json`. See
[conventions.md](conventions.md).
