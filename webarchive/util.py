"""Utility classes and functions for internal use."""

import io
import re
import html

from html.parser import HTMLParser
from urllib.parse import urljoin

from . import webresource
from .exceptions import WebArchiveError


__all__ = ["is_html_mime_type", "is_text_mime_type",
           "process_css_resource", "process_html_resource"]


# Regular expression matching a URL in a style sheet
RX_STYLE_SHEET_URL = re.compile(r"url\(([^\)]+)\)")


class HTMLRewriter(HTMLParser):
    """Class to process the main resource in the webarchive.

    Most of the work here is rewriting references to external resources,
    like the <img> tag's "src" attribute, since our local directory
    structure may not match that of the original site. The intent is to
    make the resulting HTML display identically to the original page.

      * If the referenced content is one of this webarchive's subresources,
        we substitute the local path of our extracted copy.

      * Otherwise, we substitute the absolute URL of the original.
    """

    # To rewrite subresource URLs, we actually regenerate all of the page's
    # HTML code. This may seem like overkill, but it's more reliable than
    # simple string replacement or regular expressions for two reasons. First,
    # we don't have to account for HTML entities, because HTMLParser always
    # gives us text it's processed in unescaped form. Second, it lets us easily
    # distinguish subresource URLs occurring in attribute values -- which we
    # want to rewrite to make the page display correctly -- from those
    # appearing as literal text, which we shouldn't touch since they are
    # part of the page's content.

    __slots__ = ["_res", "_archive", "_output", "_subresource_dir",
                 "_is_xhtml", "_style_buffer", "_in_style_block"]

    def __init__(self, res, output, subresource_dir):
        """Return a new HTMLRewriter."""

        HTMLParser.__init__(self, convert_charrefs=False)

        self._res = res
        self._archive = res.archive
        self._output = output
        self._subresource_dir = subresource_dir

        # Identify whether this document is XHTML based on the MIME type
        self._is_xhtml = (res.mime_type == "application/xhtml+xml")

        # Buffer for processing inline CSS code
        self._style_buffer = ""
        self._in_style_block = False

    def handle_starttag(self, tag, attrs):
        """Handle a start tag."""

        if tag == "style":
            self._in_style_block = True

        self._output.write(self._build_starttag(tag, attrs))

    def handle_startendtag(self, tag, attrs):
        """Handle an XHTML-style "empty" start tag."""

        self._output.write(self._build_starttag(tag, attrs, True))

    def handle_endtag(self, tag):
        """Handle an end tag."""

        if tag == "style":
            self._in_style_block = False
            self._flush_style_buffer()

        self._output.write("</{0}>".format(tag))

    def handle_data(self, data):
        """Handle arbitrary data."""

        if self._in_style_block:
            # Buffer inline CSS so we can rewrite URLs; this buffer will be
            # flushed when we close the tag
            self._style_buffer = "".join((self._style_buffer, data))
        else:
            self._output.write(data)

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

        self._output.write("<!{0}>".format(decl))

        # This catches XHTML documents incorrectly served with an HTML type
        if "//DTD XHTML " in decl:
            self._is_xhtml = True

    def _resource_url(self, orig_url):
        """Return an appropriate URL for the specified resource."""

        return self._archive._get_local_url(self._subresource_dir, orig_url)

    def _build_starttag(self, tag, attrs, is_empty=False):
        """Build an HTML start tag."""

        # Open the tag
        tag_data = ["<", tag]

        # Process attributes
        for attr, value in attrs:
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

        return "".join(tag_data)

    def _flush_style_buffer(self):
        """Write out buffered inline CSS code."""

        # Create a dummy WebResource to feed to process_css_resource()
        css_res = webresource.WebResource(self._archive,
                                          self._style_buffer,
                                          "text/css",
                                          self._res.url,
                                          self._res.text_encoding)

        content = process_css_resource(css_res, self._subresource_dir)
        self._output.write(content)
        self._style_buffer = ""

    def _process_attr_value(self, tag, attr, value):
        """Process the value of a tag's attribute."""

        if ((tag == "a" and attr == "href")
            or (tag == "form" and attr == "action")):
            # These always refer to content outside the WebArchive, which
            # only stores a single page and its embedded content
            value = self._archive._get_absolute_url(value)

        elif (attr == "src"
              or (tag == "link" and attr == "href")):
            # It may be tempting to add special handling here to inline
            # scripts and style sheets using <script> and <style> blocks.
            # Resist this urge. The naive approach of using data URIs
            # regardless is much safer, since we don't have to worry about
            # further complications like unescaped HTML tags in such content.
            value = self._resource_url(value)

        elif attr == "srcset":
            # Process the HTML5 srcset attribute
            srcset = []
            for item in map(str.strip, value.split(",")):
                if " " in item:
                    # Source-size pair, like "image.png 2x"
                    src, size = item.split(" ", 1)
                    src = self._resource_url(src)
                    srcset.append("{0} {1}".format(src, size))
                else:
                    # Source only -- no size specified
                    srcset.append(self._resource_url(item))

            value = ", ".join(srcset)

        return html.escape(value, True)

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


