from __future__ import annotations

import os
import re
from enum import auto
from enum import Enum
from itertools import chain
from typing import Any
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
    FieldDescriptorProto.TYPE_FIXED32,
    FieldDescriptorProto.TYPE_FIXED64,
}


def proto_filename_to_base(proto_filename):
    return re.sub(r"\.proto$", "", proto_filename)


class ProtoCythonSymbol(NamedTuple):
    file_descriptor: FileDescriptorProto
    name: str
    is_map_entry: bool
    descriptor: Optional[DescriptorProto] = None

    @staticmethod
    def build_fqn_to_symbol_map(
        file_descriptors: Iterable[FileDescriptorProto]
    ) -> Dict[str, ProtoCythonSymbol]:
        fqn_to_symbol: Dict[str, ProtoCythonSymbol] = {}

        def _add_symbols(
            symbols: Iterable[str],
            prefix: Iterable[str],
            file_descriptor: FileDescriptorProto,
            descriptor: DescriptorProto = None,
        ) -> None:
            fqn_prefix = ".".join(chain(["." + file_descriptor.package or "."], prefix))
            for symbol in symbols:
                fqn = f"{fqn_prefix}.{symbol}"
                symbol = "_".join(chain(prefix, [symbol]))
                fqn_to_symbol[fqn] = ProtoCythonSymbol(
                    file_descriptor,
                    symbol,
                    descriptor is not None and descriptor.options.map_entry,
                    descriptor,
                )

        def _add_messages(
            messages: Iterable[DescriptorProto],
            prefix: List[str],
            file_descriptor: FileDescriptorProto,
        ) -> None:
            for message in messages:
                _add_symbols([message.name], prefix, file_descriptor, message)
                sub_prefix = prefix + [message.name]
                _add_messages(message.nested_type, sub_prefix, file_descriptor)
                _add_symbols(
                    (enum.name for enum in message.enum_type), sub_prefix, file_descriptor, None
                )

        for fd in file_descriptors:
            _add_messages(fd.message_type, [], fd)
            _add_symbols((enum.name for enum in fd.enum_type), [], fd)
        return fqn_to_symbol


class Module(NamedTuple):
    module_basename: str
    package: str = ""
    proto_module: bool = False
    output_prefix: str = ""

    @property
    def prefix(self):
        prefix = f"{self.package}." if self.package else ""
        return f"{self.output_prefix}{prefix}"

    @property
    def cython_module(self):
        if self.proto_module:
            return f"{self.prefix}_{self.module_basename}__cy_pb2"
        return f"{self.prefix}{self.module_basename}"

    @property
    def python_module(self):
        return f"{self.prefix}{self.module_basename}_pb2"

    @property
    def externs_module(self):
        if self.proto_module:
            return f"{self.cython_module}_externs"
        return self.cython_module

    @staticmethod
    def from_package_and_file(package: str, filename: str, output_prefix: str) -> Module:
        module_basename = (
            proto_filename_to_base(os.path.basename(filename)).replace("-", "_").replace(".", "/")
        )
        result = Module(
            package=package,
            module_basename=module_basename,
            proto_module=True,
            output_prefix=output_prefix,
        )
        return result


class CImport(NamedTuple):
    module: Module
    symbol: str


class Name(NamedTuple):
    prefix: str
    name: str

    def __str__(self):
        return f"{self.prefix}{self.name}"


