"""Module for reading Apple's .webarchive files.

pywebarchive is a Python module for reading Apple's webarchive format,
used most notably by the Safari browser to save complete web pages --
including external resources like images, scripts, and style sheets --
in a single file.

Media in the archive (called "resources") are indexed by URL. A webarchive
may include resources of any type, including nested webarchives for HTML
frames. Archived content is byte-for-byte identical to the original source.

pywebarchive can "extract" webarchives by converting them to standard HTML
documents. Because it may not be possible to recreate the archived content's
original URL structure locally, extraction aims to preserve function rather
than byte-identicality, making whatever changes to the code are necessary
for the converted page to display identically to the original.

Alternately, pywebarchive also allows applications to access archived
content directly, preserving byte-identicality.

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
