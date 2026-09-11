# Running tests against real hardware on your own machine

This driver's simulator-backed tests (`pytest`, `tests/robot`, `tests/api`,
`tests/conformance`) run anywhere with no instrument attached — that's what
CI does. This guide is for the separate, opt-in step: pointing the driver at
a real HP/Agilent/Keysight 34401A.

It also documents the exact USB/kernel wrinkle discovered while validating
this driver's `scpi-driver-core` migration (see
[`scpi_driver_core_review.md`](scpi_driver_core_review.md)) in a sandboxed
dev environment, so you don't have to rediscover it. Run everything below on
your **host machine** (or a container with real USB device-rebind
capability) — a restricted sandbox may not be able to complete step 3.

## 1. Prerequisites

```bash
git clone https://github.com/ami3go/hp34401a-driver.git
cd hp34401a-driver
python3 -m venv .venv
source .venv/bin/activate
```

`scpi-driver-core` has no PyPI release yet, so it installs from its git repo
directly (you need read access to `ami3go/scpi-driver-core`, which is
private):

```bash
pip install -e ".[hardware]"
```

If that dependency fails to resolve, install it explicitly first:

```bash
pip install "scpi-driver-core[serial,visa] @ git+https://github.com/ami3go/scpi-driver-core.git@main"
pip install -e . --no-deps
```

## 2. Identify how your instrument is connected

- **GPIB** (a real GPIB card, or a USB-GPIB bridge that presents a VISA GPIB
  resource): needs NI-VISA or Keysight IO Libraries — `pyvisa-py` alone
  cannot drive GPIB.
- **RS-232** (a serial cable, or a USB-to-serial adapter such as a PL2303):
  needs `pyserial` only (`pip install pyserial`), no VISA layer at all.
