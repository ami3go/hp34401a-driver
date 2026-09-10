# Windows VISA/GPIB setup

1. Install the USB-GPIB adapter vendor driver.
2. Install one compatible VISA runtime, such as Keysight IO Libraries Suite or NI-VISA.
3. Confirm the instrument at its configured GPIB address in the vendor connection utility.
4. Install `python -m pip install -e ".[visa]"`.
5. Run `List VISA Resources` or the VISA example with the discovered resource.
6. Do not install or switch VISA implementations during an active production run.
