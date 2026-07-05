"""trial-eligibility-compiler (tec).

Compiled AI reference implementation: an LLM compiles verbatim ClinicalTrials.gov
eligibility prose into a deterministic OHDSI Circe cohort definition at compile
time only. The runtime (``trcheck``) is unmodified standard OHDSI tooling — no
model in the path.
"""

__version__ = "0.1.0"
