# Safety

The library rejects overload and invalid data. It does not silently return stale readings, retry arbitrary writes, or fall back to simulation. BUS triggering uses `INITiate → *TRG → FETCh?` and does not issue `READ?` in BUS mode. Calibration commands remain blocked by default.
