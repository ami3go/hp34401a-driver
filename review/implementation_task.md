# Production Implementation Task: Robot Framework Driver for HP/Agilent/Keysight 34401A

## Document status

| Item | Value |
|---|---|
| Task status | **Ready for implementation** |
| Final task quality score | **9.7 / 10** |
| Target release | `rf_hp34401a_v26.01.zip` |
| Required ZIP root folder | `rf_hp34401a/` |
| Source baseline | `hp34401a-production-dmm` version `1.2.8` |
| Implementation strategy | Thin Robot Framework adapter over the existing Python driver |
| Repository layout | Flat layout; **do not use a `src/` directory** |
| Primary platforms | Windows 11 and Linux |
| Python compatibility target | Python 3.10–3.13 |
| Robot Framework compatibility target | Robot Framework 7.x |

---

# 1. Review of the original request

## 1.1 Original request interpreted as an implementation task

Create a Robot Framework driver based on the supplied HP/Agilent/Keysight 34401A Python driver, review the task for production readiness, identify missing requirements, and revise the task until it is sufficiently precise to guide an implementation with a quality score of at least 9.5/10.

## 1.2 Initial task-readiness score: 4.8 / 10

The original request correctly identifies the desired result but does not define:

- the required package and internal folder names;
- whether the existing Python driver should be reused, forked, or rewritten;
- the Robot Framework library architecture;
- required keywords and return-value conventions;
- error, overload, timeout, and connection behavior;
- hardware-independent and hardware-in-the-loop test requirements;
- documentation, examples, scripts, release files, and GitHub Pages requirements;
- acceptance criteria and Definition of Done;
- supported Python, Robot Framework, transport, and operating-system versions;
- how the library should expose multiple instruments or connection aliases;
- how raw SCPI access and calibration commands should be controlled;
- release traceability and code-review requirements.

Without these decisions, two implementers could produce materially different packages and both claim completion.

---

# 2. Source-package readiness assessment

The supplied archive was reviewed as the implementation baseline.

## 2.1 Verified source facts

- Python package: `hp34401a_dmm`
- Source version: `1.2.8`
- Flat repository layout with no `src/` folder
- Supported core transports:
  - RS-232 through PySerial
  - GPIB through PyVISA and a vendor VISA implementation
  - deterministic fake transport for tests
- Major existing capabilities:
  - connection and identity validation;
  - DC and AC voltage configuration;
  - DC and AC current configuration;
  - 2-wire and 4-wire resistance;
  - frequency, period, continuity, and diode modes;
  - immediate and BUS-triggered acquisition;
  - SCPI error-queue handling;
  - timeout recovery and guarded query retry;
  - overload detection;
  - stable-resistance acquisition;
  - terminal verification;
  - production step and sequence models;
  - CSV and JSONL logging utilities;
  - thread-safety option;
  - calibration-command protection.
- Existing automated-test result:
  - **67 tests passed**
  - **2 real-hardware tests skipped when hardware variables were absent**
- Measured source line coverage: **73%**
- Python wheel build: **successful**
- No existing Robot Framework library, Robot tests, Robot examples, Libdoc output, or Robot-specific documentation

## 2.2 Source readiness score: 8.8 / 10

| Area | Score | Assessment |
|---|---:|---|
| Core architecture | 9.4 | Strong transport abstraction and centralized SCPI behavior |
| Functional coverage | 9.1 | Covers the essential 34401A measurement and trigger modes |
| Safety and data integrity | 9.4 | Explicit overload behavior, no fabricated readings, guarded recovery |
| Unit-test baseline | 8.6 | 67 passing tests; core logic is well exercised |
| Overall coverage | 7.4 | 73% is acceptable as a baseline but should be raised |
| Packaging | 9.0 | Valid flat package and successful wheel build |
| Hardware verification | 7.0 | HIL tests exist but were not executed in this review |
| Robot Framework readiness | 8.7 | Public APIs are suitable for a thin adapter; adapter does not yet exist |

## 2.3 Architecture decision

**Do not rewrite the SCPI driver.**

Implement a thin, typed Robot Framework adapter that delegates instrument behavior to `hp34401a_dmm.Hp34401A`. The Robot layer shall provide:

- Robot-friendly keyword names and argument conversion;
- named connection sessions;
- deterministic return values;
- failure messages suitable for Robot reports;
- assertion keywords;
- full reading metadata conversion to dictionaries;
- automatic resource cleanup;
- Robot-specific documentation and tests.

