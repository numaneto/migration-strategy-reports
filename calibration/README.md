# Contoso calibration

`contoso.json` contains sanitized observations extracted from supplied inventories.
VM, application, segment, routing-scope and endpoint identities are pseudonymous;
the domain is `contoso.local`. Original paths, names and free text are discarded.
Addressing is reused with the operator's explicit authorization. Source-local
identities are preserved; duplicates across exports require reconciliation.

The calibration contains **592 source-local VM records**, 163 declared dependency
edges and 51 VM port summaries from eight useful inputs. A ninth Office-readable
input did not expose a populated inventory/assessment table and remains a coverage
gap (`source-009`). Ninety-five populated auxiliary/unmapped tables require review;
their counts are recorded, but the report does not claim full assessment coverage.
No input provided complete per-VM CIDRs, so zero detected CIDR overlaps does **not**
prove a conflict-free address plan. Originals are discarded only with explicit
operator approval after sanitized extraction.

`output/Contoso_Migration_Report.html` is the offline EN/PT-BR/ES comparison of
four migration hypotheses. Unknown is intentional when an inventory does not
establish method-specific readiness. Unsupported tabs remain in coverage for
manual mapping; they are not treated as successfully assessed.

`generate_synthetic.py` generates a separate `synthetic/` fixture/report with
eight deliberately artificial cases exercising blockers, conversion checks,
SELinux, sizing, duplicate addressing and explicit TCP/UDP dependencies.
Never present those artificial cases as sample-derived observations.

```powershell
python decision-tree-engine\scripts\populate_from_assessment.py --input calibration\contoso.json --scenario all --customer Contoso --output-dir calibration\output
python calibration\generate_synthetic.py
```

This is deterministic ruleset calibration and regression testing, not training
an AI model. Real customer artifacts belong only in isolated Git-ignored
`Customers\<Customer>\` folders after cloning the repository into an engagement.
