"""WebArchive class implementation."""

import os
import io
import plistlib
import mimetypes

from urllib.parse import urlparse, urljoin

from .exceptions import WebArchiveError
from .webresource import WebResource
from .util import (is_html_mime_type,
                   process_css_resource, process_html_resource)


__all__ = ["WebArchive"]


class WebArchive(object):
    """An archive storing a webpage's content and embedded external media.

    A webarchive consists of the following elements:

      * A main resource (required). This is a WebResource object storing
        the page's HTML content.

      * Subresources (optional). These are WebResource objects storing
        external media like images, scripts, and style sheets.

      * Subframe archives (optional). These are nested WebArchive objects
        storing other webpages displayed in HTML frames.

    You can examine these resources using this class's main_resource,
    subresources, and subframe_archives properties, respectively.

    The main operation of interest on webarchives is extraction, which
    here simply means converting the webarchive to a standard HTML page.
    See the extract() method's documentation for details.

    Note: You should always use webarchive.open() to access a webarchive
    file rather than instantiate this class directly.
    """

    __slots__ = ["_parent",
                 "_main_resource", "_subresources", "_subframe_archives",
                 "_local_paths"]

    def __init__(self, parent=None):
        """Return a new WebArchive object.

        You should always use webarchive.open() to access a WebArchive
        rather than instantiate this class directly, since the constructor
        arguments may change in a future release.
        """

        self._parent = parent
        self._main_resource = None
        self._subresources = []
        self._subframe_archives = []

        # Basenames for extracted subresources, indexed by (absolute) URL
        #
        # This also contains entries for the main resources, but not
        # subresources, of any subframe archives.
        #
        # Each subframe archive has its own local paths dictionary so it
        # can be extracted independently of its parent archive.
        self._local_paths = {}

    def __del__(self):
        """Clean up before deleting this object."""

        self.close()

    def __enter__(self):
        """Enter the runtime context."""

        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """Exit the runtime context."""

        self.close()
        return False  # process any raised exception normally

    def close(self):
        """Close this webarchive."""

        # This currently does nothing, but is provided for semantic
        # compatibility with io.open().
        pass

    def extract(self, output_path, embed_subresources=False,
                *, before_cb=None, after_cb=None, canceled_cb=None):
        """Extract this webarchive.

        Extraction converts a webarchive to a standard HTML document.
        The resulting document should look and behave identically to the
        original webarchive file as displayed by Safari (apart from the
        usual rendering differences if you are using a different browser).

        External media such as images, scripts, and style sheets are
        handled as follows:

          * If embed_subresources is False (the default), this archive's
            subresources will be saved as individual files. References
            to those resources will be rewritten to use the local copies.
            This is how the "Save As" command in other browsers like
            Mozilla Firefox usually works.

          * If embed_subresources is True, subresources will be embedded
            inline using data URIs. This allows the entire page to be
            stored in a single file, mimicking the webarchive format's
            main feature, with full cross-browser support but much lower
            efficiency. Be aware that this typically requires more disk
            space and processing time than extracting to separate files.

          * Regardless of the above setting, references to media not
            stored as subresources will be replaced with absolute URLs.

        To allow monitoring or canceling an extraction in process, you
        can specify callback functions for the following keyword arguments:

          before_cb(res, path)
            Called just before extracting a WebResource. No return value.
            - res is the WebResource object to be extracted.
            - path is the absolute path where it will be extracted.

          after_cb(res, path)
            Called just after extracting a WebResource. No return value.
            - res is the WebResource object that was extracted.
            - path is the absolute path where it was extracted.

          canceled_cb()
            Called periodically to check if extraction was canceled
            by the user. Should return True to cancel, False otherwise.

        If an error occurs during extraction, this will raise a
        WebArchiveError with a message explaining what went wrong.
        """

        # Note: _extract_main_resource() checks that an archive actually
        # has a main resource, and raises an exception if it's missing.

        # The embed_subresources argument was previously named single_file.
        # Since it is intended to be used as a positional rather than a
        # keyword argument, I think this is an acceptable change to provide
        # a more descriptive name for this feature. However, this does break
        # backwards compatibility for any code passing single_file as a
        # keyword argument against our intentions.

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

        if embed_subresources:
            # Extract the main resource, embedding subresources recursively
            # using data URIs
            BEFORE(self._main_resource, output_path)
            self._extract_main_resource(output_path, None)
            AFTER(self._main_resource, output_path)

        else:
            # Make sure all subresources have local paths
            # (this is redundant for read-only archives, but could be
            # useful if pywebarchive ever implements write support)
            self._make_local_paths()

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

                sf_main = subframe_archive._main_resource
                sf_local_path = os.path.join(subresource_dir,
                                             self._local_paths[sf_main.url])

                subframe_archive.extract(sf_local_path,
                                         embed_subresources,
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

        res_count = 0

        # Just because we should have a main resource doesn't mean we do
        if self._main_resource:
            res_count += 1

        res_count += len(self._subresources)
        for subframe_archive in self._subframe_archives:
            res_count += subframe_archive.resource_count()

        return res_count

    def to_html(self):
        """Return this archive's contents as an HTML document.

        Subresources will be embedded recursively using data URIs,
        as they are when extracting the archive in single-file mode.
        """

        if not self._main_resource:
            raise WebArchiveError("archive does not have a main resource")

        with io.StringIO() as output:
            process_html_resource(self._main_resource, output, None)
            return output.getvalue()

    def _extract_main_resource(self, output_path, subresource_dir):
        """Extract the archive's main resource."""

        main_resource = self._main_resource
        if not main_resource:
            raise WebArchiveError("archive does not have a main resource")

        if is_html_mime_type(main_resource.mime_type):
            with io.open(output_path, "w",
                         encoding=main_resource.text_encoding) as output:
                process_html_resource(main_resource, output, subresource_dir)

        else:
            # Non-HTML main resources are possible; for example, I have
            # one from YouTube where the main resource is JavaScript.
            with io.open(output_path, "wb") as output:
                output.write(bytes(main_resource))

    def _extract_subresource(self, res, output_path):
        """Extract the specified subresource from the archive."""

        if res.mime_type == "text/css":
            with io.open(output_path, "w",
                         encoding=res.text_encoding) as output:
                # URLs in CSS are resolved relative to the style sheet's
                # location, and in our case all subresources are extracted
                # to the same directory.
                process_css_resource(res, output, "")

        elif is_html_mime_type(res.mime_type):
            # HTML subresources are weird, but possible
            with io.open(output_path, "w",
                         encoding=res.text_encoding) as output:
                process_html_resource(res, output, "")

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

        This is used to rewrite subresource URLs in HTML and CSS
        resources when extracting a webarchive.

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
        """Returns a local path for the specified WebResource."""

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

        # Files served over HTTP(S) can have any extension, or none at
        # all, because the Content-type header indicates what type of
        # data they contain. However, local files don't have HTTP headers,
        # so browsers rely on file extensions to determine their types.
        # We should thus choose extensions they'll be likely to recognize.
        ext = mimetypes.guess_extension(res.mime_type)
        if not ext:
            ext = ""

        # Certain characters can cause problems in local paths.
        # "%" is used as an escape character in URLs, and both forward-
        # and backslashes are common directory separators. The other
        # characters are forbidden on Windows and some Unix filesystems.
        for c in "%", "<", ">", ":", '"', "/", "\\", "|", "?", "*":
            base = base.replace(c, "_")

        # Windows also doesn't allow certain reserved names that were
        # historically used for DOS devices. Even if we're not running
        # on Windows, it's better to avoid these names anyway in case
        # our extracted files are later copied over to a Windows system.
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
        return local_path

    def _make_local_paths(self):
        """Make local paths for all of this archive's resources."""

        resources = []

        # This check is to safely handle archives without a main resource.
        # A well-formed webarchive should always have one, but this isn't
        # the place to enforce that.
        if self._main_resource:
            resources.append(self._main_resource)

        for subresource in self._subresources:
            resources.append(subresource)
        # The main resource of a subframe archive is effectively also
        # a subresource, so we include entries for those here
        for subframe_archive in self._subframe_archives:
            resources.append(subframe_archive._main_resource)

        # Generate local paths for any URLs we don't have them for
        for res in resources:
            if not res.url in self._local_paths:
                self._local_paths[res.url] = self._make_local_path(res)

    def _populate_from_plist_data(self, archive_data):
        """Populate this webarchive using parsed data from plistlib."""

        # Property names:
        # - WebMainResource
        # - WebSubresources
        # - WebSubframeArchives

        # Process the main resource
        self._main_resource = WebResource._create_from_plist_data(
            archive_data["WebMainResource"], self
        )

        # Process subresources
        if "WebSubresources" in archive_data:
            for res_data in archive_data["WebSubresources"]:
                res = WebResource._create_from_plist_data(res_data, self)
                self._subresources.append(res)

        # Process subframe archives
        if "WebSubframeArchives" in archive_data:
            for sa_data in archive_data["WebSubframeArchives"]:
                sa = WebArchive._create_from_plist_data(sa_data, self)
                self._subframe_archives.append(sa)

        # Make local paths for subresources
        self._make_local_paths()

    def _populate_from_stream(self, stream):
        """Populate this webarchive from the specified stream."""

        if isinstance(stream, io.IOBase):
            archive_data = plistlib.load(stream)
            self._populate_from_plist_data(archive_data)

        else:
            raise WebArchiveError("invalid stream type")

    @classmethod
    def _create_from_plist_data(cls, archive_data, parent=None):
        """Create a WebArchive object using parsed data from plistlib."""

        res = cls(parent)
        res._populate_from_plist_data(archive_data)

        return res

    @classmethod
    def _open(cls, path, mode="r"):
        """Open the specified webarchive file.

        Only mode 'r' (reading) is currently supported.
        """

        # Note this is the actual function exported as webarchive.open().
        # It uses a private name here to hide its real location from pydoc,
        # since that is an implementation detail that could change, but be
        # aware that any changes made here will be very public indeed.

        archive = cls()

        if isinstance(mode, str):
            if mode == "r":
                # Read this webarchive
                with io.open(path, "rb") as stream:
                    archive._populate_from_stream(stream)
            else:
                raise WebArchiveException(
                    "only mode 'r' (reading) is currently supported"
                )
        else:
            raise WebArchiveError("mode must be a str")

        return archive

    @property
    def main_resource(self):
        """This archive's main resource (a WebResource object)."""

        return self._main_resource

    @property
    def parent(self):
        """This archive's parent WebArchive, if this is a subframe archive.

        This will be set to None if this is the top-level webarchive.
        Note this property is not part of the webarchive format itself,
        but rather is provided by pywebarchive as a convenience.
        """

        return self._parent

    @property
    def subresources(self):
        """This archive's subresources (a list of WebResource objects)."""

        return self._subresources

    @property
    def subframe_archives(self):
        """This archive's subframes (a list of WebArchive objects)."""

        return self._subframe_archives


# These are common file extensions for web content
# that the mimetypes module may not already know
mimetypes.add_type("application/font-woff", ".woff")
mimetypes.add_type("application/x-font-woff", ".woff")
mimetypes.add_type("application/x-javascript", ".js")
mimetypes.add_type("font/woff", ".woff")
mimetypes.add_type("font/woff2", ".woff2")
mimetypes.add_type("text/javascript", ".js")