Any source-driver defect discovered during implementation must be corrected in the core driver, covered by a regression test, and recorded in both `history/` and `review/`. SCPI behavior must not be duplicated inside the Robot adapter.

---

# 3. Objective

Develop a production-ready Robot Framework library for the HP/Agilent/Keysight 34401A DMM using the supplied `hp34401a_dmm` version 1.2.8 driver as the core implementation.

The completed package shall support automated laboratory and production testing over:

- VISA/GPIB;
- RS-232;
- deterministic simulation for automated tests and examples.

The library shall preserve the source driver's core principle:

> Invalid, stale, unstable, or overload data must not be silently returned as a valid measurement.

---

# 4. Required release structure

The release archive shall be named:

```text
rf_hp34401a_v26.01.zip
```

The archive shall contain exactly one top-level project folder:

```text
rf_hp34401a/
```

Required project structure:

```text
rf_hp34401a/
├── rf_hp34401a/                  # Robot Framework Python package
│   ├── __init__.py
│   ├── library.py
│   ├── sessions.py
│   ├── converters.py
│   ├── exceptions.py
│   └── version.py
├── hp34401a_dmm/                 # Reviewed core driver, no src/ layout
├── tests/
│   ├── unit/
│   ├── robot/
│   ├── integration/
│   ├── hil/
│   └── support/
├── examples/
│   ├── 01_identify_and_health.robot
│   ├── 02_dc_voltage_limits.robot
│   ├── 03_ac_voltage.robot
│   ├── 04_dc_current.robot
│   ├── 05_two_wire_resistance.robot
│   ├── 06_four_wire_resistance.robot
│   ├── 07_stable_resistance.robot
│   ├── 08_frequency_and_period.robot
│   ├── 09_bus_trigger.robot
│   ├── 10_error_queue_and_recovery.robot
│   ├── 11_rs232_connection.robot
│   └── 12_production_sequence.robot
├── scripts/
│   ├── setup_venv.bat
│   ├── setup_venv.ps1
│   ├── setup_venv.sh
│   ├── run_example.bat
│   ├── run_example.ps1
│   ├── run_example.sh
│   ├── run_all_examples.bat
│   ├── run_all_examples.ps1
│   ├── run_all_examples.sh
│   ├── run_tests.bat
│   ├── run_tests.ps1
│   ├── run_tests.sh
│   ├── run_hil_tests.bat
│   ├── run_hil_tests.ps1
│   ├── run_hil_tests.sh
│   ├── generate_libdoc.bat
│   ├── generate_libdoc.ps1
│   ├── generate_libdoc.sh
│   └── build_release.py
├── history/
│   └── v26.01.md
├── review/
│   ├── v26.01_code_review.md
│   ├── v26.01_readiness_review.md
│   ├── requirement_traceability.md
│   └── known_risks.md
├── guide/
│   ├── pycharm_robot_framework_setup.md
│   ├── windows_visa_gpib_setup.md
│   ├── linux_visa_gpib_setup.md
│   ├── rs232_setup.md
│   ├── hardware_test_setup.md
│   └── troubleshooting.md
├── docs/
│   ├── index.md
│   ├── installation.md
│   ├── quick_start.md
│   ├── keywords.md
│   ├── architecture.md
│   ├── examples.md
│   ├── safety.md
│   ├── migration.md
│   └── release_notes.md
├── generated/
│   └── libdoc/
├── .github/
│   └── workflows/
│       ├── ci.yml
│       ├── pages.yml
│       └── hil-manual.yml
├── mkdocs.yml
├── pyproject.toml
├── requirements.txt
├── requirements-dev.txt
├── requirements-hardware.txt
├── README.md
├── CHANGELOG.md
├── LICENSE
├── CONTRIBUTING.md
├── SECURITY.md
└── MANIFEST.in
```

No `src/` directory is permitted.

Generated build outputs, virtual environments, Robot output files, and caches shall not be stored in the release ZIP.

---

# 5. Robot Framework library design

## 5.1 Main library

Implement:

```python
class Hp34401ALibrary:
    ROBOT_LIBRARY_SCOPE = "SUITE"
    ROBOT_AUTO_KEYWORDS = False
```

Requirements:

