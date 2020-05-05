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
from cytobuf.protoc_gen_cython.constants import INT_TYPES
from cytobuf.protoc_gen_cython.constants import LONG_TYPES
from cytobuf.protoc_gen_cython.constants import UNSIGNED_TYPES


def proto_filename_to_base(proto_filename):
    return re.sub(r"\.proto$", "", proto_filename)


class Module(NamedTuple):
    module_basename: str
    package: str = ""
    proto_filename: str = ""
    output_prefix: str = ""
    pure_python_module: bool = False

    @property
    def prefix(self) -> str:
        prefix = f"{self.package}." if self.package else ""
        return f"{self.output_prefix}{prefix}"

    @property
    def cython_module(self) -> str:
        if self.proto_filename:
            return f"{self.prefix}_{self.module_basename}__cy_pb2"
        return f"{self.prefix}{self.module_basename}"

    @property
    def python_module(self) -> str:
        return f"{self.prefix}{self.module_basename}_pb2"

    @property
    def pxd_filename(self) -> str:
        return f"{self.cython_module.replace('.', '/')}.pxd"

    @property
    def pyx_filename(self) -> str:
        return f"{self.cython_module.replace('.', '/')}.pyx"

    @property
    def py_filename(self) -> str:
        return f"{self.python_module.replace('.', '/')}.py"

    @property
    def enum_module(self) -> Module:
        return self.generate_enum_module(self.package, self.proto_filename, self.output_prefix)

    @staticmethod
    def generate_enum_module(package: str, filename: str, prefix: str = "") -> Module:
        return Module.from_package_and_file(f"{package}._enums", filename, prefix, True)

    @staticmethod
    def from_package_and_file(
        package: str, filename: str, output_prefix: str, pure_python_module: bool = False
    ) -> Module:
        module_basename = (
            proto_filename_to_base(os.path.basename(filename)).replace("-", "_").replace(".", "/")
        )
        result = Module(
            package=package,
            module_basename=module_basename,
            proto_filename=filename,
            output_prefix=output_prefix,
            pure_python_module=pure_python_module,
        )
        return result


class ImportType(Enum):
    cython = "cimport"
    python = "import"


class Import(NamedTuple):
    module: Module
    import_type: ImportType
    symbol: Optional[Name] = None
    alias: Optional[str] = None
    internal_proto_module: Optional[Module] = None

    @property
    def python_import(self) -> str:
        if not self.symbol:
            result = f"import {self.module.python_module}"
        else:
            result = f"from {self.module.python_module} import {self.symbol}"
        if self.alias:
            result += f" as {self.alias}"
        return result

    @property
    def cython_import(self) -> str:
        if self.module.pure_python_module:
            return self.python_import
        if not self.symbol:
            result = f"{self.import_type.value} {self.module.cython_module}"
        else:
            result = f"from {self.module.cython_module} {self.import_type.value} {self.symbol}"
        if self.alias:
            result += f" as {self.alias}"
        return result

    @property
    def proto_module(self) -> Module:
        return self.internal_proto_module or self.module


class ProtoCythonSymbol(NamedTuple):
    """Represents a symbol that can be referenced by cython code.
    """

    package: str
    filename: str
    name: Name
    is_map_entry: bool
    module: Module
    imports: List[Import]
    descriptor: Optional[DescriptorProto] = None

    @staticmethod
    def build_fqn_to_symbol_map(
        file_descriptors: Iterable[FileDescriptorProto], output_prefix: str
    ) -> Dict[str, ProtoCythonSymbol]:
        """Given a set of FileDescriptorProts, builds a map of fully qualified names
        to ProtoCythonSymbol.
        """
        fqn_to_symbol: Dict[str, ProtoCythonSymbol] = {}

        def _add_symbols(
            symbols: Iterable[str],
            prefix: Iterable[str],
            package: str,
            filename: str,
            are_enums: bool,
            descriptor: DescriptorProto = None,
        ) -> None:
            fqn_prefix = ".".join(chain(["." + package or "."], prefix))
            module = Module.from_package_and_file(package, filename, output_prefix=output_prefix)
            symbol_prefix = package.replace(".", "_")
            for symbol in symbols:
                fqn = f"{fqn_prefix}.{symbol}"
                module_symbol = Name("_".join(prefix), symbol)
                cython_module = module
                symbol_name = Name(symbol_prefix, module_symbol)
                cpp_import = Import(
                    cython_module,
                    ImportType.cython,
                    symbol_name.unwrap(),
                    alias=f"_cpp_{symbol_name}",
                    internal_proto_module=module,
                )
                imports = [cpp_import]
                if are_enums:
                    # Due to the way C++ enums are implemented, enum definitions live in
                    # a python file as opposed to using the C++ enum.  The main limitation here
                    # is enums pollute the local namespace, so there's no way to have 2 distinct
                    # enums in the same file that have the same value name, e.g.:
                    #
                    # enum Foo {
                    #     DEFAULT = 0;
                    #     THING = 1;
                    # }
                    # enum Bar {
                    #     DEFAULT = 0;
                    #     OTHER = 1;
                    # }
                    #
                    # The C++ API would emit enum values prefixed with the enum name, e.g.
                    # Bar_DEFAULT and Foo_DEFAULT.  The Python protobuf library doesn't do
                    # such prefixing.  Since cpp types in Cython are subject to the same name
                    # scoping rules as C++ we have to emit a Python object here.
                    imports.append(
                        Import(
                            cython_module.enum_module,
                            ImportType.python,
                            symbol_name,
                            alias=f"_py_{symbol_name}",
                            internal_proto_module=module,
                        )
                    )
                else:
                    imports.append(
                        Import(
                            cython_module,
                            ImportType.cython,
                            symbol_name,
                            internal_proto_module=module,
                        )
                    )
                fqn_to_symbol[fqn] = ProtoCythonSymbol(
                    package,
                    filename,
                    symbol_name,
                    descriptor is not None and descriptor.options.map_entry,
                    module,
                    imports,
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
                    are_enums=False,
                    descriptor=message,
                )
                sub_prefix = prefix + [message.name]
                _add_messages(message.nested_type, sub_prefix, file_descriptor)
                _add_symbols(
                    (enum.name for enum in message.enum_type),
                    sub_prefix,
                    file_descriptor.package,
                    file_descriptor.name,
                    are_enums=True,
                    descriptor=None,
                )

        for fd in file_descriptors:
            _add_messages(fd.message_type, [], fd)
            _add_symbols(
                (enum.name for enum in fd.enum_type), [], fd.package, fd.name, are_enums=True
            )
        return fqn_to_symbol


