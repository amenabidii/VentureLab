#!/bin/sh
# Starts as root only to choose an unprivileged user and prepare the state folder,
# then drops privileges. The application itself never runs as root.
#
# On Linux, bind-mounted folders belong to the host user (any UID), and Docker creates a
# missing bind-mount source (a fresh clone has no .venturelab) as root. The app therefore
# runs as the owner of the mounted outputs folder, so files it writes into the checkout
# stay owned by that user. Docker Desktop on Windows/macOS reports mounts as root-owned
# but writable; then the image's own "app" user (UID 1000) is used.
set -eu

if [ "$(id -u)" != "0" ]; then
  exec "$@"  # already unprivileged (e.g. started with --user)
fi

uid=$(stat -c %u /srv/outputs 2>/dev/null || echo 1000)
gid=$(stat -c %g /srv/outputs 2>/dev/null || echo 1000)
if [ "$uid" = "0" ]; then
  uid=1000
  gid=1000
fi

mkdir -p /srv/.venturelab /srv/outputs
# .venturelab holds only this app's private state (run records, approval store and the
# founder key), never source files, so it may be handed to the runtime user.
if [ "$(stat -c %u /srv/.venturelab)" != "$uid" ]; then
  chown -R "$uid:$gid" /srv/.venturelab 2>/dev/null || true
fi
chmod 700 /srv/.venturelab 2>/dev/null || true

# A root-owned checkout (e.g. cloned as root on a Linux server) is not writable by the
# fallback user; only then hand the output folder and the audit log to that user.
as_user() { setpriv --reuid="$uid" --regid="$gid" --clear-groups -- "$@"; }
if ! as_user test -w /srv/outputs; then
  chown -R "$uid:$gid" /srv/outputs 2>/dev/null || true
fi
if [ -f /srv/decision_log.json ] && ! as_user test -w /srv/decision_log.json; then
  chown "$uid:$gid" /srv/decision_log.json 2>/dev/null || true
fi

export HOME=/tmp
exec setpriv --reuid="$uid" --regid="$gid" --clear-groups -- "$@"
