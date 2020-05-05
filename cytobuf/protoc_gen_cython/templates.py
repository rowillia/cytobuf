# flake8: noqa E501
from jinja2 import Template

from cytobuf.protoc_gen_cython.constants import DEFAULT_INCLUDE_DIRECTORY
from cytobuf.protoc_gen_cython.constants import DEFAULT_LIBRARY_DIRECTORY

PYX_HEADER = f"""\
# cython: language_level=3
# distutils: language = c++
# distutils: libraries = protobuf
# distutils: include_dirs = {DEFAULT_INCLUDE_DIRECTORY} .
# distutils: library_dirs = {DEFAULT_LIBRARY_DIRECTORY}
# distutils: extra_compile_args= -std=c++11
"""


MESSAGE_PXD_TEMPLATE = """\
# cython: language_level=3
# distutils: language = c++
cimport cytobuf.protobuf.common
cimport cytobuf.protobuf.message

{%- for import in file.imports if not import.module.pure_python_module %}
{{ import.cython_import }}
{%- endfor %}

{% if file.enums or file.classes %}
cdef extern from "{{ file.cpp_header }}" namespace "{{ file.namespace | join("::") }}":
{%- endif %}

{%- for enum in file.enums %}

    cpdef enum {{ enum.name.name }}:
    {%- for value in enum.value_names %}
        {{ value.name }},
    {%- endfor %}
{%- endfor %}

{%- for cdef_class in file.classes %}

    cdef cppclass {{ cdef_class.name.name }}(cytobuf.protobuf.common.Message):
        {{ cdef_class.name.name }}()
    {%- for field in cdef_class.fields %}
        void clear_{{ field.cpp_name }}()
        {{ field.const_reference(file.module) }} {{ field.cpp_name }}({%- if field.repeated -%}int) except +{%- else -%}){%- endif -%}
        {%- if field.field_type.name == 'message' %}
        {{ field.local_cpp_type(file.module) }}* mutable_{{ field.cpp_name }}({%- if field.repeated -%}int) except +{%- else -%}){%- endif -%}
        {%- endif -%}
        {%- if field.settable %}
        void set_{{ field.cpp_name }}({%- if field.repeated -%}int, {% endif -%}{{ field.const_reference(file.module) }}) except +
        {%- endif %}
        {%- if field.repeated %}
        size_t {{ field.cpp_name }}_size() const
            {%- if field.field_type.name == 'message' %}
        {{ field.local_cpp_type(file.module) }}* add_{{ field.cpp_name }}()
            {%- endif -%}
            {%- if field.settable %}
        void add_{{ field.cpp_name }}({{ field.const_reference(file.module) }}) except +
            {%- endif %}
        {%- elif field.field_type.name == 'message' and not field.is_map %}
        bint has_{{ field.cpp_name }}() const;
        {%- endif -%}
    {%- endfor %}
{%- endfor %}

{%- for cdef_class in file.classes %}

    {%- for field in cdef_class.fields if field.repeated or field.is_map %}

cdef class __{{ cdef_class.name }}__{{ field.name }}__container:
    cdef {{ cdef_class.name.name }}* _instance
    {%- endfor %}

cdef class {{ cdef_class.name }}(cytobuf.protobuf.message.Message):
    {%- for field in cdef_class.fields if field.repeated or field.is_map %}
    cdef readonly __{{ cdef_class.name }}__{{ field.name }}__container {{ field.name }}
    {%- endfor %}
    cdef {{ cdef_class.name.name }}* _message(self)

    @staticmethod
    cdef from_cpp({{ cdef_class.name.name }}* other)
{%- endfor %}
"""


message_pxd_template = Template(MESSAGE_PXD_TEMPLATE)


