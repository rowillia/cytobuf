from setuptools import find_packages
from setuptools import setup
from Cython.Build import cythonize


setup(
    name="cytobuf",
    version="0.1",
    description="Generate cython bindings for protobuf",
    keywords="cython proto protobuf cytobuf lyft",
    author="Roy Williams",
    author_email="roy@lyft.com",
    url="https://github.com/rowillia/protoc-gen-cython",
    packages=find_packages(),
    ext_modules=cythonize(["cytobuf/protobuf/message.pyx"]),
    include_package_data=True,
    setup_requires=["cython"],
    install_requires=["protobuf", "jinja2"],
    entry_points={"console_scripts": ["protoc-gen-cython = cytobuf.protoc_gen_cython:main"]},
    zip_safe=False,
)
