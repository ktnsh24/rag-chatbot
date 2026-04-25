# Poetry Guide — How Poetry Works in This Project

## Table of Contents

- [What is Poetry?](#what-is-poetry)
- [Poetry vs pip — what is different](#poetry-vs-pip--what-is-different)
- [Key files Poetry uses](#key-files-poetry-uses)
- [pyproject.toml explained](#pyprojecttoml-explained)
- [poetry.lock](#poetrylock)
- [Every Poetry command you need](#every-poetry-command-you-need)
- [How Poetry manages the virtual environment](#how-poetry-manages-the-virtual-environment)
- [Adding a new package](#adding-a-new-package)
- [Removing packages](#removing-packages)
- [Updating](#updating)
- [Common issues and fixes](#common-issues-and-fixes)

---

## What is Poetry?

Poetry is a **package manager for Python**. It does three things:

1. **Manages dependencies** — knows which packages your project needs
2. **Manages the virtual environment** — creates an isolated Python installation
3. **Manages the lock file** — records the exact versions of every package

Think of it as npm/yarn for Python.

- 🫏 **Donkey:** The supply shed manifest — every tool and library is pinned to an exact version so any stable can reproduce the same setup.

---

## Poetry vs pip — what is different

| Task | pip (old way) | Poetry (this project) | 🫏 Donkey |
| --- | --- | --- | --- |
| Define dependencies | `requirements.txt` (manual) | `pyproject.toml` (structured) | The supply shed manifest — every tool the donkey needs, structured and versioned |
| Lock exact versions | `pip freeze > requirements.txt` (fragile) | `poetry.lock` (automatic) | Locks every tool to an exact version so any stable rebuilds the donkey identically |
| Install dependencies | `pip install -r requirements.txt` | `poetry install` | Tack-room inventory list — Install dependencies: pip install -r requirements.txt · poetry install |
| Add a package | Edit requirements.txt + `pip install` | `poetry add <package>` | Supply shed manifest — Add a package: Edit requirements.txt + pip install · poetry add <package> |
| Remove a package | Edit requirements.txt + `pip uninstall` | `poetry remove <package>` | Stable's supply ledger — Remove a package: Edit requirements.txt + pip uninstall · poetry remove <package> |
| Create venv | `python -m venv .venv` (manual) | `poetry install` (automatic) | Stable's supply ledger — Create venv: python -m venv .venv (manual) · poetry install (automatic) |
| Run a command in venv | `source .venv/bin/activate && python` | `poetry run python` | Stable's supply ledger — Run a command in venv: source .venv/bin/activate && python · poetry run python |
| Separate dev deps | Multiple requirements files | `[tool.poetry.group.dev.dependencies]` | Tack-room inventory list — Separate dev deps: Multiple requirements files · [tool.poetry.group.dev.dependencies] |

- 🫏 **Donkey:** The supply shed manifest — every tool and library is pinned to an exact version so any stable can reproduce the same setup.

---

## Key files Poetry uses

### `pyproject.toml`

This is the **source of truth** for your project. It defines:

- Project metadata (name, version, author)
- Python version requirement
- Runtime dependencies (what the app needs to run)
- Dev dependencies (what developers need: pytest, ruff, etc.)
- Tool configurations (ruff, pytest settings)
- Scripts (shortcuts like `poetry run start`)

### `poetry.lock`

This is the **lock file**. It records the exact version of every package (and their dependencies).

Why?
- `pyproject.toml` says `fastapi = "^0.115.0"` (any version >= 0.115.0 and < 1.0)
- `poetry.lock` says `fastapi = 0.115.2` (this exact version)
- This ensures everyone on the team gets the same versions
- Without a lock file, `poetry install` might install different versions on different machines

**Rule: Always commit `poetry.lock` to git.**

### `.venv/` directory

This is the virtual environment. It contains:

```
.venv/
├── bin/
│   ├── python → python3.12
│   ├── pip
│   ├── uvicorn
│   ├── pytest
│   └── ruff
├── lib/
│   └── python3.12/
│       └── site-packages/   ← all installed packages live here
│           ├── fastapi/
│           ├── pydantic/
│           ├── boto3/
│           └── ...
└── pyvenv.cfg
```

- 🫏 **Donkey:** The supply shed manifest — every tool and library is pinned to an exact version so any stable can reproduce the same setup.

---

## pyproject.toml explained

Here's what each section in this project's `pyproject.toml` means:

```toml
[tool.poetry]
name = "rag-chatbot"          # Project name
version = "0.1.0"             # Semantic version
description = "..."           # One-line description
authors = ["Your Name"]      # Who wrote it
packages = [{ include = "src" }]  # Where the source code is
```

```toml
[tool.poetry.dependencies]
python = "^3.12"              # Requires Python >= 3.12 and < 4.0
fastapi = "^0.115.0"          # Web framework
pydantic = "^2.9.0"           # Data validation
boto3 = "^1.35.0"             # AWS SDK
```

The `^` means "compatible with":
- `^0.115.0` → any version `>= 0.115.0` and `< 1.0.0`
- `^2.9.0` → any version `>= 2.9.0` and `< 3.0.0`

```toml
[tool.poetry.group.dev.dependencies]
pytest = "^8.3.0"             # Only installed in development, not production
ruff = "^0.6.0"               # Linter — not needed in production
```

```toml
[tool.poetry.scripts]
start = "src.main:run"        # `poetry run start` calls src/main.py → run()
```

- 🫏 **Donkey:** The specific delivery address the donkey is dispatched to — each route handles a different type of cargo drop-off.

---

## Every Poetry command you need

### Installing

```bash
# Install all dependencies (runtime + dev)
poetry install

# Install only runtime dependencies (for production)
poetry install --without dev

# Install and update the lock file
poetry install --no-cache
```

### Running

```bash
# Run a command inside the virtual environment
poetry run python -c "print('hello')"

# Run the app
poetry run start

# Run tests
poetry run pytest

# Run linter
poetry run ruff check src/
```

### Adding packages

```bash
# Add a runtime dependency
poetry add httpx

# Add a dev dependency
poetry add --group dev pytest-mock

# Add with version constraint
poetry add "pydantic>=2.9,<3.0"
```

### Removing packages

```bash
# Remove a package
poetry remove httpx

# Remove a dev package
poetry remove --group dev pytest-mock
```

### Updating

```bash
# Update all packages to latest compatible versions
poetry update

# Update a specific package
poetry update fastapi

# Show outdated packages
poetry show --outdated
```

### Environment management

```bash
# Show current environment info
poetry env info

# Use a specific Python version
poetry env use python3.12

# List all environments
poetry env list

# Delete the environment (to recreate)
poetry env remove python3.12
# Then: poetry install
```

### Inspecting

```bash
# Show all installed packages
poetry show

# Show a specific package and its dependencies
poetry show fastapi

# Show the dependency tree
poetry show --tree

# Validate pyproject.toml
poetry check
```

- 🫏 **Donkey:** The supply shed manifest — every tool and library is pinned to an exact version so any stable can reproduce the same setup.

---

## How Poetry manages the virtual environment

When you run `poetry install`, Poetry:

1. Reads `pyproject.toml` for dependency requirements
2. Reads `poetry.lock` for exact versions (or resolves new versions if no lock file)
3. Creates `.venv/` if it doesn't exist (because we set `virtualenvs.in-project = true`)
4. Installs all packages into `.venv/lib/python3.12/site-packages/`
5. Makes commands available in `.venv/bin/` (uvicorn, pytest, ruff, etc.)

### Activating the virtual environment

Two ways to use the venv:

**Option A: Activate it (traditional)**
```bash
source .venv/bin/activate
python -c "import fastapi; print(fastapi.__version__)"
deactivate
```

**Option B: Use `poetry run` (recommended)**
```bash
poetry run python -c "import fastapi; print(fastapi.__version__)"
```

`poetry run` automatically uses the correct Python from `.venv/` without needing to activate.

- 🫏 **Donkey:** The supply shed manifest — every tool and library is pinned to an exact version so any stable can reproduce the same setup.

---

## Adding a new package

Example: you want to add Redis support.

```bash
# 1. Add the package
poetry add redis

# What happens:
#   - pyproject.toml gets a new line: redis = "^5.0.0"
#   - poetry.lock gets updated with the exact version
#   - The package gets installed into .venv/

# 2. Use it in your code
# src/some_file.py:
# import redis
# client = redis.Redis()

# 3. Commit both files
git add pyproject.toml poetry.lock
git commit -m "feat: add Redis support"
```

- 🫏 **Donkey:** Like a well-trained donkey that knows this part of the route by heart — reliable, consistent, and essential to the delivery system.

---

## Common issues and fixes

### "The currently activated Python version X.Y is not supported"

```bash
# Install the correct Python version first, then:
poetry env use python3.12
poetry install
```

### "No module named 'xxx'"

```bash
# The venv isn't activated. Either:
source .venv/bin/activate
# or use:
poetry run python your_script.py
```

### "poetry.lock is not consistent with pyproject.toml"

```bash
# Regenerate the lock file
poetry lock --no-update
poetry install
```

### "Resolver takes too long"

```bash
# Clear the cache
poetry cache clear --all pypi
poetry install
```

- 🫏 **Donkey:** When the donkey returns empty-hooved — use the trip log and bag inspection checklist to find what went wrong.
