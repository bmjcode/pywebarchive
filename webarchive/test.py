"""Test cases for pywebarchive."""

# Some things to consider when writing tests:
#   - Unit tests are fully automated and must run non-interactively.
#     (Earlier versions of pywebarchive did include interactive tests,
#     but these have since been split into separate scripts.)
#   - When using io.open() in text mode, you MUST specify an encoding
#     to avoid a UnicodeDecodeError if your system does not use UTF-8.

import os
import io
import tempfile
import unittest

from . import (open as open_webarchive,
               WebArchive, WebArchiveError, WebResource)
from .util import HTMLRewriter, is_html_mime_type, process_css_resource


# Absolute path to this file
TEST_PY_PATH = os.path.realpath(__file__)

# Directory containing sample data
SAMPLE_DATA_DIR = os.path.join(os.path.dirname(TEST_PY_PATH), "sample_data")

# Path to our sample archive
# Source: https://en.wikipedia.org/wiki/Main_Page (CC BY-SA)
SAMPLE_ARCHIVE_PATH = os.path.join(SAMPLE_DATA_DIR, "Wikipedia.webarchive")


class WebArchiveTest(unittest.TestCase):
    """Test case for the WebArchive class."""

    def setUp(self):
        """Set up the test case."""

        # Load our sample archive
        self.archive = open_webarchive(SAMPLE_ARCHIVE_PATH)

    def tearDown(self):
        """Clean up the test case."""

        pass

    def test_webarchive_context_manager(self):
        """Test the WebArchive's class context manager."""

        # The actual test is simply that this does not fail
        with WebArchive(SAMPLE_ARCHIVE_PATH) as archive:
            self.assertIsInstance(archive, WebArchive)

    def test_is_html_mime_type(self):
        """Test the is_html_mime_type() method."""

        # HTML and XHTML both count
        self.assertTrue(is_html_mime_type("text/html"))
        self.assertTrue(is_html_mime_type("application/xhtml+xml"))

        # Plain XML does not
        self.assertFalse(is_html_mime_type("application/xml"))
        self.assertFalse(is_html_mime_type("text/xml"))

        # These are right out
        self.assertFalse(is_html_mime_type("text/css"))
        self.assertFalse(is_html_mime_type("text/javascript"))

    def test_webarchive_properties(self):
        """Test WebArchive object properties."""

        archive = self.archive

        # Assert that WebArchive properties return the correct values
        self.assertEqual(archive.main_resource, archive._main_resource)
        self.assertEqual(archive.subframe_archives, archive._subframe_archives)
        self.assertEqual(archive.subresources, archive._subresources)

        # Assert that WebArchive properties return the correct types
        self.assertTrue(isinstance(archive.main_resource, WebResource))
        for subframe_archive in archive.subframe_archives:
            self.assertTrue(isinstance(subframe_archive, WebArchive))
        for subresource in archive.subresources:
            self.assertTrue(isinstance(subresource, WebResource))

    def test_webresource_properties(self):
        """Test WebResource object properties."""

        resource = self.archive.main_resource

        # Assert that we can identify this WebResource's parent WebArchive
        self.assertEqual(resource.archive, self.archive)

        # Assert that WebResource properties return the correct values
        self.assertEqual(resource.data, resource._data)
        self.assertEqual(resource.frame_name, resource._frame_name)
        self.assertEqual(resource.mime_type, resource._mime_type)
        self.assertEqual(resource.text_encoding, resource._text_encoding)
        self.assertEqual(resource.url, resource._url)

        # Assert that WebResource properties return the correct types
        self.assertTrue(isinstance(resource.data, bytes))
        self.assertTrue(isinstance(resource.frame_name, str))
        self.assertTrue(isinstance(resource.mime_type, str))
        self.assertTrue(isinstance(resource.text_encoding, str))
        self.assertTrue(isinstance(resource.url, str))

        # Assert that WebResource properties return the expected values
        # for this sample archive
        data_str = "".join(map(chr, resource.data))
        self.assertTrue(data_str.startswith("<!DOCTYPE html>"))
        self.assertEqual(resource.frame_name, "")
        self.assertEqual(resource.mime_type, "text/html")
        self.assertEqual(resource.text_encoding, "utf-8")
        self.assertEqual(resource.url,
                         "https://en.wikipedia.org/wiki/Main_Page")

    def test_webresource_type_conversion(self):
        """Test WebResource type conversion."""

        main_resource = self.archive.main_resource
        image_subresource = None

        # Find a subresource with a non-text MIME type
        for subresource in self.archive.subresources:
            if subresource.mime_type.startswith("image/"):
                image_subresource = subresource
                break
        self.assertTrue(isinstance(image_subresource, WebResource))

        # Assert that we can convert the resource to bytes
        data = bytes(main_resource)
        self.assertEqual(data, main_resource.data)

        # Assert that we can convert a text resource to a string
        self.assertTrue(main_resource.mime_type.startswith("text/"))
        data = str(main_resource)
        self.assertTrue(data.startswith("<!DOCTYPE html>"))

        # Assert that we can't convert a non-text resource to a string,
        # and that attempting to do so fails with a TypeError exception
        with self.assertRaises(TypeError):
            data = str(image_subresource)

    def test_webarchive_resource_count(self):
        """Test that WebArchive.resource_count() returns the expected value."""

        resource_count = self.archive.resource_count()
        self.assertTrue(isinstance(resource_count, int))

        # All webarchives should have a main resource, but let's double-check
        self.assertIsNotNone(self.archive.main_resource)
        for subframe_archive in self.archive.subframe_archives:
            self.assertIsNotNone(subframe_archive.main_resource)
            # Make sure none of the subframe archives have their own nested
            # subframe archives, since it's simpler to write the test that way
            self.assertEqual(len(subframe_archive.subframe_archives), 0)

        # Count the main resource and subresources
        manual_resource_count = 1 + len(self.archive.subresources)

        for subframe_archive in self.archive.subframe_archives:
            # Count each subframe's main resource and subresources
            manual_resource_count += 1 + len(subframe_archive.subresources)

        self.assertEqual(resource_count, manual_resource_count)

    def test_webarchive_extraction(self):
        """Test WebArchive extraction."""

        with tempfile.TemporaryDirectory() as tmp_dir:
            output_path = os.path.join(tmp_dir, "Wikipedia.html")

            # Directory where we expect subresources to be extracted
            output_dir = os.path.join(tmp_dir, "Wikipedia_files")

            # Assert that our output paths don't already exist
            self.assertFalse(os.path.exists(output_path))
            self.assertFalse(os.path.exists(output_dir))

            # Extract the archive, and assert that it succeeded
            self.archive.extract(output_path)
            self.assertTrue(os.path.isfile(output_path))
            self.assertTrue(os.path.isdir(output_dir))

            # Assert that the output file contains HTML data
            text_encoding = self.archive.main_resource.text_encoding
            with io.open(output_path, "r",
                         encoding=text_encoding) as output_file:
                contents = output_file.read()
                self.assertTrue(contents.startswith("<!DOCTYPE html>"))

            # Assert that the output directory contains the expected number
            # of files (the archive's resource count, minus the main resource)
            output_dir_contents = os.listdir(output_dir)
            self.assertEqual(len(output_dir_contents),
                             self.archive.resource_count() - 1)

    def test_webarchive_to_html(self):
        """Test the WebArchive.to_html() method."""

        # WebArchive.to_html() should produce the same output as
        # extracting the archive in single-file mode
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_path = os.path.join(tmp_dir, "Wikipedia.html")

            self.assertFalse(os.path.exists(output_path))
            self.archive.extract(output_path, True)
            self.assertTrue(os.path.isfile(output_path))

            text_encoding = self.archive.main_resource.text_encoding
            with io.open(output_path, "r",
                         encoding=text_encoding) as source:
                content = source.read()

            self.assertEqual(self.archive.to_html(), content)

    def test_webarchive_parent(self):
        """Test the WebArchive.parent property."""

        # The top-level archive does not have a parent
        self.assertIsNone(self.archive.parent)

        # Create an empty subframe archive
        subframe_archive = WebArchive(self.archive)

        # Assert that its parent property is set to the right value
        self.assertIsNotNone(subframe_archive._parent)
        self.assertEqual(subframe_archive.parent, subframe_archive._parent)
        self.assertEqual(subframe_archive.parent, self.archive)


