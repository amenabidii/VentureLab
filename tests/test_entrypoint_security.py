"""Security tests for docker-entrypoint.sh (privileged start-up, then privilege drop).

Static checks always run. The Docker scenarios are opt-in (VENTURELAB_DOCKER_TESTS=1):
they build the image and simulate checkouts with Linux bind-mount semantics in throwaway
folders under /tmp of the Docker host (Docker Desktop's VM or a Linux host). Each attack
asserts both that start-up is refused and that no file outside the checkout changed owner.
All data is SYNTHETIC; no running stack or approval database is touched.
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import uuid
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = (ROOT / "docker-entrypoint.sh").read_text(encoding="utf-8")
CODE = "\n".join(line for line in SCRIPT.splitlines() if not line.lstrip().startswith("#"))
IMAGE = "venturelab-entrypoint-test"


# --- static checks ----------------------------------------------------------------------

def test_no_recursive_or_link_following_privileged_operations():
    assert not re.search(r"\b(chown|chmod|chgrp)\s+(-\w*\s+)*-\w*R", CODE)
    assert not re.search(r"\brm\s", CODE) and not re.search(r"\bln\s", CODE)
    for line in re.findall(r"^.*\bchown\b.*$", CODE, re.M):
        assert "chown -h" in line, line
    # chmod is applied only to the state folder, right after a symlink check.
    assert re.findall(r"\bchmod\s+\S+\s+(\S+)", CODE) == ['"$STATE"']


def test_privileges_are_dropped_without_a_way_back():
    final = CODE.strip().splitlines()[-2:]
    joined = " ".join(final)
    assert joined.startswith("exec setpriv") and "--no-new-privs" in joined
    assert "--clear-groups" in joined and "--bounding-set=-all" in joined
    assert 'uid=1000' in CODE  # a root-owned mount never makes the app run as root


def test_dockerfile_uses_the_entrypoint_and_never_switches_back_to_root():
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    assert 'ENTRYPOINT ["/srv/docker-entrypoint.sh"]' in dockerfile
    assert not re.search(r"^USER\s+(root|0)\b", dockerfile, re.M)


# --- Docker scenarios ----------------------------------------------------------------------

docker = pytest.mark.skipif(os.environ.get("VENTURELAB_DOCKER_TESTS") != "1" or not shutil.which("docker"),
                            reason="set VENTURELAB_DOCKER_TESTS=1 (needs Docker)")


def sh(*args, check=True):
    env = dict(os.environ, MSYS_NO_PATHCONV="1")
    return subprocess.run(list(args), capture_output=True, text=True, env=env, check=check)


def host(script: str) -> str:
    """Run a shell script as root on the Docker host's /tmp (via a helper container)."""
    return sh("docker", "run", "--rm", "-v", "/tmp:/tmp", "python:3.11-slim", "sh", "-ec", script).stdout


@pytest.fixture(scope="module")
def image():
    sh("docker", "build", "-q", "-t", IMAGE, str(ROOT))
    yield IMAGE


@pytest.fixture
def base():
    path = f"/tmp/vlsec-{uuid.uuid4().hex[:12]}"
    yield path
    host(f"rm -rf '{path}'")


def checkout(base: str, owner: int, *, state: bool = False) -> None:
    host(f"mkdir -p {base}/repo/outputs && echo '[]' > {base}/repo/decision_log.json"
         + (f" && mkdir {base}/repo/.venturelab" if state else "")
         + f" && chown -R {owner}:{owner} {base}/repo && chown {owner}:{owner} {base}")


def victims(base: str) -> None:
    host(f"mkdir -p {base}/victim-dir/.venturelab {base}/victim-dir/outputs && echo s > {base}/victim-dir/f"
         f" && echo '[]' > {base}/victim-dir/decision_log.json && echo s > {base}/victim-file"
         f" && chown -R 0:0 {base}/victim-dir {base}/victim-file && chmod 600 {base}/victim-file")


def owners(base: str) -> str:
    return host(f"find {base}/victim-dir {base}/victim-file -exec stat -c '%u:%g %a %n' {{}} + | sort")


def start(image: str, base: str, *, command=("true",), mounts=True):
    args = ["docker", "run", "--rm"]
    if mounts:
        for name in (".venturelab", "outputs", "decision_log.json"):
            args += ["-v", f"{base}/repo/{name}:/srv/{name}"]
    return sh(*args, image, *command, check=False)


