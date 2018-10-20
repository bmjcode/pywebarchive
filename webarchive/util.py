#!/usr/bin/env python3

"""Utility classes and functions for internal use."""

import os
import sys

from base64 import b64decode
from html import escape
from html.parser import HTMLParser
from urllib.parse import unquote, urlparse, urljoin


__all__ = ["MainResourceProcessor"]


class DataURL(object):
    """Class to process the components of a data URL.

    Usage: data_url = DataURL(urlparse("data:,").path)
    """

    __slots__ = ["mime_type", "charset", "data"]

    def __init__(self, url_path):
        """Return a new DataURL object."""

        # Default values per RFC 2397
        self.mime_type = "text/plain"
        self.charset = "US-ASCII"
        # This is an implementation detail and doesn't need to be exported
        use_base64 = False

        self.data = None

        # Separate the media type and the data
        media_type, raw_data = url_path.split(",", 1)

        # Separate media type fields
        media_type_fields = media_type.split(";")

        # The first field is the MIME type
        self.mime_type = media_type_fields[0]

        # Process remaining fields
        for field in media_type_fields[1:]:
            if "=" in field:
                attr, value = field.split("=", 1)
                if attr == "charset":
                    # Record the character set
                    self.charset = value

        # The base64 extension must come last
        if media_type_fields[-1] == "base64":
            use_base64 = True

        # Decode the raw data
        if use_base64:
            self.data = b64decode(raw_data)

        else:
            self.data = bytes(unquote(raw_data), encoding=self.charset)


class MainResourceProcessor(HTMLParser):
    """Class to process the main resource in the webarchive.

    This class uses HTMLParser to rewrite the main resource's HTML code
    to make changes necessary to render the extracted page:

      * All href and src attributes referring to subresources in the
        archive are changed to point to the local extracted copies.

      * The optional srcset attribute is removed from <img> tags, since
        it causes rendering problems when extracting webarchives saved by
        older versions of Safari that don't support that attribute.
    """

    __slots__ = ["_url", "_root", "_local_paths", "_output"]

    def __init__(self, url, root, local_paths, output):
        """Return a new MainResourceProcessor."""

        HTMLParser.__init__(self, convert_charrefs=False)

        self._url = url
        self._root = root
        self._local_paths = local_paths
        self._output = output

    def handle_starttag(self, tag, attrs):
        """Handle the start of a tag."""

        # Open the tag
        tag_data = ["<", tag]

        # Process attributes
        for attr, value in attrs:
            if tag == "img" and attr == "srcset":
                # Omit the srcset attribute, which is not supported by older
                # versions of Safari (including the obsolete 5.1.7 for Windows,
                # which is the only version I have available to test with).
                continue

            tag_data.append(" ")
            tag_data.append(attr)
            tag_data.append('="')
            tag_data.append(self._process_attr_value(tag, attr, value))
            tag_data.append('"')

        # Close the tag
        tag_data.append(">")

        # If this is the opening <html> tag, indicate that this file
        # has been processed
        if tag == "html":
            tag_data.insert(0, "<!-- Processed by pywebarchive -->\n")

        self._output.write("".join(tag_data))

    def handle_endtag(self, tag):
        """Handle the end of a tag."""

        self._output.write("</{0}>".format(tag))

    def handle_data(self, data):
        """Handle arbitrary data."""

        self._output.write(escape(data, False))

    def handle_entityref(self, name):
        """Handle a named character reference."""

        self._output.write("&{0};".format(name))

    def handle_charref(self, name):
        """Handle a numeric character reference."""

        self._output.write("&#{0};".format(name))

    def handle_comment(self, data):
        """Handle a comment."""

        # Note IE conditional comments potentially can affect rendering
        self._output.write("<!--{0}-->".format(data))

    def handle_decl(self, decl):
        """Handle a doctype declaration."""

        # This should probably be on its own line
        self._output.write("<!{0}>\n".format(decl))

    def _local_path(self, value):
        """Return the local path for resources inside the archive."""

        # Get the absolute URL of the original resource
        abs_url = urljoin(self._url, value)

        if abs_url in self._local_paths:
            # Return the local path to this resource
            return "{0}/{1}".format(self._root, self._local_paths[abs_url])

        else:
            # Return the original value unmodified
            return value

    def _process_attr_value(self, tag, attr, value):
        """Process the value of a tag's attribute."""

        if tag == "a" and attr == "href":
            # Rewrite href's for <a> tags relative to the original URL
            value = urljoin(self._url, value)

        elif tag == "img" and attr == "srcset":
            # Process the HTML5 srcset attribute
            srcset = []
            for item in map(str.strip, value.split(",")):
                src, res = item.split(" ", 1)
                src = self._local_path(src)
                srcset.append("{0} {1}".format(src, res))
        
            value = ", ".join(srcset)

        elif attr in ("href", "src"):
            # Substitute the local path for resources inside the archive
            value = self._local_path(value)

        return escape(value, True)
