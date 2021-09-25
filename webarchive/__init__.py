"""Module for reading Apple's webarchive format.

A webarchive stores a complete web page -- including external media like
images, scripts, and style sheets -- in a single file. It is most notable
as the default format for the Safari browser's "Save As" command, though
other Apple software also uses it for various purposes.

Media in the archive, called "resources", are indexed by URL. A webarchive
may include resources of any type, including nested webarchives for HTML
frames. Archived content is byte-for-byte identical to the original source.

pywebarchive's primary function is to "extract" webarchives by converting
them to standard HTML documents, so their content can be viewed in non-
Apple browsers. However, it can also be used to examine archives directly.

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
