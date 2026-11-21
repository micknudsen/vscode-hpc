# Releasing vscode-hpc

## Prepare

Release only when the maintainer explicitly requests publication. Agree on
version, scope and release notes before tagging. The first version also needs a
real-cluster check: install the candidate, request an allocation, open a remote
folder, check where the VS Code terminal is running, then cancel the owned job.
Record the platform, cluster, package version, job outcome and remaining limits.
CI with simulated peers does not establish real-cluster compatibility.

Update `setup.cfg` and `conda-recipe/meta.yaml` versions together. Archive agreed
notes in `docs/releases/vVERSION.md`. Deliver these changes through a protected
squash PR and wait for all post-merge checks on the exact commit.

The repository needs an `ANACONDA_API_TOKEN` secret authorized to upload
`vscode-hpc` to the `micknudsen` Anaconda channel. Inspect secret names rather than
printing values. Configure this before tagging; credentials are not stored here.

## Publish

Tag the verified master commit `vVERSION` and push that tag. The **Release**
workflow verifies version/tag agreement, release notes, and membership in master.
It then runs the complete CI workflow for that source. The build job records
source, version and SHA-256 digests in `manifest.json`; both Conda installation
jobs consume the same immutable Actions artifact.

Only after all qualification jobs pass does publication download that artifact,
verify its manifest and upload the tested Conda file without rebuilding. It
checks a fresh channel installation with the full test suite, then creates a
GitHub release with the source distribution, wheel, Conda package and manifest.
Python packages are attached to GitHub; PyPI publication is not configured.

Verify the public release assets, source/tag, manifest and channel installation.
Record the release URL, CI run and artifact IDs, package digest, and cluster
qualification in the release notes or dated project notes.

## Partial publication

Uploads intentionally do not use overwrite/force flags. If a run fails after a
channel upload, inspect the channel file and compare its digest with the retained
CI artifact before resuming. Do not rebuild or replace an existing version, move
its tag, or blindly rerun an upload. Complete missing verification and GitHub
publication using the same retained artifact, or prepare a new version through
a PR if source changes are needed. No release has been published by adding this
workflow.
