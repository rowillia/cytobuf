# flake8: noqa E501
import textwrap

import pytest

from cytobuf.protoc_gen_cython.cython_file import CImport
from cytobuf.protoc_gen_cython.cython_file import Class
from cytobuf.protoc_gen_cython.cython_file import Field
from cytobuf.protoc_gen_cython.cython_file import Module
from cytobuf.protoc_gen_cython.cython_file import Name
from cytobuf.protoc_gen_cython.cython_file import ProtoEnum
from cytobuf.protoc_gen_cython.cython_file import ProtoFile
from cytobuf.protoc_gen_cython.templates import externs_pxd_template
from cytobuf.protoc_gen_cython.templates import message_pxd_template
from cytobuf.protoc_gen_cython.templates import message_pyx_template
from cytobuf.protoc_gen_cython.templates import py_module_template
from cytobuf.protoc_gen_cython.templates import setup_py_template


@pytest.fixture
def pxd_file():
    return ProtoFile(
        imports=[
            CImport(Module(package="libcpp", module_basename="string"), "string"),
            CImport(
                Module.from_package_and_file("pb.address.models", "address.proto", ""), "Address"
            ),
        ],
        proto_filename="pb/people/models/people.proto",
        proto_package="pb.people.models",
        output_prefix="",
        namespace=["pb", "people", "models"],
        enums=[
            ProtoEnum(
                name=Name("Person_", "PhoneType"),
                value_names=["MOBILE", "HOME", "WORK"],
                exported=False,
            )
        ],
        classes=[
            Class(
                name=Name("Person_", "PhoneNumber"),
                fields=[
                    Field.create_string("number"),
                    Field.create_enum("type", "Person_PhoneType"),
                ],
                exported=False,
                nested_names=[],
            ),
            Class(
                name=Name("", "Person"),
                fields=[
                    Field.create_string("name"),
                    Field.create_int("id"),
                    Field.create_string("email"),
                    Field.create_message("phones", "Person_PhoneNumber", repeated=True),
                    Field.create_message("address", "Address"),
                ],
                exported=True,
                nested_names=[Name("Person_", "PhoneNumber")],
            ),
        ],
    )


def test_extern_pxd_render(pxd_file):
    expected = textwrap.dedent(
        """\
    # cython: language_level=3
    # distutils: language = c++
    from libcpp.string cimport string
    from pb.address.models._address__cy_pb2_externs cimport Address
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
            void clear_phones()
            const Person_PhoneNumber& phones(int index) except +
            Person_PhoneNumber* mutable_phones(int index) except +
            int phones_size() const
            Person_PhoneNumber* add_phones()
            void clear_address()
            const Address& address()
            Address* mutable_address()
            bool has_address() const;
    """
    )
    actual = externs_pxd_template.render(file=pxd_file)
    assert expected.strip() == actual.strip()


