
# Installation Guide

This guide covers how to install **Slurpy** using `uv`, an extremely
fast Python package installer and resolver. The project is available
on PyPI under the name `super-slurpy`.

## Prerequisites
Before you begin, ensure you have `uv` installed on your system. If
you do not have `uv` installed, you can install it via curl, pip, or
your system package manager.

[How to install uv](https://docs.astral.sh/uv/getting-started/installation/)

## Installing slurpy

If you just want to run slurpy as an isolated application so the `slurpy`
command is available everywhere on your system, use the `tool` command:

```bash
uv tool install super-slurpy
```

If you are going to be using slurpy in scripting, install the package globally
or within an active virtual environment with the following command:

```bash
uv pip install super-slurpy
```


## Verifying the Installation
Once installed, you can verify that the CLI is accessible by
checking the available commands:

```bash
slurpy --help
```
