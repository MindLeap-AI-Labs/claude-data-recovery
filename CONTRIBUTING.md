# Contributing

Thank you for helping improve Claude Data Recovery.

## Before opening an issue

- Search existing issues.
- Reproduce the problem with the latest `main` branch.
- Remove all personal information.
- Create the smallest possible synthetic JSON fixture.

Never upload a real Claude export, conversation transcript, account identifier, memory file, attachment, or generated recovery output.

## Development setup

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
python -m unittest discover -s tests -v
```

## Pull requests

1. Keep each pull request focused.
2. Add or update tests for parser changes.
3. Use synthetic fixtures only.
4. Preserve offline operation and standard-library-only runtime dependencies.
5. Update the README when behavior changes.

By contributing, you agree that your contribution is licensed under the MIT License.
