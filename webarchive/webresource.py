"""WebResource class implementation."""

import io
from base64 import b64encode

from . import util
from .exceptions import WebArchiveError


__all__ = ["WebResource"]


class WebResource(object):
    """An individual resource within a webarchive.

    A webresource consists of the following elements:

      * The resource's data (required). This is a bytes field storing
        its verbatim content as received from the original web server.

      * The resource's MIME type (required).

      * The absolute URL of this resource's source (required).

      * The resource's text encoding (optional). This is only present
        for plain-text resources, as defined below; if the archive did
        not specify an encoding for this resource, it defaults to UTF-8.

      * The resource's frame name (optional). This is only present if
        the resource is a webpage displayed in an HTML frame.

    You can examine these resource using this class's properties.
    To retrieve a resource's data, you can also convert it to bytes,
    which is equivalent to using its data property.

    A plain-text resource is one whose MIME type is text/plain, or
    whose data can be losslessly presented as that type (this includes
    HTML and CSS code). The quickest way to access a plain-text
    resource's content is to convert it to str; this automatically
    uses the resource's specified text encoding.

    Note: WebResource objects are created and managed by a parent
    WebArchive; applications should not attempt to create them directly.
    """

    __slots__ = ["_archive", "_data", "_mime_type", "_url",
                 "_text_encoding", "_frame_name"]

    def __init__(self, archive, data, mime_type, url,
                 text_encoding=None, frame_name=None):
        """Return a new WebResource object.

        Note WebResources are created and managed by a parent WebArchive.
        Applications should not attempt to instantiate this class directly,
        since the constructor arguments may change in a future release.
        """

        # The parent WebArchive
        self._archive = archive

        # Ensure an encoding is always specified for text resources
        is_text = util.is_text_mime_type(mime_type)
        if is_text and not text_encoding:
            text_encoding = "utf-8"

        # This resource's data
        if isinstance(data, str):
            if is_text:
                self._data = bytes(data, encoding=text_encoding)
            else:
                raise WebArchiveError(
                    "MIME type '{0}' does not support text data"
                    .format(mime_type)
                )
        else:
            self._data = data

        # Other required attributes
        self._mime_type = mime_type
        self._url = url

        # Optional attributes
        self._text_encoding = text_encoding
        self._frame_name = frame_name

    def __bytes__(self):
        """Return this resource's data as bytes."""

        return bytes(self._data)

    def __str__(self):
        """Return this resource's data as a printable string.

        This is only available for plain-text resources; attempting
        to convert non-text resources to str will raise a TypeError.

        The returned string will use the encoding specified by this
        resource's text_encoding property.
        """

        if util.is_text_mime_type(self._mime_type):
            return str(self._data, encoding=self._text_encoding)

        else:
            raise TypeError("cannot convert non-text resource to str")

    def to_data_uri(self):
        """Return this resource's content formatted as a data URI.

        If this is an HTML or CSS resource, other resources in the parent
        archive will be embedded using nested data URIs.
        """

        # Since URLs are unique by definition, comparing them is the
        # fastest way to do this check.
        if self._url == self._archive._main_resource._url:
            # This is the archive's main resource.
            # Embed subresources recursively using data URIs.
            data = bytes(self._archive.to_html(),
                         encoding=self._text_encoding)

        elif self._mime_type == "text/css":
            # This is a style sheet.
            # Embed external content recursively using data URIs.
            buffer = io.StringIO()
            util.process_css_resource(self, buffer)
            data = bytes(buffer.getvalue(), encoding=self._text_encoding)

        else:
            data = self._data

        url_data = str(b64encode(data), encoding="ascii")
        return "data:{0};base64,{1}".format(self._mime_type, url_data)

    @classmethod
    def _create_from_plist_data(cls, plist_data, archive):
        """Create a WebResource object using parsed data from plistlib."""

        # Note the argument order was originally (plist_data, archive).
        # I find this order more natural, but changed it for consistency
        # with WebArchive's method of the same name, where the parent
        # argument is optional and thus must come later. My reason for
        # doing so is to reduce confusion if either method is made public
        # in a future release.

        # Property names:
        #   - WebResourceData
        #   - WebResourceMIMEType
        #   - WebResourceTextEncodingName
        #   - WebResourceURL
        #   - WebResourceFrameName

        data = plist_data["WebResourceData"]
        mime_type = plist_data["WebResourceMIMEType"]
        url = plist_data["WebResourceURL"]

        res = cls(archive, data, mime_type, url)

        # Text encoding (not present for all WebResources)
        if "WebResourceTextEncodingName" in plist_data:
            res._text_encoding = plist_data["WebResourceTextEncodingName"]
            res._text_encoding = res._text_encoding.lower()
        elif res._mime_type.startswith("text/"):
            # Fall back on UTF-8 for text resources
            res._text_encoding = "utf-8"

        # Frame name (not present for all WebResources)
        if "WebResourceFrameName" in plist_data:
            res._frame_name = plist_data["WebResourceFrameName"]

        return res

    @property
    def archive(self):
        """This resource's parent WebArchive.

        Note this property is not part of the webarchive format itself,
        but rather is provided by pywebarchive as a convenience.
        """

        return self._archive

    @property
    def data(self):
        """This resource's data.

        This always returns a bytes object containing raw binary data,
        and is equivalent to converting this resource to bytes.

        If this is a plain-text resource, an easier way to access its
        content is to convert this object to a str.
        """

        return self._data

    @property
    def mime_type(self):
        """The MIME type of this resource's data."""

        return self._mime_type

    @property
    def url(self):
        """The absolute URL of this resource's source."""

        return self._url

    @property
    def text_encoding(self):
        """The text encoding of this resource's data.

        This is only set for plain-text resources. If the parent
        archive did not specify an encoding for this resource, it
        defaults to UTF-8.
        """

        return self._text_encoding

    @property
    def frame_name(self):
        """This resource's frame name.

        If this resource is a webpage displayed in an HTML frame,
        this gives the value of the frame tag's name attribute.
        Otherwise, it is not set.
        """

        return self._frame_name
