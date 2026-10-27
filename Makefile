.PHONY: all setup build install test lint clean run-help

PYTHON ?= python3
CARGO ?= cargo

all: build

## Set up Python virtual environment and install dependencies
setup:
	$(PYTHON) -m venv .venv
	.venv/bin/pip install --upgrade pip
	.venv/bin/pip install -e ".[dev]"

## Compile the optimized native Rust `kit` binary
build:
	$(CARGO) build --release

## Install both the Rust binary and Python companion toolkit locally
install:
	$(PYTHON) -m pip install -e .
	$(CARGO) install --path .

## Run Python unit tests and Rust cargo tests
test:
	PYTHONPATH=python $(PYTHON) -m unittest discover -s tests -p "test_*.py" -v
	@if command -v $(CARGO) >/dev/null 2>&1; then $(CARGO) test; else echo "Cargo not installed; skipping Rust test target"; fi

## Run the standalone Python CLI directly (works without compiling Rust)
run-help:
	PYTHONPATH=python $(PYTHON) -m kit_py.cli --help

clean:
	rm -rf target/ build/ dist/ python/*.egg-info .pytest_cache/
	find . -name "__pycache__" -type d -exec rm -rf {} +