- expose keywords only through explicit `@keyword` decorators;
- use SUITE scope to keep one controlled session registry per suite;
- support named aliases, with `default` as the default alias;
- allow multiple DMM sessions without sharing driver state;
- close all open sessions during library teardown;
- make repeated close operations safe and idempotent;
- retain the last complete `MeasurementReading` for each alias;
- provide the library and core-driver versions in logs and metadata;
- never expose internal helper methods as keywords.

## 5.2 Session behavior

The session manager shall:

- reject duplicate aliases unless `replace=${TRUE}` is explicitly supplied;
- make the selected active alias explicit;
- raise a clear error when no session is open;
- close a partially opened transport if identity validation or initialization fails;
- isolate state, last reading, reconnect count, and transport metadata by alias;
- support `Close All DMMs` in suite teardown even after a prior test failure.

---

# 6. Required keyword groups

Exact keyword names may only be changed when the replacement is clearer and the change is recorded in the traceability matrix.

## 6.1 Connection and session keywords

- `Open DMM Via VISA`
- `Open DMM Via Serial`
- `List VISA Resources`
- `Select DMM`
- `Get Active DMM Alias`
- `Get Open DMM Aliases`
- `DMM Should Be Connected`
- `Close DMM`
- `Close All DMMs`

`Open DMM Via VISA` shall support:

- resource;
- alias;
- timeout;
- optional VISA library;
- reset-on-connect;
- identity verification;
- error-queue drain;
- retry policy;
- calibration-command permission.

`Open DMM Via Serial` shall support:

- port;
- alias;
- baud rate;
- parity;
- data bits;
- stop bits;
- timeout;
- DTR/DSR;
- remote-on-connect;
- local-on-close;
- identity verification;
- retry policy;
- calibration-command permission.

## 6.2 Identity, status, health, and recovery

- `Identify DMM`
- `DMM Model Should Be 34401A`
- `Run DMM Self Test`
- `DMM Self Test Should Pass`
- `Get DMM Health`
- `Recover DMM`
- `Clear DMM Status`
- `Read DMM Error`
- `Get DMM Error Queue`
- `DMM Error Queue Should Be Empty`
- `Get DMM Input Terminal`
- `Require DMM Input Terminal`
- `Get DMM State`
- `Get DMM Driver Version`
- `Get Robot DMM Library Version`

## 6.3 Measurement configuration

- `Configure DC Voltage`
- `Configure AC Voltage`
- `Configure DC Current`
- `Configure AC Current`
- `Configure 2 Wire Resistance`
- `Configure 4 Wire Resistance`
- `Configure Frequency`
- `Configure Period`
- `Configure Continuity`
- `Configure Diode`

## 6.4 Measurement acquisition

- `Read DMM`
- `Measure DC Voltage`
- `Measure AC Voltage`
- `Measure DC Current`
- `Measure AC Current`
- `Measure 2 Wire Resistance`
- `Measure 4 Wire Resistance`
- `Measure Frequency`
- `Measure Period`
- `Measure Continuity`
- `Measure Diode`
- `Read Stable Resistance`
- `Try Read Stable Resistance`
- `Get Last DMM Reading`
- `Get Last DMM Reading Value`

Convenience measurement keywords not directly present in the core driver shall call the existing core configuration method followed by `read_once()`. They shall not contain duplicated SCPI command strings.

## 6.5 Trigger keywords

- `Set DMM Trigger Source`
- `Initiate DMM Measurement`
- `Send DMM Bus Trigger`
- `Fetch DMM Readings`
- `Read DMM Once With Bus Trigger`

BUS-trigger keywords must preserve the source driver's safe sequence:

```text
configure → BUS trigger source → INITiate → wait-for-trigger → *TRG → FETCh?
```

The adapter must not issue `READ?` while BUS triggering is active.

## 6.6 Assertion keywords

- `DMM Reading Should Be Valid`
- `DMM Reading Should Not Be Overload`
- `DMM Reading Should Be Between`
- `DMM Reading Should Be Close To`
- `DMM Reading Should Be Greater Than`
- `DMM Reading Should Be Less Than`
- `Stable Resistance Should Be Between`
- `DMM Should Have No Errors`

Assertion failures shall include:

- measured value and unit;
- expected value or limits;
- active alias;
- measurement function;
- range/NPLC where available;
- overload, retry, reconnect, and recovery information where relevant.

## 6.7 Controlled raw-SCPI keywords

- `Write DMM Command`
- `Query DMM Command`

Requirements:

