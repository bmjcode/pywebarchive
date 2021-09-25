#!/usr/bin/env python3

from setuptools import setup, find_packages

NAME = "pywebarchive"
VERSION = "0.3.1"
AUTHOR = "Benjamin Johnson"
AUTHOR_EMAIL = "bmjcode@gmail.com"
DESCRIPTION = "Module for reading Apple's .webarchive files"

with open("README.md", "r") as readme:
    LONG_DESCRIPTION = readme.read()

URL = "https://github.com/bmjcode/pywebarchive"
PACKAGES = find_packages(exclude="test")
CLASSIFIERS = [
    "Development Status :: 4 - Beta",
    "Programming Language :: Python :: 3",
    "License :: OSI Approved :: MIT License",
    "Operating System :: OS Independent",
]

setup(name=NAME,
      version=VERSION,
      author=AUTHOR,
      author_email=AUTHOR_EMAIL,
      description=DESCRIPTION,
      long_description=LONG_DESCRIPTION,
      long_description_content_type="text/markdown",
      url=URL,
      packages=PACKAGES,
      classifiers=CLASSIFIERS)
