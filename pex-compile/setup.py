#!/usr/bin/env python3

from setuptools import setup


setup(
    name                = 'pex_compile',
    version             = '0.0.0',
    description         = 'A program to compile Python files to PEX format for Pyke',
    author              = 'Alexander Korzun',
    author_email        = 'korzun.sas@mail.ru',
    packages            = ['pex_compile'],
    entry_points        = {
        'console_scripts': ['pex-compile=pex_compile.__main__:main'],
    },
    classifiers         = [
        'Development Status :: 1 - Planning',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: Apache Software License',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: Implementation :: CPython',
        'Programming Language :: Python :: 3.7',
        'Topic :: Software Development :: Compilers',
    ]
)
