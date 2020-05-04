# flake8: noqa E501
import textwrap

import pytest
from google.protobuf import json_format
from google.protobuf.descriptor_pb2 import FileDescriptorProto

from cytobuf.protoc_gen_cython import ProtoFile
from cytobuf.protoc_gen_cython.templates import externs_pxd_template
from cytobuf.protoc_gen_cython.templates import message_pxd_template
from cytobuf.protoc_gen_cython.templates import message_pyx_template
from cytobuf.protoc_gen_cython.templates import py_module_template
from cytobuf.protoc_gen_cython.templates import setup_py_template


@pytest.fixture
def pxd_file():
    proto_files = [
        {
            "name": "pb/people/models/people.proto",
            "package": "pb.people.models",
            "dependency": ["pb/address/models/address.proto"],
            "messageType": [
                {
                    "name": "Person",
                    "field": [
                        {
                            "name": "name",
                            "number": 1,
                            "label": "LABEL_OPTIONAL",
                            "type": "TYPE_STRING",
                            "jsonName": "name",
                        },
                        {
                            "name": "id",
                            "number": 2,
                            "label": "LABEL_OPTIONAL",
                            "type": "TYPE_INT32",
                            "jsonName": "id",
                        },
                        {
                            "name": "email",
                            "number": 3,
                            "label": "LABEL_OPTIONAL",
                            "type": "TYPE_STRING",
                            "jsonName": "email",
                        },
                        {
                            "name": "phones",
                            "number": 4,
                            "label": "LABEL_REPEATED",
                            "type": "TYPE_MESSAGE",
                            "typeName": ".pb.people.models.Person.PhoneNumber",
                            "jsonName": "phones",
                        },
                        {
                            "name": "address",
                            "number": 5,
                            "label": "LABEL_OPTIONAL",
                            "type": "TYPE_MESSAGE",
                            "typeName": ".pb.address.models.Address",
                            "jsonName": "address",
                        },
                    ],
                    "nestedType": [
                        {
                            "name": "PhoneNumber",
                            "field": [
                                {
                                    "name": "number",
                                    "number": 1,
                                    "label": "LABEL_OPTIONAL",
                                    "type": "TYPE_STRING",
                                    "jsonName": "number",
                                },
                                {
                                    "name": "type",
                                    "number": 2,
                                    "label": "LABEL_OPTIONAL",
                                    "type": "TYPE_ENUM",
                                    "typeName": ".pb.people.models.Person.PhoneType",
                                    "jsonName": "type",
                                },
                            ],
                        }
                    ],
                    "enumType": [
                        {
                            "name": "PhoneType",
                            "value": [
                                {"name": "MOBILE", "number": 0},
                                {"name": "HOME", "number": 1},
                                {"name": "WORK", "number": 2},
                            ],
                        }
                    ],
                }
            ],
            "syntax": "proto3",
        },
        {
            "name": "pb/address/models/address.proto",
            "package": "pb.address.models",
            "messageType": [
                {
                    "name": "Address",
                    "field": [
                        {
                            "name": "street",
                            "number": 1,
                            "label": "LABEL_OPTIONAL",
                            "type": "TYPE_STRING",
                            "jsonName": "street",
                        }
                    ],
                }
            ],
            "syntax": "proto3",
        },
    ]
    parsed_files = ProtoFile.from_file_descriptor_protos(
        [json_format.ParseDict(x, FileDescriptorProto()) for x in proto_files],
        {"pb/people/models/people.proto"},
        "",
    )
    return next(x for x in parsed_files if x.proto_filename == "pb/people/models/people.proto")


def test_extern_pxd_render(pxd_file):
    expected = textwrap.dedent(
        """\
    # cython: language_level=3
    # distutils: language = c++
    from pb.address.models._address__cy_pb2_externs cimport Address as pb_address_models_Address
    from libcpp.string cimport string as string
    cimport cytobuf.protobuf.common

    cdef extern from "pb/people/models/people.pb.h" namespace "pb::people::models":

        cdef enum Person_PhoneType:
            Person_PhoneType_MOBILE,
            Person_PhoneType_HOME,
            Person_PhoneType_WORK,

        cdef cppclass Person_PhoneNumber(cytobuf.protobuf.common.Message):
            Person_PhoneNumber()
            void clear_number()
            const string& number()
            void set_number(const string&) except +
            void clear_type()
            Person_PhoneType type()
            void set_type(Person_PhoneType) except +

        cdef cppclass Person(cytobuf.protobuf.common.Message):
            Person()
            void clear_name()
            const string& name()
            void set_name(const string&) except +
            void clear_id()
            int id()
            void set_id(int) except +
            void clear_email()
            const string& email()
            void set_email(const string&) except +
            void clear_phones()
            const Person_PhoneNumber& phones(int) except +
            Person_PhoneNumber* mutable_phones(int) except +
            size_t phones_size() const
            Person_PhoneNumber* add_phones()
            void clear_address()
            const pb_address_models_Address& address()
            pb_address_models_Address* mutable_address()
            bint has_address() const;
    """
    )
    actual = externs_pxd_template.render(file=pxd_file)
    assert expected.strip() == actual.strip()


