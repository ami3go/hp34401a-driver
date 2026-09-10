# Driver configuration

RFDS-014 configuration is host-side. Importing a profile never opens the DMM and never writes instrument non-volatile state. Persistence occurs only through the explicit `Save Driver Configuration` keyword.

## Authorities and integrity

The repository authorities are:

```text
config/schema.json
config/schema.lock
config/default.json
```

Installed-package copies live under `rf_hp34401a/resources/configuration/`. Unit tests require the root and packaged copies to be byte-identical.

`ConfigurationManager` verifies the structured `schema.lock` SHA-256 before it accepts any configuration. A missing, malformed, or mismatched lock fails initialization with an RFDS configuration-integrity error.

Every imported/default profile is then validated against the Draft 2020-12 JSON Schema. Unknown RFDS core keys are rejected even when the compatibility `strict=False` argument is used; extensions belong under the schema-approved `extensions` namespace.

## Safe default

`config/default.json` is disconnected and has:

- no transport resource;
- simulation disabled;
- raw SCPI disabled;
- calibration commands disabled;
- finite communication/self-test/long-measurement timeouts;
- bounded query retry;
- expected model `34401A` and terminal policy `ANY`.

Calling canonical `Connect` without a resource therefore fails. It becomes an explicit simulation connect only when a validated imported profile sets `settings.simulation.enabled=true`.

## Effective runtime settings

The active facade consumes the following settings:

| Setting | Runtime effect |
|---|---|
| `transport.resource` | Default canonical `Connect` resource |
| `transport.kind` | AUTO/VISA/SERIAL selection |
| VISA/serial framing fields | Defaults for the matching transport |
| `timeouts.communication_s` | Driver/default + live transport communication timeout |
| `timeouts.self_test_s` | Core self-test timeout policy |
| `timeouts.long_measurement_s` | Long-measurement timeout policy |
| `retry.query_enabled` | Safe query-retry enablement |
| `retry.max_query_retries` | Bounded query retry count |
| `logging.raw_traffic` | Core transport raw-traffic logging policy |
| `simulation.enabled` | Explicit permission to resolve an omitted resource to `SIM::HP34401A` |
| `simulation.identity` / `reading` | Deterministic simulator identity/value |
| `safety.allow_raw_scpi` | Raw-I/O authorization state |
| `safety.allow_calibration_commands` | Core calibration command authorization |
| `device.expected_terminal` | Optional FRONT/REAR post-connect verification |

`device.expected_model` is schema-constrained to `34401A`; normal identity verification in the core enforces the supported model when enabled.

## Precedence

The runtime precedence is:

```text
package default
→ explicitly imported/loaded profile
→ explicit Connect/keyword argument
```

Constructor `default_timeout_s` remains effective until a runtime profile has actually overridden the communication-timeout source. Explicit `Connect(timeout_s=...)` is highest priority for that connection.

`Get Driver Configuration(... include_sources=True)` reports source scope per settings leaf, for example:

```text
settings.timeouts.communication_s = PACKAGE_DEFAULT
```

or after an imported profile:

```text
settings.timeouts.communication_s = RUNTIME_IMPORT
```

## Example

```robotframework
${cfg}=    Get Driver Default Configuration
Set To Dictionary    ${cfg}[profile]    name=sim_session    description=Simulation profile    scope=SESSION
Set To Dictionary    ${cfg}[settings][simulation]    enabled=${TRUE}    reading=7.5
Set To Dictionary    ${cfg}[settings][timeouts]    communication_s=3.0
${result}=    Import Driver Configuration    ${cfg}
${state}=     Connect    alias=dmm
Should Be True    ${state}[simulated]
```

The dedicated Python regression tests prove that imported timeout/retry/safety/logging/simulation settings reach the active session/core policy rather than merely appearing in exported JSON.

## Schema version migration

The current implementation supports exactly configuration schema `1.0.0`. The `config/migrations/` directory is reserved for future reviewed migrations; there is no implicit migration engine today. A different schema version is rejected instead of being guessed or silently rewritten.
