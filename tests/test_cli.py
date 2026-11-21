"""Exercise the installed CLI with controlled external processes."""

import json
import os
import shlex
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path


class InstalledCLI(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.bin = self.root / "bin"
        self.bin.mkdir()
        self.state = self.root / "state.json"
        self.log = self.root / "calls.jsonl"
        self.state.write_text("{}")
        peer = Path(__file__).with_name("fake_peer.py").read_text()
        for name in ("ssh", "code"):
            target = self.bin / name
            target.write_text(f"#!{sys.executable}\n" + peer)
            target.chmod(0o755)
        self.cli = shutil.which("vscode-hpc")
        self.assertIsNotNone(self.cli, "Install the package before running tests")
        self.env = {k: v for k, v in os.environ.items() if not k.startswith("VSCODE_HPC_")}
        self.env.update(
            PATH=str(self.bin), VSCODE_HPC_HOST="login.example", VSCODE_HPC_USER="tester",
            VSCODE_HPC_TIME="04:00:00", VSCODE_HPC_CPUS="4", VSCODE_HPC_MEMORY="8G",
            VSCODE_HPC_TEST_STATE=str(self.state), VSCODE_HPC_TEST_LOG=str(self.log),
        )

    def configure(self, **state):
        self.state.write_text(json.dumps(state))

    def run_cli(self, *args, status=0):
        result = subprocess.run(
            [self.cli, *args], env=self.env, cwd=self.root,
            text=True, capture_output=True, timeout=20,
        )
        self.assertEqual(result.returncode, status, result.stdout + result.stderr)
        self.assertNotIn("Traceback", result.stderr)
        return result

    def calls(self, kind="ssh"):
        if not self.log.exists():
            return []
        calls = [json.loads(line) for line in self.log.read_text().splitlines()]
        return [shlex.split(args[-1]) if kind == "ssh" else args
                for name, args in calls if name == kind]

    def test_help_and_version_need_no_configuration_or_peers(self):
        self.env = {"PATH": ""}
        for args in ((), ("--help",), ("open", "--help"), ("cancel", "--help"), ("--version",)):
            with self.subTest(args=args):
                self.assertTrue(self.run_cli(*args).stdout)

    def test_open_uses_defaults_and_launches_remote_folder(self):
        result = self.run_cli("open", "/project")
        submission = self.calls()[0]
        for arg in ("--job-name=vscode", "--cpus-per-task=4", "--mem=8G", "--time=04:00:00"):
            self.assertIn(arg, submission)
        self.assertEqual(self.calls("code"), [["--remote", "ssh-remote+cn-1", "/project"]])
        self.assertIn("vscode-hpc cancel 12345", result.stdout)
        self.assertFalse(any(c[0] == "scancel" for c in self.calls()))

    def test_cli_overrides_environment(self):
        self.env.update(VSCODE_HPC_PARTITION="old", VSCODE_HPC_ACCOUNT="old", VSCODE_HPC_CPUS="bad")
        self.run_cli("open", "--time", "10", "--cpus", "2", "--mem", "4G",
                     "--partition", "short", "--account", "research", "/project")
        for arg in ("--time=10", "--cpus-per-task=2", "--mem=4G", "--partition=short", "--account=research"):
            self.assertIn(arg, self.calls()[0])

    def test_optional_scheduler_defaults(self):
        self.env.update(VSCODE_HPC_PARTITION="short", VSCODE_HPC_ACCOUNT="research")
        self.run_cli("open", "/project")
        self.assertIn("--partition=short", self.calls()[0])
        self.assertIn("--account=research", self.calls()[0])

    def test_shell_characters_and_spaces_remain_single_arguments(self):
        folder = "/project's work/$(touch marker); [a]"
        account = "research; $(touch marker) 'quoted'"
        self.run_cli("open", "--account", account, folder)
        self.assertIn("--account=" + account, self.calls()[0])
        self.assertEqual(self.calls("code")[0][-1], folder)
        self.assertFalse((self.root / "marker").exists())

    def test_double_dash_accepts_folder_beginning_with_dash(self):
        self.run_cli("open", "--", "-project")
        self.assertEqual(self.calls("code")[0][-1], "-project")

    def test_pending_allocation_eventually_opens(self):
        self.configure(queue=["PENDING (null)", "RUNNING cn-2"])
        self.assertIn("state: PENDING", self.run_cli("open", "/project").stdout)
        self.assertEqual(self.calls("code")[0][1], "ssh-remote+cn-2")

    def test_missing_required_configuration_fails_before_ssh(self):
        for name in ("HOST", "USER", "TIME", "CPUS", "MEMORY"):
            key = "VSCODE_HPC_" + name
            saved = self.env.pop(key)
            with self.subTest(name=name):
                self.assertIn(key, self.run_cli("open", "/project", status=2).stderr)
                self.assertEqual(self.calls(), [])
            self.env[key] = saved

    def test_invalid_cpus_fail_before_ssh(self):
        for cpus in ("0", "-1", "1.5", "abc"):
            with self.subTest(cpus=cpus):
                self.run_cli("open", "--cpus", cpus, "/project", status=2)
                self.assertEqual(self.calls(), [])

    def test_invalid_arguments_fail_before_ssh(self):
        for args in (("open",), ("open", "--cpus"), ("open", "/a", "/b"),
                     ("cancel", "12345", "--all"), ("cancel", "bad"),
                     ("cancel", "12345", "12346"), ("unknown",), ("open", "--unknown")):
            with self.subTest(args=args):
                self.run_cli(*args, status=2)
                self.assertEqual(self.calls(), [])

    def test_invalid_ssh_destination_fails_before_ssh(self):
        for host in ("-oProxyCommand=evil", "host name", "user@host", "host\nname"):
            self.env["VSCODE_HPC_HOST"] = host
            with self.subTest(host=host):
                self.run_cli("cancel", status=2)
                self.assertEqual(self.calls(), [])

    def test_missing_code_fails_before_allocation(self):
        (self.bin / "code").unlink()
        self.assertIn("'code'", self.run_cli("open", "/project", status=2).stderr)
        self.assertEqual(self.calls(), [])

    def test_missing_ssh_reports_prerequisite(self):
        (self.bin / "ssh").unlink()
        self.assertIn("OpenSSH", self.run_cli("cancel", status=2).stderr)

    def test_ssh_failure_preserves_status_and_diagnostic(self):
        self.configure(ssh_status=255)
        result = self.run_cli("open", "/project", status=255)
        self.assertIn("Connection refused", result.stderr)
        self.assertEqual(self.calls("code"), [])

    def test_malformed_submission_never_polls_or_launches(self):
        self.configure(submission="warning\n12345")
        self.assertIn("did not return a job ID", self.run_cli("open", "/project", status=1).stderr)
        self.assertEqual(len(self.calls()), 1)

    def test_disappeared_job_reports_failure_and_cleanup_command(self):
        self.configure(queue=[""])
        result = self.run_cli("open", "/project", status=1)
        self.assertIn("disappeared", result.stderr)
        self.assertIn("vscode-hpc cancel 12345", result.stderr)
        self.assertEqual(self.calls("code"), [])

    def test_polling_ssh_error_is_distinct_from_a_disappeared_job(self):
        self.configure(queue_status=255)
        result = self.run_cli("open", "/project", status=255)
        self.assertIn("Queue connection lost", result.stderr)
        self.assertNotIn("disappeared", result.stderr)
        self.assertIn("vscode-hpc cancel 12345", result.stderr)
        self.assertEqual(self.calls("code"), [])

    def test_terminal_job_state_stops_waiting(self):
        self.configure(queue=["FAILED cn-1"])
        self.assertIn("state FAILED", self.run_cli("open", "/project", status=1).stderr)
        self.assertEqual(self.calls("code"), [])

    def test_malformed_queue_response_does_not_open_vscode(self):
        self.configure(queue=["Unexpected banner\nRUNNING cn-1"])
        self.run_cli("open", "/project", status=1)
        self.assertEqual(self.calls("code"), [])

    def test_code_failure_keeps_allocation_and_reports_cleanup(self):
        self.configure(code_status=7)
        result = self.run_cli("open", "/project", status=7)
        self.assertIn("vscode-hpc cancel 12345", result.stderr)
        self.assertFalse(any(c[0] == "scancel" for c in self.calls()))

    def test_interrupt_keeps_allocation_and_reports_cleanup(self):
        self.configure(queue_delay=1, queue=["PENDING (null)"])
        process = subprocess.Popen(
            [self.cli, "open", "/project"], env=self.env, cwd=self.root,
            text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True,
        )
        try:
            deadline = time.monotonic() + 10
            while len(self.calls()) < 2 and process.poll() is None and time.monotonic() < deadline:
                time.sleep(0.02)
            self.assertEqual(len(self.calls()), 2, "Client did not reach allocation polling")
            os.killpg(process.pid, signal.SIGINT)
            stdout, stderr = process.communicate(timeout=10)
            self.assertEqual(process.returncode, 130, stdout + stderr)
            self.assertIn("vscode-hpc cancel 12345", stderr)
            self.assertFalse(any(c[0] == "scancel" for c in self.calls()))
        finally:
            if process.poll() is None:
                os.killpg(process.pid, signal.SIGKILL)
                process.communicate()

    def test_cancel_without_selection_only_lists(self):
        self.assertIn("12345 RUNNING cn-1", self.run_cli("cancel").stdout)
        self.assertEqual(len(self.calls()), 1)
        self.assertIn("--me", self.calls()[0])
        self.assertIn("--name=vscode", self.calls()[0])

    def test_cancel_does_not_need_scheduler_defaults_or_code(self):
        for key in ("TIME", "CPUS", "MEMORY"):
            del self.env["VSCODE_HPC_" + key]
        (self.bin / "code").unlink()
        self.run_cli("cancel", "12345")
        self.assertEqual(self.calls()[-1], ["scancel", "12345"])

    def test_cancel_all_filters_banners_and_keeps_array_ids(self):
        self.configure(jobs="Welcome to HPC\n12345 RUNNING cn-1\n42_3 RUNNING cn-2\n42_[4-9%2] PENDING (null)\n123 junk\n")
        self.run_cli("cancel", "--all")
        self.assertEqual(self.calls()[-1], ["scancel", "12345", "42_3", "42_[4-9%2]"])

    def test_cancel_only_accepts_matching_job(self):
        result = self.run_cli("cancel", "999", status=1)
        self.assertIn("not a cancellable", result.stderr)
        self.assertEqual(len(self.calls()), 1)

    def test_dry_run_never_cancels(self):
        for args in (("--dry-run", "12345"), ("--all", "--dry-run"), ("--dry-run",)):
            with self.subTest(args=args):
                self.run_cli("cancel", *args)
                self.assertFalse(any(c[0] == "scancel" for c in self.calls()))

    def test_no_matching_jobs_is_success_for_list_and_all(self):
        self.configure(jobs="Welcome to HPC")
        for args in ((), ("--all",)):
            with self.subTest(args=args):
                self.assertIn("No Slurm jobs", self.run_cli("cancel", *args).stdout)
        self.assertFalse(any(c[0] == "scancel" for c in self.calls()))

    def test_failed_listing_never_cancels(self):
        self.configure(ssh_status=255)
        self.run_cli("cancel", "--all", status=255)
        self.assertEqual(len(self.calls()), 1)

    def test_cancellation_failure_propagates(self):
        self.configure(cancel_status=5)
        self.assertIn("Cancellation denied", self.run_cli("cancel", "12345", status=5).stderr)


if __name__ == "__main__":
    unittest.main()
