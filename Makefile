.PHONY: install install_dev clean test


install:
	pip install -e .

install_dev:
	pip install -e ".[dev]"

test:
	nox

clean:
	rm -vf dist/*

