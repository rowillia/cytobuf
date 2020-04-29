proto_files	:=      $(shell cd ./tests && find . -iname "*.proto")

.PHONY: benchmark
benchmark: install
	./venv/bin/python benchmark.py

scratch:
	mkdir -p scratch

cc: scratch
	mkdir -p scratch/cc
	protoc -I. --cpp_out=scratch/cc $(proto_files)

py: scratch
	mkdir -p scratch/py
	protoc -I. --python_out=scratch/py $(proto_files)

cy: scratch install
	mkdir -p scratch/cy
	( \
		source venv/bin/activate; \
        cd ./tests; \
		protoc -I. --cython_out=../scratch/cy --cpp_out=../scratch/cy $(proto_files); \
		cd ../scratch/cy; \
		python -m pip install .; \
	)

venv:
	python3 -m virtualenv venv

install: venv scratch dev-requirements.txt setup.py $(shell find cytobuf -type f)
	./venv/bin/pip install -r dev-requirements.txt
	./venv/bin/pip install .
