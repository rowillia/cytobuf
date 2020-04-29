# cython: language_level=3
# distutils: language = c++
# distutils: libraries = protobuf
# distutils: include_dirs = /usr/local/include
# distutils: library_dirs = /usr/local/lib
# distutils: extra_compile_args= -std=c++11

from libcpp.string cimport string


cdef extern from "google/protobuf/util/message_differencer.h" namespace "google::protobuf::util":
    cdef cppclass MessageDifferencer:
        MessageDifferencer()
        bint Equals(const Message & message1, const Message & message2)


cdef extern from "google/protobuf/message.h" namespace "google::protobuf":
    cdef cppclass Message:
        bint ParseFromString(const string& data) except +
        bint SerializeToString(string* output) const
        string DebugString() const


cdef extern from "google/protobuf/stubs/status.h" namespace "google::protobuf::util":
    cdef cppclass Status:
        Status()
        string ToString() const


cdef extern from "google/protobuf/util/json_util.h" namespace "google::protobuf::util":
    cdef Status MessageToJsonString(const Message & message, string* output)
    cdef Status JsonStringToMessage(const char* input, Message* output)