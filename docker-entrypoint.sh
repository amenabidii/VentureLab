#!/bin/sh
# Container start-up: validate the three state mounts, then drop root privileges.
# The application never runs as root.
#
# State lives in the checkout: .venturelab/ (run records, approval store, founder key),
# outputs/ and decision_log.json, bind-mounted by docker-compose.yml. On Linux the app runs
# as the owner of the mounted outputs/ folder, so files it writes stay owned by that user.
# Docker Desktop (Windows, macOS) reports mounts as root-owned but writable; then the
# image's "app" user (UID 1000) is used.
#
# Security rules (root is used for checks only, plus at most one narrow change):
# - none of the three paths may be a symlink inside the container;
# - when they are bind mounts, /proc/self/mountinfo shows the host path Docker resolved;
#   each must keep its expected name, and all must be siblings on one device, so a
#   symlink in the checkout that redirects a mount elsewhere is refused;
# - nothing is changed recursively and nothing follows a link: the only privileged change
#   is `chown -h` of .venturelab itself, and only when it is an empty, root-owned folder
#   (what Docker creates for a missing mount source) in a checkout owned by a normal user;
# - anything else that is not writable stops start-up with an explanation.
set -eu

STATE=/srv/.venturelab
OUTPUTS=/srv/outputs
LOG=/srv/decision_log.json

fail() {
  echo "venturelab: refusing to start: $*" >&2
  exit 64
}

if [ "$(id -u)" != "0" ]; then
  exec "$@"  # already unprivileged (for example docker run --user)
fi

# 1. No symlinks at the paths privileged code could touch.
for path in "$STATE" "$OUTPUTS" "$LOG"; do
  [ -L "$path" ] && fail "$path is a symbolic link; state paths must be real folders/files in the checkout"
done
[ -e "$OUTPUTS" ] && [ ! -d "$OUTPUTS" ] && fail "$OUTPUTS must be a folder"
[ -d "$LOG" ] && fail "$LOG is a folder (Docker creates one when the file is missing); restore decision_log.json from git"
[ -e "$LOG" ] && [ ! -f "$LOG" ] && fail "$LOG must be a regular file"

# 2. Bind-mount sources must be the expected siblings (detects host-side symlinks).
#    mountinfo fields: 3 = device, 4 = source path within that device, 5 = mount point.
mounts=$(awk -v s="$STATE" -v o="$OUTPUTS" -v l="$LOG" \
  '$5 == s || $5 == o || $5 == l { print $5 " " $3 " " $4 }' /proc/self/mountinfo)
parent="" device=""
state_mounted=no
if [ -n "$mounts" ]; then
  while read -r point dev src; do
    case "$point" in
      "$STATE") want=.venturelab; state_mounted=yes ;;
      "$OUTPUTS") want=outputs ;;
      "$LOG") want=decision_log.json ;;
    esac
    [ "${src##*/}" = "$want" ] || fail "$point is mounted from '$src', not from '$want' (is it a symlink in the checkout?)"
    case "$src" in */../*|*/./*|*/..|*/.) fail "$point has an unexpected mount source '$src'" ;; esac
    dir=${src%/*}
    [ -z "$parent" ] && parent=$dir && device=$dev
    [ "$dir" = "$parent" ] || fail "state mounts come from different folders ('$dir' and '$parent'); a state path is redirected"
    [ "$dev" = "$device" ] || fail "state mounts come from different file systems; a state path is redirected"
  done <<EOF
$mounts
EOF
fi

# 3. Choose the unprivileged runtime user: the owner of outputs/, never root.
uid=$(stat -c %u "$OUTPUTS" 2>/dev/null || echo 1000)
gid=$(stat -c %g "$OUTPUTS" 2>/dev/null || echo 1000)
if [ "$uid" = "0" ]; then
  uid=1000
  gid=1000
fi

# 4. The one privileged change: hand over a fresh, empty .venturelab that Docker created
#    as root for a checkout owned by a normal user. Not recursive, does not follow links.
mkdir_state=no
if [ ! -e "$STATE" ]; then
  mkdir -m 700 "$STATE"   # not mounted (plain docker run); a private folder in the container
  mkdir_state=yes
fi
if [ "$mkdir_state" = yes ] || { [ "$state_mounted" = yes ] \
    && [ "$(stat -c %u "$OUTPUTS")" != "0" ] \
    && [ "$(stat -c %u "$STATE")" = "0" ] \
    && [ -z "$(find "$STATE" -mindepth 1 -maxdepth 1 -print -quit)" ]; }; then
  [ -L "$STATE" ] && fail "$STATE changed into a symbolic link"
  chown -h "$uid:$gid" "$STATE"
  chmod 700 "$STATE"
fi

# 5. Everything the app writes must already be writable by the runtime user.
as_user() { setpriv --reuid="$uid" --regid="$gid" --clear-groups -- "$@"; }
for path in "$STATE" "$OUTPUTS"; do
  as_user test -w "$path" -a -x "$path" || fail "$path is not writable by UID $uid. Run 'docker compose up' from a checkout owned by your normal user (not root), or fix the folder's ownership yourself."
done
if [ -e "$LOG" ]; then
  as_user test -w "$LOG" || fail "$LOG is not writable by UID $uid. Fix its ownership in the checkout."
fi

export HOME=/tmp
exec setpriv --reuid="$uid" --regid="$gid" --clear-groups --no-new-privs \
  --inh-caps=-all --bounding-set=-all -- "$@"
