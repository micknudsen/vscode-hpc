---
name: vscode-hpc-release
description: Prepare or resume a requested vscode-hpc release through agreed notes, protected PRs, exact-artifact Conda publication to micknudsen, and verified GitHub Releases. Release questions and workflow edits alone do not authorize publication.
---

# Release vscode-hpc

Read [Releasing](../../../docs/releasing.md) and the
[contribution policy](../../../.github/CONTRIBUTING.md) before acting. Inspect the
current [Release workflow](../../../.github/workflows/release.yml) and
[Tests workflow](../../../.github/workflows/tests.yml) for the actual publication
steps and required qualification. Keep dated progress and evidence under
`.local/releases/<tag>/` so a later session can resume the same attempt.

## Agree on scope and notes

Fetch `master` and tags. Inspect merged scope, issue acceptance, version PRs,
existing tags/releases, channel files, and retained workflow artifacts. Resume
an existing attempt when present. Propose a normal release unless the maintainer
requests a prerelease; check that the workflow supports the requested release
type before tagging.

Draft notes covering actual changes, requirements, validation, and remaining
limits. Present the version, scope, notes, and intended publication for agreement.
For an explicit publication request, agreement authorizes the described version
PR, checked squash merge, tag push, Conda upload, and GitHub publication without
another publish prompt. A preparation-only request stops before publication.
Reuse recorded agreement when resuming unchanged scope; source or release-content
changes beyond the agreed version/notes preparation need updated notes and renewed
agreement.

## Prepare and qualify

For the first release, locate the recorded real-cluster check required by
`docs/releasing.md` and match its package/source identity to the candidate.
Assess intervening changes and repeat affected checks when the evidence no longer
applies. Preserve the platform, cluster, allocation, terminal location,
cancellation outcome, and remaining limits. Controlled CI peers alone do not
establish real-cluster compatibility. Obtain missing cluster access or user-run
evidence before tagging; retain completed preparation while waiting.

Update `setup.cfg` and `conda-recipe/meta.yaml` versions together and archive
agreed notes in `docs/releases/<tag>.md`. Run local verification from the
contribution policy and deliver preparation through a protected squash PR.
Wait for all required post-merge checks on the exact master commit to be tagged.
Record that SHA and verify version/tag agreement with
`python3 scripts/distributions.py version`.

Before tagging, confirm the `ANACONDA_API_TOKEN` secret is configured for the
`micknudsen` channel. Inspect secret names, never values. Report missing access or
configuration without exposing credentials.

## Publish and verify

Push `vVERSION` at the verified commit only after the publication agreement and
prerequisites are satisfied. This repository's `Release` workflow runs complete
qualification, uploads the tested Conda artifact, verifies a fresh channel
installation, and creates a public GitHub release directly. Tagging starts that
publication; there is no draft-release approval step.

Monitor the workflow through completion. Record the run ID, immutable
`distributions` artifact ID, source SHA, and Conda digest. Independently download
the public source distribution, wheel, Conda package, and `manifest.json` into a
separate directory. At the tagged source, use
`python3 scripts/distributions.py verify --directory DIRECTORY --source SHA --tag TAG`
to verify version, source, asset set, and digests against the retained qualified
artifact. Confirm the channel file has the same digest, the fresh channel-install
tests passed, and the public tag and release body match the approved source and
archived notes. Python packages are GitHub assets; PyPI publication is outside
this workflow.

If publication partially succeeds, follow `docs/releasing.md` before any retry.
Inspect existing channel/GitHub files against the retained artifact; complete
missing verification or publication with those same bytes. Do not blindly rerun
uploads, overwrite an existing version, rebuild replacement artifacts, or move
its tag. Source changes require a new version through a protected PR and renewed
agreement.

Finish with the version, release URL, installation command, source and workflow
evidence, cluster qualification, and remaining limits. Keep evidence in dated
project notes; changes to tracked release notes go through another protected PR
and must remain consistent with the GitHub body. Close milestones only when their
acceptance criteria are met.