class Name(NamedTuple):
    prefix: str
    name: Any  # Should be Union[Name, str] but recursive types break mypy

    def unwrap(self) -> Name:
        if isinstance(self.name, Name):
            return self.name
        else:
            return Name("", self.name)

    @property
    def fully_unwrapped(self):
        if isinstance(self.name, Name):
            return self.name.fully_unwrapped
        else:
            return self.name

    def __str__(self):
        return f"{(self.prefix + '_') if self.prefix else ''}{self.name}"


class ProtoEnumValue(NamedTuple):
    name: Name
    number: int


class ProtoEnum(NamedTuple):
    name: Name
    value_names: List[ProtoEnumValue]
    exported: bool

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
            value_names=[
                ProtoEnumValue(Name(value_prefix, value.name), value.number)
                for value in enum_type.value
            ],
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
    decode_function: str = ""
    is_map: bool = False
    key_field: Optional[Any] = None
    value_field: Optional[Any] = None
    type_symbol: Optional[ProtoCythonSymbol] = None

    def const_reference(self, module: Module) -> str:
        if self.is_reference:
            return f"const {self.local_cpp_type(module)}&"
        return self.local_cpp_type(module)

    def local_cpp_type(self, module: Module) -> str:
        """Given a module, returns the name of this field's type within that module.

        If we're referring to a type that's defined with the same module this field
        is defined within, we strip any prefixes from the original cpp type since we
        can't alias types locally.
        """
        if self.is_map and self.key_field and self.value_field:
            return (
                f"Map[{self.key_field.local_cpp_type(module)}, "
                f"{self.value_field.local_cpp_type(module)}]"
            )
        if self.type_symbol and module == self.type_symbol.module:
            return self.type_symbol.name.name
        return self.cpp_type

    def local_cython_type(self, module: Module) -> str:
        if self.type_symbol and module == self.type_symbol.module:
            return self.type_symbol.name.name
        return self.cython_type

    @property
    def cpp_name(self):
        if self.name in CPP_KEYWORDS:
            # protobuf will prefix fields with an underscore if they collide with a C++ keyword.
            return f"{self.name.lower()}_"
        return self.name.lower()

    @staticmethod
    def _create_string_or_bytes(
        name: str,
        python_type: str,
        repeated: bool = False,
        encode_suffix: str = "",
        decode_function: str = "",
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
            decode_function=decode_function,
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
            name, "str", repeated, encode_suffix=".encode()", decode_function="bytes.decode"
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
            cython_type=f"_cpp_{str(enum_type_symbol.name)}",
            cpp_type=f"_cpp_{str(enum_type_symbol.name)}",
            python_type=str(enum_type_symbol.name),
            type_symbol=enum_type_symbol,
            decode_function=f"_py_{enum_type_symbol.name}",
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
            cpp_type=f"_cpp_{str(message_type_symbol.name)}",
            cython_type=str(message_type_symbol.name),
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
        imports: Set[Import],
        output_prefix: str,
    ) -> Optional[Field]:
        repeated = field_descriptor.label == FieldDescriptorProto.LABEL_REPEATED
        field_type = field_descriptor.type
        field_name = field_descriptor.name
        if repeated and field_type == FieldDescriptorProto.TYPE_MESSAGE:
            # special case for maps.  The C++ API doesn't treating maps as repeated key values.
            message_type = fqn_map[field_descriptor.type_name]
            if message_type.is_map_entry:
                return Field.build_map(field_name, fqn_map, message_type, output_prefix, imports)
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
    def build_map(field_name, fqn_map, message_type, output_prefix, imports):
        imports.add(
            Import(
                Module(package="cytobuf.protobuf", module_basename="common"),
                ImportType.cython,
                Name("", "Map"),
            )
        )
        imports.add(
            Import(
                Module(package="cython", module_basename="operator"),
                ImportType.cython,
                Name("", "dereference"),
            )
        )
        imports.add(
            Import(
                Module(package="cython", module_basename="operator"),
                ImportType.cython,
                Name("", "postincrement"),
            )
        )
        key_field = Field.get_field_by_name("key", fqn_map, imports, message_type, output_prefix)
        value_field = Field.get_field_by_name(
            "value", fqn_map, imports, message_type, output_prefix
        )
        return Field.create_map(field_name, key_field, value_field)

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
        imports: Set[Import],
    ) -> ProtoCythonSymbol:
        type_name: str = field_descriptor.type_name
        symbol = fqn_map[type_name]
        if symbol.package:
            imports.update(symbol.imports)
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
        imports: Set[Import],
        nested_names: List[Name],
        prefix: List[str],
        output_prefix: str,
    ) -> Class:
        prefix = prefix or []
        fqn = "." + ".".join(chain([package], prefix, [descriptor.name]))
        symbol = fqn_map[fqn]
        invalid_field_names = Class._invalid_field_names(descriptor)

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

    @staticmethod
    def _invalid_field_names(descriptor):
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
        return invalid_field_names


