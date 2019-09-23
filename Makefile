test: test_workunit test_read

test_workunit:
	python3 -m unittest -v bfabric/tests/test_bfabric_workunit.py 

test_read:
	cd bfabric/tests && python3 -m unittest -v test_bfabric_read.py 

install: test build
	sudo pip3 install dist/bfabric*.gz -e .

build: clean 
	python3 setup.py sdist 


clean:
	rm -vf dist/*