MESSAGE_PYX_TEMPLATE = (
    PYX_HEADER
    + """\

cimport cytobuf.protobuf.message
{%- for import in file.imports %}
{{ import.cython_import }}
{%- endfor %}

{%- for cdef_class in file.classes %}
    {%- for field in cdef_class.fields if field.repeated %}

cdef class __{{ cdef_class.name }}__{{ field.name }}__container:

    def __iter__(self):
        cdef size_t i
        for i in range(self._instance.{{ field.cpp_name }}_size()):
        {%- if field.field_type.name == 'message' %}
            yield {{ field.python_type }}.from_cpp(self._instance.mutable_{{ field.cpp_name }}(i))
        {%- else %}
            yield {{ field.decode_function }}(self._instance.{{ field.cpp_name }}(i))
        {%- endif %}

    def __len__(self):
        return self._instance.{{ field.cpp_name }}_size()

    def __getitem__(self, key):
        cdef size_t size, index
        cdef int start, stop, step
        size = self._instance.{{ field.cpp_name }}_size()
        if isinstance(key, int):
            if key < 0:
                index = size + key
            else:
                index = key
            if not 0 <= index < size:
                raise IndexError(f"list index ({key}) out of range")
        {%- if field.field_type.name == 'message' %}
            return {{ field.python_type }}.from_cpp(self._instance.mutable_{{ field.cpp_name }}(index))
        {%- else %}
            return {{ field.decode_function }}(self._instance.{{ field.cpp_name }}(index))
        {%- endif %}
        else:
            start, stop, step = key.indices(size)
            return [
        {%- if field.field_type.name == 'message' %}
                {{ field.python_type }}.from_cpp(self._instance.mutable_{{ field.cpp_name }}(index))
        {%- else %}
                {{ field.decode_function }}(self._instance.{{ field.cpp_name }}(index))
        {%- endif %}
                for index in range(start, stop, step)
            ]

        {%- if field.field_type.name == 'message' %}

    def add(self):
        return {{ field.python_type }}.from_cpp(self._instance.add_{{ field.cpp_name }}())
        {%- else %}

    def add(self, {{ field.local_cython_type(file.module) }} value):
        self._instance.add_{{ field.cpp_name }}(value{{ field.encode_suffix }})
        {%- endif -%}
    {%- endfor %}

    {%- for field in cdef_class.fields if field.is_map %}

cdef class __{{ cdef_class.name }}__{{ field.name }}__container:

    def __iter__(self):
        cdef {{ field.local_cpp_type(file.module) }} map_instance = self._instance.{{ field.cpp_name }}()
        cdef {{ field.local_cpp_type(file.module) }}.iterator it = map_instance.begin()
        while it != map_instance.end():
            yield {{ field.key_field.decode_function }}({{ field.decode_function }}(dereference(it).first))
            postincrement(it)

    def items(self):
        cdef {{ field.local_cpp_type(file.module) }} map_instance = self._instance.{{ field.cpp_name }}()
        cdef {{ field.local_cpp_type(file.module) }}.iterator it = map_instance.begin()
        cdef {{ field.key_field.local_cython_type(file.module) }} key_value
        while it != map_instance.end():
            key_value = {{ field.key_field.decode_function }}({{ field.decode_function }}(dereference(it).first))
            {%- if field.value_field.field_type.name == 'message' %}
            yield key_value, {{ field.value_field.python_type }}.from_cpp(&(dereference(it).second))
            {%- else %}
            yield key_value, {{ field.decode_function }}(dereference(it).second)
            {%- endif %}
            postincrement(it)

    def __len__(self):
        return self._instance.{{ field.cpp_name }}().size()

    def __contains__(self, {{ field.key_field.local_cython_type(file.module) }} key):
        cdef {{ field.local_cpp_type(file.module) }} map_instance = self._instance.{{ field.cpp_name }}()
        cdef {{ field.key_field.local_cpp_type(file.module) }} key_value = key{{ field.key_field.encode_suffix }}
        return map_instance.contains(key_value)

    def __getitem__(self, {{ field.key_field.local_cython_type(file.module) }} key):
        cdef {{ field.key_field.local_cpp_type(file.module) }} key_value = key{{ field.key_field.encode_suffix }}
        {%- if field.value_field.field_type.name == 'message' %}
        cdef {{ field.local_cpp_type(file.module) }}* map_instance = self._instance.mutable_{{ field.cpp_name }}()
        return {{ field.value_field.python_type }}.from_cpp(&dereference(map_instance)[key_value])
        {%- else %}
        cdef {{ field.local_cpp_type(file.module) }} map_instance = self._instance.{{ field.cpp_name }}()
        return {{ field.value_field.decode_function }}(map_instance[key_value])
        {%- endif %}

    def __delitem__(self, {{ field.key_field.local_cython_type(file.module) }} key):
        cdef {{ field.local_cpp_type(file.module) }}* map_instance = self._instance.mutable_{{ field.cpp_name }}()
        cdef {{ field.key_field.local_cpp_type(file.module) }} key_value = key{{ field.key_field.encode_suffix }}
        cdef size_t result
        result = dereference(map_instance).erase(key_value)
        if result == 0:
            raise KeyError(key)

        {%- if field.value_field.field_type.name != 'message' %}
    def __setitem__(self, {{ field.key_field.local_cython_type(file.module) }} key, {{ field.value_field.local_cpp_type(file.module) }} value):
        cdef {{ field.local_cpp_type(file.module) }}* map_instance = self._instance.mutable_{{ field.cpp_name }}()
        cdef {{ field.key_field.local_cpp_type(file.module) }} key_value = key{{ field.key_field.encode_suffix }}
        dereference(map_instance)[key_value] = {{ field.value_field.decode_function }}(value)
        {%- endif %}

    {%- endfor %}

cdef class {{ cdef_class.name }}(cytobuf.protobuf.message.Message):

    def __cinit__(self, _init = True):
    {%- for field in cdef_class.fields if field.repeated or field.is_map %}
        self.{{ field.name }} = __{{ cdef_class.name }}__{{ field.name }}__container()
    {%- endfor %}
        if _init:
            instance = new {{ cdef_class.name.name }}()
    {%- for field in cdef_class.fields if field.repeated or field.is_map %}
            self.{{ field.name }}._instance = instance
    {%- endfor %}
            self._internal = instance

    cdef {{ cdef_class.name.name }}* _message(self):
        return <{{ cdef_class.name.name }}*>self._internal

    @staticmethod
    cdef from_cpp({{ cdef_class.name.name }}* other):
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
        return {{ field.decode_function }}(self._message().{{ field.cpp_name }}())

    @{{ field.name }}.setter
    def {{ field.name }}(self, {{ field.local_cython_type(file.module) }} value):
        self._message().set_{{ field.cpp_name }}(value{{ field.encode_suffix }})
        {%- else %}

    @property
    def {{ field.name }}(self):
        return {{ field.python_type }}.from_cpp(self._message().mutable_{{ field.cpp_name }}())
        {%- endif %}

    @{{ field.name }}.deleter
    def {{ field.name }}(self):
        self._message().clear_{{ field.cpp_name }}()
    {%- endfor %}
{%- endfor %}
"""
)