- delegate to the source driver's guarded `write()` and `query()` methods;
- preserve calibration-command blocking by default;
- document that raw SCPI can alter measurement state;
- never add an unguarded direct transport-write keyword;
- log the command at debug level without logging secrets or unrelated environment data.

---

# 7. Argument conversion rules

The Robot adapter shall provide centralized converters. Keyword methods shall not implement ad-hoc conversion independently.

## 7.1 Accepted string forms

Conversions shall be case-insensitive and whitespace-tolerant.

Examples:

- range: `AUTO`, `MIN`, `MAX`, `DEF`, or a numeric value;
- NPLC: `0.02`, `0.2`, `1`, `10`, `100`;
- AC filter: `3`, `20`, `200`;
- aperture: `0.01`, `0.1`, `1`;
- trigger source: `IMMEDIATE`, `BUS`, `EXTERNAL`;
- terminal: `FRONT`, `REAR`;
- Boolean: native Robot Boolean values and documented true/false strings;
- timeout and settling durations: numeric seconds or Robot time strings such as `500 ms` and `10 s`.

Invalid enum or range values shall fail before sending a command to the instrument.

## 7.2 Return-value policy

Production measurement keywords shall:

1. obtain a complete `MeasurementReading`;
2. store it as the alias's last reading;
3. fail if the reading is invalid or overload;
4. return a numeric scalar only when valid.

`Get Last DMM Reading` shall return a Robot dictionary containing at least:

```text
timestamp_utc
function
value
unit
raw
range_value
nplc
aperture_s
is_overload
is_valid
was_retried
retry_count
reconnect_count
recovery_actions
terminal
transport
alias
library_version
driver_version
```

`Try Read Stable Resistance` shall return a dictionary and shall not fail solely because stability was not reached. `Read Stable Resistance` shall fail when stability was not reached and shall never return the last unstable sample as a valid result.

---

# 8. Error and safety behavior

## 8.1 Error translation

Create a Robot-layer exception type, for example:

```python
class Hp34401ARobotError(RuntimeError):
    ...
```

Translate errors only to add Robot-relevant context. Preserve the original exception as the cause.

Messages shall include the operation and alias, but shall not expose passwords, full environment dumps, or unrelated host data.

The following conditions must always fail the keyword:

- no active connection;
- identity mismatch;
- transport timeout after the configured recovery policy;
- protocol-state violation;
- invalid parse;
- overload when a scalar measurement is requested;
- unstable result from a strict stable-reading keyword;
- SCPI error assertion failure;
- disallowed calibration command;
- invalid range, NPLC, aperture, trigger source, terminal, or serial configuration.

## 8.2 No fabricated or stale data

The Robot layer shall not:

- substitute zero, NaN, the previous reading, or an empty string for an invalid measurement;
- return a stale `FETCh?` result after a failed immediate measurement;
- retry arbitrary writes by default;
- retry unsafe queries beyond the core driver's policy;
- suppress overload state;
- silently reconnect unless configured by the caller.

## 8.3 Cleanup

- Every example and HIL suite shall use teardown that closes the DMM.
- `Close All DMMs` shall continue closing remaining aliases even if one close operation fails.
- Cleanup errors shall be aggregated and reported after all close attempts.
- Serial local-on-close behavior shall remain configurable.
- A failed open operation shall not leave a session registered.

---

# 9. Simulation and test support

Use the existing `FakeTransport` for deterministic automated tests.

Simulation support shall be isolated from production hardware configuration. It may be implemented as:

- a dedicated test-support library under `tests/support/`; or
- an explicitly named `Open Simulated DMM` keyword documented as simulation-only.

Simulation must support scripted:

- identity responses;
- valid readings;
- overload readings;
- SCPI errors;
- timeout and retry behavior;
- BUS-trigger command ordering;
- stable and unstable resistance sequences;
- connection and recovery failures.

Simulation shall never be selected automatically when a real connection fails.

---

# 10. Automated testing requirements

## 10.1 Preserve source tests

All existing source-driver tests shall remain passing.

Baseline acceptance:

```text
67 passed
2 hardware tests skipped when hardware variables are absent
```

Any intentional update to an existing test must be justified in the code-review document.

## 10.2 Python unit tests

Add tests for:

- session creation, selection, replacement, and cleanup;
- duplicate aliases;
- argument conversion;
- all keyword-to-core mappings;
- return dictionary schema;
- overload rejection;
- invalid-reading rejection;
- stable and unstable resistance behavior;
- assertion messages;
- calibration-command blocking;
- raw SCPI delegation;
- teardown after failures;
- multiple independent aliases;
- version metadata;
- exception chaining;
- prevention of unintended auto-keywords.

Coverage targets:

- Robot adapter package: **at least 95% line coverage**
- Combined non-GUI project code: **at least 85% line coverage**
- Critical session, conversion, overload, trigger, and stability modules: **100% branch coverage where practical**

## 10.3 Robot Framework acceptance tests

Create Robot tests using the fake transport for at least:

1. VISA-style simulated open and identity;
2. serial-style simulated open and identity;
3. DC voltage measurement;
4. AC voltage measurement;
5. DC current measurement;
6. AC current measurement;
7. 2-wire resistance;
8. 4-wire resistance;
9. stable resistance success;
10. stable resistance timeout;
11. overload failure;
12. error-queue assertion;
13. BUS-trigger sequence;
14. invalid range rejection;
15. invalid NPLC rejection;
16. terminal assertion;
17. recovery report;
18. multiple aliases;
19. alias selection;
20. suite teardown;
21. raw command safety;
22. scalar return behavior;
23. metadata dictionary behavior;
24. retry metadata;
25. generated Libdoc import and keyword visibility.

Robot tests shall verify both PASS and expected FAIL behavior.

## 10.4 Hardware-in-the-loop tests

Provide separately tagged HIL suites for:

- VISA/GPIB;
- RS-232;
- identity;
- self-test;
- DC voltage on a known safe source;
- 2-wire resistance on a known resistor;
- optional 4-wire resistance fixture;
- error queue;
- repeated measurement;
- BUS trigger where supported by the bench configuration;
- connection close and reopen.

HIL tests shall:

- be disabled by default;
- require explicit environment variables or Robot variables;
- never reset or run self-test unless explicitly enabled;
- define safe expected ranges;
- record Python version, Robot Framework version, library version, core-driver version, instrument identity, transport, and test configuration;
- produce Robot XML, log, and report files;
- preserve a raw command transcript when debug logging is enabled.

Hardware results are required before declaring the release “hardware validated,” but are not required for the source-only implementation phase.

## 10.5 Installation and packaging tests

CI shall verify:

- clean virtual-environment installation;
- package import;
- Robot library import;
- Libdoc generation;
- wheel and source-distribution build;
- archive generation with the exact required name;
- exact top-level ZIP folder;
- no `src/` directory;
- no cache, virtual-environment, or generated Robot-output contamination;
- README quick-start smoke test;
- at least one offline example on Windows and Linux.

---

# 11. Examples

Provide at least 10 complete Robot Framework examples; 12 are required by this task.

Each example shall include:

- purpose;
- required hardware or simulation mode;
- variables;
- setup and teardown;
- expected result;
- exact command to run it;
- safe limits;
- notes about overload or connection failure.

At least eight examples shall run without hardware using deterministic simulation. Real-hardware equivalents shall be documented through variables rather than requiring users to edit the example source.

Examples shall not contain hard-coded personal paths, COM ports, or VISA resources.

---

# 12. Scripts

Scripts shall work from any current working directory by resolving the project root from the script's own location.

Required behavior:

- create or reuse `.venv`;
- install the correct dependency group;
- display Python and Robot Framework versions;
- fail on command errors;
- preserve Robot outputs under a configurable `results/` directory;
- accept a VISA resource or serial port through command-line arguments or environment variables;
- provide help text;
- quote Windows paths correctly;
- support PowerShell and CMD on Windows and shell on Linux;
- never silently install a vendor VISA implementation.

`build_release.py` shall:

1. run formatting, linting, typing, unit, and Robot tests;
2. generate Libdoc and documentation;
3. build wheel and source distribution;
4. create `rf_hp34401a_v26.01.zip`;
5. verify that its only top-level folder is `rf_hp34401a/`;
6. produce SHA-256 checksums;
7. reject untracked build outputs, secrets, virtual environments, or test results.

---

# 13. Documentation requirements

## 13.1 README

The GitHub README shall include:

- supported instrument names: HP, Agilent, and Keysight 34401A;
- package and release versions;
- supported transports;
- installation commands;
- vendor VISA requirement;
- serial configuration warning;
- Robot Framework quick start;
- example test;
- keyword-documentation link;
- GitHub Pages link;
- supported Python and Robot versions;
- test status;
- safety principles;
- known limitations;
- license;
- release-history link.

