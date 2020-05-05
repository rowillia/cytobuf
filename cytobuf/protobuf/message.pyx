# cython: language_level=3
# distutils: language = c++
# distutils: libraries = protobuf
# distutils: include_dirs = /usr/local/include
# distutils: library_dirs = /usr/local/lib
# distutils: extra_compile_args= -std=c++11


from libcpp.string cimport string

from cytobuf.protobuf.common cimport JsonParseOptions
from cytobuf.protobuf.common cimport JsonPrintOptions
from cytobuf.protobuf.common cimport JsonStringToMessage
from cytobuf.protobuf.common cimport MessageDifferencer
from cytobuf.protobuf.common cimport MessageToJsonString


cdef class Message:

    def __cinit__(self, bint _init = True):
        self._ptr_owner = _init

    def __dealloc__(self):
        if self._internal is not NULL and self._ptr_owner is True:
            del self._internal
            self._internal = NULL

    def SerializeToString(self):
        cdef string result = string()
        self._internal.SerializeToString(&result)
        return result

    def FromJsonString(self, bytes data, bint ignore_unknown_fields = False):
        cdef JsonParseOptions args = JsonParseOptions()
        args.ignore_unknown_fields = ignore_unknown_fields
        JsonStringToMessage(data, self._internal, args)

    def ToJsonString(
            self,
            bint including_default_value_fields = False,
            bint preserving_proto_field_name = False,
            bint use_integers_for_enums = False,
    ):
        cdef string result = string()
        cdef JsonPrintOptions args = JsonPrintOptions()
        args.preserve_proto_field_names = preserving_proto_field_name
        args.always_print_primitive_fields = including_default_value_fields
        args.always_print_enums_as_ints = use_integers_for_enums
        MessageToJsonString(self._internal[0], &result, args)
        return result.decode('utf-8')

    def ParseFromString(self, bytes data):
        self._internal.ParseFromString(data)

    def Clear(self):
        self._internal.Clear()

    def __repr__(self):
        return self.DebugString()

    def __str__(self):
        return self.DebugString()

    def __eq__(self, other):
        cdef MessageDifferencer differencer
        cdef Message _other_message
        if isinstance(other, Message):
            _other_message = <Message> other
            return differencer.Equals(self._internal[0], _other_message._internal[0])
        return False