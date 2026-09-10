# RF HP34401A 26.07

RFDS Robot Framework driver for the HP/Agilent/Keysight 34401A DMM.

Release 26.07 adds an RFDS-008 structured evidence engine (`hp34401a_dmm/evidence.py`) — every public keyword call is now recorded with correlated arguments, duration, and the underlying SCPI traffic, finalized into a SHA-256-hashed manifest for troubleshooting. See [Logging and Evidence](logging_and_evidence.md). This added one new keyword, `Export Diagnostic Bundle`, bringing the public API to 109 keywords.

Release 26.06 fixed real-hardware API evidence bookkeeping. The official HIL launcher now registers a file-backed Robot listener, disabled fixture profiles are recorded during suite setup as `EXCLUDED`, and the summary is logged before acceptance is asserted.

**Qualification:** D0 development candidate. The user's prior physical run proved the real VISA connection and non-fixture lifecycle/status groups; rerun v26.06 to generate corrected per-keyword evidence.

Start with [Installation](installation.md), [Quick start](quick_start.md), and [Real-hardware all-API verification](real_hardware_api_verification.md).
