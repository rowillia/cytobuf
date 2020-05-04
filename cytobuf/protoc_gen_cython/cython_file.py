from __future__ import annotations

import keyword
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

from cytobuf.protoc_gen_cython.constants import CPP_KEYWORDS

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


class Module(NamedTuple):
    module_basename: str
    package: str = ""
    proto_module: bool = False
    is_enum_module: bool = False
    output_prefix: str = ""

    @property
    def prefix(self) -> str:
        prefix = f"{self.package}." if self.package else ""
        return f"{self.output_prefix}{prefix}"

    @property
    def cython_module(self) -> str:
        if self.proto_module:
            return f"{self.prefix}_{self.module_basename}__cy_pb2"
        return f"{self.prefix}{self.module_basename}"

    @property
    def python_module(self) -> str:
        if self.is_enum_module:
            return self.cython_module
        return f"{self.prefix}{self.module_basename}_pb2"

    @property
    def externs_module(self) -> str:
        if self.proto_module:
            return f"{self.cython_module}_externs"
        return self.cython_module

    @property
    def extern_pxd_filename(self) -> str:
        return f"{self.externs_module.replace('.', '/')}.pxd"

    @property
    def pxd_filename(self) -> str:
        return f"{self.cython_module.replace('.', '/')}.pxd"

    @property
    def pyx_filename(self) -> str:
        return f"{self.cython_module.replace('.', '/')}.pyx"

    @property
    def py_filename(self) -> str:
        return f"{self.python_module.replace('.', '/')}.py"

    @staticmethod
    def from_package_and_file(
        package: str, filename: str, output_prefix: str, is_enum_module: bool = False
    ) -> Module:
        module_basename = (
            proto_filename_to_base(os.path.basename(filename)).replace("-", "_").replace(".", "/")
        )
        result = Module(
            package=package,
            module_basename=module_basename,
            proto_module=True,
            output_prefix=output_prefix,
            is_enum_module=is_enum_module,
        )
        return result


class CImport(NamedTuple):
    module: Module
    symbol: Name
    internal_cpp_module: Optional[Module] = None

    @property
    def cpp_module(self) -> Module:
        return self.internal_cpp_module or self.module


class ProtoCythonSymbol(NamedTuple):
    package: str
    filename: str
    name: Name
    is_map_entry: bool
    c_import: CImport
    descriptor: Optional[DescriptorProto] = None

    @staticmethod
    def build_fqn_to_symbol_map(
        file_descriptors: Iterable[FileDescriptorProto], output_prefix: str
    ) -> Dict[str, ProtoCythonSymbol]:
        fqn_to_symbol: Dict[str, ProtoCythonSymbol] = {}

        def _add_symbols(
            symbols: Iterable[str],
            prefix: Iterable[str],
            package: str,
            filename: str,
            is_enum: bool,
            descriptor: DescriptorProto = None,
        ) -> None:
            fqn_prefix = ".".join(chain(["." + package or "."], prefix))
            module = Module.from_package_and_file(package, filename, output_prefix=output_prefix)
            symbol_prefix = package.replace(".", "_")
            for symbol in symbols:
                fqn = f"{fqn_prefix}.{symbol}"
                module_symbol = Name("_".join(prefix), symbol)
                cython_module = module
                if is_enum:
                    enum_package = ProtoFile.generate_enum_module_prefix(
                        package, filename, ""
                    ) + str(module_symbol)
                    split_enum_package = enum_package.rsplit(".", 1)
                    cython_module = Module.from_package_and_file(
                        split_enum_package[0], split_enum_package[1], output_prefix, True
                    )
                symbol_name = Name(symbol_prefix, module_symbol)
                c_import = CImport(cython_module, symbol_name, module)
                fqn_to_symbol[fqn] = ProtoCythonSymbol(
                    package,
                    filename,
                    symbol_name,
                    descriptor is not None and descriptor.options.map_entry,
                    c_import,
                    descriptor,
                )

        def _add_messages(
            messages: Iterable[DescriptorProto],
            prefix: List[str],
            file_descriptor: FileDescriptorProto,
        ) -> None:
            for message in messages:
                _add_symbols(
                    [message.name],
                    prefix,
                    file_descriptor.package,
                    file_descriptor.name,
                    False,
                    message,
                )
                sub_prefix = prefix + [message.name]
                _add_messages(message.nested_type, sub_prefix, file_descriptor)
                _add_symbols(
                    (enum.name for enum in message.enum_type),
                    sub_prefix,
                    file_descriptor.package,
                    file_descriptor.name,
                    True,
                    None,
                )

        for fd in file_descriptors:
            _add_messages(fd.message_type, [], fd)
            _add_symbols((enum.name for enum in fd.enum_type), [], fd.package, fd.name, True)
        return fqn_to_symbol