class ProtoEnum(NamedTuple):
    name: Name
    value_names: List[str]
    exported: bool

    @staticmethod
    def from_enum_descriptor(enum_type: EnumDescriptorProto, prefix: str = "") -> ProtoEnum:
        return ProtoEnum(
            name=Name(prefix, enum_type.name),
            value_names=[value.name for value in enum_type.value],
            exported=not prefix,
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
    is_reference: bool
    settable: bool
    cpp_type: str
    cython_type: str
    python_type: str
    encode_suffix: str = ""
    decode_suffix: str = ""
    is_map: bool = False
    key_field: Optional[Any] = None
    value_field: Optional[Any] = None

    @property
    def const_reference(self):
        if self.is_reference:
            return f"const {self.cpp_type}&"
        return self.cpp_type

    @staticmethod
    def _create_string_or_bytes(
        name: str,
        python_type: str,
        repeated: bool = False,
        encode_suffix: str = "",
        decode_suffix: str = "",
    ) -> Field:
        return Field(
            name=name,
            field_type=FieldType.scalar,
            repeated=repeated,
            is_reference=True,
            settable=True,
            cpp_type="string",
            cython_type=python_type,
            python_type=python_type,
            encode_suffix=encode_suffix,
            decode_suffix=decode_suffix,
        )

    @staticmethod
    def _create_scalar(name: str, python_type: str, cython_type: str, repeated: bool) -> Field:
        return Field(
            name=name,
            field_type=FieldType.scalar,
            repeated=repeated,
            is_reference=False,
            settable=True,
            cpp_type=cython_type,
            cython_type=cython_type,
            python_type=python_type,
        )

    @staticmethod
    def create_string(name: str, repeated: bool = False) -> Field:
        return Field._create_string_or_bytes(
            name,
            "str",
            repeated,
            encode_suffix=".encode('utf-8')",
            decode_suffix=".decode('utf-8')",
        )

    @staticmethod
    def create_bytes(name: str, repeated: bool = False) -> Field:
        return Field._create_string_or_bytes(name, "bytes", repeated)

    @staticmethod
    def create_float(name: str, repeated: bool = False) -> Field:
        return Field._create_scalar(name, "float", "float", repeated)

    @staticmethod
    def create_double(name: str, repeated: bool = False) -> Field:
        return Field._create_scalar(name, "float", "double", repeated)

    @staticmethod
    def create_int(name: str, unsigned: bool = False, repeated: bool = False) -> Field:
        prefix = "unsigned " if unsigned else ""
        return Field._create_scalar(name, "int", f"{prefix}int", repeated)

    @staticmethod
    def create_bool(name: str, repeated: bool = False) -> Field:
        return Field._create_scalar(name, "bool", "bint", repeated)

    @staticmethod
    def create_long(name: str, unsigned: bool = False, repeated: bool = False) -> Field:
        prefix = "unsigned " if unsigned else ""
        return Field._create_scalar(name, "int", f"{prefix}long long", repeated)

    @staticmethod
    def create_enum(name: str, enum_type: str, repeated: bool = False) -> Field:
        return Field(
            name=name,
            field_type=FieldType.scalar,
            repeated=repeated,
            is_reference=False,
            settable=True,
            cython_type=enum_type,
            cpp_type=enum_type,
            python_type=enum_type,
        )

    @staticmethod
    def create_message(name: str, message_name: str, repeated: bool = False) -> Field:
        return Field(
            name=name,
            field_type=FieldType.message,
            repeated=repeated,
            is_reference=True,
            settable=False,
            cpp_type=message_name,
            cython_type=f"Cpp{message_name}",
            python_type=message_name,
        )

    @staticmethod
    def create_map(name: str, key_field: Field, value_field: Field) -> Field:
        cython_type = value_field.cpp_type
        if value_field.field_type == FieldType.message:
            cython_type = value_field.cython_type
        return Field(
            name=name,
            field_type=FieldType.message,
            repeated=False,
            is_reference=True,
            settable=False,
            cython_type=f"Map[{key_field.cpp_type}, {cython_type}]",
            python_type=f"Dict[{key_field.python_type}, {value_field.python_type}]",
            cpp_type=f"Map[{key_field.cpp_type}, {value_field.cpp_type}]",
            is_map=True,
            key_field=key_field,
            value_field=value_field,
        )

    @staticmethod
    def from_field_descriptor(
        field_descriptor: FieldDescriptorProto,
        fqn_map: Dict[str, ProtoCythonSymbol],
        imports: Set[CImport],
        output_prefix: str,
    ) -> Optional[Field]:
        repeated = field_descriptor.label == FieldDescriptorProto.LABEL_REPEATED
        field_type = field_descriptor.type
        if repeated and field_type == FieldDescriptorProto.TYPE_MESSAGE:
            # special case for maps.  The C++ API doesn't treating maps as repeated key values.
            message_type = fqn_map[field_descriptor.type_name]
            if message_type.is_map_entry:
                imports.add(
                    CImport(Module(package="cytobuf.protobuf", module_basename="common"), "Map")
                )
                imports.add(
                    CImport(Module(package="cython", module_basename="operator"), "dereference")
                )
                imports.add(
                    CImport(Module(package="cython", module_basename="operator"), "postincrement")
                )
                key_field = Field.get_field_by_name(
                    "key", fqn_map, imports, message_type, output_prefix
                )
                value_field = Field.get_field_by_name(
                    "value", fqn_map, imports, message_type, output_prefix
                )
                return Field.create_map(field_descriptor.name, key_field, value_field)
        if field_type in INT_TYPES:
            return Field.create_int(field_descriptor.name, field_type in UNSIGNED_TYPES, repeated)
        elif field_type in LONG_TYPES:
            return Field.create_long(field_descriptor.name, field_type in UNSIGNED_TYPES, repeated)
        elif field_type == FieldDescriptorProto.TYPE_STRING:
            return Field.create_string(field_descriptor.name, repeated)
        elif field_type == FieldDescriptorProto.TYPE_BYTES:
            return Field.create_bytes(field_descriptor.name, repeated)
        elif field_type == FieldDescriptorProto.TYPE_FLOAT:
            return Field.create_float(field_descriptor.name, repeated)
        elif field_type == FieldDescriptorProto.TYPE_DOUBLE:
            return Field.create_double(field_descriptor.name, repeated)
        elif field_type == FieldDescriptorProto.TYPE_BOOL:
            return Field.create_bool(field_descriptor.name, repeated)
        elif field_type == FieldDescriptorProto.TYPE_ENUM:
            symbol = Field.add_import(field_descriptor, fqn_map, imports, output_prefix)
            return Field.create_enum(field_descriptor.name, symbol.name, repeated)
        elif field_type == FieldDescriptorProto.TYPE_MESSAGE:
            symbol = Field.add_import(field_descriptor, fqn_map, imports, output_prefix)
            return Field.create_message(field_descriptor.name, symbol.name, repeated)
        return None

    @staticmethod
    def get_field_by_name(name: str, fqn_map, imports, message_type, output_prefix):
        key_field_descriptor = next(
            field for field in message_type.descriptor.field if field.name == name
        )
        key_field = Field.from_field_descriptor(
            key_field_descriptor, fqn_map, imports, output_prefix
        )
        return key_field

    @staticmethod
    def add_import(
        field_descriptor: FieldDescriptorProto,
        fqn_map: Dict[str, ProtoCythonSymbol],
        imports: Set[CImport],
        output_prefix: str,
    ) -> ProtoCythonSymbol:
        type_name: str = field_descriptor.type_name
        symbol = fqn_map[type_name]
        dependency_fd = symbol.file_descriptor
        if dependency_fd.package:
            module = Module.from_package_and_file(
                dependency_fd.package, dependency_fd.name, output_prefix=output_prefix
            )
            imports.add(CImport(module, symbol.name))
        return symbol


class Class(NamedTuple):
    name: Name
    fields: List[Field]
    exported: bool
    nested_names: List[Name]

    @staticmethod
    def from_descriptor(
        descriptor: DescriptorProto,
        fqn_map: Dict[str, ProtoCythonSymbol],
        imports: Set[CImport],
        nested_names: List[Name],
        prefix: str,
        output_prefix: str,
    ) -> Class:
        return Class(
            name=Name(prefix, descriptor.name),
            fields=[
                cython_field
                for cython_field in (
                    Field.from_field_descriptor(field, fqn_map, imports, output_prefix)
                    for field in descriptor.field
                )
                if cython_field is not None
            ],
            nested_names=nested_names,
            exported=not prefix,
        )


class ProtoFile(NamedTuple):
    imports: Iterable[CImport]
    namespace: List[str]
    enums: List[ProtoEnum]
    classes: List[Class]
    proto_filename: str
    proto_package: str
    output_prefix: str

    @property
    def extern_pxd_filename(self) -> str:
        return f"{self.module.externs_module.replace('.', '/')}.pxd"

    @property
    def pxd_filename(self) -> str:
        return f"{self.module.cython_module.replace('.', '/')}.pxd"

    @property
    def pyx_filename(self) -> str:
        return f"{self.module.cython_module.replace('.', '/')}.pyx"

    @property
    def py_filename(self) -> str:
        return f"{self.module.python_module.replace('.', '/')}.py"

    @property
    def module(self) -> Module:
        return Module.from_package_and_file(
            self.proto_package, self.proto_filename, self.output_prefix
        )

    @property
    def cpp_header(self):
        return proto_filename_to_base(self.proto_filename) + ".pb.h"

    @property
    def cpp_source(self):
        return proto_filename_to_base(self.proto_filename) + ".pb.cc"

    @staticmethod
    def from_file_descriptor_proto(
        file_descriptor: FileDescriptorProto,
        fqn_map: Dict[str, ProtoCythonSymbol],
        output_prefix: str,
    ) -> ProtoFile:
        namespace = file_descriptor.package.split(".")
        classes: List[Class] = []
        imports = {CImport(Module(package="libcpp", module_basename="string"), "string")}
        enums = [
            ProtoEnum.from_enum_descriptor(enum_type) for enum_type in file_descriptor.enum_type
        ]
        for descriptor in file_descriptor.message_type:
            ProtoFile._add_class(descriptor, fqn_map, classes, enums, imports, "", output_prefix)
        current_module = Module.from_package_and_file(
            file_descriptor.package, file_descriptor.name, output_prefix=output_prefix
        )
        filtered_imports = sorted(imp for imp in imports if imp.module != current_module)
        return ProtoFile(
            imports=filtered_imports,
            namespace=namespace,
            enums=enums,
            classes=classes,
            proto_filename=file_descriptor.name,
            proto_package=file_descriptor.package,
            output_prefix=output_prefix,
        )

    @staticmethod
    def from_file_descriptor_protos(
        file_descriptors: Iterable[FileDescriptorProto],
        files_to_generate: Set[str],
        output_prefix: str,
    ) -> List[ProtoFile]:
        fqn_map = ProtoCythonSymbol.build_fqn_to_symbol_map(file_descriptors)
        return [
            ProtoFile.from_file_descriptor_proto(descriptor, fqn_map, output_prefix)
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
        path: str,
        output_prefix: str,
    ) -> Class:
        nested_names: List[Name] = []
        embedded_path = (
            path + "_" + class_descriptor.name if path else class_descriptor.name
        ) + "_"
        for nested_class in class_descriptor.nested_type:
            if nested_class.options.map_entry:
                continue
            new_class = ProtoFile._add_class(
                nested_class, fqn_map, classes, enums, imports, embedded_path, output_prefix
            )
            nested_names.append(new_class.name)
        nested_enums = [
            ProtoEnum.from_enum_descriptor(nested_enum, embedded_path)
            for nested_enum in class_descriptor.enum_type
        ]
        enums.extend(nested_enums)
        nested_names.extend(enum.name for enum in nested_enums)
        new_class = Class.from_descriptor(
            class_descriptor, fqn_map, imports, nested_names, path, output_prefix
        )
        classes.append(new_class)
        return new_class