class ProtoFile(NamedTuple):
    imports: Iterable[Import]
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

    @staticmethod
    def from_file_descriptor_proto(
        file_descriptor: FileDescriptorProto,
        fqn_map: Dict[str, ProtoCythonSymbol],
        filename_to_package_map: Dict[str, str],
        output_prefix: str,
    ) -> ProtoFile:
        namespace = file_descriptor.package.split(".")
        classes: List[Class] = []
        imports = {
            Import(
                Module(package="libcpp", module_basename="string"),
                ImportType.cython,
                Name("", "string"),
            )
        }
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
        dependent_modules = {
            Module.from_package_and_file(filename_to_package_map[dep], dep, output_prefix)
            for dep in file_descriptor.dependency
        } - {imp.module for imp in imports}
        current_module = Module.from_package_and_file(
            file_descriptor.package, file_descriptor.name, output_prefix=output_prefix
        )
        filtered_imports = sorted(imp for imp in imports if imp.module != current_module)
        dependent_imports = [
            Import(module, ImportType.cython) for module in sorted(dependent_modules)
        ]
        return ProtoFile(
            imports=dependent_imports + filtered_imports,
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
        package_map = {x.name: x.package for x in file_descriptors}
        proto_files = [
            ProtoFile.from_file_descriptor_proto(descriptor, fqn_map, package_map, output_prefix)
            for descriptor in file_descriptors
        ]
        module_to_proto = {proto_file.module: proto_file for proto_file in proto_files}
        filename_to_proto = {proto_file.proto_filename: proto_file for proto_file in proto_files}
        result: Set[Module] = set()
        remaining = list(files_to_generate)
        while remaining:
            next_proto_filename = remaining.pop()
            next_protofile = filename_to_proto.get(next_proto_filename)
            if not next_protofile:
                raise ValueError(f"Unsatisfied dependency: {next_proto_filename}")
            if next_protofile.module in result:
                continue
            # Find all files we haven't yet added but will need to compile.
            missing_deps = [
                module_to_proto[dep.proto_module].proto_filename
                for dep in next_protofile.imports
                if dep.module.proto_filename
                and not dep.module.pure_python_module
                and dep.module not in result
            ]
            if not missing_deps:
                result.add(next_protofile.module)
            else:
                remaining.append(next_protofile.proto_filename)
                remaining.extend(missing_deps)
        return [module_to_proto[module] for module in result]

    @staticmethod
    def _add_class(
        package: str,
        class_descriptor: DescriptorProto,
        fqn_map: Dict[str, ProtoCythonSymbol],
        classes: List[Class],
        enums: List[ProtoEnum],
        imports: Set[Import],
        path: List[str],
        output_prefix: str,
    ) -> Class:
        nested_names: List[Name] = []
        embedded_path = path + [class_descriptor.name]
        for nested_class in class_descriptor.nested_type:
            if nested_class.options.map_entry or nested_class.name in keyword.kwlist:
                # The C++ protobuf library doesn't allow using the repeated KV
                # message for a map.  We generate a wrapper instead.
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
