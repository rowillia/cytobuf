from google.protobuf.descriptor_pb2 import FieldDescriptorProto

DEFAULT_LIBRARY_DIRECTORY = "/usr/local/lib"
DEFAULT_INCLUDE_DIRECTORY = "/usr/local/include"


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


CPP_KEYWORDS = {
    "NULL",
    "alignas",
    "alignof",
    "and",
    "and_eq",
    "asm",
    "auto",
    "bitand",
    "bitor",
    "bool",
    "break",
    "case",
    "catch",
    "char",
    "class",
    "compl",
    "const",
    "constexpr",
    "const_cast",
    "continue",
    "decltype",
    "default",
    "delete",
    "do",
    "double",
    "dynamic_cast",
    "else",
    "enum",
    "explicit",
    "export",
    "extern",
    "false",
    "float",
    "for",
    "friend",
    "goto",
    "if",
    "inline",
    "int",
    "long",
    "mutable",
    "namespace",
    "new",
    "noexcept",
    "not",
    "not_eq",
    "nullptr",
    "operator",
    "or",
    "or_eq",
    "private",
    "protected",
    "public",
    "register",
    "reinterpret_cast",
    "return",
    "short",
    "signed",
    "sizeof",
    "static",
    "static_assert",
    "static_cast",
    "struct",
    "switch",
    "template",
    "this",
    "thread_local",
    "throw",
    "true",
    "try",
    "typedef",
    "typeid",
    "typename",
    "union",
    "unsigned",
    "using",
    "virtual",
    "void",
    "volatile",
    "wchar_t",
    "while",
    "xor",
    "xor_eq",
}