def test_message_pxd_render(pxd_file):
    expected = textwrap.dedent(
        """\
    # cython: language_level=3
    # distutils: language = c++

    from cytobuf.protobuf.message cimport Message
    from pb.people.models._people__cy_pb2_externs cimport Person_PhoneType as CppPerson_PhoneType
    from pb.people.models._people__cy_pb2_externs cimport Person_PhoneNumber as CppPerson_PhoneNumber
    from pb.people.models._people__cy_pb2_externs cimport Person as CppPerson

    cpdef enum Person_PhoneType:
        MOBILE = CppPerson_PhoneType.Person_PhoneType_MOBILE,
        HOME = CppPerson_PhoneType.Person_PhoneType_HOME,
        WORK = CppPerson_PhoneType.Person_PhoneType_WORK,

    cdef class Person_PhoneNumber(Message):
        cdef CppPerson_PhoneNumber* _message(self)

        @staticmethod
        cdef from_cpp(CppPerson_PhoneNumber* other)

    cdef class __Person__phones__container:
        cdef CppPerson* _instance

    cdef class Person(Message):
        cdef readonly __Person__phones__container phones
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
        # cython: language_level=3
        # distutils: language = c++
        # distutils: libraries = protobuf
        # distutils: include_dirs = /usr/local/include .
        # distutils: library_dirs = /usr/local/lib
        # distutils: extra_compile_args= -std=c++11
        # distutils: sources = pb/people/models/people.pb.cc

        from cytobuf.protobuf.message cimport Message
        from libcpp.string cimport string
        from pb.address.models._address__cy_pb2 cimport Address
        from pb.people.models._people__cy_pb2_externs cimport Person_PhoneNumber as CppPerson_PhoneNumber
        from pb.people.models._people__cy_pb2_externs cimport Person as CppPerson

        cdef class Person_PhoneNumber(Message):

            def __cinit__(self, _init = True):
                if _init:
                    instance = new CppPerson_PhoneNumber()
                    self._internal = instance

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

            @number.deleter
            def number(self):
                self._message().clear_number()

            @property
            def type(self):
                return self._message().type()

            @type.setter
            def type(self, Person_PhoneType value):
                self._message().set_type(value)

            @type.deleter
            def type(self):
                self._message().clear_type()

        cdef class __Person__phones__container:

            def __iter__(self):
                cdef int i
                for i in range(self._instance.phones_size()):
                    yield Person_PhoneNumber.from_cpp(self._instance.mutable_phones(i))

            def __len__(self):
                return self._instance.phones_size()

            def __getitem__(self, key):
                cdef int size, index, start, stop, step
                size = self._instance.phones_size()
                if isinstance(key, int):
                    index = key
                    if index < 0:
                        index = size + index
                    if not 0 <= index < size:
                        raise IndexError(f"list index ({key}) out of range")
                    return Person_PhoneNumber.from_cpp(self._instance.mutable_phones(index))
                else:
                    start, stop, step = key.indices(size)
                    return [
                        Person_PhoneNumber.from_cpp(self._instance.mutable_phones(index))
                        for index in range(start, stop, step)
                    ]

            def add(self):
                return Person_PhoneNumber.from_cpp(self._instance.add_phones())

        cdef class Person(Message):

            def __cinit__(self, _init = True):
                self.phones = __Person__phones__container()
                if _init:
                    instance = new CppPerson()
                    self.phones._instance = instance
                    self._internal = instance

            cdef CppPerson* _message(self):
                return <CppPerson*>self._internal

            @staticmethod
            cdef from_cpp(CppPerson* other):
                result = Person(_init=False)
                result._internal = other
                result.phones._instance = other
                return result

            @property
            def name(self):
                return self._message().name().decode('utf-8')

            @name.setter
            def name(self, str value):
                self._message().set_name(value.encode('utf-8'))

            @name.deleter
            def name(self):
                self._message().clear_name()

            @property
            def id(self):
                return self._message().id()

            @id.setter
            def id(self, int value):
                self._message().set_id(value)

            @id.deleter
            def id(self):
                self._message().clear_id()

            @property
            def email(self):
                return self._message().email().decode('utf-8')

            @email.setter
            def email(self, str value):
                self._message().set_email(value.encode('utf-8'))

            @email.deleter
            def email(self):
                self._message().clear_email()

            @property
            def address(self):
                return Address.from_cpp(self._instance.mutable_address())

            @address.deleter
            def address(self):
                self._message().clear_address()
    """
    )
    actual = message_pyx_template.render(file=pxd_file)
    assert expected.strip() == actual.strip()


def test_py_module_render(pxd_file):
    expected = textwrap.dedent(
        """\
        from pb.address.models.address_pb2 import Address
        from pb.people.models._people__cy_pb2 import Person_PhoneType as Person_PhoneType
        from pb.people.models._people__cy_pb2 import Person_PhoneNumber as _Cy_Person_PhoneNumber
        from pb.people.models._people__cy_pb2 import Person as _Cy_Person

        Person_PhoneNumber = _Cy_Person_PhoneNumber

        class Person(_Cy_Person):
            PhoneNumber = Person_PhoneNumber
        del Person_PhoneType
        del _Cy_Person_PhoneNumber
        del Person_PhoneNumber
        del _Cy_Person
        del Address

        __all__ = (
            'Person',
        )
        """
    )
    actual = py_module_template.render(file=pxd_file)
    assert expected.strip() == actual.strip()


def test_setup_py_render(pxd_file):
    expected = textwrap.dedent(
        """\
        from setuptools import find_packages
        from setuptools import setup
        from Cython.Build import cythonize


        EXTENSIONS = cythonize(
            [
                'pb/people/models/_people__cy_pb2.pyx',
            ],
            language_level="3",
        )


        setup(
            packages=find_packages(),
            package_data={
                "": ["*.pxd", "py.typed"]
            },
            ext_modules=EXTENSIONS,
            install_requires=["cytobuf"],
            zip_safe=False,
        )
        """
    )
    actual = setup_py_template.render(files=[pxd_file])
    assert expected.strip() == actual.strip()
