from cytobuf.protobuf.repeated_field cimport RepeatedField

cdef class RepeatedFieldBase:
    cdef:
        RepeatedField[Element]* _instance