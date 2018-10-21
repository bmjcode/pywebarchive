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

    def __init__(self, path_or_stream, *, subframe=False):
        """Return a new WebArchive object.

        The subframe argument is reserved for internal use.
        """

        self._main_resource = None
        self._subresources = []
        self._subframe_archives = []

        # Basenames for extracted subresources, indexed by URL
        #
        # Implementation note: Starting in version 0.2.2, each subframe
        # archive has its own local paths dictionary so it can be extracted
        # independently of its parent archive. (Earlier releases did not
        # generate this for subframes for performance reasons, but it was
        # found not to incur a significant penalty in practice.)
        #
        # The parent archive also generates its own local paths for its
        # subframe archives' resources. When extracting the parent archive,
        # its subframe archives' resources are processed as subresources.
        #
        # This slight inefficiency is a side effect of how the extraction
        # code evolved, and may be cleaned up in a future release. For now,
        # however, it will remain on the "if-it-ain't-broke" principle.
        self._local_paths = {}

        # Read data from the archive
        if subframe and isinstance(path_or_stream, dict):
            # This is a subframe, and the constructor argument is the
            # processed plist data from the parent archive
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
            for plist_data in archive["WebSubresources"]:
                res = WebResource(plist_data)
                self._subresources.append(res)

                # Make local paths for extracting each subresource
                self._make_local_path(res)

        # Process WebSubframeArchives
        if "WebSubframeArchives" in archive:
            for plist_data in archive["WebSubframeArchives"]:
                subframe_archive = WebArchive(plist_data, subframe=True)
                self._subframe_archives.append(subframe_archive)

                # Make local paths for extracting the subframe's main
                # resource and subresources
                self._make_local_path(subframe_archive.main_resource)
                for res in subframe_archive._subresources:
                    self._make_local_path(res)

    def extract(self, output_path,
                *, before_cb=None, after_cb=None, canceled_cb=None):
        """Extract the archive's contents as a standard HTML document.

        You can specify these callback functions as keyword arguments to
        monitor or cancel the extraction process:

          before_cb(res, path)
            Called before extracting a WebResource.
            - res is the WebResource object to be extracted.
            - path is the absolute path where it will be extracted.

          after_cb(res, path)
            Called after extracting a WebResource.
            - res is the WebResource object that was extracted.
            - path is the absolute path where it was extracted.

          canceled_cb()
            Returns True if extraction was canceled, False otherwise.
        """

        def BEFORE(res, path):
            if before_cb:
                before_cb(res, path)

        def AFTER(res, path):
            if after_cb:
                after_cb(res, path)

        # Strip the extension from the output path
        base, ext = os.path.splitext(os.path.basename(output_path))

        # Basename of the directory containing extracted subresources
        subresource_dir_base = "{0}_files".format(base)

        # Full path to the directory containing extracted subresources
        subresource_dir = os.path.join(os.path.dirname(output_path),
                                       subresource_dir_base)

        if canceled_cb and canceled_cb():
            return

        # Extract the main resource
        BEFORE(self._main_resource, output_path)
        self._extract_main_resource(self._main_resource,
                                    output_path,
                                    subresource_dir_base)
        AFTER(self._main_resource, output_path)

        # Make a directory for subresources
        if self._subresources or self._subframe_archives:
            os.makedirs(subresource_dir, exist_ok=True)

        # Identify subresources of this archive and any subframe archives
        subresources = self._subresources[:]
        for subframe_archive in self._subframe_archives:
            subresources += subframe_archive._subresources

            # Extract this subframe's main resource to our subresources folder
            sf_main_res = subframe_archive._main_resource
            sf_local_path = os.path.join(subresource_dir,
                                         self._local_paths[sf_main_res.url])

            if canceled_cb and canceled_cb():
                return

            BEFORE(sf_main_res, sf_local_path)
            self._extract_main_resource(sf_main_res, sf_local_path, "")
            AFTER(sf_main_res, sf_local_path)

        # Extract subresources
        for res in subresources:
            # Full path to the extracted subresource
            subresource_path = os.path.join(subresource_dir,
                                            self._local_paths[res.url])

            if canceled_cb and canceled_cb():
                return

            # Extract this subresource
            BEFORE(res, subresource_path)
            self._extract_subresource(res, subresource_path)
            AFTER(res, subresource_path)

    def resource_count(self):
        """Return the total number of WebResources in this archive.

        This includes WebResources in subframe archives.
        """

        # Count the main resource and all subresources, both for this
        # archive and any subframe archives
        res_count = 1 + len(self._subresources)
        for subframe_archive in self._subframe_archives:
            res_count += 1 + len(subframe_archive._subresources)

        return res_count

    def _extract_main_resource(self, res, output_path, subresource_dir):
        """Extract the archive's main resource."""

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
        """Extract a style sheet subresource from the archive."""

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

                else:
                    # Substitute the absolute URL of this resource.
                    content = content.replace(match, abs_url)

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

    def _make_local_path(self, res):
        """Generate a local path for the specified WebResource."""

        # Basename for the extracted resource
        base = ""

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

        if not base:
            # No URL, or blank URL path (why would this occur?)
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

        # Replace characters that could cause problems in local paths
        #
        # "%" is used as an escape character in URLs, and the others are
        # invalid characters in Windows and some Unix paths.
        for c in "%", "<", ">", ":", '"', "/", "\\", "|", "?", "*":
            base = base.replace(c, "_")

        # Replace reserved names on Windows
        if (base.lower() in ("con", "prn", "aux", "nul")
            or (len(base) == 4
                and base[:3].lower() in ("com", "lpt")
                and base[3].isdigit())):
            base = "{0}_".format(base)

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
        """This archive's main resource (a WebResource object)."""

        return self._main_resource

    @property
    def subresources(self):
        """This archive's subresources (a list of WebResource objects)."""

        return self._subresources

    @property
    def subframe_archives(self):
        """This archive's subframes (a list of WebArchive objects)."""

        return self._subframe_archives

    # Regular expression matching a URL in a style sheet
    _rx_style_sheet_url = re.compile(r"url\(([^\)]+)\)")


# Record extensions for MIME types sometimes encountered in data URLs
# that the mimetypes module may not already recognize
mimetypes.add_type("application/font-woff", ".woff")
mimetypes.add_type("application/x-font-woff", ".woff")
mimetypes.add_type("application/x-javascript", ".js")
mimetypes.add_type("font/woff", ".woff")
mimetypes.add_type("font/woff2", ".woff2")
mimetypes.add_type("text/javascript", ".js")
