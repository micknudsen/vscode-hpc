"""SSH transport and Slurm responses used by the local client."""

import re
import shlex
import subprocess
from dataclasses import dataclass
from typing import List, Optional, Sequence


class CommandError(Exception):
    def __init__(self, message: str, returncode: int = 1):
        super().__init__(message)
        self.returncode = returncode if 0 < returncode < 256 else 1


@dataclass(frozen=True)
class Job:
    job_id: str
    state: str
    node: str


# Accept scalar IDs and Slurm's individual or compressed array IDs.
JOB_ID = re.compile(r"[0-9]+(?:_[0-9]+|_\[[0-9,%-]+\])?")


class Slurm:
    def __init__(self, host: str, user: str):
        self.target = f"{user}@{host}"

    def run(self, arguments: Sequence[str]) -> str:
        # SSH sends one remote shell command: quote each argument independently.
        result = subprocess.run(
            ["ssh", "--", self.target, shlex.join(arguments)],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        if result.returncode:
            detail = result.stderr.strip() or "no diagnostic output"
            raise CommandError(
                f"SSH command failed on {self.target}: {detail}", result.returncode
            )
        return result.stdout

    def submit(
        self, wall_time: str, cpus: int, memory: str,
        partition: Optional[str], account: Optional[str],
    ) -> str:
        arguments = [
            "sbatch", "--parsable", "--job-name=vscode", "--nodes=1", "--ntasks=1",
            f"--cpus-per-task={cpus}", f"--mem={memory}", f"--time={wall_time}",
            "--output=/dev/null", "--error=/dev/null",
        ]
        if partition:
            arguments.append(f"--partition={partition}")
        if account:
            arguments.append(f"--account={account}")
        arguments.append('--wrap=trap "exit 0" TERM INT; while :; do sleep 3600; done')
        response = self.run(arguments).strip()
        match = re.fullmatch(r"([0-9]+)(?:;[^\s;]+)?", response)
        if not match:
            raise CommandError(f"Slurm did not return a job ID: {response}")
        return match[1]

    def allocation(self, job_id: str) -> Optional[Job]:
        response = self.run([
            "squeue", "--noheader", f"--jobs={job_id}", "--format=%T|%N",
        ]).strip()
        if not response:
            return None
        fields = response.split("|")
        if len(response.splitlines()) != 1 or len(fields) != 2 or not fields[0]:
            raise CommandError(f"Unexpected Slurm allocation response: {response}")
        return Job(job_id, fields[0], fields[1])

    def matching_jobs(self) -> List[Job]:
        response = self.run([
            "squeue", "--me", "--name=vscode", "--noheader", "--format=%i|%T|%N",
        ])
        jobs = []
        for line in response.splitlines():
            fields = line.split("|")
            # Preserve an empty node field while ignoring login banners.
            if len(fields) == 3 and JOB_ID.fullmatch(fields[0]) and fields[1]:
                jobs.append(Job(*fields))
        return jobs

    def cancel(self, jobs: Sequence[Job]) -> None:
        if jobs:
            self.run(["scancel", *(job.job_id for job in jobs)])
