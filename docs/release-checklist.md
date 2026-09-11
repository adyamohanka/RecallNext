# Release and submission checklist

Record the reviewer, timestamp, revision and evidence path for each completed
item. Leave an item unchecked when it has not been verified.

## Repository and reproducibility

- [ ] Canonical repository is public and `main` contains the final application
  and submission assets.
- [ ] Dependency pull requests are merged; the demo uses no unpushed code.
- [ ] A fresh checkout has no modified or untracked files after the documented
  setup.
- [ ] Python, Node.js, pnpm and Exasol versions are recorded.
- [ ] `python -m data.generate_fixture --check` passes.
- [ ] `python -m pytest -q` passes.
- [ ] Ruff lint and formatting checks pass.
- [ ] `pnpm --dir frontend install --frozen-lockfile` and
  `pnpm --dir frontend build` pass.
- [ ] `frontend/pnpm-lock.yaml` is committed; npm and Yarn lockfiles are absent.
- [ ] The README and run guide match the actual commands and ports.

## Exasol and integration

- [ ] Exasol Personal schema load and smoke check pass on the documented
  deployment.
- [ ] Exasol version, deployment type, sanitized output and tested revision are
  saved.
- [ ] Candidate count, blocking issues and query timings are measured rather
  than copied from fixture expectations.
- [ ] The demo clearly labels the API’s data source. Do not describe the API as
  Exasol-backed until its repository adapter is connected and tested.
- [ ] Database, planner and end-to-end times are reported separately.

## Correctness and safety

- [ ] All four statuses agree across SQL, Python, API tests and UI text.
- [ ] Missing coverage, duplicate inventory, invalid scenarios, conflicts,
  infeasibility, timeout and limits remain unresolved.
- [ ] Same lot code from different sources remains distinct.
- [ ] One mixed-container case scan cannot clear the remaining cases.
- [ ] Proposed and rejected evidence leaves the incident unchanged.
- [ ] Stale proposals and stale expected versions return a conflict.
- [ ] Retraction creates a version and invalidates its dependent decision.
- [ ] Exasol persistence rejects status/bounds/solver/completeness disagreement.
- [ ] The UI states that exclusion under assumptions does not mean safe.

## Evaluation

- [ ] Correctness claims are limited to the declared finite fixtures.
- [ ] Each strategy receives the same facts, evidence, outcomes and budget.
- [ ] Hidden truth is accessible only to the scorer or oracle.
- [ ] Raw per-incident results retain seeds, ties, failures and baseline wins.
- [ ] Simulated retrieval minutes are separate from computation time.
- [ ] No estimated or expected value is presented as measured.

## Secrets and files

- [ ] Tracked files and the PR diff contain no token, password, private key,
  personal record or private document.
- [ ] `.env`, databases, deployment state and generated secrets are untracked.
- [ ] Generated files are reproducible and small enough for the public repo.
- [ ] Links, filenames and capitalization work from a logged-out browser.
- [ ] Licence and third-party attribution are present.

## Deck, video and submission

- [ ] Final pitch deck PDF or PPT is in the public repository.
- [ ] Demo video is present and no longer than three minutes.
- [ ] Deck and narration use measured results or explicit pending language.
- [ ] Exasol is visibly running substantive SQL if the demo claims live use.
- [ ] Human review, the safety notice and one conflict or retraction are visible.
- [ ] Video shows no credential, private tab or unsupported feature.
- [ ] Repository, deck, video and run guide open from a logged-out browser.
- [ ] Final form is submitted before 13 September 2026, 11:59 pm IST.
- [ ] Submission acknowledgement is saved by the team owner.
