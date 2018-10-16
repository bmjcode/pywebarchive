#!/usr/bin/env python3

from setuptools import setup, find_packages

NAME = "pywebarchive"
VERSION = "0.1.0"
AUTHOR = "Benjamin Johnson"
AUTHOR_EMAIL = "bmjcode@gmail.com"
DESCRIPTION = "Module for reading Apple's .webarchive files"

with open("README.md", "r") as readme:
    LONG_DESCRIPTION = readme.read()

LONG_DESCRIPTION_CONTENT_TYPE = "text/markdown"
URL = "https://github.com/bmjcode/pywebarchive"
PACKAGES = find_packages()
CLASSIFIERS = [
    "Development Status :: 2 - Pre-Alpha",
    "Programming Language :: Python :: 3",
    "License :: OSI Approved :: MIT License",
    "Operating System :: OS Independent",
]

ENTRY_POINTS = {
    "console_scripts": [
        "webarchive-extractor = webarchive.extractor:main",
    ],
}

setup(name=NAME,
      version=VERSION,
      author=AUTHOR,
      author_email=AUTHOR_EMAIL,
      description=DESCRIPTION,
      long_description=LONG_DESCRIPTION,
      long_description_content_type=LONG_DESCRIPTION_CONTENT_TYPE,
      url=URL,
      packages=PACKAGES,
      classifiers=CLASSIFIERS,
      entry_points=ENTRY_POINTS)
