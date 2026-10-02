#!/bin/sh
# Install the app on a MicroPythonOS device over Wi-Fi and (with --start) open it.
#   HOST_IP=<this machine's LAN address> tools/deploy.sh [--start]
# Builds the .mpk, serves it from this machine for up to two minutes, and types the install
# command into the device's REPL over USB serial (PORT, default /dev/ttyUSB0; PYTHON is a
# python3 with pyserial). Bulk copies over the serial REPL are unreliable on the SenseCAP
# Indicator, so only short commands go that way; the package itself travels over Wi-Fi.
set -e
cd "$(dirname "$0")/.."
: "${HOST_IP:?set HOST_IP to this machine's address on the device's LAN}"
APP=com.confituurke.meshcore
PORT=${PORT:-/dev/ttyUSB0}
PY=${PYTHON:-python3}
HTTP_PORT=${HTTP_PORT:-8765}

dist=$(mktemp -d)
python3 build_mpk.py >/dev/null
mv ${APP}_*.mpk "$dist/app.mpk"
log="$dist/http.log"
(cd "$dist" && timeout 120 python3 -m http.server "$HTTP_PORT" --bind "$HOST_IP" >"$log" 2>&1) &
server=$!
trap 'kill $server 2>/dev/null; rm -rf "$dist"' EXIT
sleep 1

$PY tools/repl_type.py "$PORT" "from mpos import TaskManager as T, AppManager as A; T.create_task(A.download_and_install_package('http://$HOST_IP:$HTTP_PORT/app.mpk', '$APP'))" 2 >/dev/null
i=0
until grep -q "GET /app.mpk HTTP/1.[01]\" 200" "$log"; do
    i=$((i + 1))
    [ $i -gt 60 ] && { echo "the device did not fetch the package"; exit 1; }
    sleep 1
done
sleep 8    # unpack
echo "installed"
if [ "$1" = "--start" ]; then
    $PY tools/repl_type.py "$PORT" "from mpos import AppManager; AppManager.start_app('$APP')" 2 >/dev/null
    echo "started"
fi
