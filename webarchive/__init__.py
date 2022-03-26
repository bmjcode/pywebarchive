"""Module for reading Apple's webarchive format.

A webarchive stores a complete web page -- including external media like
images, scripts, and style sheets -- in a single file. It is most notable
as the default format for the Safari browser's "Save As" command, though
other Apple software also uses it for various purposes.

Media in the archive, called "resources", are indexed by URL. A webarchive
may include resources of any type, including nested webarchives for HTML
frames. Archived content is byte-for-byte identical to the original source.

pywebarchive's primary focus is on "extracting" webarchives -- converting
them to standard HTML pages that can be opened in any browser. However, it
also includes an extensive API for examining archives and their resources
directly; see the WebArchive and WebResource class docs for details.

Example usage:

>>> import webarchive
>>> with webarchive.open("example.webarchive") as archive:
...     # Do something with this archive
...     archive.extract("example.html")
"""

from .webarchive import WebArchive
from .webresource import WebResource
from .exceptions import WebArchiveError

__version__ = "0.4.0"

__all__ = [
    "__version__",
    "WebArchive",
    "WebResource",
    "WebArchiveError",
    # Earlier versions of pywebarchive omitted this to avoid clobbering the
    # builtin of the same name, but it's better to expose this so pydoc will
    # see it than to try protecting people who don't check if the modules
    # they are using are "import *"-safe.
    "open",
]

open = WebArchive._open