class MalformedArchiveTest(unittest.TestCase):
    """Test case for safe handling of malformed webarchives."""

    def test_webarchive_without_main_resource(self):
        """Test safe handling of archives without a main resource."""

        archive = WebArchive()
        self.assertIsNone(archive.main_resource)

        # This archive contains zero resources, and should report as much
        self.assertEqual(archive.resource_count(), 0)

        # Attempting to extract this archive should raise an exception
        with self.assertRaises(WebArchiveError):
            with tempfile.TemporaryDirectory() as tmp_dir:
                output_path = os.path.join(tmp_dir, "output.html")
                archive.extract(output_path)

        # Attempting to convert it to HTML should also raise an exception
        with self.assertRaises(WebArchiveError):
            archive.to_html()


class RewriterTest(WebArchiveTest):
    """Base class for HTML and CSS rewriter tests."""

    def setUp(self):
        """Set up the test case."""

        WebArchiveTest.setUp(self)
        abs_url = self.archive._get_absolute_url

        # URL of some page not within this archive
        self.external_url = "https://www.example.com/"

        # Relative URL of some page not within this archive
        self.rel_external_url = "/wiki/P._G._Wodehouse"

        # URL of some (arbitrary) subresource within this archive
        self.subresource_url = (
            "https://upload.wikimedia.org/wikipedia/commons"
            "/thumb/0/08/Kinewell_Lake_4.jpg/125px-Kinewell_Lake_4.jpg"
        )

        # Local path for the above subresource
        self.subresource_local_path = "/".join((
            "TestArchive_files",
            self.archive.get_local_path(self.subresource_url)
        ))

        # Relative URL of another subresource
        # Also arbitrary, so long as it's on the same server
        self.rel_subresource_url = (
            "/static/images/poweredby_mediawiki_88x31.png"
        )

        # Local path for the above subresource
        self.rel_subresource_local_path = "/".join((
            "TestArchive_files",
            self.archive.get_local_path(abs_url(self.rel_subresource_url))
        ))

    def tearDown(self):
        """Clean up the test case."""

        WebArchiveTest.tearDown(self)

    def test_internal_urls(self):
        """Internal sanity checks on our various sample URLs."""

        abs_url = self.archive._get_absolute_url

        def have_subresource(url):
            for res in self.archive.subresources:
                if res.url == url:
                    return True
            else:
                return False

        # Make sure external URLs are actually external
        for res in self.archive.subresources:
            self.assertNotEqual(res.url, self.external_url)
            self.assertNotEqual(res.url, abs_url(self.rel_external_url))

        # Make sure subresource URLs are actually subresources
        self.assertTrue(have_subresource(self.subresource_url))
        self.assertTrue(have_subresource(abs_url(self.rel_subresource_url)))


