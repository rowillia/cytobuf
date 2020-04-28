from setuptools import find_packages
from setuptools import setup

setup(
    name="cytobuf",
    version="0.1",
    description="Generate cython bindings for protobuf",
    keywords="cython proto protobuf cytobuf lyft",
    author="Roy Williams",
    author_email="roy@lyft.com",
    url="https://github.com/rowillia/protoc-gen-cython",
    packages=find_packages(exclude=["tests*"]),
    install_requires=["protobuf>=3.11.0", "jinja2>=2.11.2"],
    entry_points={"console_scripts": ["protoc-gen-cython = cytobuf.protoc_gen_cython:main"]},
)
