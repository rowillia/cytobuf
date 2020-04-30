import json
from enum import EnumMeta

import pytest
from cytobuf_pb.addressbook.models import addressbook_pb2
from cytobuf_pb.people.models import people_pb2
from cytobuf_type_test import type_test_pb2

BASELINE_ATTRIBUTES = {
    "__all__",
    "__builtins__",
    "__cached__",
    "__doc__",
    "__file__",
    "__loader__",
    "__name__",
    "__package__",
    "__path__",
    "__spec__",
}


def test_exported_symbols():
    assert set(dir(addressbook_pb2)) - BASELINE_ATTRIBUTES == {"AddressBook"}
    assert set(dir(people_pb2)) - BASELINE_ATTRIBUTES == {"Person"}


def test_enum():
    phone_type = people_pb2.Person.PhoneType
    assert isinstance(phone_type, EnumMeta)
    assert [e.name for e in phone_type] == ["MOBILE", "HOME", "WORK"]
    assert [e.value for e in phone_type] == [0, 1, 2]
    assert phone_type.MOBILE == 0
    assert phone_type.HOME == 1


@pytest.mark.parametrize("value", [1, people_pb2.Person.PhoneType.HOME])
def test_set_enum(value):
    person = people_pb2.Person()
    new_phone = person.phones.add()
    new_phone.type = people_pb2.Person.PhoneType.HOME
    assert new_phone.type == people_pb2.Person.PhoneType.HOME
    assert new_phone.type == 1
    assert new_phone.ToJsonString() == '{"type":"HOME"}'


def test_string():
    person = people_pb2.Person()
    assert isinstance(person.name, str)
    assert person.name == ""
    person.name = "bob"
    assert isinstance(person.name, str)
    assert person.name == "bob"
    assert json.loads(person.ToJsonString()) == {"name": "bob"}


def test_bytes():
    test_type = type_test_pb2.TypeTester()
    assert test_type.bytes_value == b""
    with pytest.raises(TypeError):
        test_type.bytes_value = "not bytes"
    test_type.bytes_value = b"ascii"
    assert test_type.bytes_value == b"ascii"
    test_type.bytes_value = b"\xc3\x28"
    assert test_type.bytes_value == b"\xc3\x28"
    assert len(test_type.bytes_value) == 2


def test_bool():
    test_type = type_test_pb2.TypeTester()
    assert test_type.bool_value is False
    test_type.bool_value = True
    assert test_type.bool_value is True


@pytest.mark.parametrize(
    "int_type,signed,bits",
    [
        ("int32", True, 32),
        ("uint32", False, 32),
        ("sint32", True, 32),
        ("fixed32", False, 32),
        ("sfixed32", True, 32),
        ("int64", True, 64),
        ("uint64", False, 64),
        ("sint64", True, 64),
        ("fixed64", False, 64),
        ("sfixed64", True, 64),
    ],
)
def test_int32(int_type, signed, bits):
    test_type = type_test_pb2.TypeTester()
    assert getattr(test_type, f"{int_type}_value") == 0
    setattr(test_type, f"{int_type}_value", 42)
    assert getattr(test_type, f"{int_type}_value") == 42
    setattr(test_type, f"{int_type}_value", (1 << (bits - 1)) - 1)
    assert getattr(test_type, f"{int_type}_value") == (1 << (bits - 1)) - 1
    if signed:
        setattr(test_type, f"{int_type}_value", -1)
        assert getattr(test_type, f"{int_type}_value") == -1
        with pytest.raises(OverflowError):
            setattr(test_type, f"{int_type}_value", (1 << bits) - 1)
    else:
        setattr(test_type, f"{int_type}_value", (1 << bits) - 1)
        assert getattr(test_type, f"{int_type}_value") == (1 << bits) - 1
        with pytest.raises(OverflowError):
            setattr(test_type, f"{int_type}_value", -1)


@pytest.mark.parametrize("float_type", ["float", "double"])
def test_floats(float_type):
    test_type = type_test_pb2.TypeTester()
    assert getattr(test_type, f"{float_type}_value") == 0
    setattr(test_type, f"{float_type}_value", 0.5)
    assert getattr(test_type, f"{float_type}_value") == 0.5
    setattr(test_type, f"{float_type}_value", 1 / 3)
    if float_type == "double":
        assert getattr(test_type, f"{float_type}_value") == 1 / 3
    else:
        assert getattr(test_type, f"{float_type}_value") == 0.3333333432674408


def test_string_unicode():
    person = people_pb2.Person()
    person.name = "\U0001f600lol"
    assert isinstance(person.name, str)
    assert person.name == "\U0001f600lol"
    assert json.loads(person.ToJsonString()) == {"name": "\U0001f600lol"}


def test_repeated_access():
    addressbook = addressbook_pb2.AddressBook()
    assert len(addressbook.people) == 0
    assert list(addressbook.people) == []
    with pytest.raises(IndexError, match=r"list index \(10\) out of range"):
        _ = addressbook.people[10]
    new_person = addressbook.people.add()
    assert len(addressbook.people) == 1
    new_person.name = "bob"
    assert addressbook.people[0].name == "bob"
    addressbook.people.add()
    addressbook.people[1].name = "alice"
    assert len(addressbook.people) == 2
    assert addressbook.people[-1].name == "alice"
    assert addressbook.people[-2].name == "bob"


def test_repeated_slice():
    addressbook = addressbook_pb2.AddressBook()
    person = addressbook.people.add()
    for x in range(10):
        person.phones.add().number = str(x)
    assert len(person.phones) == 10
    assert [int(phone.number) for phone in person.phones[::]] == list(range(10))
    assert [int(phone.number) for phone in person.phones[0:10:]] == list(range(10))
    assert [int(phone.number) for phone in person.phones[-100:100:]] == list(range(10))
    assert [int(phone.number) for phone in person.phones[0:8:2]] == [0, 2, 4, 6]
    assert [int(phone.number) for phone in person.phones[8::-2]] == [8, 6, 4, 2, 0]
    expected = {
        "people": [
            {
                "phones": [
                    {"number": "0"},
                    {"number": "1"},
                    {"number": "2"},
                    {"number": "3"},
                    {"number": "4"},
                    {"number": "5"},
                    {"number": "6"},
                    {"number": "7"},
                    {"number": "8"},
                    {"number": "9"},
                ]
            }
        ]
    }
    assert json.loads(addressbook.ToJsonString()) == expected
