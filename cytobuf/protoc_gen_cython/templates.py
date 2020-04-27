# flake8: noqa E501
from jinja2 import Template


PXD_TEMPLATE_SOURCE = """\
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
        {%- if field.mutable_return_type %}
        {{ field.mutable_return_type }} mutable_{{ field.name }}({%- if field.repeated -%}int index) except +{%- else -%}){%- endif -%}
        {%- endif -%}
        {%- for signature in field.input_signatures %}
        void set_{{ field.name }}({%- if field.repeated -%}int index, {% endif -%}{{ signature.parameters | join(", ") }}) except +
        {%- endfor %}
        {%- if field.repeated %}
        int {{ field.name }}_size() const
            {%- if field.mutable_return_type %}
        {{ field.mutable_return_type }} add_{{ field.name }}()
            {%- endif -%}
            {%- for signature in field.input_signatures %}
        void add_{{ field.name }}({{ signature.parameters | join(", ") }})
            {%- endfor %}
        {% elif field.type == 'message' %}
        bool has_{{ field.name }}() const;
        {%- endif -%}
    {%- endfor -%}
{%- endfor %}
"""


pxd_template = Template(PXD_TEMPLATE_SOURCE)