message_pyx_template = Template(MESSAGE_PYX_TEMPLATE)


PY_ENUM_TEMPLATE = """\
from enum import Enum

{%- for enum in file.enums %}

class {{ enum.name }}(Enum):
    {%- for value in enum.value_names %}
    {{ value.name.fully_unwrapped }} = {{ value.number }}
    {%- endfor %}
{%- endfor %}
"""


py_enum_template = Template(PY_ENUM_TEMPLATE)


PY_MODULE_TEMPLATE = """\
import _merged_cython_protos
{%- for class in file.classes %}
from {{ file.module.cython_module }} import {{ class.name }} as _cy_{{ class.name }}
{%- endfor %}
{%- for enum in file.enums %}
from {{ file.module.enum_module.python_module }} import {{ enum.name }} as _cy_{{ enum.name }}
{%- endfor %}

{%- for enum in file.enums if enum.exported %}
{{ enum.name.name }} = _cy_{{ enum.name }}
{%- endfor %}

{%- for class in file.classes if class.exported %}
    {%- if class.nested_names %}

class {{ class.name.name }}(_cy_{{ class.name }}):
        {%- for name in class.nested_names %}
    {{ name.fully_unwrapped }} = _cy_{{ name }}
        {%- endfor %}
    {%- else %}

{{ class.name.name }} = _cy_{{ class.name }}
    {%- endif %}
{%- endfor %}

{%- for enum in file.enums %}
del _cy_{{ enum.name }}
{%- endfor %}
{%- for class in file.classes %}
del _cy_{{ class.name }}
{%- endfor %}
del _merged_cython_protos

__all__ = (
{%- for enum in file.enums if enum.exported %}
    '{{ enum.fully_unwrapped }}',
{%- endfor %}
{%- for class in file.classes if class.exported %}
    '{{ class.name.fully_unwrapped }}',
{%- endfor %}
)
"""


py_module_template = Template(PY_MODULE_TEMPLATE)


SETUP_PY_TEMPLATE = """\
import multiprocessing
from setuptools import find_packages
from setuptools import setup
from Cython.Build import cythonize


EXTENSIONS = cythonize(
    [
{%- for pyx_file in pyx_files %}
        '{{ pyx_file }}',
{%- endfor %}
    ],
    language_level="3",
    nthreads=multiprocessing.cpu_count(),
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


MERGED_PYX_MODULE_TEMLATE = (
    PYX_HEADER
    + """\
# distutils: sources = {{ files|map(attribute='cpp_source')|join(' ') }}
    """
)

merged_pyx_template = Template(MERGED_PYX_MODULE_TEMLATE)
