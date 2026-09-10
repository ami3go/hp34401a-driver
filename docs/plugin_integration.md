# Plugin integration

The distribution registers exactly one RFDS driver entry point:

```text
[project.entry-points."rfds.drivers"]
rf_hp34401a = "rf_hp34401a.plugin:Hp34401APluginProvider"
```

Plugin discovery and descriptor inspection are side-effect free: they do not construct a connected session, enumerate hardware, or send SCPI commands.

## Environment validation

`Hp34401APluginProvider.validate_environment()` reports:

- Python runtime;
- Robot Framework availability;
- mandatory `rfds-core` availability, installed distribution version, and compatibility with `>=1.0,<2.0`;
- optional PyVISA capability availability;
- optional pyserial capability availability.

A missing or incompatible shared core is a failed release-environment check; it is never converted into simulation fallback.

## Artifact resolution

The source manifest identifies the RFDS capability model, configuration schema, AI contract and RFDS-019 protocol vectors. `get_descriptor()` additionally returns `resolved_artifacts`, which resolves those files from either:

1. the repository/source checkout; or
2. the installed wheel's `share/rf_hp34401a/...` data files.

`scripts/validate_installed_wheel.py` creates an isolated virtual environment, installs the built wheel without dependency resolution, discovers `rf_hp34401a` through `importlib.metadata.entry_points(group="rfds.drivers")`, loads the provider, and asserts that every resolved artifact exists. This prevents a source-only plugin from being mistaken for a valid installed distribution.

## Library construction

`create_library()` performs its library import lazily and returns an unconnected `Hp34401ALibrary`. Passing a configuration document imports/validates host configuration only; it does not connect hardware. Simulation requires an explicit SIM resource or a validated profile with `settings.simulation.enabled=true`.
