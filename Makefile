
install: test build
	sudo pip3 install dist/bfabric*.gz -e .

build: clean 
	python3 setup.py sdist 


clean:
	rm -vf dist/*

test:
	cd bfabric/tests/ && python3 -m unittest discover
