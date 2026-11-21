"""Executable SSH/VS Code peers; never connects to a cluster."""

import json
import os
import shlex
import sys
import time
from pathlib import Path

state_path = Path(os.environ["VSCODE_HPC_TEST_STATE"])
state = json.loads(state_path.read_text())
kind = Path(sys.argv[0]).name
args = sys.argv[1:]
with Path(os.environ["VSCODE_HPC_TEST_LOG"]).open("a") as stream:
    stream.write(json.dumps([kind, args]) + "\n")
if kind == "code":
    sys.exit(state.get("code_status", 0))
assert args[:2] == ["--", "tester@login.example"], args
command = shlex.split(args[2])
if state.get("ssh_status"):
    print("Connection refused", file=sys.stderr)
    sys.exit(state["ssh_status"])
if command[0] == "sbatch":
    print(state.get("submission", "12345;cluster"))
elif command[0] == "squeue" and "--me" in command:
    print(state.get("jobs", "12345 RUNNING cn-1\n12346 PENDING (null)"))
elif command[0] == "squeue":
    if state.get("queue_status"):
        print("Queue connection lost", file=sys.stderr)
        sys.exit(state["queue_status"])
    if state.get("queue_delay"):
        time.sleep(state["queue_delay"])
    responses = state.get("queue", ["RUNNING cn-1"])
    print(responses[0])
    if len(responses) > 1:
        state["queue"] = responses[1:]
        state_path.write_text(json.dumps(state))
elif command[0] == "scancel":
    if state.get("cancel_status"):
        print("Cancellation denied", file=sys.stderr)
    sys.exit(state.get("cancel_status", 0))
else:
    raise AssertionError(command)
