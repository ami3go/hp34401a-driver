# AI agent implementation guide

- Preserve the stable package root `rf_hp34401a/` and flat source layout.
- Treat `rf_hp34401a/library.py` as the authoritative Robot keyword surface.
- Do not add a public keyword without updating `api/public_api.yaml`, RFDS-017, RFDS-019 inventory/vectors, tests, docs, history, and review.
- Do not duplicate SCPI in the Robot adapter; use `hp34401a_dmm`.
- Never silently fall back from hardware to simulation.
- Keep raw I/O and calibration operations explicitly authorized.
- Keep HIL disabled by default and preserve explicit profile safety variables.
- Run `scripts/validate_ai_contract.py` and `scripts/validate_call_protocol_conformance.py` after API changes.
- Use `scripts/run_all_api_hil.*` for complete physical API accounting.
- Do not claim D2 or P1 from simulator evidence.
