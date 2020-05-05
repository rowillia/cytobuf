import argparse
import os
import sys
from typing import List
from typing import Set

from google.protobuf.compiler import plugin_pb2

from cytobuf.protoc_gen_cython.constants import DEFAULT_INCLUDE_DIRECTORY
from cytobuf.protoc_gen_cython.cython_file import Module
from cytobuf.protoc_gen_cython.cython_file import ProtoFile
from cytobuf.protoc_gen_cython.templates import merged_pyx_template
from cytobuf.protoc_gen_cython.templates import message_pxd_template
from cytobuf.protoc_gen_cython.templates import message_pyx_template
from cytobuf.protoc_gen_cython.templates import py_enum_template
from cytobuf.protoc_gen_cython.templates import py_module_template
from cytobuf.protoc_gen_cython.templates import setup_py_template


FILENAME_TO_TEMPLATE = [
    (Module.pxd_filename, message_pxd_template),
    (Module.pyx_filename, message_pyx_template),
    (Module.py_filename, py_module_template),
]


def write_module(proto_files: List[ProtoFile], response: plugin_pb2.CodeGeneratorResponse) -> None:
    modules: Set[str] = set()
    pyx_files: Set[str] = set()
    for proto_file in proto_files:
        for filename_func, template in FILENAME_TO_TEMPLATE:
            output = response.file.add()
            output.name = filename_func.fget(proto_file.module)  # type: ignore
            output.content = template.render(file=proto_file)
            filename = output.name
            register_modules(filename, modules)
        pyx_files.add(proto_file.module.pyx_filename)
        if proto_file.enums:
            output = response.file.add()
            output.name = proto_file.module.enum_module.py_filename
            output.content = py_enum_template.render(file=proto_file)
            register_modules(output.name, modules)

    for module in modules:
        output = response.file.add()
        output.name = f"{module}/__init__.pxd"
        output = response.file.add()
        output.name = f"{module}/__init__.py"
    pyx_files.add("_merged_cython_protos.pyx")
    output = response.file.add()
    output.name = "setup.py"
    output.content = setup_py_template.render(pyx_files=pyx_files)
    filtered_proto_files = []
    for proto_file in proto_files:
        if proto_file.cpp_header.startswith("google") and os.path.exists(
            os.path.join(DEFAULT_INCLUDE_DIRECTORY, proto_file.cpp_header)
        ):
            continue
        filtered_proto_files.append(proto_file)
    output = response.file.add()
    output.name = "_merged_cython_protos.pyx"
    output.content = merged_pyx_template.render(files=filtered_proto_files)


def register_modules(filename: str, modules: Set[str]) -> None:
    module_path, _ = os.path.split(filename)
    while module_path:
        modules.add(module_path)
        module_path, _ = os.path.split(module_path)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prefix", type=str, default="")
    data = sys.stdin.buffer.read()
    request = plugin_pb2.CodeGeneratorRequest()
    request.ParseFromString(data)
    args = parser.parse_args(request.parameter.split())

    response = plugin_pb2.CodeGeneratorResponse()
    cython_files = ProtoFile.from_file_descriptor_protos(
        request.proto_file, set(request.file_to_generate), args.prefix
    )
    write_module(cython_files, response)
    sys.stdout.buffer.write(response.SerializeToString())


if __name__ == "__main__":
    main()
