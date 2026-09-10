# Configuration source

JSON files in this directory are the RFDS-014 reviewable repository authorities. Runtime copies under `rf_hp34401a/resources/configuration/` shall remain byte-identical where a packaged copy exists; CI regression tests enforce that parity.

## Files

- `schema.json` — Draft 2020-12 schema for configuration version `1.0.0`.
- `schema.lock` — structured `{schema_id, schema_version, sha256}` integrity record. `ConfigurationManager` verifies it before accepting configuration.
- `default.json` — safe disconnected package default: no resource, simulation disabled, raw SCPI/calibration disabled.
- `example.json` — project example with no guessed hardware resource.
- `profiles/simulator.json` — explicit deterministic simulator profile.
- `migrations/` — reserved for future reviewed schema-version migrations; no automatic migration engine exists today.

## Runtime behavior

A validated imported profile can affect transport defaults, communication/self-test/long-measurement timeouts, safe query retries, raw-traffic logging, simulation selection/identity/reading, raw-I/O/calibration authorization, and terminal verification.

Unknown RFDS core keys are rejected even when the compatibility `strict=False` argument is supplied. Driver/vendor extensions belong in the schema-approved `extensions` object.

Do not edit `schema.json` without regenerating/reviewing both schema-lock copies and running the configuration integrity/tamper tests.
