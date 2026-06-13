# Contributing

Thanks for considering an improvement to Auto-Sentinel.

## Before You Start

- Search existing issues and open a focused issue for substantial changes.
- Keep the project within passive wireless discovery, capture analysis, and
  authorized security assessment.
- Never commit real capture data, credentials, private network identifiers, or
  generated reports containing sensitive information.

## Development Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

Run the checks used by CI:

```bash
ruff check .
python -m coverage run -m unittest discover -s tests -v
python -m coverage report
```

Set `QT_QPA_PLATFORM=offscreen` when running GUI tests on a headless Linux
system.

## Pull Requests

- Keep each pull request limited to one clear problem.
- Add or update tests for behavioral changes.
- Update the README and changelog when user-facing behavior changes.
- Explain platform-specific behavior for Linux hardware mode or macOS/Windows
  mock mode.

By contributing, you agree that your contribution is licensed under the MIT
License.
