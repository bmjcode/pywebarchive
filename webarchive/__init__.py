"""Module for reading Apple's webarchive format.

Webarchive is the default format for the "Save As" command in Apple's
Safari browser. (Other Apple software also uses it internally for various
purposes.) Its main advantage is that it can save all the content on a
webpage -- including external media like images, scripts, and style
sheets -- in a single file. This module allows non-Apple applications
to read the webarchive format, which is proprietary and not publicly
documented, and to convert webarchive files to standard HTML pages that
can be opened in any browser or editor.

To get started, use webarchive.open() on a webarchive file, like so:

>>> import webarchive
>>> with webarchive.open("example.webarchive") as archive:
...     # Convert this file to a standard HTML page
...     archive.extract("example.html")

For details on the file format and other available operations, see the
documentation for the WebArchive class.
"""

from .webarchive import WebArchive
from .webresource import WebResource
from .exceptions import WebArchiveError

__version__ = "0.5.1"

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
