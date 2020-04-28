from cytobuf.protobuf.common cimport Message as CppMessage

cdef class Message:
    cdef:
        CppMessage* _internal
        bint _ptr_owner

    cdef inline str DebugString(self):
        return self._internal.DebugString().decode('utf-8')