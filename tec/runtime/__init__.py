"""Runtime package (Part 5).

Deterministic, offline, key-free. Cohort execution is delegated to standard OHDSI
packages via ``ohdsi_bridge.R``; nothing here builds cohort SQL by hand or calls a
model. ``trcheck`` never imports ``tec.compile`` or ``tec.gates.oracle``.
"""
