# To create venv with uv

```bash
uv venv
```

# To install dependencies with custom wheel files

This will install dependencies defined in ```pyproject.toml```
But it will also attempt to install packages within project, which is not desirable for this django project

```bash
uv pip install --find-links ./py_wheels/ -e .
```

# To install pip compiling

To generate requirements.txt from requirements.in

```bash
❯ uv pip compile --find-links ./py_wheels requirements.in > requirements.txt
```

Then install dependencies

```bash
❯ uv pip install --find-links ./py_wheels -r requirements.txt
```