"""Sample a runner while executing the pinned desktop shard twice."""

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import threading
import time

OUT = Path("build/desktop-profile")
SHARD = os.environ.get("PROFILE_SHARD", "2")
TIMINGS = Path(f"build/browser-timings/desktop-chromium-shard-{SHARD}.json")
COMMAND = ["node", "tools/browser-tests/run-shard.mjs", "desktop-chromium", SHARD]
INTERVAL = 5
MEM_FIELDS = {"MemTotal", "MemAvailable", "SwapTotal", "SwapFree", "Dirty", "Writeback", "Cached"}
VM_FIELDS = {"pgmajfault", "pgpgin", "pgpgout", "pswpin", "pswpout"}


def stamp():
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def read_optional(path):
    try:
        return Path(path).read_text().strip()
    except (FileNotFoundError, PermissionError):
        return None


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2) + "\n")


def read_numbers(path, fields):
    data = {}
    for line in Path(path).read_text().splitlines():
        name, value, *_ = line.split()
        key = name.rstrip(":")
        if key in fields:
            data[key] = int(value)
    return data


def workspace_device():
    dev = Path.cwd().stat().st_dev
    path = Path(f"/sys/dev/block/{os.major(dev)}:{os.minor(dev)}")
    return path.resolve().name if path.exists() else None


def process_cgroup():
    for line in Path("/proc/self/cgroup").read_text().splitlines():
        if line.startswith("0::"):
            return Path("/sys/fs/cgroup") / line[3:].lstrip("/")
    return None


WORKSPACE_DEVICE = workspace_device()
DISK_DEVICES = {path.name for path in Path("/sys/block").iterdir() if not path.name.startswith(("loop", "ram"))}
if WORKSPACE_DEVICE:
    DISK_DEVICES.add(WORKSPACE_DEVICE)

CGROUP = process_cgroup()


def sample(phase):
    now = stamp()
    stats = Path("/proc/stat").read_text().splitlines()[0].split()
    disk = {}
    for line in Path("/proc/diskstats").read_text().splitlines():
        _, _, dev, *counters = line.split()
        if dev in DISK_DEVICES:
            disk[dev] = [int(value) for value in counters]
    cgroup = {}
    if CGROUP:
        for metric in ("cpu.stat", "memory.current", "memory.events", "io.stat"):
            cgroup[metric] = read_optional(CGROUP / metric)
    return {
        "time": now,
        "monotonic_s": time.monotonic(),
        "phase": phase,
        "cpu_jiffies": [int(counter) for counter in stats[1:]],
        "loadavg": Path("/proc/loadavg").read_text().strip(),
        "meminfo_kib": read_numbers("/proc/meminfo", MEM_FIELDS),
        "vmstat": read_numbers("/proc/vmstat", VM_FIELDS),
        "pressure": {name: read_optional(f"/proc/pressure/{name}") for name in ("cpu", "memory", "io")},
        "diskstats": disk,
        "cgroup": cgroup,
    }


def check_runner():
    command = ["lscpu", "--json"]
    cpu = json.loads(subprocess.check_output(command, text=True))
    write_json(OUT / "runner.json", {
        "time": stamp(),
        "runner": os.environ.get("RUNNER_NAME"),
        "image": {name: os.environ.get(name) for name in ("ImageOS", "ImageVersion")},
        "source": os.environ["FROZEN_SOURCE"],
        "source_tree": os.environ["FROZEN_TREE"],
        "web_commit": os.environ["FROZEN_SOURCE"],
        "web_sha256": os.environ["FROZEN_WEB_CONTENT"],
        "diagnostic_commit": os.environ["DIAGNOSTIC_COMMIT"],
        "source_run": int(os.environ["SOURCE_RUN"]),
        "artifact_id": int(os.environ["BASELINE_WEB_ARTIFACT"]),
        "linux": list(os.uname()),
        "cpu": cpu,
        "affinity": sorted(os.sched_getaffinity(0)),
        "uptime_seconds": float(Path("/proc/uptime").read_text().split()[0]),
        "memory_kib": read_numbers("/proc/meminfo", MEM_FIELDS),
        "workspace_device": WORKSPACE_DEVICE,
        "cgroup_limits": {name: read_optional(CGROUP / name)
                          for name in ("cpu.max", "memory.max", "io.max")} if CGROUP else {},
        "sample_interval_seconds": INTERVAL,
    })
    for row in cpu["lscpu"]:
        if row["field"] in ("Model name:", "CPU(s):", "Hypervisor vendor:"):
            print(f"{row['field']} {row['data']}", flush=True)


def cpu_probe():
    values = []
    for _ in range(3):
        wall = time.perf_counter()
        cpu = time.process_time()
        hashlib.pbkdf2_hmac("sha256", b"tk2-browser-control", b"ci-runner-sample", 1_500_000)
        values.append({"wall": time.perf_counter() - wall, "cpu": time.process_time() - cpu})
    return values


def run_pass(number):
    folder = OUT / f"repeat-{number}"
    folder.mkdir()
    TIMINGS.unlink(missing_ok=True)
    probe = cpu_probe()
    with (folder / "resources.jsonl").open("w", buffering=1) as resources:
        for _ in range(3):
            resources.write(json.dumps(sample("idle-before")) + "\n")
            time.sleep(INTERVAL)
        started = stamp()
        clock = time.monotonic()
        stop = threading.Event()

        def record():
            while not stop.is_set():
                resources.write(json.dumps(sample("test")) + "\n")
                stop.wait(INTERVAL)

        monitor = threading.Thread(target=record)
        monitor.start()
        try:
            with (folder / "playwright.log").open("w", buffering=1) as log:
                with subprocess.Popen(COMMAND, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                      text=True, bufsize=1, env={**os.environ, "FORCE_COLOR": "0"}) as cmd:
                    for line in cmd.stdout:
                        log.write(f"{stamp()} {line}")
                        print(line, end="", flush=True)
                    exit_code = cmd.wait()
        finally:
            stop.set()
            monitor.join()
        ended = stamp()
        wall = time.monotonic() - clock
        for _ in range(2):
            resources.write(json.dumps(sample("idle-after")) + "\n")
            time.sleep(INTERVAL)
    write_json(folder / "execution.json", {
        "repeat": number, "started_at": started, "ended_at": ended,
        "elapsed_seconds": wall, "exit_code": exit_code, "command": COMMAND,
        "cpu_probe": probe, "cpu_probe_after": cpu_probe(),
    })
    if TIMINGS.is_file():
        shutil.copyfile(TIMINGS, folder / "case-timings.json")
    print(f"Repetition {number}: {wall:.2f}s (exit {exit_code})", flush=True)
    return exit_code


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    check_runner()
    statuses = [run_pass(number) for number in (1, 2)]
    return int(any(statuses))


if __name__ == "__main__":
    raise SystemExit(main())
