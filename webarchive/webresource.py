#!/usr/bin/env python3

"""WebResource class implementation."""

import os
import sys


__all__ = ["WebResource"]


class WebResource(object):
    """An individual resource within a WebArchive.

    WebResource objects are created by their parent WebArchive as it
    processes the .webarchive file's contents. This class is not meant
    to be instantiated directly by users.
    """

    # WebResourceData
    # WebResourceMIMEType
    # WebResourceTextEncodingName
    # WebResourceURL
    # WebResourceFrameName

    __slots__ = ["_data", "_mime_type", "_url",
                 "_text_encoding", "_frame_name"]

    def __init__(self, plist_data):
        """Return a new WebResource object."""

        # Required attributes
        self._data = plist_data["WebResourceData"]
        self._mime_type = plist_data["WebResourceMIMEType"]
        self._url = plist_data["WebResourceURL"]

        # Text encoding (not present for all WebResources)
        if "WebResourceTextEncodingName" in plist_data:
            self._text_encoding = plist_data["WebResourceTextEncodingName"]
            self._text_encoding = self._text_encoding.lower()

        elif self._mime_type.startswith("text/"):
            # Fall back on UTF-8 for text resources
            self._text_encoding = "utf-8"

        else:
            # No encoding specified or needed
            self._text_encoding = None

        # Frame name (not present for all WebResources)
        if "WebResourceFrameName" in plist_data:
            self._frame_name = plist_data["WebResourceFrameName"]
        else:
            self._frame_name = None

    def __bytes__(self):
        """Return this resource's data as bytes."""

        return bytes(self._data)

    def __str__(self):
        """Return this resource's data as a printable string.

        This is only available for text resources (i.e., those whose MIME
        type starts with "text/"), and will raise a TypeError for other
        resources that cannot be reliably converted to strings.
        """

        if self.mime_type.startswith("text/"):
            return str(self._data, encoding=self._text_encoding)

        else:
            raise TypeError("cannot convert non-text resource to str")

    @property
    def data(self):
        """This resource's data."""

        return self._data

    @property
    def mime_type(self):
        """MIME type of this resource's data."""

        return self._mime_type

    @property
    def url(self):
        """Original URL of this resource."""

        return self._url

    @property
    def text_encoding(self):
        """Text encoding of this resource's data."""

        return self._text_encoding

    @property
    def frame_name(self):
        """This resource's frame name."""

        return self._url
