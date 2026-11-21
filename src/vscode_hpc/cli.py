"""Command-line interface; allocations deliberately outlive this local client."""

import argparse
import os
import re
import shutil
import subprocess
import sys
import time
from importlib.metadata import version
from typing import Optional, Sequence

from .slurm import CommandError, Slurm


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(
        prog="vscode-hpc", description="Open VS Code on a Slurm compute node."
    )
    root.add_argument("--version", action="version", version=version("vscode-hpc"))
    commands = root.add_subparsers(dest="command")
    opening = commands.add_parser(
        "open", help="Request a Slurm allocation and open a remote folder",
        epilog="Required defaults: VSCODE_HPC_HOST, VSCODE_HPC_USER, "
        "VSCODE_HPC_TIME, VSCODE_HPC_CPUS, VSCODE_HPC_MEMORY. "
        "Scheduler options override their environment variables. "
        "Ctrl-C leaves the submitted allocation active.",
    )
    for flag, destination, variable in (
        ("--time", "wall_time", "TIME"),
        ("--cpus", "cpus", "CPUS"),
        ("--mem", "memory", "MEMORY"),
        ("--partition", "partition", "PARTITION"),
        ("--account", "account", "ACCOUNT"),
    ):
        opening.add_argument(
            flag, dest=destination, default=os.environ.get(f"VSCODE_HPC_{variable}"),
            help=f"Override VSCODE_HPC_{variable}",
        )
    opening.add_argument("folder", help="Folder path on the HPC filesystem")
    cancel = commands.add_parser(
        "cancel", help="List or cancel your Slurm jobs named 'vscode'",
        epilog="Requires VSCODE_HPC_HOST and VSCODE_HPC_USER. "
        "With no job ID or --all, lists matching jobs without cancelling them.",
    )
    selection = cancel.add_mutually_exclusive_group()
    selection.add_argument("job_id", nargs="?")
    selection.add_argument("--all", action="store_true")
    cancel.add_argument("--dry-run", action="store_true")
    return root


def value(text: Optional[str], name: str) -> str:
    if not text or not text.strip():
        raise CommandError(f"Missing required value: {name}", 2)
    if any(ord(char) < 32 or ord(char) == 127 for char in text):
        raise CommandError(f"Control characters are not allowed in {name}", 2)
    return text


def connection() -> Slurm:
    host = value(os.environ.get("VSCODE_HPC_HOST"), "VSCODE_HPC_HOST")
    user = value(os.environ.get("VSCODE_HPC_USER"), "VSCODE_HPC_USER")
    for text, name in ((host, "VSCODE_HPC_HOST"), (user, "VSCODE_HPC_USER")):
        if text.startswith("-") or any(c.isspace() or c in "@/" for c in text):
            raise CommandError(f"Invalid SSH destination in {name}", 2)
    if not shutil.which("ssh"):
        raise CommandError("The OpenSSH 'ssh' command is not on PATH.", 2)
    return Slurm(host, user)


def open_folder(args: argparse.Namespace, slurm: Slurm) -> None:
    wall_time = value(args.wall_time, "VSCODE_HPC_TIME / --time")
    cpus = value(args.cpus, "VSCODE_HPC_CPUS / --cpus")
    if not re.fullmatch(r"[0-9]+", cpus) or int(cpus) < 1:
        raise CommandError("CPUs must be a positive integer.", 2)
    memory = value(args.memory, "VSCODE_HPC_MEMORY / --mem")
    folder = value(args.folder, "FOLDER")
    for option in ("partition", "account"):
        if getattr(args, option):
            value(getattr(args, option), f"--{option}")
    if not shutil.which("code"):
        raise CommandError(
            "The VS Code 'code' command is not on PATH. In VS Code, run: "
            "Shell Command: Install 'code' command in PATH", 2,
        )
    print(f"Requesting a compute node via {slurm.target}...", flush=True)
    job_id = slurm.submit(wall_time, int(cpus), memory, args.partition, args.account)
    print(
        f"Job {job_id} submitted; waiting for a node (Ctrl-C will not cancel it).\n"
        f"Release the allocation when finished: vscode-hpc cancel {job_id}",
        flush=True,
    )
    try:
        while True:
            job = slurm.allocation(job_id)
            if job is None:
                raise CommandError(f"Job {job_id} disappeared before an allocation was available.")
            if job.state == "RUNNING" and job.node and job.node not in ("(null)", "None", "(None)"):
                break
            if job.state not in ("PENDING", "CONFIGURING", "RUNNING", "REQUEUED", "REQUEUE_FED"):
                raise CommandError(f"Job {job_id} cannot start in state {job.state}.")
            print(f"  state: {job.state}", flush=True)
            time.sleep(5)
        print(f"Allocated node: {job.node} (job {job_id})", flush=True)
        print(f"Opening VS Code on {job.node}...", flush=True)
        result = subprocess.run(["code", "--remote", f"ssh-remote+{job.node}", folder])
        if result.returncode:
            raise CommandError("VS Code failed to open the remote folder.", result.returncode)
    except (CommandError, KeyboardInterrupt, OSError):
        print(f"If job {job_id} is still active, release it with: vscode-hpc cancel {job_id}", file=sys.stderr)
        raise


def cancel_jobs(args: argparse.Namespace, slurm: Slurm) -> None:
    if args.job_id and not re.fullmatch(r"[0-9]+", args.job_id):
        raise CommandError(f"Invalid job ID: {args.job_id}", 2)
    jobs = slurm.matching_jobs()
    if args.job_id:
        jobs = [job for job in jobs if job.job_id == args.job_id]
        if not jobs:
            raise CommandError(
                f"Job ID {args.job_id} is not a cancellable 'vscode' job for {slurm.target}."
            )
    if not jobs:
        print(f"No Slurm jobs named 'vscode' found for {slurm.target}.")
        return
    print(f"Cancellable Slurm jobs on {slurm.target}:")
    for job in jobs:
        print(f"{job.job_id} {job.state} {job.node}")
    if args.job_id or args.all:
        ids = " ".join(job.job_id for job in jobs)
        if args.dry_run:
            print(f"Dry run: would cancel job IDs: {ids}")
        else:
            print(f"Cancelling job IDs: {ids}", flush=True)
            slurm.cancel(jobs)


def main(argv: Optional[Sequence[str]] = None) -> int:
    root = parser()
    args = root.parse_args(argv)
    if args.command is None:
        root.print_help()
        return 0
    try:
        slurm = connection()
        if args.command == "open":
            open_folder(args, slurm)
        else:
            cancel_jobs(args, slurm)
        return 0
    except CommandError as error:
        print(f"vscode-hpc: {error}", file=sys.stderr)
        return error.returncode
    except KeyboardInterrupt:
        print("vscode-hpc: interrupted.", file=sys.stderr)
        return 130
    except OSError as error:
        print(f"vscode-hpc: {error}", file=sys.stderr)
        return 1
