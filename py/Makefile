build: clean
	python setup.py sdist 

install: build
	sudo pip install dist/bfabric*.gz -e .

clean:
	rm -vf dist/*