class HTMLRewriterTest(RewriterTest):
    """Test case for the HTMLRewriter class."""

    def setUp(self):
        """Set up the test case."""

        RewriterTest.setUp(self)
        abs_url = self.archive._get_absolute_url

        # Create an output stream and HTML rewriter
        self.output = io.StringIO()
        self.rewriter = HTMLRewriter(self.archive.main_resource,
                                     self.output,
                                     "TestArchive_files")

    def tearDown(self):
        """Clean up the test case."""

        RewriterTest.tearDown(self)

    # Note that for the URL-rewriting tests, we variously reuse the same
    # resource as a link target, image, script, and style sheet. Since
    # we're not actually interpreting any HTML code here, just checking
    # the rewriting logic, this saves us the trouble of generating unique
    # URLs for each test. In most cases the only property of interest is
    # whether the URL belongs to one of our archive's subresources or not.

    def test_a_href_absolute(self):
        """Test <a href="..."> with an absolute URL."""

        template = '<a href="{0}">'
        in_value = template.format(self.external_url)

        self.rewriter.feed(in_value)
        self.assertEqual(self.output.getvalue(), in_value)

    def test_a_href_relative(self):
        """Test <a href="..."> with a relative URL."""

        # Relative URLs should be rewritten as absolute URLs
        template = '<a href="{0}">'
        in_value = template.format(self.rel_external_url)
        out_value = template.format(
            self.archive._get_absolute_url(self.rel_external_url)
        )
        self.assertNotEqual(in_value, out_value)

        self.rewriter.feed(in_value)
        self.assertEqual(self.output.getvalue(), out_value)

    def test_a_href_subresource(self):
        """Test <a href="..."> with a subresource URL."""

        # Links should always use absolute URLs even for subresources
        template = '<a href="{0}">'
        in_value = template.format(self.subresource_url)

        self.rewriter.feed(in_value)
        self.assertEqual(self.output.getvalue(), in_value)

    def test_img_src_external(self):
        """Test <img src="..."> with an external URL."""

        template = '<img src="{0}">'
        in_value = template.format(self.external_url)

        self.rewriter.feed(in_value)
        self.assertEqual(self.output.getvalue(), in_value)

    def test_img_src_subresource(self):
        """Test <img src="..."> with a subresource URL."""

        template = '<img src="{0}">'
        in_value = template.format(self.subresource_url)
        out_value = template.format(self.subresource_local_path)
        self.assertNotEqual(in_value, out_value)

        self.rewriter.feed(in_value)
        self.assertEqual(self.output.getvalue(), out_value)

    def test_img_src_subresource_rel(self):
        """Test <img src="..."> with a relative subresource URL."""

        template = '<img src="{0}">'
        in_value = template.format(self.rel_subresource_url)
        out_value = template.format(self.rel_subresource_local_path)
        self.assertNotEqual(in_value, out_value)

        self.rewriter.feed(in_value)
        self.assertEqual(self.output.getvalue(), out_value)

    def test_link_href_external(self):
        """Test <link href="..."> with an external URL."""

        template = '<link href="{0}">'
        in_value = template.format(self.external_url)

        self.rewriter.feed(in_value)
        self.assertEqual(self.output.getvalue(), in_value)

    def test_link_href_subresource(self):
        """Test <link href="..."> with a subresource URL."""

        template = '<link href="{0}">'
        in_value = template.format(self.subresource_url)
        out_value = template.format(self.subresource_local_path)
        self.assertNotEqual(in_value, out_value)

        self.rewriter.feed(in_value)
        self.assertEqual(self.output.getvalue(), out_value)

    def test_link_href_subresource_rel(self):
        """Test <link href="..."> with a relative subresource URL."""

        template = '<link href="{0}">'
        in_value = template.format(self.rel_subresource_url)
        out_value = template.format(self.rel_subresource_local_path)
        self.assertNotEqual(in_value, out_value)

        self.rewriter.feed(in_value)
        self.assertEqual(self.output.getvalue(), out_value)

    def test_style_subresource(self):
        """Test inline <style> with a subresource URL."""

        template = '<style>html {{ background: url({0}); }}</style>'
        in_value = template.format(self.subresource_url)
        out_value = template.format(self.subresource_local_path)
        self.assertNotEqual(in_value, out_value)

        self.rewriter.feed(in_value)
        self.assertEqual(self.output.getvalue(), out_value)

    def test_style_subresource_rel(self):
        """Test inline <style> with a relative subresource URL."""

        template = '<style>html {{ background: url({0}); }}</style>'
        in_value = template.format(self.rel_subresource_url)
        out_value = template.format(self.rel_subresource_local_path)
        self.assertNotEqual(in_value, out_value)

        self.rewriter.feed(in_value)
        self.assertEqual(self.output.getvalue(), out_value)

    def test_xhtml_void_elements(self):
        """Test handling of self-closing XHTML tags like <img />."""

        # Any XHTML doctype will work here
        doctype = (
            '<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" '
            '"http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">'
        )

        tags = self.rewriter._VOID_ELEMENTS
        in_tags = "".join(("<{0}>".format(tag) for tag in tags))
        out_tags = "".join(("<{0} />".format(tag) for tag in tags))
        in_value = "\n".join((doctype.strip(), in_tags))
        out_value = "\n".join((doctype.strip(), out_tags))

        # Should be pretty obvious, but...
        self.assertNotEqual(in_value, out_value)

        self.rewriter.feed(in_value)
        self.assertTrue(self.rewriter._is_xhtml)
        self.assertEqual(self.output.getvalue(), out_value)

    def test_subresource_url_literals(self):
        """Test handling of subresource URLs appearing as literal text."""

        # This is, of course, not the correct way to use alt text,
        # but will suffice for the purpose of this unit test.
        template = '<img src="{0}" alt="{1}"><br>{1}'
        in_value = template.format(self.rel_subresource_url,
                                   self.rel_subresource_url)
        # The URL should be rewritten in the src attribute's value,
        # but not in the alt text or the page's content.
        out_value = template.format(self.rel_subresource_local_path,
                                    self.rel_subresource_url)
        self.assertNotEqual(in_value, out_value)

        self.rewriter.feed(in_value)
        self.assertEqual(self.output.getvalue(), out_value)


