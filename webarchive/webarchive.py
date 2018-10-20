#!/usr/bin/env python3

"""WebArchive class implementation."""

import os
import sys
import io
import plistlib
import re
import mimetypes

from urllib.parse import urlparse, urljoin

from .webresource import WebResource
from .util import MainResourceProcessor


__all__ = ["WebArchive"]


class WebArchive(object):
    """Class for reading a .webarchive file."""

    # WebMainResource
    # WebSubresources
    # WebSubframeArchives

    __slots__ = ["_main_resource", "_subresources", "_subframe_archives",
                 "_local_paths"]

    def __init__(self, path_or_stream):
        """Return a new WebArchive object."""

        self._main_resource = None
        self._subresources = []
        self._subframe_archives = []

        # Basenames for extracted subresources, indexed by URL
        self._local_paths = {}

        # Read data from the archive
        if isinstance(path_or_stream, dict):
            # For processing subframe archives
            archive = path_or_stream

        elif isinstance(path_or_stream, io.IOBase):
            # The constructor argument is a stream
            archive = plistlib.load(path_or_stream)

        else:
            # Assume the constructor argument is a file path
            with io.open(path_or_stream, "rb") as fp:
                archive = plistlib.load(fp)

        # Process the main resource
        self._main_resource = WebResource(archive["WebMainResource"])

        # Process subresources
        if "WebSubresources" in archive:
            for res in archive["WebSubresources"]:
                self._subresources.append(WebResource(res))

        # Process WebSubframeArchives
        if "WebSubframeArchives" in archive:
            for plist_data in archive["WebSubframeArchives"]:
                subframe_archive = WebArchive(plist_data)
                self._subframe_archives.append(subframe_archive)

        # Generate local paths for each subresource in the archive
        self._make_local_paths()

    def extract(self, output_path):
        """Extract the webarchive's contents as a standard HTML document."""

        # Strip the extension from the output path
        base, ext = os.path.splitext(os.path.basename(output_path))

        # Basename of the directory containing extracted subresources
        subresource_dir_base = "{0}_files".format(base)

        # Full path to the directory containing extracted subresources
        subresource_dir = os.path.join(os.path.dirname(output_path),
                                       subresource_dir_base)
        os.makedirs(subresource_dir, exist_ok=True)

        # Extract the main resource
        self._extract_main_resource(self._main_resource,
                                    output_path,
                                    subresource_dir_base)

        # Identify subresources of this archive and any subframe archives
        subresources = self._subresources[:]
        for subframe_archive in self._subframe_archives:
            subresources += subframe_archive._subresources

            # Extract this subframe's main resource to our subresources folder
            sf_main_res = subframe_archive._main_resource
            sf_local_path = os.path.join(subresource_dir,
                                         self._local_paths[sf_main_res.url])
            self._extract_main_resource(sf_main_res, sf_local_path, "")

        # Extract subresources
        for res in subresources:
            # Full path to the extracted subresource
            subresource_path = os.path.join(subresource_dir,
                                            self._local_paths[res.url])

            # Extract this subresource
            self._extract_subresource(res, subresource_path)

    def _extract_main_resource(self, res, output_path, subresource_dir):
        """Extract the main resource of the webarchive."""

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
        """Extract the specified subresource from the archive."""

        if res.mime_type == "text/css":
            # Process style sheets to rewrite subresource URLs
            self._extract_style_sheet(res, output_path)

        else:
            # Extract other subresources as-is
            with io.open(output_path, "wb") as output:
                output.write(bytes(res))

    def _make_local_paths(self):
        """Generate local paths for each subresource in the archive."""

        # Process this archive's own subresources, and both main resources
        # and subresources in any subframe archives
        resources = self._subresources[:]
        for subframe_archive in self._subframe_archives:
            resources.append(subframe_archive._main_resource)
            resources += subframe_archive._subresources

        for res in resources:
            if res.url:
                # Parse the resource's URL
                parsed_url = urlparse(res.url)

                if parsed_url.scheme == "data":
                    # Data URLs are anonymous, so assign a default basename
                    base = "data_url"

                else:
                    # Get the basename of the URL path
                    url_path_basename = os.path.basename(parsed_url.path)
                    base, ext = os.path.splitext(url_path_basename)

            else:
                # FIXME: Why would this occur?
                base = "blank_url"

            # Attempt to automatically determine an appropriate extension
            # based on the MIME type
            #
            # Files served over HTTP(S) can have any extension, or none at
            # all, because the Content-type header indicates what type of
            # data they contain. However, because local files don't come with
            # HTTP headers, most browsers rely on the extension to determine
            # their file types, so we'll have to choose extensions they're
            # likely to recognize.
            ext = mimetypes.guess_extension(res.mime_type)
            if not ext:
                ext = ""

            # Safe substitution for "%", which is used as an escape character
            # in URLs and can cause problems when used in local paths
            base = base.replace("%", "_")

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
        """This webarchive's subframes (a list of WebArchive objects)."""

        return self._subframe_archives

    # Regular expression matching a URL in a style sheet
    _rx_style_sheet_url = re.compile(r"url\(([^\)]+)\)")


# Record extensions for MIME types sometimes encountered in data URLs
# that the mimetypes module may not already recognize
mimetypes.add_type("application/font-woff", ".woff")
mimetypes.add_type("application/x-font-woff", ".woff")
mimetypes.add_type("font/woff", ".woff")
mimetypes.add_type("font/woff2", ".woff2")
