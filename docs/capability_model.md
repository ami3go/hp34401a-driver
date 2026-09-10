# Capability model

The RFDS-013 capability model has two synchronized representations:

- runtime implementation: `rf_hp34401a/capabilities.py`;
- reviewed static artifact: `capability/capability_model.yaml`.

Both identify driver version 26.07 and the same modeled capability IDs/Robot bindings. Operation timing and retry safety are explicit properties; retry safety is not inferred from a generic risk class.

Runtime discovery is available through:

- `Get Driver Capabilities` — RFDS-002 list of stable high-level capability IDs;
- `Get Driver Capability Model` — detailed RFDS-013 model;
- `Get Driver Capability` — one detailed capability;
- `Find Driver Capabilities` — filtered capability query;
- `Get Driver Features`;
- `Refresh Driver Capabilities`;
- `Validate Driver Capabilities`.

`Validate Driver Capabilities` compares model bindings to the **actual decorated effective Robot surface**, including inherited facade methods. It does not validate the capability registry against a list generated from the same registry.

Example:

```robotframework
${model}=    Get Driver Capability Model    mode=static
${voltage}=  Get Driver Capability    measure.voltage.dc    mode=static
${matches}=  Find Driver Capabilities    capability_id=measure.    maximum_risk=low    mode=static
${valid}=    Validate Driver Capabilities
Should Be True    ${valid}[valid]
```

`static` mode performs no device I/O. `live`/`effective` mode may refresh connected identity as documented by the public API.
