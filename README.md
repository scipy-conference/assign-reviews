# Python project template

This is a template repository for any Python project that comes with the following dev tools:

* `ruff`: identifies many errors and style issues (`flake8`, `isort`, `pyupgrade`)
* `black`: auto-formats code

Those checks are run as pre-commit hooks using the `pre-commit` library.

It includes `pytest` for testing plus the `pytest-cov` plugin to measure coverage.

The checks and tests are all run using Github actions on every pull request and merge to main.

This repository is setup for Python 3.11. To customize that, change the `VARIANT` argument in `.devcontainer/devcontainer.json`, change the config options in `.precommit-config.yaml` and change the version number in `.github/workflows/python.yaml`.

## Assign Reviewers

First download the following files from Preltax into the `data/` directory:

* `scipy_reviewers.csv`  # people who signed up as reviewers
* `sessions.csv`  # all proposal exported from pretalx
* `speakers.csv`  # all speakers exported from pretalx
* `pretalx_reviewers.csv`  # all reviewers copy-pasted from pretalx
* `scipy_coi_export.csv`  # all responses to the coi form
* `coi_authors.csv`  # copy pasted values of author names from coi form
* `tracks.csv`  # manually entered track IDs

Then run the notebooks as Python files in the following order with `pixi`

```
$ pixi run pre-processing
$ pixi run assignments
```

## Development instructions

## With devcontainer

This repository comes with a devcontainer (a Dockerized Python environment). If you open it in Codespaces, it should automatically initialize the devcontainer.

Locally, you can open it in VS Code with the Dev Containers extension installed.

## Without devcontainer

If you can't or don't want to use the devcontainer, then use [`pixi`](https://pixi.sh/) to control the application.
If you don't have `pixi` installed yet, follow the 1-liner [install command](https://pixi.sh/latest/#installation) for the Rust binary for your operating system.

Then to install the full environment from the multi platform lock file simply just run

```
pixi install
```

To execute a specific task defined in the [task runner section](https://pixi.sh/latest/advanced/advanced_tasks/) just run

```
pixi run <task name>
```

So for example, to run all the tests run

```
pixi run test
```

or to lint

```
pixi run lint
```

If you would like to have interactive shell access (like a classic virtual environment) run

```
pixi shell
```

and you will be dropped into a new shell with the environment activated.

## Updating the lock file

To regenerate the lock file from the project `pixi.toml` run

```
rm pixi.lock && pixi install
```

This will be very fast!

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
