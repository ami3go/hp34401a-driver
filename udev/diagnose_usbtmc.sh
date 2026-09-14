#!/usr/bin/env bash
# Diagnose and (optionally) fix pyvisa-py/libusb access to a USBTMC-bridged
# 34401A. Covers both known blockers, in order:
#   1. the kernel usbtmc driver holding the interface (unbind it), and
#   2. the raw /dev/bus/usb/<bus>/<dev> node not being readable/writable by
#      libusb once it's unbound.
#
# Usage:
#   source .venv/bin/activate              # needs pyvisa/pyvisa-py/pyusb installed
#   ./udev/diagnose_usbtmc.sh              # diagnose + report only
#   ./udev/diagnose_usbtmc.sh --fix        # also apply both fixes (needs sudo)
#
# See guide/real_hardware_host_setup.md for the full explanation of what
# each step below does and why.

set -u
VID="03eb"
PID="2065"
FIX="${1:-}"

list_pyvisa_resources() {
  python3 -c "
try:
    import pyvisa
except ImportError:
    print('pyvisa not importable -- activate the project venv first (source .venv/bin/activate)')
    raise SystemExit(0)
rm = pyvisa.ResourceManager('@py')
print(rm.list_resources())
" 2>&1 | grep -v -i warn
}

probe_pyusb() {
  python3 -c "
import sys
try:
    import usb.core
except ImportError:
    print('pyusb not importable -- pip install pyusb')
    sys.exit(0)
d = usb.core.find(idVendor=0x${VID}, idProduct=0x${PID})
if d is None:
    print('usb.core.find() returned nothing for VID:PID ${VID}:${PID}')
    sys.exit(0)
print(d)
for attr in ('manufacturer', 'product', 'serial_number'):
    try:
        print(f'{attr}: {getattr(d, attr)}')
    except Exception as exc:
        print(f'{attr}: <error reading it: {exc!r}>')
"
}

echo "=== 1. USB enumeration ==="
lsusb || true
echo

echo "=== 2. Locate the device in sysfs (VID:PID ${VID}:${PID}) ==="
DEV_PATH=""
for idv in /sys/bus/usb/devices/*/idVendor; do
  [ -f "$idv" ] || continue
  v=$(cat "$idv" 2>/dev/null)
  dir=$(dirname "$idv")
  idp="$dir/idProduct"
  [ -f "$idp" ] || continue
  p=$(cat "$idp" 2>/dev/null)
  if [ "$v" = "$VID" ] && [ "$p" = "$PID" ]; then
    DEV_PATH="$dir"
    break
  fi
done

if [ -z "$DEV_PATH" ]; then
  echo "No device with VID:PID ${VID}:${PID} found in sysfs. Is it plugged in?"
  exit 1
fi
echo "Found: $DEV_PATH"

BUSNUM=$(cat "$DEV_PATH/busnum" 2>/dev/null)
DEVNUM=$(cat "$DEV_PATH/devnum" 2>/dev/null)
RAW_NODE=""
if [ -n "$BUSNUM" ] && [ -n "$DEVNUM" ]; then
  RAW_NODE=$(printf "/dev/bus/usb/%03d/%03d" "$BUSNUM" "$DEVNUM")
  echo "Raw device node: $RAW_NODE"
else
  echo "Could not read busnum/devnum from $DEV_PATH"
fi

# The TMC interface is usually the first (and only) interface: <bus-port>:1.0
IFACE_PATH=""
for cand in "$DEV_PATH"/*:1.0; do
  [ -d "$cand" ] && IFACE_PATH="$cand" && break
done
if [ -z "$IFACE_PATH" ]; then
  echo "Could not find a *:1.0 interface under $DEV_PATH -- inspect manually:"
  ls "$DEV_PATH"
  exit 1
fi
IFACE_NAME=$(basename "$IFACE_PATH")
echo "Interface: $IFACE_NAME"
echo

echo "=== 3. Current driver binding ==="
if [ -e "$IFACE_PATH/driver" ]; then
  echo "Bound to: $(readlink -f "$IFACE_PATH/driver")"
else
  echo "Not bound to any driver."
fi
if [ -f "$IFACE_PATH/driver_override" ]; then
  echo "driver_override: $(cat "$IFACE_PATH/driver_override")"
fi
echo

echo "=== 4. Device node permissions ==="
ls -la /dev/usbtmc* 2>&1
[ -n "$RAW_NODE" ] && ls -la "$RAW_NODE" 2>&1
echo

if [ "$FIX" != "--fix" ]; then
  echo "=== Diagnosis only (pass --fix to apply both fixes) ==="
  echo "=== 5. pyusb probe (before any fix) ==="
  probe_pyusb
  echo
  echo "=== 6. pyvisa-py resource list (before any fix) ==="
  list_pyvisa_resources
  exit 0
fi

echo "=== 5. Fix 1/2: unbind the kernel usbtmc driver (needs sudo) ==="
echo "none" | sudo tee "$IFACE_PATH/driver_override"
echo "$IFACE_NAME" | sudo tee /sys/bus/usb/drivers/usbtmc/unbind
if [ -e "$IFACE_PATH/driver" ]; then
  echo "Still bound to: $(readlink -f "$IFACE_PATH/driver")  <-- unbind did not take"
else
  echo "Unbound successfully."
fi
echo

if [ -n "$RAW_NODE" ]; then
  echo "=== 6. Fix 2/2: open up the raw USB device node for libusb (needs sudo) ==="
  # After unbind, the busnum/devnum captured above should still be current,
  # but re-read them in case unbinding triggered a re-enumeration.
  BUSNUM2=$(cat "$DEV_PATH/busnum" 2>/dev/null || echo "$BUSNUM")
  DEVNUM2=$(cat "$DEV_PATH/devnum" 2>/dev/null || echo "$DEVNUM")
  RAW_NODE2=$(printf "/dev/bus/usb/%03d/%03d" "$BUSNUM2" "$DEVNUM2")
  if [ -e "$RAW_NODE2" ]; then
    sudo chmod 666 "$RAW_NODE2"
    ls -la "$RAW_NODE2"
  else
    echo "$RAW_NODE2 does not exist (device may have re-enumerated under a new number -- re-run this script)"
  fi
  echo
fi

echo "=== 7. pyusb probe (after fix) ==="
probe_pyusb
echo
echo "=== 8. pyvisa-py resource list (after fix) ==="
list_pyvisa_resources
