# cython: language_level=3
# distutils: language = c++
# distutils: libraries = protobuf
# distutils: include_dirs = /usr/local/include
# distutils: library_dirs = /usr/local/lib
# distutils: extra_compile_args= -std=c++11

from libcpp.pair cimport pair
from libcpp.string cimport string


cdef extern from "google/protobuf/util/message_differencer.h" namespace "google::protobuf::util":
    cdef cppclass MessageDifferencer:
        MessageDifferencer()
        bint Equals(const Message & message1, const Message & message2)


cdef extern from "google/protobuf/map.h" namespace "google::protobuf":
    cdef cppclass MapPair[Key, T]:
        ctypedef const Key first_type;
        ctypedef T second_type;

        MapPair()
        const Key first
        T second

    cdef cppclass Map[Key, T]:
        ctypedef Key key_type
        ctypedef T mapped_type
        ctypedef MapPair[Key, T] value_type;
        ctypedef value_type* pointer
        ctypedef value_type& reference;
        cppclass iterator:
            reference operator*() const
            iterator& operator++()
            iterator operator++(int)
            bint operator==(iterator)
            bint operator!=(iterator)

        Map()
        iterator begin()
        iterator end()
        void clear()
        size_t size()
        bint empty()
        bint contains(const Key & key) const
        T & operator[](const key_type & key)
        const T & at(const key_type & key) const
        T & at(const key_type & key)
        size_t count(const key_type & key) const
        iterator find(const key_type & key)
        pair[iterator, bint] insert(const value_type & value)
        size_t erase(const key_type & key)


cdef extern from "google/protobuf/message.h" namespace "google::protobuf":
    cdef cppclass Message:
        bint ParseFromString(const string& data) except +
        bint SerializeToString(string* output) const
        string DebugString() const
        void Clear()


cdef extern from "google/protobuf/stubs/status.h" namespace "google::protobuf::util":
    cdef cppclass Status:
        Status()
        string ToString() const


cdef extern from "google/protobuf/util/json_util.h" namespace "google::protobuf::util":
    cdef struct JsonPrintOptions:
        bint add_whitespace
        bint always_print_primitive_fields
        bint always_print_enums_as_ints
        bint preserve_proto_field_names

    cdef struct JsonParseOptions:
        bint ignore_unknown_fields
        bint case_insensitive_enum_parsing

    cdef Status MessageToJsonString(const Message &, string*, const JsonPrintOptions &)
    cdef Status JsonStringToMessage(const char*, Message*, const JsonParseOptions &)