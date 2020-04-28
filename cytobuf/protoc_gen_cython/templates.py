# flake8: noqa E501
from jinja2 import Template


EXTERNS_PXD_TEMPLATE_SOURCE = """\
# distutils: language = c++

{%- for import in file.imports %}
from {{ import.module }} cimport {{ import.symbol }}
{%- endfor %}
from cytobuf.protobuf.common cimport Message

cdef extern from "{{ file.cpp_header }}" namespace "{{ file.namespace | join("::") }}":
{%- for enum in file.enums %}

    cdef enum {{ enum.name }}:
    {%- for value in enum.value_names %}
        {{ enum.name }}_{{ value }},
    {%- endfor %}
{%- endfor %}

{%- for cdef_class in file.classes %}

    cdef cppclass {{ cdef_class.name }}(Message):
        {{ cdef_class.name }}()
    {%- for field in cdef_class.fields %}
        void clear_{{ field.name }}()
        {{ field.return_type }} {{ field.name }}({%- if field.repeated -%}int index) except +{%- else -%}){%- endif -%}
        {%- if field.field_type.name == 'message' %}
        {{ field.python_type }}* mutable_{{ field.name }}({%- if field.repeated -%}int index) except +{%- else -%}){%- endif -%}
        {%- endif -%}
        {%- for signature in field.input_signatures %}
        void set_{{ field.name }}({%- if field.repeated -%}int index, {% endif -%}{{ signature.parameters | join(", ") }}) except +
        {%- endfor %}
        {%- if field.repeated %}
        int {{ field.name }}_size() const
            {%- if field.field_type.name == 'message' %}
        {{ field.python_type }}* add_{{ field.name }}()
            {%- endif -%}
            {%- for signature in field.input_signatures %}
        void add_{{ field.name }}({{ signature.parameters | join(", ") }})
            {%- endfor %}
        {%- elif field.field_type.name == 'message' %}
        bool has_{{ field.name }}() const;
        {%- endif -%}
    {%- endfor -%}
{%- endfor %}
"""


externs_pxd_template = Template(EXTERNS_PXD_TEMPLATE_SOURCE)


MESSAGE_PXD_TEMPLATE = """\
# distutils: language = c++

from cytobuf.protobuf.message cimport Message
{%- for cdef_class in file.classes %}
from {{ file.extern_module }} cimport {{ cdef_class.name }} as Cpp{{ cdef_class.name }}
{%- endfor %}

{%- for cdef_class in file.classes %}

    {%- for field in cdef_class.fields if field.repeated %}

cdef class __{{ cdef_class.name }}__{{ field.name }}__container:
    cdef Cpp{{ cdef_class.name }}* _instance
    {%- endfor %}

cdef cppclass {{ cdef_class.name }}(Message):
    {%- for field in cdef_class.fields if field.repeated %}
    cdef readonly __{{ cdef_class.name }}__{{ field.name }}__container {{ field.name }}
    {%- endfor %}
    cdef Cpp{{ cdef_class.name }}* _message(self)

    @staticmethod
    cdef from_cpp(Cpp{{ cdef_class.name }}* other)
{%- endfor %}
"""


message_pxd_template = Template(MESSAGE_PXD_TEMPLATE)


MESSAGE_PYX_TEMPLATE = """\
# distutils: language = c++
# distutils: libraries = protobuf
# distutils: include_dirs = /usr/local/include ../cc
# distutils: library_dirs = /usr/local/lib
# distutils: extra_compile_args= -std=c++11
# distutils: sources = ../cc/pb/addressbook/models/addressbook.pb.cc

from cytobuf.protobuf.message cimport Message
{%- for cdef_class in file.classes %}
from {{ file.extern_module }} cimport {{ cdef_class.name }} as Cpp{{ cdef_class.name }}
{%- endfor %}

{%- for cdef_class in file.classes %}
    {%- for field in cdef_class.fields if field.repeated %}

cdef class __{{ cdef_class.name }}__{{ field.name }}__container:
    def __iter__(self):
        cdef int i
        for i in range(self._instance.{{ field.name }}_size()):
        {%- if field.field_type.name == 'message' %}
            yield {{ field.python_type }}.from_cpp(self._instance.mutable_{{ field.name }}(i))
        {%- else %}
            yield self._instance.{{ field.name }}(i)
        {%- endif %}

    def __len__(self):
        return self._instance.{{ field.name }}_size()

        {%- if field.field_type.name == 'message' %}

    def add(self):
        return {{ field.python_type }}.from_cpp(self._instance.add_{{ field.name }}())
        {%- else -%}

    def add(self, value):
        self._instance.add_{{ field.name }}(value)
        {%- endif -%}
    {%- endfor %}

cdef cppclass {{ cdef_class.name }}(Message):
    def __cinit__(self, _init = True):
    {%- for field in cdef_class.fields if field.repeated %}
        self.{{ field.name }} = __{{ cdef_class.name }}__{{ field.name }}__container()
    {%- endfor %}
        if _init:
            instance = new Cpp{{ cdef_class.name }}()
    {%- for field in cdef_class.fields if field.repeated %}
            self.{{ field.name }}._instance = instance
    {%- endfor %}
            self.internal = instance

    cdef Cpp{{ cdef_class.name }}* _message(self):
        return <Cpp{{ cdef_class.name }}*>self._internal

    @staticmethod
    cdef from_cpp(Cpp{{ cdef_class.name }}* other):
        result = {{ cdef_class.name }}(_init=False)
        result._internal = other   
    {%- for field in cdef_class.fields if field.repeated %}
        result.{{ field.name }}._instance = instance
    {%- endfor %}
        return result
        
    {%- for field in cdef_class.fields if not field.repeated %}
        {%- if field.field_type.name == 'scalar' %}

    @property
    def {{ field.name }}(self):
        return self._message().{{ field.name }}(){%- if field.python_type == 'str' -%}.decode('utf-8'){%- endif %}

    @{{ field.name }}.setter
    def {{ field.name }}(self, {{ field.python_type }} value):
        self._message().set_{{ field.name }}(value{%- if field.python_type == 'str' -%}.encode('utf-8'){%- endif %})
        {%- else %}

    @property
    def {{ field.name }}(self):
        return {{ field.python_type }}.from_cpp(self._instance.mutable_{{ field.name }}())
        {%- endif -%}
    {%- endfor %}
{%- endfor %}
"""


message_pyx_template = Template(MESSAGE_PYX_TEMPLATE)
