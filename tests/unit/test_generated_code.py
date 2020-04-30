import json
from enum import EnumMeta

import pytest
from cytobuf_pb.addressbook.models import addressbook_pb2
from cytobuf_pb.people.models import people_pb2


BASELINE_ATTRIBUTES = {'__all__', '__builtins__', '__cached__', '__doc__', '__file__', '__loader__', '__name__', '__package__', '__path__', '__spec__'}


def test_exported_symbols():
    assert set(dir(addressbook_pb2)) - BASELINE_ATTRIBUTES == {'AddressBook'}
    assert set(dir(people_pb2)) - BASELINE_ATTRIBUTES == {'Person'}


def test_enum():
    phone_type = people_pb2.Person.PhoneType
    assert isinstance(phone_type, EnumMeta)
    assert [e.name for e in phone_type] == ['MOBILE', 'HOME', 'WORK']
    assert [e.value for e in phone_type] == [0, 1, 2]
    assert phone_type.MOBILE == 0
    assert phone_type.HOME == 1
    assert phone_type.WORK == 2


def test_enum():
    assert isinstance(phone_type, EnumMeta)
    assert [e.name for e in phone_type] == ['MOBILE', 'HOME', 'WORK']
    assert [e.value for e in phone_type] == [0, 1, 2]
    assert phone_type.MOBILE == 0
    assert phone_type.HOME == 1
    assert phone_type.WORK == 2


def test_string():
    person = people_pb2.Person()
    assert isinstance(person.name, str)
    assert person.name == ''
    person.name = 'bob'
    assert isinstance(person.name, str)
    assert person.name == 'bob'
    assert json.loads(person.ToJsonString()) == {'name': 'bob'}


def test_string_unicode():
    person = people_pb2.Person()
    person.name = "\U0001f600lol"
    assert isinstance(person.name, str)
    assert person.name == "\U0001f600lol"
    assert json.loads(person.ToJsonString()) == {'name': "\U0001f600lol"}


def test_repeated_access():
    addressbook = addressbook_pb2.AddressBook()
    assert len(addressbook.people) == 0
    assert list(addressbook.people) == []
    with pytest.raises(IndexError, match='list index \(10\) out of range'):
        _ = addressbook.people[10]
    new_person = addressbook.people.add()
    assert len(addressbook.people) == 1
    new_person.name = 'bob'
    assert addressbook.people[0].name == 'bob'
    addressbook.people.add()
    addressbook.people[1].name = 'alice'
    assert len(addressbook.people) == 2
    assert addressbook.people[-1].name == 'alice'
    assert addressbook.people[-2].name == 'bob'


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
        "people":
            [
                {"phones":[{"number":"0"},{"number":"1"},{"number":"2"},{"number":"3"},{"number":"4"},{"number":"5"},{"number":"6"},{"number":"7"},{"number":"8"},{"number":"9"}]}]}
    assert json.loads(addressbook.ToJsonString()) == expected
