#!/usr/bin/env python3

"""Module for reading Apple's .webarchive files.

pywebarchive is a Python module for reading Apple's .webarchive files.
It consists of two main classes:

  * WebArchive, to read .webarchive files
  * Extractor, to extract a WebArchive to a standard HTML document

Individual resources (i.e., files) in a WebArchive are represented by
WebResource objects.

Example usage:

    from webarchive import WebArchive, Extractor

    archive = WebArchive("example.webarchive")

    extractor = Extractor(archive)
    extractor.extract("example.html")
"""

import os
import sys

from .extractor import Extractor
from .webarchive import WebArchive
from .webresource import WebResource

__all__ = ["Extractor", "WebArchive", "WebResource"]