def test_message_pxd_render(pxd_file):
    expected = textwrap.dedent(
        """\
    # cython: language_level=3
    # distutils: language = c++
    cimport cytobuf.protobuf.message
    from pb.people.models._people__cy_pb2_externs cimport Person_PhoneNumber as _Cpp_pb_people_models_Person_PhoneNumber
    from pb.people.models._people__cy_pb2_externs cimport Person as _Cpp_pb_people_models_Person

    cdef class pb_people_models_Person_PhoneNumber(cytobuf.protobuf.message.Message):
        cdef _Cpp_pb_people_models_Person_PhoneNumber* _message(self)

        @staticmethod
        cdef from_cpp(_Cpp_pb_people_models_Person_PhoneNumber* other)

    cdef class __pb_people_models_Person__phones__container:
        cdef _Cpp_pb_people_models_Person* _instance

    cdef class pb_people_models_Person(cytobuf.protobuf.message.Message):
        cdef readonly __pb_people_models_Person__phones__container phones
        cdef _Cpp_pb_people_models_Person* _message(self)

        @staticmethod
        cdef from_cpp(_Cpp_pb_people_models_Person* other)
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

        cimport cytobuf.protobuf.message
        from pb.address.models._address__cy_pb2 cimport pb_address_models_Address
        from pb.address.models._address__cy_pb2_externs cimport Address as _Cpp_pb_address_models_Address
        from pb.people.models._cy_enums._people_Person_PhoneType__cy_pb2 cimport pb_people_models_Person_PhoneType
        from libcpp.string cimport string
        from pb.people.models._people__cy_pb2_externs cimport Person_PhoneNumber as _Cpp_pb_people_models_Person_PhoneNumber
        from pb.people.models._people__cy_pb2_externs cimport Person as _Cpp_pb_people_models_Person

        cdef class pb_people_models_Person_PhoneNumber(cytobuf.protobuf.message.Message):

            def __cinit__(self, _init = True):
                if _init:
                    instance = new _Cpp_pb_people_models_Person_PhoneNumber()
                    self._internal = instance

            cdef _Cpp_pb_people_models_Person_PhoneNumber* _message(self):
                return <_Cpp_pb_people_models_Person_PhoneNumber*>self._internal

            @staticmethod
            cdef from_cpp(_Cpp_pb_people_models_Person_PhoneNumber* other):
                result = pb_people_models_Person_PhoneNumber(_init=False)
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
            def type(self, pb_people_models_Person_PhoneType value):
                self._message().set_type(value)

            @type.deleter
            def type(self):
                self._message().clear_type()

        cdef class __pb_people_models_Person__phones__container:

            def __iter__(self):
                cdef int i
                for i in range(self._instance.phones_size()):
                    yield pb_people_models_Person_PhoneNumber.from_cpp(self._instance.mutable_phones(i))

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
                    return pb_people_models_Person_PhoneNumber.from_cpp(self._instance.mutable_phones(index))
                else:
                    start, stop, step = key.indices(size)
                    return [
                        pb_people_models_Person_PhoneNumber.from_cpp(self._instance.mutable_phones(index))
                        for index in range(start, stop, step)
                    ]

            def add(self):
                return pb_people_models_Person_PhoneNumber.from_cpp(self._instance.add_phones())

        cdef class pb_people_models_Person(cytobuf.protobuf.message.Message):

            def __cinit__(self, _init = True):
                self.phones = __pb_people_models_Person__phones__container()
                if _init:
                    instance = new _Cpp_pb_people_models_Person()
                    self.phones._instance = instance
                    self._internal = instance

            cdef _Cpp_pb_people_models_Person* _message(self):
                return <_Cpp_pb_people_models_Person*>self._internal

            @staticmethod
            cdef from_cpp(_Cpp_pb_people_models_Person* other):
                result = pb_people_models_Person(_init=False)
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
                return pb_address_models_Address.from_cpp(self._message().mutable_address())

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
        from pb.people.models._cy_enums._people_Person_PhoneType__cy_pb2 import Person_PhoneType
        pb_people_models_Person_PhoneType = Person_PhoneType
        from pb.people.models._people__cy_pb2 import pb_people_models_Person_PhoneNumber as _Cy_pb_people_models_Person_PhoneNumber
        from pb.people.models._people__cy_pb2 import pb_people_models_Person as _Cy_pb_people_models_Person

        Person_PhoneNumber = _Cy_pb_people_models_Person_PhoneNumber

        class Person(_Cy_pb_people_models_Person):
            PhoneNumber = Person_PhoneNumber
            PhoneType = Person_PhoneType
        del pb_people_models_Person_PhoneType
        del Person_PhoneType
        del _Cy_pb_people_models_Person_PhoneNumber
        del Person_PhoneNumber
        del _Cy_pb_people_models_Person
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
    actual = setup_py_template.render(pyx_files=[pxd_file.module.pyx_filename])
    assert expected.strip() == actual.strip()
