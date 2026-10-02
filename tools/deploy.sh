#!/bin/sh
# Copy the app onto a MicroPythonOS device over USB serial, then restart the device so the
# launcher picks it up (and, with --start, open the app).
#   tools/deploy.sh [--start]
# PORT (default /dev/ttyUSB0), MPREMOTE (default mpremote) and PYTHON (a python3 with
# pyserial; default python3) can be overridden.
#
# MicroPythonOS runs an asyncio REPL that mpremote cannot drive, so the TaskManager is
# stopped first (typed slowly by repl_type.py); the restart at the end brings the OS back.
set -e
cd "$(dirname "$0")/.."
APP=com.confituurke.meshcore
PORT=${PORT:-/dev/ttyUSB0}
MP=${MPREMOTE:-mpremote}
PY=${PYTHON:-python3}
DEST=:/apps/$APP

set -- "$@"
start=0
[ "$1" = "--start" ] && start=1

$PY tools/repl_type.py "$PORT" --stop
# A running radio manager prints to the console, which breaks mpremote's transfers.
$PY tools/repl_type.py "$PORT" "import sys; m = sys.modules.get('meshcore_manager'); m and m.MeshCoreManager.get_instance().stop()" 3 >/dev/null

args="connect $PORT resume fs mkdir :/apps + fs mkdir $DEST + fs mkdir $DEST/fonts"
$MP $args >/dev/null 2>&1 || true

args="connect $PORT resume"
for f in $APP/*.py $APP/MANIFEST.JSON $APP/icon_64x64.png; do
    args="$args fs cp $f $DEST/ +"
done
for f in $APP/fonts/*; do
    args="$args fs cp $f $DEST/fonts/ +"
done
eval "$MP $args"

# Check every file arrived whole (a disturbed transfer can leave an empty file).
check="import os
bad = []
for f, n in ("
for f in $APP/*.py $APP/MANIFEST.JSON $APP/icon_64x64.png $APP/fonts/*; do
    check="$check('${f#$APP/}', $(wc -c < "$f")),"
done
check="$check):
    try:
        if os.stat('/apps/$APP/' + f)[6] != n: bad.append(f)
    except OSError:
        bad.append(f)
print('BAD' if bad else 'ALL OK', bad)"
result=$($MP connect "$PORT" resume exec "$check")
echo "$result"
case "$result" in *"ALL OK"*) ;; *) echo "deploy incomplete"; exit 1 ;; esac

$MP connect "$PORT" resume exec "import machine; machine.reset()" || true   # drops the link

if [ $start -eq 1 ]; then
    sleep 12                  # boot + launcher
    $PY tools/repl_type.py "$PORT" "from mpos import AppManager; AppManager.start_app('$APP')" 3
fi
