"""Utility classes and functions for internal use."""

import io
import re

from base64 import b64encode
from html import escape
from html.parser import HTMLParser
from urllib.parse import urljoin

from .exceptions import WebArchiveError


__all__ = ["base64_string", "bytes_to_str",
           "make_data_uri", "process_main_resource", "process_style_sheet"]


# Regular expression matching a URL in a style sheet
RX_STYLE_SHEET_URL = re.compile(r"url\(([^\)]+)\)")


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

    __slots__ = ["_archive", "_output", "_root", "_is_xhtml"]

    def __init__(self, archive, output, root):
        """Return a new MainResourceProcessor."""

        HTMLParser.__init__(self, convert_charrefs=False)

        self._archive = archive
        self._output = output
        self._root = root

        # Identify whether this document is XHTML based on the MIME type
        main_resource = archive.main_resource
        self._is_xhtml = (main_resource.mime_type == "application/xhtml+xml")

    def handle_starttag(self, tag, attrs):
        """Handle a start tag."""

        self._output.write(self._build_starttag(tag, attrs))

    def handle_startendtag(self, tag, attrs):
        """Handle an XHTML-style "empty" start tag."""

        self._output.write(self._build_starttag(tag, attrs, True))

    def handle_endtag(self, tag):
        """Handle an end tag."""

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

        # This caches pre-XHTML5 documents incorrectly served as standard HTML
        if "//DTD XHTML " in decl:
            self._is_xhtml = True

    def _absolute_url(self, url):
        """Return the absolute URL to the specified resource."""

        return urljoin(self._archive.main_resource.url, url)

    def _resource_url(self, orig_url):
        """Return an appropriate URL for the specified resource.

        If the resource exists in this archive, this will be its local path.
        Otherwise, it will be the absolute URL to the original resource.
        """

        # Get the absolute URL of the original resource
        abs_url = self._absolute_url(orig_url)

        try:
            local_path = self._archive.get_local_path(abs_url)
            # Return the local path to this resource
            if self._root:
                return "{0}/{1}".format(self._root, local_path)
            else:
                return local_path

        except (WebArchiveError):
            # Return the absolute URL to this resource
            return abs_url

    def _build_starttag(self, tag, attrs, is_empty=False):
        """Build an HTML start tag."""

        if self._root is None and tag == "link":
            link_href = None
            is_stylesheet = False
            for attr, value in attrs:
                if attr == "rel" and value.lower() == "stylesheet":
                    is_stylesheet = True
                elif attr == "href":
                    link_href = self._absolute_url(value)
            if is_stylesheet:
                # Convert <link rel="stylesheet"> to <style>...</style>
                content = ""
                try:
                    res = self._archive.get_subresource(link_href)
                    subresources = self._archive.subresources
                    # HTML entities in <style> are NOT escaped
                    content = process_style_sheet(res, subresources)
                except (WebArchiveError):
                    pass
                # Bypass the standard logic since we're replacing this
                # with an entirely different tag
                return "<style>{0}</style>".format(content)

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
        if self._is_xhtml and (is_empty or tag in self._VOID_ELEMENTS):
            tag_data.append(" />")
        else:
            tag_data.append(">")

        # If this is the opening <html> tag, indicate that this file
        # has been processed by pywebarchive
        if tag == "html":
            tag_data.insert(0, "<!-- Processed by pywebarchive -->\n")

        return "".join(tag_data)

    def _process_attr_value(self, tag, attr, value):
        """Process the value of a tag's attribute."""

        # NOTE: <link rel="stylesheet"> receives special handling in
        # _build_starttag(), so we do not need to process it here.

        if ((tag == "a" and attr == "href")
            or (tag == "form" and attr == "action")):
            # These always refer to content outside the WebArchive, which
            # only stores a single page and its embedded content
            value = self._absolute_url(value)

        elif (attr == "src"
              or (tag == "link" and attr == "href")):
            if tag in ("frame", "iframe"):
                # Process the src attribute for HTML frames
                if self._root:
                    value = self._resource_url(value)
                else:
                    # Attempt to inline this frame's contents using a data URI
                    try:
                        frame_src = self._absolute_url(value)
                        sf = self._archive.get_subframe_archive(frame_src)
                        mime_type = sf.main_resource.mime_type
                        text_encoding = sf.main_resource.text_encoding
                        data = sf.to_html().encode(encoding=text_encoding)
                        value = make_data_uri(mime_type, data)
                    except (WebArchiveError):
                        # Content is not in this WebArchive
                        pass

            else:
                # Process the src attribute for images, scripts, etc.
                if self._root:
                    value = self._resource_url(value)
                else:
                    # Attempt to inline this content using a data URI
                    #
                    # Note that scripts, too, are deliberately inlined using
                    # data URIs, rather than by inserting their content
                    # directly into the <script> block as might seem more
                    # intuitive. This is to avoid difficulties with scripts
                    # containing unescaped HTML tags.
                    try:
                        content_src = self._absolute_url(value)
                        res = self._archive.get_subresource(content_src)
                        value = res.to_data_uri()
                    except (WebArchiveError):
                        # Content is not in this WebArchive
                        pass

        elif attr == "srcset":
            # Process the HTML5 srcset attribute
            srcset = []
            for item in map(str.strip, value.split(",")):
                src, res = item.split(" ", 1)
                src = self._resource_url(src)
                srcset.append("{0} {1}".format(src, res))

            value = ", ".join(srcset)

        return escape(value, True)

    # Valid self-closing tags (formally termed "void elements") in HTML
    # See: http://xahlee.info/js/html5_non-closing_tag.html
    #
    # Python's HTMLParser is supposed to call handle_startendtag() when it
    # encounters such a tag, but in practice this does not always happen.
    # We thus check against this list of known self-closing tags to ensure
    # these are correctly closed when processing XHTML documents.
    _VOID_ELEMENTS = (
        "area", "base", "br", "col", "embed", "hr", "img", "input", "link",
        "meta", "param", "source", "track", "wbr",
        # Obsolete tags
        "command", "keygen", "menuitem"
    )


