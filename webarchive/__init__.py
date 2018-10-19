#!/usr/bin/env python3

"""Module for reading Apple's .webarchive files.

pywebarchive is a Python module for reading Apple's .webarchive files
and extracting their contents to standard HTML documents.

Example usage:

    from webarchive import WebArchive
    archive = WebArchive("example.webarchive")
    archive.extract("example.html")
"""

import os
import sys

from .extractor import Extractor
from .webarchive import WebArchive
from .webresource import WebResource

__all__ = ["Extractor", "WebArchive", "WebResource"]
