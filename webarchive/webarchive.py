#!/usr/bin/env python3

"""WebArchive class implementation."""

import os
import sys
import io
import plistlib
import re

from urllib.parse import urlparse, urljoin
from urllib.request import pathname2url
from pprint import pprint

from .webresource import WebResource
from .util import MainResourceProcessor


__all__ = ["WebArchive"]


class WebArchive(object):
    """Webarchive file reader.

    Pass the name of a .webarchive file as the constructor's path argument.
    """

    # WebMainResource
    # WebSubresources
    # WebSubframeArchives

    __slots__ = ["_main_resource", "_subresources", "_subframe_archives",
                 "_local_paths"]

    def __init__(self, path):
        """Return a new WebArchive."""

        self._main_resource = None
        self._subresources = []
        self._subframe_archives = []

        # Basenames for extracted subresources, indexed by URL
        self._local_paths = {}

        if path:
            # Read data from the specified webarchive file
            with io.open(path, "rb") as fp:
                archive = plistlib.load(fp)

                # Process the main resource
                self._main_resource = WebResource(archive["WebMainResource"])

                # Process subresources
                for res in archive["WebSubresources"]:
                    self._subresources.append(WebResource(res))

                # TODO: Process WebSubframeArchives

            # Generate local paths for each subresource in the archive
            self._make_local_paths()

    def extract(self, output_path):
        """Extract the webarchive's contents as a standard HTML document."""

        # Basename of the directory containing extracted subresources
        base, ext = os.path.splitext(os.path.basename(output_path))
        subresource_dir = "{0}_files".format(base)

        # Full path to the directory containing extracted subresources
        output_dir = os.path.join(os.path.dirname(output_path),
                                  subresource_dir)
        os.makedirs(output_dir, exist_ok=True)

        # Extract the main resource
        self._extract_main_resource(output_path, subresource_dir)

        # Extract subresources
        for res in self._subresources:
            # Full path to the extracted subresource
            res_path = os.path.join(output_dir, self._local_paths[res.url])

            if res.mime_type == "text/css":
                # Process style sheets to rewrite subresource URLs
                self._extract_style_sheet(res, res_path)

            else:
                # Extract other subresources as-is
                self._extract_subresource(res, res_path)

    def _extract_main_resource(self, output_path, subresource_dir):
        """Extract the main resource of the webarchive."""

        res = self._main_resource

        with io.open(output_path, "w",
                     encoding=res.text_encoding) as output:
            # Feed the content through the MainResourceProcessor to rewrite
            # references to files inside the archive
            mrp = MainResourceProcessor(res.url,
                                        subresource_dir,
                                        self._local_paths,
                                        output)
            mrp.feed(str(res))

    def _extract_style_sheet(self, res, output_path):
        """Extract a style sheet subresource from the webarchive."""

        content = str(res)

        with io.open(output_path, "w",
                     encoding=res.text_encoding) as output:
            # Find URLs in the stylesheet
            matches = self._rx_style_sheet_url.findall(content)
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

        for res in self._subresources:
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

    @property
    def main_resource(self):
        """This webarchive's main resource (a WebResource object)."""

        return self._main_resource

    @property
    def subresources(self):
        """This webarchive's subresources (a list of WebResource objects)."""

        return self._subresources

    @property
    def subframe_archives(self):
        """This webarchive's subframe archives (currently not implemented)."""

        return self._subframe_archives

    # Regular expression matching a URL in a style sheet
    _rx_style_sheet_url = re.compile(r"url\(([^\)]+)\)")
