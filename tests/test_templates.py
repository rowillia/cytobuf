import textwrap

import pytest

from cytobuf.protoc_gen_cython.cython_file import CImport
from cytobuf.protoc_gen_cython.cython_file import Class
from cytobuf.protoc_gen_cython.cython_file import Field
from cytobuf.protoc_gen_cython.cython_file import ProtoEnum
from cytobuf.protoc_gen_cython.cython_file import ProtoFile
from cytobuf.protoc_gen_cython.templates import externs_pxd_template
from cytobuf.protoc_gen_cython.templates import message_pxd_template
from cytobuf.protoc_gen_cython.templates import message_pyx_template


@pytest.fixture
def pxd_file():
    return ProtoFile(
        imports=[CImport("libcpp.string", "string")],
        cpp_header="pb/people/models/people.pb.h",
        proto_filename="pb/people/models/people.proto",
        proto_package="pb.people.models",
        namespace=["pb", "people", "models"],
        enums=[
            ProtoEnum(
                name="Person_PhoneType", value_names=["MOBILE", "HOME", "WORK"], exported=False
            )
        ],
        classes=[
            Class(
                name="Person_PhoneNumber",
                fields=[
                    Field.create_string("number"),
                    Field.create_enum("type", "Person_PhoneType"),
                ],
                exported=False,
            ),
            Class(
                name="Person",
                fields=[
                    Field.create_string("name"),
                    Field.create_int("id"),
                    Field.create_string("email"),
                    Field.create_message("alternate_phones", "Person_PhoneNumber", repeated=True),
                    Field.create_message("main_phone", "Person_PhoneNumber"),
                ],
                exported=True,
            ),
        ],
    )


def test_extern_pxd_render(pxd_file):
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
            void set_number(const char*) except +
            void set_number(const char*, int index) except +
            void clear_type()
            Person_PhoneType type()
            void set_type(Person_PhoneType value) except +

        cdef cppclass Person(Message):
            Person()
            void clear_name()
            const string& name()
            void set_name(const char*) except +
            void set_name(const char*, int index) except +
            void clear_id()
            int id()
            void set_id(int) except +
            void clear_email()
            const string& email()
            void set_email(const char*) except +
            void set_email(const char*, int index) except +
            void clear_alternate_phones()
            const Person_PhoneNumber& alternate_phones(int index) except +
            Person_PhoneNumber* mutable_alternate_phones(int index) except +
            int alternate_phones_size() const
            Person_PhoneNumber* add_alternate_phones()
            void clear_main_phone()
            const Person_PhoneNumber& main_phone()
            Person_PhoneNumber* mutable_main_phone()
            bool has_main_phone() const;
    """
    )
    actual = externs_pxd_template.render(file=pxd_file)
    assert expected.strip() == actual.strip()


def test_message_pxd_render(pxd_file):
    expected = textwrap.dedent(
        """\
    # distutils: language = c++

    from cytobuf.protobuf.message cimport Message
    from pb.people.models.people_externs cimport Person_PhoneNumber as CppPerson_PhoneNumber
    from pb.people.models.people_externs cimport Person as CppPerson

    cdef cppclass Person_PhoneNumber(Message):
        cdef CppPerson_PhoneNumber* _message(self)

        @staticmethod
        cdef from_cpp(CppPerson_PhoneNumber* other)

    cdef class __Person__alternate_phones__container:
        cdef CppPerson* _instance

    cdef cppclass Person(Message):
        cdef readonly __Person__alternate_phones__container alternate_phones
        cdef CppPerson* _message(self)

        @staticmethod
        cdef from_cpp(CppPerson* other)
    """
    )

    actual = message_pxd_template.render(file=pxd_file)
    assert expected.strip() == actual.strip()


def test_message_pyx_render(pxd_file):
    expected = textwrap.dedent(
        """\
        # distutils: language = c++
        # distutils: libraries = protobuf
        # distutils: include_dirs = /usr/local/include ../cc
        # distutils: library_dirs = /usr/local/lib
        # distutils: extra_compile_args= -std=c++11
        # distutils: sources = ../cc/pb/addressbook/models/addressbook.pb.cc

        from cytobuf.protobuf.message cimport Message
        from pb.people.models.people_externs cimport Person_PhoneNumber as CppPerson_PhoneNumber
        from pb.people.models.people_externs cimport Person as CppPerson

        cdef cppclass Person_PhoneNumber(Message):
            def __cinit__(self, _init = True):
                if _init:
                    instance = new CppPerson_PhoneNumber()
                    self.internal = instance

            cdef CppPerson_PhoneNumber* _message(self):
                return <CppPerson_PhoneNumber*>self._internal

            @staticmethod
            cdef from_cpp(CppPerson_PhoneNumber* other):
                result = Person_PhoneNumber(_init=False)
                result._internal = other
                return result

            @property
            def number(self):
                return self._message().number().decode('utf-8')

            @number.setter
            def number(self, str value):
                self._message().set_number(value.encode('utf-8'))

            @property
            def type(self):
                return self._message().type()

            @type.setter
            def type(self, int value):
                self._message().set_type(value)

        cdef class __Person__alternate_phones__container:
            def __iter__(self):
                cdef int i
                for i in range(self._instance.alternate_phones_size()):
                    yield Person_PhoneNumber.from_cpp(self._instance.mutable_alternate_phones(i))

            def __len__(self):
                return self._instance.alternate_phones_size()

            def add(self):
                return Person_PhoneNumber.from_cpp(self._instance.add_alternate_phones())

        cdef cppclass Person(Message):
            def __cinit__(self, _init = True):
                self.alternate_phones = __Person__alternate_phones__container()
                if _init:
                    instance = new CppPerson()
                    self.alternate_phones._instance = instance
                    self.internal = instance

            cdef CppPerson* _message(self):
                return <CppPerson*>self._internal

            @staticmethod
            cdef from_cpp(CppPerson* other):
                result = Person(_init=False)
                result._internal = other
                result.alternate_phones._instance = instance
                return result

            @property
            def name(self):
                return self._message().name().decode('utf-8')

            @name.setter
            def name(self, str value):
                self._message().set_name(value.encode('utf-8'))

            @property
            def id(self):
                return self._message().id()

            @id.setter
            def id(self, int value):
                self._message().set_id(value)

            @property
            def email(self):
                return self._message().email().decode('utf-8')

            @email.setter
            def email(self, str value):
                self._message().set_email(value.encode('utf-8'))

            @property
            def main_phone(self):
                return Person_PhoneNumber.from_cpp(self._instance.mutable_main_phone())
    """
    )

    actual = message_pyx_template.render(file=pxd_file)
    assert expected.strip() == actual.strip()
