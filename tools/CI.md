# ABDO CI

`tools/ci-workflow.yml` is a ready GitHub Actions workflow. It cannot be pushed with the current
token: GitHub rejects any commit that creates or edits a file under `.github/workflows/` unless
the token has the **workflow** scope.

Two ways to enable it, both one-time:
1. GitHub → Settings → Developer settings → Personal access tokens → the token in use → tick
   **workflow** → regenerate. Then tell me and I push it.
2. Or paste it yourself: repo → Add file → commit path exactly `.github/workflows/gates.yml`,contents from `tools/ci-workflow.yml`.

Until then every gate below still runs locally (`python3 tools/gates.py`) and I must report that
it ran, rather than assuming CI did it.
