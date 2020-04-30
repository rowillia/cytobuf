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

    {%- for field in cdef_class.fields if field.repeated %}

cdef class __{{ cdef_class.name }}__{{ field.name }}__container:
    cdef Cpp{{ cdef_class.name }}* _instance
    {%- endfor %}

cdef class {{ cdef_class.name }}(Message):
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
            yield self._instance.{{ field.name }}(i)
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
            return self._instance.{{ field.name }}(key)
        {%- endif %}
        else:
            start, stop, step = key.indices(size)
            return [
        {%- if field.field_type.name == 'message' %}
                {{ field.python_type }}.from_cpp(self._instance.mutable_{{ field.name }}(index))
        {%- else %}
                self._instance.{{ field.name }}(index)
        {%- endif %}
                for index in range(start, stop, step)
            ]

        {%- if field.field_type.name == 'message' %}

    def add(self):
        return {{ field.python_type }}.from_cpp(self._instance.add_{{ field.name }}())
        {%- else -%}

    def add(self, value):
        self._instance.add_{{ field.name }}(value)
        {%- endif -%}
    {%- endfor %}

cdef class {{ cdef_class.name }}(Message):

    def __cinit__(self, _init = True):
    {%- for field in cdef_class.fields if field.repeated %}
        self.{{ field.name }} = __{{ cdef_class.name }}__{{ field.name }}__container()
    {%- endfor %}
        if _init:
            instance = new Cpp{{ cdef_class.name }}()
    {%- for field in cdef_class.fields if field.repeated %}
            self.{{ field.name }}._instance = instance
    {%- endfor %}
            self._internal = instance

    cdef Cpp{{ cdef_class.name }}* _message(self):
        return <Cpp{{ cdef_class.name }}*>self._internal

    @staticmethod
    cdef from_cpp(Cpp{{ cdef_class.name }}* other):
        result = {{ cdef_class.name }}(_init=False)
        result._internal = other   
    {%- for field in cdef_class.fields if field.repeated %}
        result.{{ field.name }}._instance = other
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
        {%- endif %}

    @{{ field.name }}.deleter
    def {{ field.name }}(self):
        self._message().clear_{{ field.name }}()
        {%- else %}
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