## 13.2 PyCharm and Robot Framework guide

`guide/pycharm_robot_framework_setup.md` shall explain, step by step:

1. install a supported Python version;
2. open the unpacked project in PyCharm;
3. create `.venv`;
4. select the project interpreter;
5. install the package in editable mode;
6. install Robot Framework and development dependencies;
7. install and configure a Robot Framework language-server plugin;
8. configure file associations for `.robot` and `.resource`;
9. configure a Robot run configuration;
10. pass VISA or serial variables;
11. run a simulated example;
12. run a real-hardware example;
13. open `log.html` and `report.html`;
14. debug Python library code from a Robot test;
15. resolve common import, interpreter, VISA, GPIB, and COM-port problems.

The guide must include Windows 11 commands and Linux equivalents.

## 13.3 GitHub Pages

Use MkDocs to publish current documentation.

Required:

- `mkdocs.yml`;
- navigation to installation, quick start, keywords, examples, architecture, safety, guides, troubleshooting, and release notes;
- generated Libdoc linked from the site;
- automated Pages workflow;
- links checked in CI;
- version shown on the home page;
- no broken local paths after publication.

## 13.4 History and review

`history/v26.01.md` shall document every implementation change in user-facing language.

`review/v26.01_code_review.md` shall include:

- reviewed files;
- issues found;
- severity;
- action taken;
- residual risk;
- test evidence;
- final code-quality score.

`review/requirement_traceability.md` shall map every requirement in this task to:

- implementation file;
- test file and test name;
- documentation location;
- status: implemented, tested, hardware tested, deferred, or not applicable.

No requirement may be marked complete without implementation and test evidence.

---

# 14. Dependency and packaging policy

The package shall define optional dependency groups, for example:

- core Robot library;
- VISA;
- serial;
- all hardware;
- development;
- documentation.

Robot Framework shall be a declared runtime dependency of the Robot adapter.

Hardware backends shall remain optional so that:

- the package can be imported without PySerial or PyVISA;
- Libdoc can be generated without hardware drivers;
- fake-transport tests can run in CI;
- a clear error is raised only when a missing backend is actually requested.

Preserve the source driver's MIT license and include attribution for the incorporated core.

Do not vendor NI-VISA, Keysight IO Libraries, or other proprietary runtime components.

---

# 15. CI and quality gates

CI shall run on Windows and Linux.

Minimum gates:

1. package structure check;
2. formatting check;
3. lint check;
4. static type check;
5. Python unit tests;
6. coverage thresholds;
7. Robot fake-transport tests;
8. Robot dry run;
9. Libdoc generation;
10. MkDocs build;
11. wheel and source-distribution build;
12. clean-install smoke test;
13. release-ZIP validation;
14. checksum generation.

A manual HIL workflow shall accept connection variables as protected inputs or runner environment values and shall upload the Robot evidence package.

The release must not be produced when any mandatory gate fails.

---

# 16. Out of scope for v26.01

Unless required to correct a defect affecting the Robot library, the following are out of scope:

- rewriting the core SCPI implementation;
- implementing the Prologix placeholder transport;
- modifying the existing Tkinter GUI;
- Prometheus metrics;
- a background measurement daemon;
- remote web control;
- automatic installation of vendor VISA software;
- calibration procedures or unrestricted calibration commands;
- support for DMM models other than 34401A;
- silent fallback from real hardware to simulation.

Out-of-scope items shall not be exposed as working features.

---

# 17. Implementation gates

## Gate A — Baseline and design

- unpack and normalize the source package;
- rerun the 67-test baseline;
- record coverage and build evidence;
- create architecture and keyword mapping;
- create requirement traceability;
- review public source APIs.

**Exit:** baseline preserved and no duplicated-SCPI design accepted.

## Gate B — Robot adapter core

- implement package, session manager, converters, exceptions, and connection keywords;
- add unit tests;
- validate multiple aliases and cleanup.

**Exit:** connection and status keywords pass fake-transport tests.

## Gate C — Measurement and assertions

- implement configuration, measurement, stability, trigger, metadata, and assertion keywords;
- complete unit and Robot acceptance tests;
- enforce overload and invalid-data behavior.

**Exit:** all mandatory keywords and Robot fake tests pass.

## Gate D — Documentation, examples, and scripts

