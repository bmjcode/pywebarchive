"""WebArchive class implementation."""

import os
import io
import plistlib
import mimetypes

from urllib.parse import urlparse, urljoin

from .exceptions import WebArchiveError
from .webresource import WebResource
from .util import process_main_resource, process_style_sheet


__all__ = ["WebArchive"]


class WebArchive(object):
    """Class representing the contents of a .webarchive file.

    You should use webarchive.open() to access a webarchive rather than
    instantiate this class directly, since the constructor arguments may
    change in a future release.
    """

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
        self._main_resource = WebResource(self, archive["WebMainResource"])

        # Process subresources
        if "WebSubresources" in archive:
            for plist_data in archive["WebSubresources"]:
                res = WebResource(self, plist_data)
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

    def extract(self, output_path, single_file=False,
                *, before_cb=None, after_cb=None, canceled_cb=None):
        """Extract this webarchive.

        Extraction converts a webarchive to a standard HTML document.
        The resulting document should display and function identically
        to the original, though it will not necessarily be byte-identical.

        External media such as images, scripts, and style sheets are
        handled as follows:

          * If single_file is False ("multi-file mode", the default),
            this archive's subresources will be saved as individual
            files. References to those resources will be rewritten
            to use the local copies. This is how the "Save As" command
            in most non-Safari browsers, like Mozilla Firefox, works.

          * If single_file is True ("single-file mode"), this archive's
            subresources will be embedded inline using data URIs. As the
            name suggests, this allows an entire page and its resources
            to be saved in a single file. However, it typically requires
            more disk space and processing time than multi-file extraction.

          * References to media not stored as subresources will be
            replaced with absolute URLs.

        You can specify the below callback functions as keyword arguments
        to monitor or cancel the extraction process:

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

        if canceled_cb and canceled_cb():
            return

        def BEFORE(res, path):
            if before_cb:
                before_cb(res, path)

        def AFTER(res, path):
            if after_cb:
                after_cb(res, path)

        # Strip the extension from the output path
        base, ext = os.path.splitext(os.path.basename(output_path))

        if single_file:
            # Extract the main resource, embedding subresources recursively
            # using data URIs
            BEFORE(self._main_resource, output_path)
            self._extract_main_resource(output_path, None)
            AFTER(self._main_resource, output_path)

        else:
            # Basename of the directory containing extracted subresources
            subresource_dir_base = "{0}_files".format(base)

            # Full path to the directory containing extracted subresources
            subresource_dir = os.path.join(os.path.dirname(output_path),
                                           subresource_dir_base)

            # Extract the main resource
            BEFORE(self._main_resource, output_path)
            self._extract_main_resource(output_path, subresource_dir_base)
            AFTER(self._main_resource, output_path)

            # Make a directory for subresources
            if self._subresources or self._subframe_archives:
                os.makedirs(subresource_dir, exist_ok=True)

            # Extract subresources
            for res in self._subresources:
                # Full path to the extracted subresource
                subresource_path = os.path.join(subresource_dir,
                                                self._local_paths[res.url])

                if canceled_cb and canceled_cb():
                    return

                # Extract this subresource
                BEFORE(res, subresource_path)
                self._extract_subresource(res, subresource_path)
                AFTER(res, subresource_path)

            # Recursively extract subframe archives
            for subframe_archive in self._subframe_archives:
                # We test this here to stop processing further subframe
                # archives; the nested calls to extract() will separately
                # test this to stop subresource extraction.
                if canceled_cb and canceled_cb():
                    return

                sf_main_res = subframe_archive._main_resource
                sf_local_path = os.path.join(subresource_dir,
                                             self._local_paths[sf_main_res.url])

                subframe_archive.extract(sf_local_path,
                                         single_file,
                                         before_cb=before_cb,
                                         after_cb=after_cb,
                                         canceled_cb=canceled_cb)

    def get_local_path(self, url):
        """Return the local path for the subresource at the specified URL.

        The local path is the basename for the file that would be created
        for this subresource if this archive were extracted.

        If no such subresource exists in this archive, this will raise
        a WebArchiveError exception.
        """

        if url in self._local_paths:
            return self._local_paths[url]

        else:
            raise WebArchiveError("no local path for the specified URL")

    def get_subframe_archive(self, url):
        """Return the subframe archive for the specified URL.

        If no such subframe archive exists in this archive, this will
        raise a WebArchiveError exception.
        """

        if not "://" in url:
            raise WebArchiveError("must specify an absolute URL")

        for subframe_archive in self._subframe_archives:
            if subframe_archive.main_resource.url == url:
                return subframe_archive
        else:
            raise WebArchiveError("no subframe archive for the specified URL")

    def get_subresource(self, url):
        """Return the subresource at the specified URL.

        If no such subresource exists in this archive, this will raise
        a WebArchiveError exception.
        """

        if not "://" in url:
            raise WebArchiveError("must specify an absolute URL")

        for subresource in self._subresources:
            if subresource.url == url:
                return subresource
        else:
            raise WebArchiveError("no subresource for the specified URL")

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

    def to_html(self):
        """Return this archive's contents as an HTML document.

        Subresources will be embedded recursively using data URIs,
        as they are when extracting the archive in single-file mode.
        """

        with io.StringIO() as output:
            process_main_resource(self, output, None)
            return output.getvalue()

    def _extract_main_resource(self, output_path, subresource_dir):
        """Extract the archive's main resource."""

        if self._main_resource.mime_type in ("text/html",
                                             "application/xhtml+xml"):
            with io.open(output_path, "w",
                         encoding=self._main_resource.text_encoding) as output:
                process_main_resource(self, output, subresource_dir)

        else:
            # Non-HTML main resources are possible; for example, I have
            # one from YouTube where the main resource is JavaScript.
            with io.open(output_path, "wb") as output:
                output.write(bytes(self._main_resource))

    def _extract_style_sheet(self, res, output_path):
        """Extract a style sheet subresource from the archive."""

        with io.open(output_path, "w",
                     encoding=res.text_encoding) as output:
            # Note that URLs in CSS are interpreted relative to the
            # style sheet's path, which in our case is the same path
            # where we extract all our other subresources.
            content = process_style_sheet(res, "")
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

    def _get_absolute_url(self, url, base=None):
        """Return the absolute URL to the specified resource.

        Relative URLs are resolved from the main resource's URL
        unless an alternative base is specified. For example,
        URLs in CSS files are resolved relative to the style sheet.
        """

        if not base:
            # Rewrite URLs relative to this archive's main resource
            base = self._main_resource.url
        elif not "://" in base:
            raise WebArchiveError("base must be an absolute URL")

        return urljoin(base, url)

    def _get_local_url(self, subresource_dir, orig_url, base=None):
        """Return a (preferably local) URL for the specified resource.

        This is used by MainResourceProcessor and others to rewrite
        subresource URLs when extracting a webarchive.

        Relative URLs are resolved from the main resource's URL
        unless an alternative base is specified. For example,
        URLs in CSS files are resolved relative to the style sheet.

        If the resource exists in this archive, this will return its
        local path if subresource_dir is a string, or a data URI
        otherwise. If the resource is not in this archive, this will
        return its absolute URL, so the extracted page will still
        display correctly so long as the original remains available.

        Note: If subresource_dir == '', this returns a local path
        relative to the current directory; this is used when rewriting
        url() values in style sheets. This is deliberately distinct
        from if subresource_dir is None, which returns a data URI.
        """

        # Get the absolute URL of the original resource
        abs_url = self._get_absolute_url(orig_url, base)

        try:
            if subresource_dir is None:
                # Single-file extraction mode
                res = self.get_subresource(abs_url)
                return res.to_data_uri()

            else:
                # Multi-file extraction mode
                local_path = self.get_local_path(abs_url)
                if subresource_dir:
                    return "{0}/{1}".format(subresource_dir, local_path)
                else:
                    return local_path

        except (WebArchiveError):
            # Resource not in archive; return its absolute URL
            return abs_url

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


# Record extensions for MIME types sometimes encountered in data URLs
# that the mimetypes module may not already recognize
mimetypes.add_type("application/font-woff", ".woff")
mimetypes.add_type("application/x-font-woff", ".woff")
mimetypes.add_type("application/x-javascript", ".js")
mimetypes.add_type("font/woff", ".woff")
mimetypes.add_type("font/woff2", ".woff2")
mimetypes.add_type("text/javascript", ".js")
