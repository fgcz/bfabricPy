.PHONY: install install_dev build clean

install: 
	pip install -e .

install_dev:
    pip install -e ".[dev]"

test: test_read

test_workunit:
	python3 -m unittest -v bfabric/tests/test_bfabric_workunit.py 

test_read:
	cd bfabric/tests && python3 -m unittest -v test_bfabric_read.py 