- complete 12 examples;
- complete Windows/Linux scripts;
- complete README, guides, Libdoc, and GitHub Pages;
- verify offline examples.

**Exit:** documentation builds and examples run without hardware.

## Gate E — Packaging and production review

- complete CI;
- build wheel, source distribution, and required ZIP;
- verify exact structure;
- complete history, code review, risk register, and traceability;
- run clean-install tests.

**Exit:** all software-only acceptance criteria pass.

## Gate F — Hardware validation

- run approved VISA and/or serial HIL suites;
- review evidence and residual risks;
- update status to hardware validated.

**Exit:** required hardware tests pass or deviations are formally documented.

---

# 18. Acceptance criteria

The task is complete only when all applicable statements are true.

## Package

- [ ] ZIP is named `rf_hp34401a_v26.01.zip`.
- [ ] ZIP contains exactly one top-level folder named `rf_hp34401a/`.
- [ ] Project uses a flat layout and contains no `src/` folder.
- [ ] Wheel and source distribution build successfully.
- [ ] Clean virtual-environment installation succeeds.

## Robot library

- [ ] Library imports as `rf_hp34401a.Hp34401ALibrary`.
- [ ] Only explicitly decorated methods are exposed as keywords.
- [ ] SUITE-scoped named sessions work independently.
- [ ] VISA and serial connection keywords use the core driver.
- [ ] All required measurement modes are exposed.
- [ ] Scalar measurement keywords fail on overload or invalid data.
- [ ] Full reading metadata is available as a Robot dictionary.
- [ ] Stable-reading strict and non-strict variants behave as specified.
- [ ] BUS triggering does not issue `READ?`.
- [ ] Calibration commands remain blocked by default.
- [ ] Cleanup is deterministic and idempotent.

## Testing

- [ ] Existing 67 source tests remain passing.
- [ ] Hardware tests remain opt-in.
- [ ] Adapter coverage is at least 95%.
- [ ] Combined non-GUI coverage is at least 85%.
- [ ] At least 25 Robot acceptance tests pass using simulation.
- [ ] Windows and Linux CI pass.
- [ ] HIL evidence records all required software and instrument versions.

## Documentation and project requirements

- [ ] At least 12 examples are present.
- [ ] Scripts run individual and all examples.
- [ ] `history/` documents the release changes.
- [ ] `review/` contains code review, readiness, risks, and traceability.
- [ ] README is current.
- [ ] GitHub Pages builds and is current.
- [ ] PyCharm and Robot Framework setup guide is complete.
- [ ] Keyword documentation is generated with Libdoc.
- [ ] No broken documentation links remain.

## Quality

- [ ] No critical or high-severity code-review findings remain open.
- [ ] Medium findings are corrected or explicitly accepted with rationale.
- [ ] No requirement is marked complete without test evidence.
- [ ] Release checksum is generated.
- [ ] Final implementation review score is at least 9.5/10.

---

# 19. Final task-readiness score

| Dimension | Weight | Score | Weighted result |
|---|---:|---:|---:|
| Objective and scope clarity | 10% | 10.0 | 1.00 |
| Architecture and reuse decision | 15% | 10.0 | 1.50 |
| Functional keyword requirements | 15% | 9.7 | 1.46 |
| Safety and error semantics | 15% | 9.9 | 1.49 |
| Testing and coverage | 15% | 9.8 | 1.47 |
| Packaging and versioning | 10% | 10.0 | 1.00 |
| Documentation and examples | 10% | 9.8 | 0.98 |
| CI, traceability, and release gates | 10% | 9.3 | 0.93 |
| **Total** | **100%** |  | **9.83 / 10** |

Conservative declared score: **9.7 / 10**.

The score is not 10/10 because real VISA/GPIB and RS-232 hardware validation has not yet been executed against the target bench, and the exact vendor VISA environment is installation-specific. These are implementation-validation risks rather than task-definition gaps.

---

# 20. Implementation instruction

Implement the package gate by gate. Do not skip directly to release packaging. At the end of each gate:

1. run the relevant tests;
2. update `history/v26.01.md`;
3. update `review/requirement_traceability.md`;
4. update README and GitHub Pages when user-visible behavior changes;
5. record open defects and residual risk;
6. do not declare the gate complete while mandatory tests fail.

The final deliverable is the verified `rf_hp34401a_v26.01.zip` package and its associated test, review, documentation, and checksum evidence.
