from __future__ import annotations

import os
import re
from enum import auto
from enum import Enum
from itertools import chain
from typing import Dict
from typing import Iterable
from typing import List
from typing import NamedTuple
from typing import Optional
from typing import Set

from google.protobuf.descriptor_pb2 import DescriptorProto
from google.protobuf.descriptor_pb2 import EnumDescriptorProto
from google.protobuf.descriptor_pb2 import FieldDescriptorProto
from google.protobuf.descriptor_pb2 import FileDescriptorProto


STRING_TYPES = {FieldDescriptorProto.TYPE_STRING, FieldDescriptorProto.TYPE_BYTES}

FLOAT_TYPES = {FieldDescriptorProto.TYPE_DOUBLE, FieldDescriptorProto.TYPE_FLOAT}

INT_TYPES = {
    FieldDescriptorProto.TYPE_INT32,
    FieldDescriptorProto.TYPE_UINT32,
    FieldDescriptorProto.TYPE_FIXED32,
    FieldDescriptorProto.TYPE_SFIXED32,
    FieldDescriptorProto.TYPE_SINT32,
}

LONG_TYPES = {
    FieldDescriptorProto.TYPE_INT64,
    FieldDescriptorProto.TYPE_UINT64,
    FieldDescriptorProto.TYPE_FIXED64,
    FieldDescriptorProto.TYPE_SFIXED64,
    FieldDescriptorProto.TYPE_SINT64,
}

UNSIGNED_TYPES = {
    FieldDescriptorProto.TYPE_UINT64,
    FieldDescriptorProto.TYPE_UINT32,
    FieldDescriptorProto.TYPE_SFIXED64,
    FieldDescriptorProto.TYPE_SFIXED32,
}


def proto_filename_to_base(proto_filename):
    return re.sub(r"\.proto$", "", proto_filename)


class ProtoCythonSymbol(NamedTuple):
    file_descriptor: FileDescriptorProto
    name: str

    @staticmethod
    def build_fqn_to_symbol_map(
        file_descriptors: Iterable[FileDescriptorProto]
    ) -> Dict[str, ProtoCythonSymbol]:
        fqn_to_symbol: Dict[str, ProtoCythonSymbol] = {}

        def _add_symbols(
            symbols: Iterable[str], prefix: Iterable[str], file_descriptor: FileDescriptorProto
        ) -> None:
            fqn_prefix = ".".join(chain(["." + file_descriptor.package or "."], prefix))
            for symbol in symbols:
                fqn = f"{fqn_prefix}.{symbol}"
                symbol = "_".join(chain(prefix, [symbol]))
                fqn_to_symbol[fqn] = ProtoCythonSymbol(file_descriptor, symbol)

        def _add_messages(
            messages: Iterable[DescriptorProto],
            prefix: List[str],
            file_descriptor: FileDescriptorProto,
        ) -> None:
            for message in messages:
                _add_symbols([message.name], prefix, file_descriptor)
                sub_prefix = prefix + [message.name]
                _add_messages(message.nested_type, sub_prefix, file_descriptor)
                _add_symbols((enum.name for enum in message.enum_type), sub_prefix, file_descriptor)

        for fd in file_descriptors:
            _add_messages(fd.message_type, [], fd)
            _add_symbols((enum.name for enum in fd.enum_type), [], fd)
        return fqn_to_symbol


class CImport(NamedTuple):
    module: str
    symbol: str


class ProtoEnum(NamedTuple):
    name: str
    value_names: List[str]

    @staticmethod
    def from_enum_descriptor(enum_type: EnumDescriptorProto, prefix: str = "") -> ProtoEnum:
        return ProtoEnum(
            name=f"{prefix}{enum_type.name}", value_names=[value.name for value in enum_type.value]
        )


class FieldType(Enum):
    scalar = auto()
    message = auto()


class Signature(NamedTuple):
    parameters: List[str]
    return_type: Optional[str] = None