@docker
@pytest.mark.parametrize("owner", [1000, 1001])
def test_fresh_user_checkout_starts_unprivileged(image, base, owner):
    checkout(base, owner)
    result = start(image, base, command=("sh", "-c", "id -u; grep -E '^(CapEff|NoNewPrivs)' /proc/self/status"))
    assert result.returncode == 0, result.stderr
    lines = result.stdout.split()
    assert lines[0] == str(owner) and "0000000000000000" in result.stdout and "NoNewPrivs:\t1" in result.stdout
    assert host(f"stat -c '%u %a' {base}/repo/.venturelab").split() == [str(owner), "700"]


@docker
def test_root_owned_checkout_is_refused_not_chowned(image, base):
    checkout(base, 0)
    result = start(image, base)
    assert result.returncode == 64 and "not writable" in result.stderr
    assert host(f"stat -c '%u' {base}/repo/outputs {base}/repo/.venturelab {base}/repo/decision_log.json").split() == ["0"] * 3


@docker
@pytest.mark.parametrize("name", [".venturelab", "outputs", "decision_log.json"])
def test_symlinked_mount_root_is_refused(image, base, name):
    checkout(base, 1001)
    victims(base)
    before = owners(base)
    target = f"{base}/victim-file" if name == "decision_log.json" else f"{base}/victim-dir"
    host(f"rm -rf {base}/repo/{name} && ln -s {target} {base}/repo/{name}")
    result = start(image, base)
    assert result.returncode == 64 and "refusing to start" in result.stderr
    assert owners(base) == before


@docker
def test_redirect_of_all_three_into_one_foreign_folder_is_refused(image, base):
    # Strongest form: the three names all exist (empty, root-owned) in one foreign folder, so
    # the mounts look like consistent siblings. Ownership must still not be taken over.
    checkout(base, 1001)
    victims(base)
    before = owners(base)
    for name in (".venturelab", "outputs", "decision_log.json"):
        host(f"rm -rf {base}/repo/{name} && ln -s {base}/victim-dir/{name} {base}/repo/{name}")
    result = start(image, base)
    assert result.returncode == 64 and "not writable" in result.stderr
    assert owners(base) == before


@docker
def test_relative_traversal_symlink_is_refused(image, base):
    checkout(base, 1001)
    host(f"mkdir -p {base}/other/.venturelab && chown -R 0:0 {base}/other"
         f" && ln -s ../other/.venturelab {base}/repo/.venturelab")
    result = start(image, base)
    assert result.returncode == 64 and "different folders" in result.stderr
    assert host(f"stat -c '%u' {base}/other/.venturelab").strip() == "0"


@docker
def test_nested_links_are_never_followed_or_changed(image, base):
    checkout(base, 1001, state=True)
    victims(base)
    before = owners(base)
    host(f"ln -s {base}/victim-file {base}/repo/.venturelab/evil && ln -s /etc {base}/repo/outputs/etc-link"
         f" && mkdir {base}/repo/outputs/sub && ln -s {base}/victim-dir {base}/repo/outputs/sub/deeper")
    result = start(image, base, command=("sh", "-c", "stat -c %u /etc /etc/shadow"))
    assert result.returncode == 0, result.stderr
    assert result.stdout.split() == ["0", "0"] and owners(base) == before


@docker
def test_non_empty_root_owned_state_is_not_taken_over(image, base):
    checkout(base, 1001)
    host(f"mkdir {base}/repo/.venturelab && ln -s /etc/shadow {base}/repo/.venturelab/link"
         f" && chown -h 0:0 {base}/repo/.venturelab {base}/repo/.venturelab/link")
    result = start(image, base)
    assert result.returncode == 64 and "not writable" in result.stderr
    assert host(f"stat -c '%u' {base}/repo/.venturelab").strip() == "0"


@docker
def test_missing_log_file_mounted_as_folder_is_refused(image, base):
    checkout(base, 1001)
    host(f"rm {base}/repo/decision_log.json")
    result = start(image, base)
    # Docker usually refuses first (it will not mount a created folder over the image's file,
    # exit 125); the entrypoint's own folder check (exit 64) is the second line of defence.
    assert result.returncode in (64, 125) and "decision_log.json" in result.stderr


@docker
def test_symlinked_log_inside_image_is_refused_and_not_followed(image):
    result = sh("docker", "run", "--rm", "--entrypoint", "sh", image, "-c",
                "ln -sf /etc/hostname /srv/decision_log.json; /srv/docker-entrypoint.sh true; "
                "echo rc=$?; stat -c %u:%g /etc/hostname", check=False)
    assert "rc=64" in result.stdout and result.stdout.strip().endswith("0:0")
