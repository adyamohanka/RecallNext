# Contributing

Create a feature branch from the latest `main`. Do not commit directly to `main`, force-push another contributor’s branch or include credentials and database files.

Before opening a pull request, run:

```bash
python -m data.generate_fixture --check
python -m pytest -q
ruff check backend data planner tests
ruff format --check backend data planner tests
cd frontend && pnpm build
```

Pull requests should explain the behavior changed, how to run it, checks completed, known limitations and the next integration dependency. Changes to status values, evidence lifecycle or API fields require an update to `docs/api-contract.md` in the same pull request.
