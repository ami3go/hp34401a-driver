# Contributing

1. Keep SCPI behavior in `hp34401a_dmm`; the Robot adapter must delegate to the core.
2. Add or update Python and Robot tests for every behavioral change.
3. Update `history/`, `review/requirement_traceability.md`, README, and docs.
4. Run `scripts/run_tests` and `scripts/generate_libdoc` before submitting a change.
5. Do not commit virtual environments, Robot result files, caches, credentials, or hardware addresses specific to one bench.
