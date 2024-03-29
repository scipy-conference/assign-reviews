# Python project template

This is a template repository for any Python project that comes with the following dev tools:

* `ruff`: identifies many errors and style issues (`flake8`, `isort`, `pyupgrade`)
* `black`: auto-formats code

Those checks are run as pre-commit hooks using the `pre-commit` library.

It includes `pytest` for testing plus the `pytest-cov` plugin to measure coverage.

The checks and tests are all run using Github actions on every pull request and merge to main.

This repository is setup for Python 3.11. To customize that, change the `VARIANT` argument in `.devcontainer/devcontainer.json`, change the config options in `.precommit-config.yaml` and change the version number in `.github/workflows/python.yaml`.

## Development instructions

## With devcontainer

This repository comes with a devcontainer (a Dockerized Python environment). If you open it in Codespaces, it should automatically initialize the devcontainer.

Locally, you can open it in VS Code with the Dev Containers extension installed.

## Without devcontainer

If you can't or don't want to use the devcontainer, then you should first create a virtual environment:

```
python3 -m venv .venv
source .venv/bin/activate
```

Then with the virtual environment activated, install the dev tools and pre-commit hooks:

```
python3 -m pip install -r requirements-dev.txt
pre-commit install
```

To install the requirements for the application from the `uv` generated lock file, run:

```
uv pip install --strict --requirement requirements.lock
```

## Updating the lock file

To regenerate the lock file from the high level `requirements.txt` run

```
uv pip compile requirements.txt --generate-hashes --output-file requirements.lock
```

## Adding code and tests

This repository starts with a very simple `main.py` and a test for it at `tests/main_test.py`.
You'll want to replace that with your own code, and you'll probably want to add additional files
as your code grows in complexity.

When you're ready to run tests, run:

```
python3 -m pytest
```

## Using `jupytext` with Jupyter notebooks

[`jupytext`](https://jupytext.readthedocs.io/) allows for easier versioning of Jupyter notebooks by saving all of the information that exists in them in [specially formatted](https://jupytext.readthedocs.io/en/latest/formats-scripts.html#the-percent-format) `.py` files and then generating the notebook representation when you [select them in a Jupyter interface](https://jupytext.readthedocs.io/en/latest/text-notebooks.html#how-to-open-a-text-notebook-in-jupyter-lab).
Version the `.py` files as you normally would with any other text file.
To run the `.py` files as Jupyter notebooks, select them in the Jupyter file browser, right click, and then select _Open With → Notebook_.
Any changes made in a Jupyter notebook will be automatically synced to the [paired](https://jupytext.readthedocs.io/en/latest/paired-notebooks.html) `.py` file.

# File breakdown

Here's a short explanation of each file/folder in this template:

* `.devcontainer`: Folder containing files used for setting up a devcontainer
  * `devcontainer.json`: File configuring the devcontainer, includes VS Code settings
  * `Dockerfile`: File with commands to build the devcontainer's Docker image
* `.github`: Folder for Github-specific files and folders
  * `workflows`: Folder containing Github actions config files
    * `python.yaml`: File configuring Github action that runs tools and tests
* `tests`: Folder containing Python tests
  * `main_test.py`: File with pytest-style tests of main.py
* `.gitignore`: File describing what file patterns Git should never track
* `.pre-commit-config.yaml`: File listing all the pre-commit hooks and args
* `main.py`: The main (and currently only) Python file for the program
* `pyproject.toml`: File configuring most of the Python dev tools
* `README.md`: You're reading it!
* `requirements-dev.txt`: File listing all PyPi packages required for development
* `requirements.txt`: File listing all PyPi packages required for production

For a longer explanation, read [this blog post](http://blog.pamelafox.org/2022/09/how-i-setup-python-project.html).

# 🔎 Found an issue or have an idea for improvement?

Help me make this template repository better by letting us know and opening an issue!
