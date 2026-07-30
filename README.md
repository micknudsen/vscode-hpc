# VS Code on Slurm compute nodes

`vscode-alloc` reserves a Slurm compute node and opens an HPC folder on that
node using VS Code Remote-SSH. This moves the VS Code server, extensions,
terminals, language servers, and indexers off the login/frontend node.

## Requirements

- A local installation of VS Code with the **Remote - SSH** extension.
- The `code` command available in your local shell. In VS Code, run
  **Shell Command: Install 'code' command in PATH** if it is missing.
- A Slurm cluster where the login node can SSH to a compute node after you have
  received an allocation.
- Permission to submit Slurm jobs to the intended partition/account.

## Install

Put `vscode-alloc` somewhere on your local machine, make it executable, and
place that directory on your `PATH`:

```bash
chmod +x vscode-alloc
mkdir -p ~/bin
mv vscode-alloc ~/bin/
```

Add this to `~/.zshrc` (or `~/.bashrc` for Bash) if `~/bin` is not already on
your path:

```bash
export PATH="$HOME/bin:$PATH"
```

Open a new terminal, or run `source ~/.zshrc`.

## Configure SSH

The following local `~/.ssh/config` configuration uses hostnames directly—no
SSH alias is required. Replace the values with those for your HPC.

```sshconfig
# The real hostname of the HPC login node. This makes SSH use a non-default key.
Host login.hpc.example.org
    User my-username
    IdentityFile ~/.ssh/my-hpc-key
    IdentitiesOnly yes

# The compute-node hostname pattern. For nodes cn-1, cn-2, ... use cn-*.
Host cn-*
    User my-username
    ProxyJump my-username@login.hpc.example.org
    ServerAliveInterval 30
    ServerAliveCountMax 3
```

`Host` patterns are SSH globs, not regular expressions. For example,
`cn-[0-9]+` does not work; use `cn-*` instead.

Test both paths before using the helper:

```bash
ssh my-username@login.hpc.example.org
# After receiving a Slurm allocation on cn-123:
ssh cn-123
```

If the second command fails despite having an allocation, ask your HPC support
team whether direct SSH to allocated compute nodes is supported and what their
recommended VS Code workflow is.

## Configure Slurm defaults

Set the required environment variables in your local shell profile, such as
`~/.zshrc`. These are examples only; use values authorized for your cluster.

```bash
export HPC_VSCODE_HOST=login.hpc.example.org
export HPC_VSCODE_USER=my-username
export HPC_VSCODE_TIME=04:00:00
export HPC_VSCODE_CPUS=4
export HPC_VSCODE_MEMORY=8G

# Optional; omit either line when your cluster does not require it.
export HPC_VSCODE_PARTITION=interactive
export HPC_VSCODE_ACCOUNT=my-project
```

Reload the profile after editing it:

```bash
source ~/.zshrc
```

| Variable | Meaning | Required |
| --- | --- | --- |
| `HPC_VSCODE_HOST` | Login node hostname | Yes |
| `HPC_VSCODE_USER` | HPC username | Yes |
| `HPC_VSCODE_TIME` | Slurm wall-time request, e.g. `04:00:00` | Yes |
| `HPC_VSCODE_CPUS` | CPUs per task | Yes |
| `HPC_VSCODE_MEMORY` | Slurm memory request, e.g. `8G` | Yes |
| `HPC_VSCODE_PARTITION` | Slurm partition | No |
| `HPC_VSCODE_ACCOUNT` | Slurm account/project | No |

## Use

Run the command locally, with a folder path that exists on the HPC filesystem:

```bash
vscode-alloc --folder /home/my-username/projects/analysis
```

The helper submits a lightweight job which holds one compute-node allocation,
waits for Slurm to schedule it, and opens the requested remote folder in VS
Code. The terminal that launched the command may then be closed; the Slurm job
remains active until it is cancelled or reaches its wall-time limit.

For one session, override any scheduler default on the command line:

```bash
vscode-alloc \
  --time 01:00:00 \
  --cpus 2 \
  --mem 4G \
  --partition short \
  --folder /home/my-username/projects/analysis
```

## Finish and release resources

When you are finished, disconnect the VS Code remote window and run the
`scancel` command printed by `vscode-alloc`, for example:

```bash
ssh my-username@login.hpc.example.org scancel 12345678
```

If the terminal output is no longer available, find and cancel the job:

```bash
ssh my-username@login.hpc.example.org squeue --me
ssh my-username@login.hpc.example.org scancel JOB_ID
```

Always release the allocation when finished. The allocated CPUs and memory are
reserved while VS Code is connected and until the job ends.

## Troubleshooting

**`The VS Code 'code' command is not on PATH`**

Run VS Code’s **Shell Command: Install 'code' command in PATH**, then open a
new terminal.

**The job stays pending**

Inspect its scheduler reason:

```bash
ssh my-username@login.hpc.example.org squeue --me -o "%.18i %.2t %.20R"
```

Choose a less busy partition, reduce the requested resources or wall time, or
wait for capacity according to local HPC policy.

**VS Code cannot connect after a node is allocated**

First verify the SSH route manually with `ssh cn-NODE`. Check that the compute
node pattern in `~/.ssh/config` matches the actual node name and that
`ProxyJump` contains the right login hostname and username.

**The login node still becomes busy**

Make sure the VS Code status bar identifies the compute node (for example,
`SSH: cn-123`), rather than the login node. Also confirm that the folder was
opened in that remote window, not in a separate login-node window.
