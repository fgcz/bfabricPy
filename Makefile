.PHONY: install build clean

## TODO(leo): make  venv
install: 
	pip install -e .
build: 
	python3 setup.py sdist 
clean:
	rm -vf dist/*

