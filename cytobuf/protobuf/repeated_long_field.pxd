# cython: language_level=3
# distutils: language = c++
# distutils: libraries = protobuf
# distutils: include_dirs = /usr/local/include
# distutils: library_dirs = /usr/local/lib
# distutils: extra_compile_args= -std=c++11

ctypedef long long Element
ctypedef int PyType

include "repeated_field_base.pxd"

cdef class RepeatedLongField(RepeatedFieldBase):
    pass