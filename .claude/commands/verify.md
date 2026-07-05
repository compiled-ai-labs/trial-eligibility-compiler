Run the validation gates on the committed artifact (read-only).

Execute `python -m pytest -q` and report the result. This runs Gate 1 (structure),
Gate 2 (coverage / anti-hallucination), and — where the OHDSI R stack is present
(devcontainer) — Gate 3 (fixture behaviour via CirceR) and Gate 4 (determinism
+ boundaries). Locally, Gates 3 and the CirceR half of 4 skip when `Rscript` is
absent; note that in your summary.

Do not modify any file. Surface any gate failure verbatim with the offending
criterion id.
