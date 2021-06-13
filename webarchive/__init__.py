"""Module for reading Apple's .webarchive files.

pywebarchive is a Python module for reading Apple's .webarchive files
and extracting them to standard HTML documents.

Example usage:

    import webarchive
    archive = webarchive.open("example.webarchive")
    archive.extract("example.html")
"""

from .webarchive import WebArchive
from .webresource import WebResource
from .exceptions import WebArchiveError

__all__ = ["WebArchive", "WebResource", "WebArchiveError"]


# This provides a somewhat more pythonic API than creating a WebArchive
# object directly.
#
# N.B. Do not export this in __all__, since we don't want to clobber
# the builtin of the same name.
def open(path):
    """Open the specified .webarchive file for reading.

    Returns a WebArchive object.
    """

    return WebArchive(path)
