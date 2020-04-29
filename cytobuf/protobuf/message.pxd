# cython: language_level=3
# distutils: language = c++
# distutils: libraries = protobuf
# distutils: include_dirs = /usr/local/include
# distutils: library_dirs = /usr/local/lib
# distutils: extra_compile_args= -std=c++11

from cytobuf.protobuf.common cimport Message as CppMessage

cdef class Message:
    cdef:
        CppMessage* _internal
        bint _ptr_owner

    cdef inline str DebugString(self):
        return self._internal.DebugString().decode('utf-8')