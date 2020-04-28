import sys

from google.protobuf.compiler import plugin_pb2

from cytobuf.protoc_gen_cython.cython_file import ProtoFile
from cytobuf.protoc_gen_cython.templates import externs_pxd_template


def write_pxd_file(proto_file: ProtoFile, response: plugin_pb2.CodeGeneratorResponse) -> None:
    output = response.file.add()
    output.name = proto_file.extern_pxd_filename
    output.content = externs_pxd_template.render(file=proto_file)


def main():
    data = sys.stdin.buffer.read()
    request = plugin_pb2.CodeGeneratorRequest()
    request.ParseFromString(data)
    response = plugin_pb2.CodeGeneratorResponse()
    cython_files = ProtoFile.from_file_descriptor_protos(
        request.proto_file, set(request.file_to_generate)
    )
    for cython_file in cython_files:
        write_pxd_file(cython_file, response)

    sys.stdout.buffer.write(response.SerializeToString())


if __name__ == "__main__":
    main()