class Field(NamedTuple):
    name: str
    field_type: FieldType
    repeated: bool
    return_type: str
    input_signatures: List[Signature]
    mutable_return_type: Optional[str] = None

    @staticmethod
    def create_string(name: str, repeated: bool = False) -> Field:
        return Field(
            name=name,
            field_type=FieldType.scalar,
            repeated=repeated,
            mutable_return_type="string*",
            return_type="const string&",
            input_signatures=[
                Signature(parameters=["const char*"]),
                Signature(parameters=["const char*", "int index"]),
            ],
        )

    @staticmethod
    def create_float(name: str, repeated: bool = False) -> Field:
        return Field(
            name=name,
            field_type=FieldType.scalar,
            repeated=repeated,
            return_type="float",
            input_signatures=[Signature(parameters=["float"])],
        )

    @staticmethod
    def create_int(name: str, unsigned: bool = False, repeated: bool = False) -> Field:
        prefix = "unsigned " if unsigned else ""
        return Field(
            name=name,
            field_type=FieldType.scalar,
            repeated=repeated,
            return_type=f"{prefix}int",
            input_signatures=[Signature(parameters=[f"{prefix}int"])],
        )

    @staticmethod
    def create_bool(name: str, repeated: bool = False) -> Field:
        return Field(
            name=name,
            field_type=FieldType.scalar,
            repeated=repeated,
            return_type="bool",
            input_signatures=[Signature(parameters=["bool"])],
        )

    @staticmethod
    def create_long(name: str, unsigned: bool = False, repeated: bool = False) -> Field:
        prefix = "unsigned " if unsigned else ""
        return Field(
            name=name,
            field_type=FieldType.scalar,
            repeated=repeated,
            return_type=f"{prefix}long long",
            input_signatures=[Signature(parameters=[f"{prefix}long long"])],
        )

    @staticmethod
    def create_enum(name: str, enum_type: str, repeated: bool = False) -> Field:
        return Field(
            name=name,
            field_type=FieldType.scalar,
            repeated=repeated,
            return_type=enum_type,
            input_signatures=[Signature(parameters=[f"{enum_type} value"])],
        )

    @staticmethod
    def create_message(name: str, message_name: str, repeated: bool = False) -> Field:
        return Field(
            name=name,
            field_type=FieldType.message,
            repeated=repeated,
            return_type=f"const {message_name}&",
            input_signatures=[],
            mutable_return_type=f"{message_name}*",
        )

    @staticmethod
    def from_field_descriptor(
        field_descriptor: FieldDescriptorProto,
        fqn_map: Dict[str, ProtoCythonSymbol],
        imports: Set[CImport],
    ) -> Optional[Field]:
        repeated = field_descriptor.label == FieldDescriptorProto.LABEL_REPEATED
        field_type = field_descriptor.type
        if field_type in FLOAT_TYPES:
            return Field.create_float(field_descriptor.name, repeated)
        elif field_type in INT_TYPES:
            return Field.create_int(field_descriptor.name, field_type in UNSIGNED_TYPES, repeated)
        elif field_type in LONG_TYPES:
            return Field.create_long(field_descriptor.name, field_type in UNSIGNED_TYPES, repeated)
        elif field_type in STRING_TYPES:
            return Field.create_string(field_descriptor.name, repeated)
        elif field_type == FieldDescriptorProto.TYPE_BOOL:
            return Field.create_bool(field_descriptor.name, repeated)
        elif field_type == FieldDescriptorProto.TYPE_ENUM:
            symbol = Field.add_import(field_descriptor, fqn_map, imports)
            return Field.create_enum(field_descriptor.name, symbol.name, repeated)
        elif field_type == FieldDescriptorProto.TYPE_MESSAGE:
            symbol = Field.add_import(field_descriptor, fqn_map, imports)
            return Field.create_message(field_descriptor.name, symbol.name, repeated)
        return None

    @staticmethod
    def add_import(
        field_descriptor: FieldDescriptorProto,
        fqn_map: Dict[str, ProtoCythonSymbol],
        imports: Set[CImport],
    ) -> ProtoCythonSymbol:
        type_name: str = field_descriptor.type_name
        symbol = fqn_map[type_name]
        if symbol.file_descriptor.package:
            module_basename = proto_filename_to_base(os.path.basename(symbol.file_descriptor.name))
            module = f"{symbol.file_descriptor.package}.{module_basename}"
            imports.add(CImport(module, symbol.name))
        return symbol


class Class(NamedTuple):
    name: str
    fields: List[Field]

    @staticmethod
    def from_descriptor(
        descriptor: DescriptorProto,
        fqn_map: Dict[str, ProtoCythonSymbol],
        imports: Set[CImport],
        prefix: str = "",
    ) -> Class:
        return Class(
            name=f"{prefix}{descriptor.name}",
            fields=[
                cython_field
                for cython_field in (
                    Field.from_field_descriptor(field, fqn_map, imports)
                    for field in descriptor.field
                )
                if cython_field is not None
            ],
        )


class ProtoFile(NamedTuple):
    imports: Iterable[CImport]
    cpp_header: str
    namespace: List[str]
    enums: List[ProtoEnum]
    classes: List[Class]
    proto_filename: str

    @property
    def pxd_filename(self):
        return self.proto_filename[:-6].replace("-", "_").replace(".", "/") + "_pb2.pxd"

    @staticmethod
    def from_file_descriptor_proto(
        file_descriptor: FileDescriptorProto, fqn_map: Dict[str, ProtoCythonSymbol]
    ) -> ProtoFile:
        cpp_header: str = proto_filename_to_base(file_descriptor.name) + ".pb.h"
        namespace = file_descriptor.package.split(".")
        classes: List[Class] = []
        imports = {CImport("libcpp.string", "string")}
        enums = [
            ProtoEnum.from_enum_descriptor(enum_type) for enum_type in file_descriptor.enum_type
        ]
        for descriptor in file_descriptor.message_type:
            ProtoFile._add_class(descriptor, fqn_map, classes, enums, imports)
        filtered_imports = sorted(imp for imp in imports if imp.module != file_descriptor.package)
        return ProtoFile(
            imports=filtered_imports,
            cpp_header=cpp_header,
            namespace=namespace,
            enums=enums,
            classes=classes,
            proto_filename=file_descriptor.name,
        )

    @staticmethod
    def from_file_descriptor_protos(
        file_descriptors: Iterable[FileDescriptorProto], files_to_generate: Set[str]
    ) -> List[ProtoFile]:
        fqn_map = ProtoCythonSymbol.build_fqn_to_symbol_map(file_descriptors)
        return [
            ProtoFile.from_file_descriptor_proto(descriptor, fqn_map)
            for descriptor in file_descriptors
            if descriptor.name in files_to_generate
        ]

    @staticmethod
    def _add_class(
        class_descriptor: DescriptorProto,
        fqn_map: Dict[str, ProtoCythonSymbol],
        classes: List[Class],
        enums: List[ProtoEnum],
        imports: Set[CImport],
        path: str = "",
    ) -> None:
        embedded_path = (
            path + "_" + class_descriptor.name if path else class_descriptor.name
        ) + "_"
        for nested_class in class_descriptor.nested_type:
            ProtoFile._add_class(nested_class, fqn_map, classes, enums, imports, embedded_path)
        enums.extend(
            ProtoEnum.from_enum_descriptor(nested_enum, embedded_path)
            for nested_enum in class_descriptor.enum_type
        )
        classes.append(Class.from_descriptor(class_descriptor, fqn_map, imports, path))