def base64_string(data, altchars=None):
    """Return data encoded as a base64 string."""
    return bytes_to_str(b64encode(data, altchars))


def bytes_to_str(data):
    """Convert bytes to str."""
    return "".join(map(chr, data))


def make_data_uri(mime_type, data):
    """Return a data URI for the specified content."""

    return "data:{0};base64,{1}".format(mime_type, base64_string(data))


def process_main_resource(archive, output, subresource_dir):
    """Process a webarchive's main WebResource."""

    # Make sure this resource is an appropriate content type
    if not archive.main_resource.mime_type in ("text/html",
                                               "application/xhtml+xml"):
        raise TypeError("res must have mime_type == "
                        "'text/html' or 'application/xhtml+xml'")

    # Feed the content through the MainResourceProcessor to rewrite
    # references to files inside the archive
    mrp = MainResourceProcessor(archive, output, subresource_dir)
    mrp.feed(str(archive.main_resource))


def process_style_sheet(res, subresources, local_paths=None):
    """Process a WebResource containing CSS data.

    If local_paths is specified, any url() value referencing another
    subresource in this webarchive will be replaced with the local path
    of the extracted copy. If no local_paths are specified, references
    to other subresources in this webarchive will be replaced with data
    URIs corresponding to their contents.
    """

    # Make sure this resource is an appropriate content type
    if res.mime_type != "text/css":
        raise TypeError("res must have mime_type == 'text/css'")

    content = str(res)

    # Find URLs in the stylesheet
    matches = RX_STYLE_SHEET_URL.findall(content)
    for match in matches:
        # Remove quote characters, if present, from the URL
        if match.startswith('"') or match.startswith("'"):
            match = match[1:]
        if match.endswith('"') or match.endswith("'"):
            match = match[:-1]

        # Filter out blank URLs; we really shouldn't encounter these
        # in the first place, but they can show up and cause problems
        if not match:
            continue

        # Get the absolute URL of the original resource.
        # Note paths in CSS are relative to the style sheet.
        abs_url = urljoin(res.url, match)

        if local_paths:
            if abs_url in local_paths:
                # Substitute the local path to this resource.
                # Because paths in CSS are relative to the style sheet,
                # and all subresources (like style sheets) are extracted
                # to the same folder, the basename is all we need.
                local_url = local_paths[abs_url]
                content = content.replace(match, local_url)

            else:
                # Substitute the absolute URL of this resource.
                content = content.replace(match, abs_url)

        else:
            # Substitute the absolute URL if this resource,
            # unless we find it in this webarchive.
            replacement = abs_url
            for subresource in subresources:
                if subresource.url == abs_url:
                    # This subresource is in our webarchive,
                    # so inline its contents using a data URI.
                    replacement = subresource.to_data_uri()
                    break

            content = content.replace(match, abs_url)

    return content
