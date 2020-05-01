# flake8: noqa E501
from jinja2 import Template


EXTERNS_PXD_TEMPLATE_SOURCE = """\
# cython: language_level=3
# distutils: language = c++

{%- for import in file.imports %}
from {{ import.module.externs_module }} cimport {{ import.symbol }}
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
        {{ field.const_reference }} {{ field.name }}({%- if field.repeated -%}int) except +{%- else -%}){%- endif -%}
        {%- if field.field_type.name == 'message' %}
        {{ field.cpp_type }}* mutable_{{ field.name }}({%- if field.repeated -%}int) except +{%- else -%}){%- endif -%}
        {%- endif -%}
        {%- if field.settable %}
        void set_{{ field.name }}({%- if field.repeated -%}int, {% endif -%}{{ field.const_reference }}) except +
        {%- endif %}
        {%- if field.repeated %}
        size_t {{ field.name }}_size() const
            {%- if field.field_type.name == 'message' %}
        {{ field.cpp_type }}* add_{{ field.name }}()
            {%- endif -%}
            {%- if field.settable %}
        void add_{{ field.name }}({{ field.const_reference }}) except +
            {%- endif %}
        {%- elif field.field_type.name == 'message' and not field.is_map %}
        bint has_{{ field.name }}() const;
        {%- endif -%}
    {%- endfor -%}
{%- endfor %}
"""


externs_pxd_template = Template(EXTERNS_PXD_TEMPLATE_SOURCE)


MESSAGE_PXD_TEMPLATE = """\
# cython: language_level=3
# distutils: language = c++

from cytobuf.protobuf.message cimport Message
{%- for cdef_enum in file.enums %}
from {{ file.module.externs_module }} cimport {{ cdef_enum.name }} as Cpp{{ cdef_enum.name }}
{%- endfor %}
{%- for cdef_class in file.classes %}
from {{ file.module.externs_module }} cimport {{ cdef_class.name }} as Cpp{{ cdef_class.name }}
{%- endfor %}

{%- for enum in file.enums %}

cpdef enum {{ enum.name }}:
{%- for value in enum.value_names %}
    {{ value }} = Cpp{{ enum.name }}.{{ enum.name }}_{{ value }},
{%- endfor %}
{%- endfor %}

{%- for cdef_class in file.classes %}

    {%- for field in cdef_class.fields if field.repeated or field.is_map %}

cdef class __{{ cdef_class.name }}__{{ field.name }}__container:
    cdef Cpp{{ cdef_class.name }}* _instance
    {%- endfor %}

cdef class {{ cdef_class.name }}(Message):
    {%- for field in cdef_class.fields if field.repeated or field.is_map %}
    cdef readonly __{{ cdef_class.name }}__{{ field.name }}__container {{ field.name }}
    {%- endfor %}
    cdef Cpp{{ cdef_class.name }}* _message(self)

    @staticmethod
    cdef from_cpp(Cpp{{ cdef_class.name }}* other)
{%- endfor %}
"""


message_pxd_template = Template(MESSAGE_PXD_TEMPLATE)


