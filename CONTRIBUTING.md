# Contributing

Fork `harinidev1507/RecallNext`, keep that canonical repository as a read-only
`upstream` remote, and create a focused branch in your fork. Open a pull request
back to the intended canonical branch. Do not commit directly to `main`,
force-push another contributor’s branch, or include credentials and database
files. State dependency pull requests when your target branch has not merged
them yet.

Before opening a pull request, run:

```bash
python -m data.generate_fixture --check
python -m pytest -q
ruff check backend data planner tests
ruff format --check backend data planner tests
pnpm --dir frontend install --frozen-lockfile
pnpm --dir frontend build
```

Pull requests should explain the behavior changed, how to run it, checks completed, known limitations and the next integration dependency. Changes to status values, evidence lifecycle or API fields require an update to `docs/api-contract.md` in the same pull request.

The frontend uses pnpm only. Commit `frontend/pnpm-lock.yaml`; do not add npm or
Yarn lockfiles.
