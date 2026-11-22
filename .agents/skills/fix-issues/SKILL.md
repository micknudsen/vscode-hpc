---
name: fix-issues
description: Deliver selected vscode-hpc issues or a queue of ready-for-agent issues through implementation, CI repair, and protected squash merge. Use for an issue execution or resume request; configuring this skill does not start delivery.
---

# Fix issues

1. Read the [contribution policy](../../../.github/CONTRIBUTING.md), relevant
   repository documentation, and issue bodies, comments, dependencies, and linked
   PRs in `micknudsen/vscode-hpc`. Honor requested issue IDs, milestone, order, and
   limits. For a general queue, snapshot open issues labeled `ready-for-agent`
   and order by dependencies, then issue number. If none qualify, report that
   result rather than widening the queue. Record scope and progress under
   `.local/fix-issues/`; preserve that scope when resuming.
2. Work one issue at a time. Fetch current `master`, preserve unrelated work, and
   reuse a matching branch or PR when resuming. Create a feature branch before
   changing files. Derive acceptance criteria from the issue and its linked
   specification. Exercise affected behavior through the installed public CLI
   and controlled SSH/VS Code peers where applicable. Real-cluster acceptance
   needs separately recorded evidence from an authorized cluster.
3. Review the diff against the issue and run the contribution policy's verification
   commands, including installation of the wheel built from the source
   distribution. Commit and push the feature branch. Open a PR with concrete test
   evidence and a closing reference only for an issue it fully resolves. Reference
   a broader specification without closing it when delivering only part of it.
4. Monitor all CI on the current head. Diagnose failures from job logs and repair
   them on the branch. Update from `master` when required and wait for checks on
   the new head. Verify effective branch protection, required checks, and resolved
   review conversations. A request to deliver issues through this skill includes
   the protected merge; honor a narrower request to prepare a PR by stopping there.
   Squash-merge only the verified head, using
   `gh pr merge NUMBER --squash --match-head-commit SHA`, and preserve protection.
5. Verify GitHub reports the PR merged, the resolved issue closed, and post-merge
   checks passing on the exact merged commit. Synchronize local `master` safely;
   clean up only the merged feature branch. Repair regressions through another
   protected PR before proceeding to the next issue. Record issue/PR links,
   checked SHAs, CI results, and remaining blockers in the progress notes.

If an issue is blocked by a dependency, missing access, or a maintainer decision,
record the concrete blocker and continue only with independent issues inside the
agreed queue. Keep release publication separate: packaging or issue delivery
alone does not authorize a release. Finish with completed, blocked, and remaining
issues and the next actionable step.