MESSAGE_PYX_TEMPLATE = """\
# cython: language_level=3
# distutils: language = c++
# distutils: libraries = protobuf
# distutils: include_dirs = /usr/local/include .
# distutils: library_dirs = /usr/local/lib
# distutils: extra_compile_args= -std=c++11
# distutils: sources = {{ file.cpp_source }}

from cytobuf.protobuf.message cimport Message
{%- for import in file.imports %}
from {{ import.module.cython_module }} cimport {{ import.symbol }}
{%- endfor %}
{%- for cdef_class in file.classes %}
from {{ file.module.externs_module }} cimport {{ cdef_class.name }} as Cpp{{ cdef_class.name }}
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
            yield self._instance.{{ field.name }}(i){{ field.decode_suffix }}
        {%- endif %}

    def __len__(self):
        return self._instance.{{ field.name }}_size()

    def __getitem__(self, key):
        cdef int size, index, start, stop, step
        size = self._instance.{{ field.name }}_size()
        if isinstance(key, int):
            index = key
            if index < 0:
                index = size + index
            if not 0 <= index < size:
                raise IndexError(f"list index ({key}) out of range")
        {%- if field.field_type.name == 'message' %}
            return {{ field.python_type }}.from_cpp(self._instance.mutable_{{ field.name }}(index))
        {%- else %}
            return self._instance.{{ field.name }}(index){{ field.decode_suffix }}
        {%- endif %}
        else:
            start, stop, step = key.indices(size)
            return [
        {%- if field.field_type.name == 'message' %}
                {{ field.python_type }}.from_cpp(self._instance.mutable_{{ field.name }}(index))
        {%- else %}
                self._instance.{{ field.name }}(index){{ field.decode_suffix }}
        {%- endif %}
                for index in range(start, stop, step)
            ]

        {%- if field.field_type.name == 'message' %}

    def add(self):
        return {{ field.python_type }}.from_cpp(self._instance.add_{{ field.name }}())
        {%- else %}

    def add(self, {{ field.python_type }} value):
        self._instance.add_{{ field.name }}(value{{ field.encode_suffix }})
        {%- endif -%}
    {%- endfor %}

    {%- for field in cdef_class.fields if field.is_map %}

cdef class __{{ cdef_class.name }}__{{ field.name }}__container:

    def __iter__(self):
        cdef {{ field.cython_type }} map_instance = self._instance.{{ field.name }}()
        cdef {{ field.cython_type }}.iterator it = map_instance.begin()
        while it != map_instance.end():
            yield dereference(it).first{{ field.key_field.decode_suffix }}
            postincrement(it)

    def items(self):
        cdef {{ field.cython_type }} map_instance = self._instance.{{ field.name }}()
        cdef {{ field.cython_type }}.iterator it = map_instance.begin()
        cdef {{ field.key_field.python_type }} key_value
        while it != map_instance.end():
            key_value = dereference(it).first{{ field.key_field.decode_suffix }}
            {%- if field.value_field.field_type.name == 'message' %}
            yield key_value, {{ field.value_field.python_type }}.from_cpp(&(dereference(it).second))
            {%- else %}
            yield key_value, dereference(it).second{{ field.value_field.decode_suffix }}
            {%- endif %}
            postincrement(it)

    def __len__(self):
        return self._instance.{{ field.name }}().size()

    def __contains__(self, key):
        cdef {{ field.cython_type }} map_instance = self._instance.{{ field.name }}()
        cdef {{ field.key_field.cpp_type }} key_value = key{{ field.key_field.encode_suffix }}
        return map_instance.contains(key_value)

    def __getitem__(self, {{ field.key_field.cython_type }} key):
        cdef {{ field.key_field.cpp_type }} key_value = key{{ field.key_field.encode_suffix }}
        {%- if field.value_field.field_type.name == 'message' %}
        cdef {{ field.cython_type }}* map_instance = self._instance.mutable_{{ field.name }}()
        return {{ field.value_field.python_type }}.from_cpp(&dereference(map_instance)[key_value])
        {%- else %}
        cdef {{ field.cython_type }} map_instance = self._instance.{{ field.name }}()
        return map_instance[key_value]{{ field.value_field.decode_suffix }}
        {%- endif %}

    def __delitem__(self, {{ field.key_field.cython_type }} key):
        cdef {{ field.cython_type }}* map_instance = self._instance.mutable_{{ field.name }}()
        cdef {{ field.key_field.cpp_type }} key_value = key{{ field.key_field.encode_suffix }}
        cdef size_t result
        result = dereference(map_instance).erase(key_value)
        if result == 0:
            raise KeyError(key)

        {%- if field.value_field.field_type.name != 'message' %}
    def __setitem__(self, {{ field.key_field.cython_type }} key, {{ field.value_field.cython_type }} value):
        cdef {{ field.cython_type }}* map_instance = self._instance.mutable_{{ field.name }}()
        cdef {{ field.key_field.cpp_type }} key_value = key{{ field.key_field.encode_suffix }}
        dereference(map_instance)[key_value] = value{{ field.value_field.decode_suffix }}
        {%- endif %}

    {%- endfor %}

cdef class {{ cdef_class.name }}(Message):

    def __cinit__(self, _init = True):
    {%- for field in cdef_class.fields if field.repeated or field.is_map %}
        self.{{ field.name }} = __{{ cdef_class.name }}__{{ field.name }}__container()
    {%- endfor %}
        if _init:
            instance = new Cpp{{ cdef_class.name }}()
    {%- for field in cdef_class.fields if field.repeated or field.is_map %}
            self.{{ field.name }}._instance = instance
    {%- endfor %}
            self._internal = instance

    cdef Cpp{{ cdef_class.name }}* _message(self):
        return <Cpp{{ cdef_class.name }}*>self._internal

    @staticmethod
    cdef from_cpp(Cpp{{ cdef_class.name }}* other):
        result = {{ cdef_class.name }}(_init=False)
        result._internal = other   
    {%- for field in cdef_class.fields if field.repeated or field.is_map %}
        result.{{ field.name }}._instance = other
    {%- endfor %}
        return result
        
    {%- for map_field in cdef_class.fields if map_field.is_map %}
    {%- endfor %}

    {%- for field in cdef_class.fields if not field.repeated and not field.is_map %}
        {%- if field.field_type.name == 'scalar' %}

    @property
    def {{ field.name }}(self):
        return self._message().{{ field.name }}(){{ field.decode_suffix }}

    @{{ field.name }}.setter
    def {{ field.name }}(self, {{ field.cython_type }} value):
        self._message().set_{{ field.name }}(value{{ field.encode_suffix }})
        {%- else %}

    @property
    def {{ field.name }}(self):
        return {{ field.python_type }}.from_cpp(self._instance.mutable_{{ field.name }}())
        {%- endif %}

    @{{ field.name }}.deleter
    def {{ field.name }}(self):
        self._message().clear_{{ field.name }}()
    {%- endfor %}
{%- endfor %}
"""