class CSSRewriterTest(RewriterTest):
    """Test case for CSS-rewriting rules."""

    def setUp(self):
        """Set up the test case."""

        RewriterTest.setUp(self)

        # URL for the dummy style sheet used by rewrite()
        # This doesn't actually have to exist.
        self.dummy_css_url = "https://www.example.com/style.css"

        # Override local paths that should now be relative to the style sheet,
        # not the main resource
        self.subresource_local_path = (
            self.archive.get_local_path(self.subresource_url)
        )

    def tearDown(self):
        """Clean up the test case."""

        RewriterTest.tearDown(self)

    def rewrite(self, data):
        """Rewrite the specified CSS data."""

        res = WebResource(self.archive,
                          data,
                          "text/css",
                          self.dummy_css_url)
        buffer = io.StringIO()

        process_css_resource(res, buffer, "")
        return buffer.getvalue()

    def test_rewrite_absolute(self):
        """Test absolute URL rewriting."""

        template = 'html {{ background: url({0}); }}'
        in_value = template.format(self.external_url)

        output = self.rewrite(in_value)
        self.assertEqual(output, in_value)

    def test_rewrite_subresource(self):
        """Test subresource URL rewriting."""

        template = 'html {{ background: url({0}); }}'
        in_value = template.format(self.subresource_url)
        out_value = template.format(self.subresource_local_path)
        self.assertNotEqual(in_value, out_value)

        output = self.rewrite(in_value)
        self.assertEqual(output, out_value)
