#!/usr/bin/env python3

"""Webarchive extractor implementation."""

import os
import sys
import io
import re

from html import escape
from html.parser import HTMLParser
from urllib.parse import urlparse, urljoin
from urllib.request import pathname2url

from .webarchive import WebArchive


__all__ = ["Extractor"]


# Regular expression matching a URL in a style sheet
rx_style_sheet_url = re.compile(r"url\(([^\)]+)\)")


class Extractor(object):
    """Webarchive extractor class.

    This extracts a .webarchive file to a standard HTML document that
    can be viewed in any web browser. Pass a WebArchive object as the
    constructor's archive argument.
    """

    __slots__ = ["_archive", "_root", "_url", "_local_paths"]

    def __init__(self, archive):
        """Return a new WebarchiveExtractor."""

        # Process the archive
        self._archive = archive

        # Save the URL of the main resource
        self._url = self._archive.main_resource.url

        # Hold this name for extract()
        self._root = None

        # Basenames of extracted subresources, indexed by URL
        self._local_paths = {}

    def extract(self, output_path):
        """Extract the webarchive to the specified output_path."""

        # Basename of the directory containing extracted subresources
        base, ext = os.path.splitext(os.path.basename(output_path))
        self._root = "{0}_files".format(base)

        # Full path to the directory containing extracted subresources
        output_dir = os.path.join(os.path.dirname(output_path), self._root)
        os.makedirs(output_dir, exist_ok=True)

        # Generate local paths for each subresource in the archive
        self._make_local_paths()

        # Extract the main resource
        self._extract_main_resource(output_path)

        # Extract subresources
        for res in self._archive.subresources:
            # Full path to the extracted subresource
            res_path = os.path.join(output_dir, self._local_paths[res.url])

            if res.mime_type == "text/css":
                # Process style sheets to rewrite subresource URLs
                self._extract_style_sheet(res, res_path)

            else:
                # Extract other subresources as-is
                self._extract_subresource(res, res_path)

    def _extract_main_resource(self, output_path):
        """Extract the main resource of the webarchive."""

        res = self._archive.main_resource

        with io.open(output_path, "w",
                     encoding=res.text_encoding) as output:
            # Feed the content through the MainResourceProcessor to rewrite
            # references to files inside the archive
            mrp = MainResourceProcessor(res.url,
                                        self._root,
                                        self._local_paths,
                                        output)
            mrp.feed(str(res))

    def _extract_style_sheet(self, res, output_path):
        """Extract a style sheet subresource from the webarchive."""

        content = str(res)

        with io.open(output_path, "w",
                     encoding=res.text_encoding) as output:
            # Find URLs in the stylesheet
            matches = rx_style_sheet_url.findall(content)
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

                if abs_url in self._local_paths:
                    # Substitute the local path to this resource.
                    # Because paths in CSS are relative to the style sheet,
                    # and all subresources (like style sheets) are extracted
                    # to the same folder, the basename is all we need.
                    local_url = self._local_paths[abs_url]
                    content = content.replace(match, local_url)

            output.write(content)

    def _extract_subresource(self, res, output_path):
        """Extract an arbitrary subresource from the archive."""

        with io.open(output_path, "wb") as output:
            output.write(bytes(res))

    def _make_local_paths(self):
        """Generate local paths for each subresource in the archive."""

        for res in self._archive.subresources:
            # Parse the resource's URL
            parsed_url = urlparse(res.url)

            # Get the basename of the URL path
            base, ext = os.path.splitext(os.path.basename(parsed_url.path))

            # Safe substitution for "%", which is used as an escape character
            # in URLs and can cause problems when used in local paths
            base = base.replace("%", "_")

            if parsed_url.query:
                # Append a hash of the query string before the extension
                # to ensure a unique filename is generated for each distinct
                # query string associated with a given url.path
                base = "{0}.{1}".format(base, hash(parsed_url.query))

            # Re-join the base and extension
            local_path = "{0}{1}".format(base, ext)

            # Append a copy number if needed to ensure a unique basename
            copy_num = 1
            while local_path in self._local_paths.values():
                copy_num += 1
                local_path = "{0}.{1}{2}".format(base, copy_num, ext)

            # Save this resource's local path
            self._local_paths[res.url] = local_path


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


def main():
    """Extract the .webarchive file specified on the command line."""

    if len(sys.argv) < 2:
        # Display an error message and exit
        print("Usage: {0} filename.webarchive [output.html]"
              .format(sys.argv[0]),
              file=sys.stderr)
        sys.exit(1)

    # Get the archive path from the command line
    archive_path = sys.argv[1]

    if len(sys.argv) >= 3:
        # Get the output path from the command line
        output_path = sys.argv[2]
    else:
        # Derive the output path from the archive path
        base, ext = os.path.splitext(archive_path)
        output_path = "{0}.html".format(base)

    # Process the archive
    archive = WebArchive(archive_path)

    # Extract the archive
    extractor = Extractor(archive)
    extractor.extract(output_path)

    try:
        # Open the output file
        os.startfile(output_path)

    except (Exception):
        # This isn't available on all platforms
        pass
