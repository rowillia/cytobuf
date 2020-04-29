import os
import sys
from typing import List
from typing import Set

from google.protobuf.compiler import plugin_pb2

from cytobuf.protoc_gen_cython.cython_file import ProtoFile
from cytobuf.protoc_gen_cython.templates import externs_pxd_template
from cytobuf.protoc_gen_cython.templates import message_pxd_template
from cytobuf.protoc_gen_cython.templates import message_pyx_template
from cytobuf.protoc_gen_cython.templates import py_module_template
from cytobuf.protoc_gen_cython.templates import setup_py_template


FILENAME_TO_TEMPLATE = [
    (ProtoFile.extern_pxd_filename, externs_pxd_template),
    (ProtoFile.pxd_filename, message_pxd_template),
    (ProtoFile.pyx_filename, message_pyx_template),
    (ProtoFile.py_filename, py_module_template),
]


def write_module(proto_files: List[ProtoFile], response: plugin_pb2.CodeGeneratorResponse) -> None:
    modules: Set[str] = set()
    for proto_file in proto_files:
        for filename_func, template in FILENAME_TO_TEMPLATE:
            output = response.file.add()
            output.name = filename_func.fget(proto_file)  # type: ignore
            output.content = template.render(file=proto_file)
            module_path, _ = os.path.split(output.name)
            while module_path:
                modules.add(module_path)
                module_path, _ = os.path.split(module_path)
    for module in modules:
        output = response.file.add()
        output.name = f"{module}/__init__.pxd"
        output = response.file.add()
        output.name = f"{module}/__init__.py"
    output = response.file.add()
    output.name = "setup.py"
    output.content = setup_py_template.render(files=proto_files)


def main():
    data = sys.stdin.buffer.read()
    request = plugin_pb2.CodeGeneratorRequest()
    request.ParseFromString(data)
    response = plugin_pb2.CodeGeneratorResponse()
    cython_files = ProtoFile.from_file_descriptor_protos(
        request.proto_file, set(request.file_to_generate)
    )
    write_module(cython_files, response)
    sys.stdout.buffer.write(response.SerializeToString())


if __name__ == "__main__":
    main()