- **USBTMC** (the instrument, or a USB-GPIB bridge, enumerates directly as a
  USB Test-and-Measurement-Class device — e.g. a
  [XyphroLabs GPIB-USB adapter](https://github.com/xyphro), which shows up
  as vendor/product `03eb:2065` "LUFA Test and Measurement Demo
  Application"): needs `pyvisa` + `pyvisa-py` + `pyusb` (no proprietary VISA
  needed). This is the case covered in detail below, since it has a real
  gotcha on Linux.

```bash
lsusb                      # look for your adapter/instrument
ls /dev/ttyUSB* /dev/ttyACM* 2>/dev/null   # RS-232 adapters
ls /dev/usbtmc* 2>/dev/null                # USBTMC devices
```

## 3. Linux USBTMC: the kernel-driver-vs-pyvisa-py conflict

If `/dev/usbtmc0` already exists, Linux's in-kernel `usbtmc` driver has
already claimed the device. That's great for talking to it directly, but
`pyvisa-py`'s USB backend goes through `libusb`/`pyusb` instead, which
**cannot** open a device the kernel driver is already holding — `pyvisa-py`
will simply not list it:

```bash
python -c "import pyvisa; print(pyvisa.ResourceManager('@py').list_resources())"
# -> only shows ASRL (serial) resources, no USB0::... entry, even though
#    lsusb shows the device
```

You have two options:

### Option A — quick, one-off (resets on unplug or reboot)

```bash
# Find the bound interface (replace 1-2 with your bus-port path from lsusb -t)
readlink -f /sys/bus/usb/devices/*/driver | grep usbtmc

# Block the kernel driver from re-claiming it, then release it:
echo "none" | sudo tee /sys/bus/usb/devices/<bus-port>:1.0/driver_override
echo "<bus-port>:1.0" | sudo tee /sys/bus/usb/drivers/usbtmc/unbind
```

Plain `unbind` without the `driver_override` line first often gets silently
re-claimed by the kernel a moment later — set the override first.

After this, `/dev/usbtmc0` disappears and `pyvisa-py` should list a
`USB0::0x03EB::0x2065::<serial>::INSTR`-style resource (VID/PID from
`lsusb`). Re-plugging the device, or a reboot, restores the kernel driver
and undoes this.

### Option B — permanent: make `/dev/usbtmc0` itself readable/writable

This repo ships [`udev/99-hp34401a-usbtmc.rules`](../udev/99-hp34401a-usbtmc.rules).
Install it:

```bash
sudo cp udev/99-hp34401a-usbtmc.rules /etc/udev/rules.d/
sudo udevadm control --reload-rules
sudo udevadm trigger
# then physically unplug and replug the adapter -- `trigger` alone does not
# reliably re-run rules that depend on attributes read at device-creation
# time, which is exactly the failure mode if this still doesn't work
```

The rule is:

```
KERNEL=="usbtmc*", ATTRS{idVendor}=="03eb", ATTRS{idProduct}=="2065", MODE="0666"
```

Two easy-to-get-wrong details, both real bugs an earlier draft of this guide
had:

- **`ATTRS` (plural), not `ATTR` (singular).** `idVendor`/`idProduct` live on
  the *parent* USB device, not on the `usbtmc0` character device node the
  rule is actually matching. `ATTR{...}` only checks the exact device the
  event fires for and will silently never match; `ATTRS{...}` walks up the
  parent chain.
- **Replug, don't just `trigger`.** `udevadm trigger` replays add-events for
  devices that are still plugged in, but on some systems the attributes this
  rule depends on aren't re-evaluated correctly without a real
  disconnect/reconnect. If `ls -la /dev/usbtmc0` still shows `root root`
  after `trigger`, unplug and replug before concluding the rule is wrong.

This rule fixes permission errors on `/dev/usbtmc0` (the direct-file check
above, and anything else that opens that device node directly). It does
**not** stop the kernel's `usbtmc` driver from claiming the interface in the
first place — for that, see Option C.

### Option C — permanent: also free the interface for `pyvisa-py`/libusb

If you additionally want `pyvisa-py` (not just direct file I/O) to see the
device, the kernel driver must not bind to it at all. Some udev versions
support setting `driver_override` from a rule, before the driver probes:

```
ACTION=="add", SUBSYSTEM=="usb", ATTR{idVendor}=="03eb", ATTR{idProduct}=="2065", ATTR{bInterfaceClass}=="fe", ATTR{driver_override}="none"
```

(here `ATTR`, singular, is correct — `idVendor`/`bInterfaceClass` genuinely
are attributes of the raw USB device/interface this rule matches, unlike the
`usbtmc0` character device in Option B). This is more kernel/distro-version
sensitive than Option B; if it doesn't take effect after a replug, fall back
to the manual `driver_override` + `unbind` from Option A each session.

### Sanity-check the raw connection first

Before touching pyvisa at all, confirm the instrument answers, independent
of any Python library:

```bash
python3 - <<'EOF'
fd = open("/dev/usbtmc0", "r+b", buffering=0)
fd.write(b"*IDN?\n")
import time; time.sleep(0.3)
print(fd.read(300))
fd.close()
EOF
```

A real 34401A replies with something like
`b'HEWLETT-PACKARD,34401A,0,11-5-2\n'`. If this doesn't work, the problem is
in the cabling/adapter, not in this driver or in pyvisa — fix that first.

Once Option A or B is done, re-run the `list_resources()` check from above;
you should see your instrument.

## 4. Identity-only check through the actual driver (safe, non-destructive)

Before running any test suite, confirm the migrated transport can talk to
the real instrument:

```bash
python3 - <<'EOF'
from hp34401a_dmm.visa_transport import VisaGpibTransport
from hp34401a_dmm.config import VisaGpibConfig

# Use the resource string pyvisa-py listed, e.g.:
config = VisaGpibConfig(resource="USB0::0x03EB::0x2065::<serial>::INSTR")
t = VisaGpibTransport(config)
t.open()
print(t.query("*IDN?"))
t.close()
EOF
```

For RS-232, use `hp34401a_dmm.serial_transport.SerialRs232Transport` with a
`SerialRs232Config(port="/dev/ttyUSB0")` instead.

## 5. Running the real-hardware Robot suite

`tests/hil/verify_all_public_api_real_hardware.robot` is fail-closed: every
physical measurement/reset/self-test family defaults to **off** and must be
explicitly enabled (see `tests/hil/profiles/real_hardware_all_api.template.yaml`).
Start with identity/health only:

```bash
./scripts/run_all_api_hil.sh "USB0::0x03EB::0x2065::<serial>::INSTR"
```

For RS-232 instead of VISA, use `scripts/run_hil_tests.sh` and pass
`--variable TRANSPORT:SERIAL --variable SERIAL_PORT:/dev/ttyUSB0`.

Only pass `--variable RUN_DC_VOLTAGE_PROFILE:True` (or the other
`RUN_*_PROFILE` variables) once you have an approved, wired, safe fixture for
that measurement — see `guide/hardware_test_setup.md` and the profile
template for what each one requires. Never enable a profile "to see what
happens" against real equipment.

Evidence lands under `results/real_hardware_all_api/rf_hp34401a/<timestamp>/`:
`real_hardware_api_coverage.{json,csv,md}`, `environment.json`,
`device_identity.json`, plus the usual Robot `output.xml`/`log.html`/`report.html`.

## 6. Troubleshooting

| Symptom | Likely cause |
|---|---|
| `pyvisa.errors.VisaIOError: ... VI_ERROR_RSRC_NFOUND` | Resource string doesn't match what `list_resources()` reports, or the kernel driver still holds the device (see step 3) |
| `pyvisa-py` lists ASRL resources but no USB one, even though `lsusb` shows the device | Kernel `usbtmc` driver has claimed the interface — do step 3 |
| `PermissionError` opening `/dev/usbtmc0` or `/dev/ttyUSB0` | Device node isn't group/world readable — `sudo chmod 666 /dev/usbtmcN` for a one-off, or install `udev/99-hp34401a-usbtmc.rules` (Option B) for a permanent fix |
| Installed the udev rule, reloaded rules, still `PermissionError` | Almost always one of: rule used `ATTR` instead of `ATTRS` (see Option B), or the device was never actually unplugged/replugged after reload — `udevadm trigger` alone is not always enough |
| `sudo: a password is required` in a CI runner or container, and unbind silently has no effect | The environment likely lacks `CAP_SYS_ADMIN` for USB driver rebinding (common in sandboxed dev containers) — this needs a real host or a container launched with USB device-rebind capability; it is not something this driver or scpi-driver-core can work around |
| `ConfigurationError: VisaTransport requires PyVISA` | `pip install pyvisa pyvisa-py pyusb` |
| `ConfigurationError: SerialTransport requires pyserial` | `pip install pyserial` |
