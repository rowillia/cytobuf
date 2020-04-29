from Cython.Build import cythonize
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
    packages=find_packages(),
    ext_modules=cythonize(["cytobuf/protobuf/message.pyx"], language_level="3"),
    include_package_data=True,
    install_requires=["protobuf", "jinja2", "cython"],
    entry_points={"console_scripts": ["protoc-gen-cython = cytobuf.protoc_gen_cython:main"]},
    zip_safe=False,
)
