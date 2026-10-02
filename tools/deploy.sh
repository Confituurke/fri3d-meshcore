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

$PY tools/repl_type.py "$PORT" "import mpos; mpos.TaskManager.stop()" 3 >/dev/null

args="connect $PORT resume fs mkdir :/apps + fs mkdir $DEST + fs mkdir $DEST/fonts"
$MP $args >/dev/null 2>&1 || true

args="connect $PORT resume"
for f in $APP/*.py $APP/MANIFEST.JSON $APP/icon_64x64.png; do
    args="$args fs cp $f $DEST/ +"
done
for f in $APP/fonts/*; do
    args="$args fs cp $f $DEST/fonts/ +"
done
args="$args exec \"import machine; machine.reset()\""
eval "$MP $args" || true      # the reset drops the connection

if [ $start -eq 1 ]; then
    sleep 12                  # boot + launcher
    $PY tools/repl_type.py "$PORT" "from mpos import AppManager; AppManager.start_app('$APP')" 3
fi