def is_html_mime_type(mime_type):
    """Return whether the specified MIME type is valid for HTML."""

    return (mime_type in ("text/html", "application/xhtml+xml"))


def is_text_mime_type(mime_type):
    """Return whether the specified MIME type is valid for text."""

    return (mime_type.startswith("text/") or is_html_mime_type(mime_type))


def process_css_resource(res, subresource_dir=None):
    """Process a WebResource containing CSS data.

    This rewrites url() values to use a local path, data URI, or
    absolute URL as appropriate; see WebArchive._get_local_url().

    Returns a string containing the modified CSS code.
    """

    # Make sure this resource is an appropriate content type
    if res.mime_type != "text/css":
        raise TypeError("res must have mime_type == 'text/css'")

    content = str(res)

    # Find URLs in the stylesheet
    for match in RX_STYLE_SHEET_URL.findall(content):
        # Remove quote characters, if present, from the URL
        if match.startswith('"') or match.startswith("'"):
            match = match[1:]
        if match.endswith('"') or match.endswith("'"):
            match = match[:-1]

        # This check is necessary because we sometimes get blank URLs
        # here, which can cause all manner of odd behavior
        if match:
            # URLs in CSS files are resolved relative to the style sheet
            local_url = res.archive._get_local_url(subresource_dir,
                                                   match,
                                                   res.url)
            if local_url != match:
                content = content.replace(match, local_url)

    return content


def process_html_resource(res, output, subresource_dir):
    """Process a WebResource containing HTML data.

    This rewrites URLs in the HTML code to use a local path, data URI,
    or absolute URL as appropriate; see WebArchive._get_local_url().

    The modified HTML is written to the specified output stream.
    """

    # This handles output the way it does because HTMLRewriter needs
    # somewhere to put the rewritten code, and since this function is
    # only (supposed to be) used internally, we know that when we call
    # this we're usually extracting a resource to a file. It's more
    # efficient for our use case to have HTMLRewriter output directly
    # to the file stream than to collect that data to return in a str.

    # Make sure this resource is an appropriate content type
    if not is_html_mime_type(res.mime_type):
        raise TypeError("res must have mime_type == "
                        "'text/html' or 'application/xhtml+xml'")

    try:
        # Feed the content through the HTMLRewriter to rewrite
        # references to files inside the archive
        rewriter = HTMLRewriter(res, output, subresource_dir)
        rewriter.feed(str(res))

    except (Exception):
        # This may indicate a non-HTML resource incorrectly served
        # with a text/html MIME type. Clear the botched attempt and
        # pass through the original data unmodified
        output.truncate(0)
        output.write(str(res))