message_pyx_template = Template(MESSAGE_PYX_TEMPLATE)


PY_MODULE_TEMPLATE = """\
{%- for import in file.imports if import.module.proto_module %}
from {{ import.module.python_module }} import {{ import.symbol }}
{%- endfor %}
{%- for enum in file.enums %}
from {{ file.module.cython_module }} import {{ enum.name }} as {{ enum.name }}
{%- endfor %}
{%- for class in file.classes %}
from {{ file.module.cython_module }} import {{ class.name }} as _Cy_{{ class.name }}
{%- endfor %}

{%- for class in file.classes %}
    {%- if class.nested_names %}

class {{ class.name }}(_Cy_{{ class.name }}):
        {%- for name in class.nested_names %}
    {{ name.name }} = {{ name }}
        {%- endfor %}
    {%- else %}

{{ class.name }} = _Cy_{{ class.name }}
    {%- endif %}
{%- endfor %}

{%- for enum in file.enums if not enum.exported %}
del {{ enum.name }}
{%- endfor %}
{%- for class in file.classes %}
del _Cy_{{ class.name }}
     {%- if not class.nested_names and not class.exported %}
del {{ class.name }}
     {%- endif %}
{%- endfor %}
{%- for import in file.imports if import.module.proto_module %}
del {{ import.symbol }}
{%- endfor %}

__all__ = (
{%- for enum in file.enums if enum.exported %}
    '{{ enum.name }}',
{%- endfor %}
{%- for class in file.classes if class.exported %}
    '{{ class.name }}',
{%- endfor %}
)
"""


py_module_template = Template(PY_MODULE_TEMPLATE)


SETUP_PY_TEMPLATE = """\
from setuptools import find_packages
from setuptools import setup
from Cython.Build import cythonize


EXTENSIONS = cythonize(
    [
{%- for proto_file in files %}
        '{{ proto_file.pyx_filename }}',
{%- endfor %}
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


setup_py_template = Template(SETUP_PY_TEMPLATE)
