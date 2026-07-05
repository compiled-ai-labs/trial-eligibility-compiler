"""Gate 2 — Coverage / anti-hallucination.

Bijection between source sentence ids (source/NCT03667300.md) and manifest
entries: no dropped criterion (silent omission) and no invented criterion (entry
with no matching source span). Each manifest source_span must reproduce the
verbatim source sentence for its id — the machine-checkable "the compiler did not
quietly rewrite a line".
"""

from __future__ import annotations

from tec.gates.common import GateResult, load_artifact, parse_source


def run(trial_id: str = "NCT03667300", art: dict | None = None) -> GateResult:
    r = GateResult("Gate 2 — Coverage")
    if art is None:
        art = load_artifact(trial_id)
    manifest = art["manifest"]
    source = parse_source(trial_id)

    source_ids = set(source)
    entries = manifest.get("entries", [])
    manifest_ids = [e["criterion_id"] for e in entries]
    manifest_id_set = set(manifest_ids)

    if len(manifest_ids) != len(manifest_id_set):
        dupes = sorted({i for i in manifest_ids if manifest_ids.count(i) > 1})
        r.fail(f"duplicate manifest entries for ids: {dupes}")

    dropped = source_ids - manifest_id_set
    if dropped:
        r.fail(f"dropped criteria (in source, absent from manifest): {sorted(dropped)}")

    invented = manifest_id_set - source_ids
    if invented:
        r.fail(f"invented criteria (in manifest, absent from source): {sorted(invented)}")

    # verbatim span fidelity for every shared id
    for e in entries:
        cid = e["criterion_id"]
        if cid in source and e["source_span"] != source[cid]:
            r.fail(f"{cid}: source_span does not match verbatim source sentence\n"
                   f"      source:   {source[cid]!r}\n"
                   f"      manifest: {e['source_span']!r}")

    if r.ok:
        r.note(f"bijection holds: {len(source_ids)} source ids "
               f"<-> {len(manifest_id_set)} manifest entries")
    return r


if __name__ == "__main__":
    res = run()
    print(res.summary())
    raise SystemExit(0 if res.ok else 1)
