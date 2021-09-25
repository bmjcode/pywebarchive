"""WebResource class implementation."""

from base64 import b64encode

from .util import process_style_sheet


__all__ = ["WebResource"]


class WebResource(object):
    """An individual resource within a WebArchive.

    A WebResource stores a particular media file's content, as well as
    metadata such as its original URL, MIME type, and text encoding (if
    applicable). Check the list of data descriptors below for details.

    You can access a WebResource's content using its "data" property, or
    by converting it to bytes. If the MIME type indicates it is a text
    resource, you can also use str() to convert it to a string using its
    specified text encoding. All of these return its content verbatim.

    WebResource objects are created and managed by their parent WebArchive;
    applications should not attempt to create them directly.
    """

    # WebResourceData
    # WebResourceMIMEType
    # WebResourceTextEncodingName
    # WebResourceURL
    # WebResourceFrameName

    __slots__ = ["_archive", "_data", "_mime_type", "_url",
                 "_text_encoding", "_frame_name"]

    def __init__(self, archive, plist_data):
        """Return a new WebResource object."""

        # The parent WebArchive
        self._archive = archive

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
        """Return this resource's data as bytes.

        The data is returned verbatim as it is stored in the archive.
        """

        return bytes(self._data)

    def __str__(self):
        """Return this resource's data as a printable string.

        This is only available for text resources (i.e., those whose MIME
        type starts with "text/"), and will raise a TypeError for other
        resources that cannot be reliably converted to strings.

        The content is returned verbatim as it is stored in the archive,
        in the encoding specified by this resource's text_encoding property.
        """

        if self.mime_type.startswith("text/"):
            return str(self._data, encoding=self._text_encoding)

        else:
            raise TypeError("cannot convert non-text resource to str")

    def to_data_uri(self):
        """Return this resource's content formatted as a data URI.

        If this is an HTML or CSS resource, other resources in the parent
        archive will be embedded using nested data URIs.
        """

        if self.url == self.archive.main_resource.url:
            # This is the archive's main resource.
            # Embed subresources recursively using data URIs.
            #
            # N.B. Comparing the URL is the quickest way to check this, but
            # assumes a well-formed webarchive where the URL field is unique.
            data = bytes(self.archive.to_html(), encoding=self._text_encoding)

        elif self.mime_type == "text/css":
            # This is a style sheet.
            # Embed external content recursively using data URIs.
            content = process_style_sheet(self)
            data = bytes(content, encoding=self._text_encoding)

        else:
            data = self._data

        url_data = str(b64encode(data), encoding="ascii")
        return "data:{0};base64,{1}".format(self.mime_type, url_data)

    @property
    def archive(self):
        """This resource's parent WebArchive."""

        return self._archive

    @property
    def data(self):
        """This resource's data."""

        return self._data

    @property
    def mime_type(self):
        """The MIME type of this resource's data."""

        return self._mime_type

    @property
    def url(self):
        """The original URL of this resource."""

        return self._url

    @property
    def text_encoding(self):
        """The text encoding of this resource's data."""

        return self._text_encoding

    @property
    def frame_name(self):
        """This resource's frame name."""

        return self._frame_name
