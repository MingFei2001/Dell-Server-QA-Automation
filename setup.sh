#!/usr/bin/env bash
# Set up the iDRAC Day-0 staging dashboard on a fresh Ubuntu VM.
# Run from the unzipped project folder: ./setup.sh
# Non-interactive: IDRAC_USER=root IDRAC_PASS=secret PORT=5001 ./setup.sh
set -euo pipefail

cd "$(dirname "$0")"

say() { printf '\n== %s\n' "$*"; }
die() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }

[ "$(id -u)" -ne 0 ] || die "Run as a normal user with sudo, not as root."
sudo -n true 2>/dev/null || sudo -v || die "sudo is required."

say "Docker"
if ! command -v docker >/dev/null 2>&1; then
  command -v curl >/dev/null 2>&1 || { sudo apt-get update && sudo apt-get install -y curl; }
  curl -fsSL https://get.docker.com | sudo sh
fi
sudo systemctl enable --now docker >/dev/null 2>&1 || true
DOCKER="docker"
docker info >/dev/null 2>&1 || DOCKER="sudo docker"
$DOCKER compose version >/dev/null 2>&1 || die "Docker compose plugin is missing."
echo "Using: $DOCKER ($($DOCKER --version))"

say ".env"
if [ -f .env ]; then
  echo ".env exists, keeping it."
else
  user="${IDRAC_USER:-}"
  pass="${IDRAC_PASS:-}"
  port="${PORT:-}"
  if [ -z "$user" ] && [ -t 0 ]; then read -r -p "iDRAC user [root]: " user; fi
  if [ -z "$pass" ] && [ -t 0 ]; then read -r -s -p "iDRAC password [calvin]: " pass; echo; fi
  if [ -z "$port" ] && [ -t 0 ]; then read -r -p "Dashboard port [5001]: " port; fi
  user="${user:-root}"; pass="${pass:-calvin}"; port="${port:-5001}"
  case "$pass" in *[\$\ \"\'\\]*) die "Password must not contain space, \$, quotes or backslash.";; esac
  case "$port" in ''|*[!0-9]*) die "Port must be a number.";; esac
  if [ -f .env.example ]; then
    sed -e "s|^IDRAC_USER=.*|IDRAC_USER=$user|" \
        -e "s|^IDRAC_PASS=.*|IDRAC_PASS=$pass|" \
        -e "s|^PORT=.*|PORT=$port|" .env.example > .env
  else
    echo ".env.example not found, using the built-in defaults."
    printf '%s\n' "IDRAC_USER=$user" "IDRAC_PASS=$pass" "PORT=$port" "FILES_PORT=3923" "DATA_DIR=/data" \
      "TZ=Asia/Singapore" "MAX_PARALLEL=4" "TSR_TIMEOUT_MIN=30" "POLL_SECONDS=5" > .env
  fi
  chmod 600 .env
  echo "Created .env"
fi

say "Data folder"
mkdir -p data
sudo chown 1000:1000 data

say "Build and start"
$DOCKER compose up -d --build

port="$(grep -E '^PORT=' .env | cut -d= -f2)"; port="${port:-5001}"
say "Wait for dashboard"
ok=0
for _ in $(seq 1 60); do
  if curl -fs -o /dev/null "http://localhost:${port}/"; then ok=1; break; fi
  sleep 1
done
[ "$ok" -eq 1 ] || { $DOCKER compose logs --tail 40; die "Dashboard did not answer on port ${port}."; }

ip="$(hostname -I | awk '{print $1}')"
say "Done"
echo "Dashboard: http://${ip}:${port}/"
fport="$(grep -E '^FILES_PORT=' .env | cut -d= -f2)"; fport="${fport:-3923}"
echo "Files:     http://${ip}:${fport}/  (read-only, also $(pwd)/data/<serial>/<stage>/)"
echo "Logs:      $DOCKER compose logs -f"
echo "Stop:      $DOCKER compose down"
