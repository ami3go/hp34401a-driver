#!/usr/bin/env bash
# Diagnose and (optionally) fix pyvisa-py access to a USBTMC-bridged 34401A.
#
# Usage:
#   source .venv/bin/activate              # needs pyvisa/pyvisa-py installed
#   ./udev/diagnose_usbtmc.sh              # diagnose + report only
#   ./udev/diagnose_usbtmc.sh --fix        # also apply the unbind fix (needs sudo)
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

echo "=== 4. /dev/usbtmc* permissions ==="
ls -la /dev/usbtmc* 2>&1
echo

if [ "$FIX" != "--fix" ]; then
  echo "=== Diagnosis only (pass --fix to apply the unbind) ==="
  echo "=== 5. pyvisa-py resource list (before any fix) ==="
  list_pyvisa_resources
  exit 0
fi

echo "=== 5. Applying the fix (needs sudo) ==="
echo "none" | sudo tee "$IFACE_PATH/driver_override"
echo "$IFACE_NAME" | sudo tee /sys/bus/usb/drivers/usbtmc/unbind
echo

echo "=== 6. Driver binding after fix ==="
if [ -e "$IFACE_PATH/driver" ]; then
  echo "Still bound to: $(readlink -f "$IFACE_PATH/driver")  <-- fix did not take"
else
  echo "Unbound successfully."
fi
echo

echo "=== 7. pyvisa-py resource list (after fix) ==="
list_pyvisa_resources
