proto_files	:=      $(shell cd ./tests && find . -iname "*.proto")

.PHONY: benchmark
benchmark: install
	./venv/bin/python benchmark.py

scratch:
	mkdir -p scratch

cc: scratch
	mkdir -p scratch/cc
	cd ./tests && protoc -I. --cpp_out=../scratch/cc $(proto_files)

py: scratch
	mkdir -p scratch/py
	cd ./tests && protoc -I. --python_out=../scratch/py $(proto_files)

cy: scratch install
	mkdir -p scratch/cy
	( \
		source venv/bin/activate; \
        cd ./tests; \
        pyrobuf pb/flat_addressbook.proto --install --package=pyrobuf_flat_pb; \
        protoc -I. --cython_out=../scratch/cy --cpp_out=../scratch/cy --cython_opt="--prefix=cytobuf_" $(proto_files); \
		cd ../scratch/cy; \
		python -m pip install .; \
	)

venv:
	python3 -m virtualenv venv

install: venv scratch dev-requirements.txt setup.py $(shell find cytobuf -type f)
	./venv/bin/pip install -r dev-requirements.txt
	./venv/bin/pip install .
	./venv/bin/python setup.py build_ext --inplace

benchmark: cy py
	cd tests/performance && ../../venv/bin/python benchmark.py