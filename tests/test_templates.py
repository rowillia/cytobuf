import textwrap

import pytest

from cytobuf.protoc_gen_cython.cython_file import CImport
from cytobuf.protoc_gen_cython.cython_file import Class
from cytobuf.protoc_gen_cython.cython_file import Field
from cytobuf.protoc_gen_cython.cython_file import ProtoEnum
from cytobuf.protoc_gen_cython.cython_file import ProtoFile
from cytobuf.protoc_gen_cython.templates import pxd_template


@pytest.fixture
def pxd_file():
    return ProtoFile(
        imports=[CImport("libcpp.string", "string")],
        cpp_header="pb/people/models/people.pb.h",
        proto_filename="pb/people/models/people.proto",
        namespace=["pb", "people", "models"],
        enums=[ProtoEnum(name="Person_PhoneType", value_names=["MOBILE", "HOME", "WORK"])],
        classes=[
            Class(
                name="Person_PhoneNumber",
                fields=[
                    Field.create_string("number"),
                    Field.create_enum("type", "Person_PhoneType"),
                ],
            ),
            Class(
                name="Person",
                fields=[
                    Field.create_string("name"),
                    Field.create_int("id"),
                    Field.create_string("email"),
                    Field.create_message("phones", "Person_PhoneNumber", repeated=True),
                ],
            ),
        ],
    )


def test_render(pxd_file):
    expected = textwrap.dedent(
        """\
    # distutils: language = c++
    from libcpp.string cimport string
    from cytobuf.protobuf.common cimport Message

    cdef extern from "pb/people/models/people.pb.h" namespace "pb::people::models":

        cdef enum Person_PhoneType:
            Person_PhoneType_MOBILE,
            Person_PhoneType_HOME,
            Person_PhoneType_WORK,

        cdef cppclass Person_PhoneNumber(Message):
            Person_PhoneNumber()
            void clear_number()
            const string& number()
            string* mutable_number()
            void set_number(const char*) except +
            void set_number(const char*, int index) except +
            void clear_type()
            Person_PhoneType type()
            void set_type(Person_PhoneType value) except +

        cdef cppclass Person(Message):
            Person()
            void clear_name()
            const string& name()
            string* mutable_name()
            void set_name(const char*) except +
            void set_name(const char*, int index) except +
            void clear_id()
            int id()
            void set_id(int) except +
            void clear_email()
            const string& email()
            string* mutable_email()
            void set_email(const char*) except +
            void set_email(const char*, int index) except +
            void clear_phones()
            const Person_PhoneNumber& phones(int index) except +
            Person_PhoneNumber* mutable_phones(int index) except +
            int phones_size() const
            Person_PhoneNumber* add_phones()
    """
    )
    actual = pxd_template.render(file=pxd_file)
    assert expected.strip() == actual.strip()
