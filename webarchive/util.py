"""Utility classes and functions for internal use."""

import io
import re
import html

from html.parser import HTMLParser
from urllib.parse import urljoin

from .exceptions import WebArchiveError


__all__ = ["process_main_resource", "process_style_sheet"]


# Regular expression matching a URL in a style sheet
RX_STYLE_SHEET_URL = re.compile(r"url\(([^\)]+)\)")


class MainResourceProcessor(HTMLParser):
    """Class to process the main resource in the webarchive.

    Most of the work here is rewriting references to external resources,
    like the <img> tag's "src" attribute, since our local directory
    structure may not match that of the original site. The intent is to
    make the resulting HTML display identically to the original page.

      * If the referenced content is one of this webarchive's subresources,
        we substitute the local path of our extracted copy.

      * Otherwise, we substitute the absolute URL of the original.
    """

    # Implementation note: Using HTMLParser is a safer way to do this
    # than simple text processing or regular expressions, given the
    # prevalence of non-standard HTML code.

    __slots__ = ["_archive", "_output", "_root", "_is_xhtml",
                 "_escape_entities"]

    def __init__(self, archive, output, root):
        """Return a new MainResourceProcessor."""

        HTMLParser.__init__(self, convert_charrefs=False)

        self._archive = archive
        self._output = output
        self._root = root

        # Identify whether this document is XHTML based on the MIME type
        main_resource = archive.main_resource
        self._is_xhtml = (main_resource.mime_type == "application/xhtml+xml")

        # Escape entities unless we're in a <script> or <style> block;
        # handle_starttag() and handle_endtag() will toggle this as needed
        self._escape_entities = True

    def handle_starttag(self, tag, attrs):
        """Handle a start tag."""

        if tag in self._UNESCAPED_ENTITY_TAGS:
            self._escape_entities = False

        self._output.write(self._build_starttag(tag, attrs))

    def handle_startendtag(self, tag, attrs):
        """Handle an XHTML-style "empty" start tag."""

        self._output.write(self._build_starttag(tag, attrs, True))

    def handle_endtag(self, tag):
        """Handle an end tag."""

        if tag in self._UNESCAPED_ENTITY_TAGS:
            self._escape_entities = True

        self._output.write("</{0}>".format(tag))

    def handle_data(self, data):
        """Handle arbitrary data."""

        if self._escape_entities:
            self._output.write(html.escape(data, False))
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

        # This should probably be on its own line
        self._output.write("<!{0}>\n".format(decl))

        # This caches pre-XHTML5 documents incorrectly served as standard HTML
        if "//DTD XHTML " in decl:
            self._is_xhtml = True

    def _resource_url(self, orig_url):
        """Return an appropriate URL for the specified resource."""

        return self._archive._get_local_url(self._root, orig_url)

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

        # If this is the opening <html> tag, indicate that this file
        # has been processed by pywebarchive
        if tag == "html":
            tag_data.insert(0, "<!-- Processed by pywebarchive -->\n")

        return "".join(tag_data)

    def _process_attr_value(self, tag, attr, value):
        """Process the value of a tag's attribute."""

        if ((tag == "a" and attr == "href")
            or (tag == "form" and attr == "action")):
            # These always refer to content outside the WebArchive, which
            # only stores a single page and its embedded content
            value = self._archive._get_absolute_url(value)

        elif (attr == "src"
              or (tag == "link" and attr == "href")):
            if tag in ("frame", "iframe"):
                # Process the src attribute for HTML frames
                value = self._resource_url(value)

            else:
                # Process the src attribute for images, scripts, etc.
                #
                # Note that we deliberately inline scripts using data URIs
                # rather than converting them to <script> blocks to avoid
                # difficulties with scripts containing unescaped HTML tags.
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

    # Tags that can include unescaped HTML entities
    _UNESCAPED_ENTITY_TAGS = ("script", "style")


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


def process_style_sheet(res, subresource_dir=None):
    """Process a WebResource containing CSS data.

    This rewrites url() values to use a local path, data URI, or
    absolute URL as appropriate; see WebArchive._get_local_url().
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