class Name(NamedTuple):
    prefix: str
    name: Any

    @property
    def raw_name(self):
        if isinstance(self.name, Name):
            return self.name.raw_name
        else:
            return self.name

    def __str__(self):
        return f"{(self.prefix + '_') if self.prefix else ''}{self.name}"


class ProtoEnum(NamedTuple):
    name: Name
    value_names: List[Name]
    exported: bool
    module: Module

    @staticmethod
    def from_enum_descriptor(
        enum_type: EnumDescriptorProto,
        package: str,
        fqn_map: Dict[str, ProtoCythonSymbol],
        prefix: Optional[List[str]] = None,
    ) -> ProtoEnum:
        prefix = prefix or []
        fqn = "." + ".".join(chain([package], prefix, [enum_type.name]))
        symbol = fqn_map[fqn]
        value_prefix = ""
        if prefix:
            value_prefix = "_".join(chain(prefix, [enum_type.name]))
        return ProtoEnum(
            name=symbol.name,
            value_names=[Name(value_prefix, value.name) for value in enum_type.value],
            exported=not prefix,
            module=symbol.c_import.module,
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
    type_symbol: Optional[ProtoCythonSymbol] = None

    def const_reference(self, module: Module) -> str:
        if self.is_reference:
            return f"const {self.local_cpp_type(module)}&"
        return self.local_cpp_type(module)

    def local_cpp_type(self, module: Module) -> str:
        if self.is_map and self.key_field and self.value_field:
            return (
                f"Map[{self.key_field.local_cpp_type(module)}, "
                f"{self.value_field.local_cpp_type(module)}]"
            )
        if self.type_symbol and module == self.type_symbol.c_import.cpp_module:
            return self.type_symbol.name.name
        return self.cpp_type

    @property
    def cpp_name(self):
        if self.name in CPP_KEYWORDS:
            return f"{self.name}_"
        return self.name

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
    def create_enum(
        name: str, enum_type_symbol: ProtoCythonSymbol, repeated: bool = False
    ) -> Field:
        return Field(
            name=name,
            field_type=FieldType.scalar,
            repeated=repeated,
            is_reference=False,
            settable=True,
            cython_type=str(enum_type_symbol.name),
            cpp_type=str(enum_type_symbol.name),
            python_type=str(enum_type_symbol.name),
            type_symbol=enum_type_symbol,
        )

    @staticmethod
    def create_message(
        name: str, message_type_symbol: ProtoCythonSymbol, repeated: bool = False
    ) -> Field:
        return Field(
            name=name,
            field_type=FieldType.message,
            repeated=repeated,
            is_reference=True,
            settable=False,
            cpp_type=str(message_type_symbol.name),
            cython_type=f"_Cpp_{str(message_type_symbol.name)}",
            python_type=str(message_type_symbol.name),
            type_symbol=message_type_symbol,
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
        field_name = field_descriptor.name
        if repeated and field_type == FieldDescriptorProto.TYPE_MESSAGE:
            # special case for maps.  The C++ API doesn't treating maps as repeated key values.
            message_type = fqn_map[field_descriptor.type_name]
            if message_type.is_map_entry:
                imports.add(
                    CImport(
                        Module(package="cytobuf.protobuf", module_basename="common"),
                        Name("", "Map"),
                    )
                )
                imports.add(
                    CImport(
                        Module(package="cython", module_basename="operator"),
                        Name("", "dereference"),
                    )
                )
                imports.add(
                    CImport(
                        Module(package="cython", module_basename="operator"),
                        Name("", "postincrement"),
                    )
                )
                key_field = Field.get_field_by_name(
                    "key", fqn_map, imports, message_type, output_prefix
                )
                value_field = Field.get_field_by_name(
                    "value", fqn_map, imports, message_type, output_prefix
                )
                return Field.create_map(field_name, key_field, value_field)
        if field_type in INT_TYPES:
            return Field.create_int(field_name, field_type in UNSIGNED_TYPES, repeated)
        elif field_type in LONG_TYPES:
            return Field.create_long(field_name, field_type in UNSIGNED_TYPES, repeated)
        elif field_type == FieldDescriptorProto.TYPE_STRING:
            return Field.create_string(field_name, repeated)
        elif field_type == FieldDescriptorProto.TYPE_BYTES:
            return Field.create_bytes(field_name, repeated)
        elif field_type == FieldDescriptorProto.TYPE_FLOAT:
            return Field.create_float(field_name, repeated)
        elif field_type == FieldDescriptorProto.TYPE_DOUBLE:
            return Field.create_double(field_name, repeated)
        elif field_type == FieldDescriptorProto.TYPE_BOOL:
            return Field.create_bool(field_name, repeated)
        elif field_type == FieldDescriptorProto.TYPE_ENUM:
            symbol = Field.add_import(field_descriptor, fqn_map, imports)
            return Field.create_enum(field_name, symbol, repeated)
        elif field_type == FieldDescriptorProto.TYPE_MESSAGE:
            symbol = Field.add_import(field_descriptor, fqn_map, imports)
            return Field.create_message(field_name, symbol, repeated)
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
    ) -> ProtoCythonSymbol:
        type_name: str = field_descriptor.type_name
        symbol = fqn_map[type_name]
        if symbol.package:
            imports.add(symbol.c_import)
        return symbol


class Class(NamedTuple):
    name: Name
    fields: List[Field]
    exported: bool
    nested_names: List[Name]

    @staticmethod
    def from_descriptor(
        descriptor: DescriptorProto,
        package: str,
        fqn_map: Dict[str, ProtoCythonSymbol],
        imports: Set[CImport],
        nested_names: List[Name],
        prefix: List[str],
        output_prefix: str,
    ) -> Class:
        prefix = prefix or []
        fqn = "." + ".".join(chain([package], prefix, [descriptor.name]))
        symbol = fqn_map[fqn]
        invalid_field_names = set(keyword.kwlist)
        for field in descriptor.field:
            field_name = field.name
            invalid_field_names.add(f"clear_{field_name}")
            invalid_field_names.add(f"set_{field_name}")
            if field.label == FieldDescriptorProto.LABEL_REPEATED:
                invalid_field_names.add(f"{field_name}_size")
                invalid_field_names.add(f"add_{field_name}")
            elif field.type == FieldDescriptorProto.TYPE_MESSAGE:
                invalid_field_names.add(f"has_{field_name}")

        return Class(
            name=symbol.name,
            fields=[
                cython_field
                for cython_field in (
                    Field.from_field_descriptor(field, fqn_map, imports, output_prefix)
                    for field in descriptor.field
                    if field.name not in invalid_field_names
                )
                if cython_field is not None
            ],
            nested_names=nested_names,
            exported=not prefix,
        )


class ProtoFile(NamedTuple):
    imports: Iterable[CImport]
    extern_imports: Iterable[CImport]
    namespace: List[str]
    enums: List[ProtoEnum]
    classes: List[Class]
    proto_filename: str
    proto_package: str
    output_prefix: str

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

    @property
    def enum_module_prefix(self):
        return self.generate_enum_module_prefix(
            self.proto_package, self.proto_filename, self.output_prefix
        )

    @staticmethod
    def generate_enum_module_prefix(package: str, filename: str, prefix: str = "") -> str:
        base_name = proto_filename_to_base(os.path.basename(filename))
        module = Module.from_package_and_file(package, filename, prefix, True)
        return f"{module.prefix}_cy_enums.{base_name}_"

    @staticmethod
    def from_file_descriptor_proto(
        file_descriptor: FileDescriptorProto,
        fqn_map: Dict[str, ProtoCythonSymbol],
        output_prefix: str,
    ) -> ProtoFile:
        namespace = file_descriptor.package.split(".")
        classes: List[Class] = []
        imports = {CImport(Module(package="libcpp", module_basename="string"), Name("", "string"))}
        enums = [
            ProtoEnum.from_enum_descriptor(enum_type, file_descriptor.package, fqn_map)
            for enum_type in file_descriptor.enum_type
            if enum_type.name not in keyword.kwlist
        ]
        for descriptor in file_descriptor.message_type:
            if descriptor.name not in keyword.kwlist:
                ProtoFile._add_class(
                    file_descriptor.package,
                    descriptor,
                    fqn_map,
                    classes,
                    enums,
                    imports,
                    [],
                    output_prefix,
                )
        current_module = Module.from_package_and_file(
            file_descriptor.package, file_descriptor.name, output_prefix=output_prefix
        )
        filtered_imports = sorted(imp for imp in imports if imp.module != current_module)
        extern_imports = [imp for imp in filtered_imports if imp.cpp_module != current_module]
        return ProtoFile(
            imports=filtered_imports,
            extern_imports=extern_imports,
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
        fqn_map = ProtoCythonSymbol.build_fqn_to_symbol_map(file_descriptors, output_prefix)
        proto_files = [
            ProtoFile.from_file_descriptor_proto(descriptor, fqn_map, output_prefix)
            for descriptor in file_descriptors
        ]
        module_to_proto = {proto_file.module: proto_file for proto_file in proto_files}
        for proto_file in proto_files:
            for enum in proto_file.enums:
                module_to_proto[enum.module] = proto_file
        filename_to_proto = {proto_file.proto_filename: proto_file for proto_file in proto_files}
        result: Set[Module] = set()
        remaining = list(files_to_generate)
        while remaining:
            next_protofile: ProtoFile = filename_to_proto[remaining.pop()]
            if next_protofile.module in result:
                continue
            missing_deps = [
                module_to_proto[dep.module].proto_filename
                for dep in next_protofile.extern_imports
                if dep.module.proto_module and dep.module not in result
            ]
            if not missing_deps:
                result.add(next_protofile.module)
                for enum in next_protofile.enums:
                    result.add(enum.module)
            else:
                remaining.append(next_protofile.proto_filename)
                remaining.extend(missing_deps)
        return [module_to_proto[module] for module in result if not module.is_enum_module]

    @staticmethod
    def _add_class(
        package: str,
        class_descriptor: DescriptorProto,
        fqn_map: Dict[str, ProtoCythonSymbol],
        classes: List[Class],
        enums: List[ProtoEnum],
        imports: Set[CImport],
        path: List[str],
        output_prefix: str,
    ) -> Class:
        nested_names: List[Name] = []
        embedded_path = path + [class_descriptor.name]
        for nested_class in class_descriptor.nested_type:
            if nested_class.options.map_entry or nested_class.name in keyword.kwlist:
                continue
            new_class = ProtoFile._add_class(
                package,
                nested_class,
                fqn_map,
                classes,
                enums,
                imports,
                embedded_path,
                output_prefix,
            )
            nested_names.append(new_class.name)
        nested_enums = [
            ProtoEnum.from_enum_descriptor(nested_enum, package, fqn_map, embedded_path)
            for nested_enum in class_descriptor.enum_type
            if nested_enum.name not in keyword.kwlist
        ]
        enums.extend(nested_enums)
        nested_names.extend(enum.name for enum in nested_enums)
        new_class = Class.from_descriptor(
            class_descriptor, package, fqn_map, imports, nested_names, path, output_prefix
        )
        classes.append(new_class)
        return new_class
