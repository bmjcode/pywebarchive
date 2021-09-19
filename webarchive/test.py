"""Test cases for pywebarchive."""

import os
import io
import tempfile
import unittest

from . import WebArchive, WebResource


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
        self.archive = WebArchive(SAMPLE_ARCHIVE_PATH)

    def tearDown(self):
        """Clean up the test case."""

        pass

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
            # Note: If we don't specify the text encoding, then open() might
            # raise a UnicodeDecodeError on Windows, causing the test to fail.
            text_encoding = self.archive.main_resource.text_encoding
            with open(output_path, "r",
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
            self.archive.extract(output_path, single_file=True)
            self.assertTrue(os.path.isfile(output_path))

            with open(output_path, "r") as source:
                content = source.read()

            self.assertEqual(self.archive.to_html(), content)

    def test_extracted_archive_display(self):
        """Test that an extracted WebArchive displays correctly.

        This means the extracted page should look exactly as it would on
        the live site. (Of course, it might not be possible to ensure a
        literally-exact match since Web pages change constantly, and the
        original page may have been dynamically generated, and so on.)

        This test runs interactively because I don't know of a suitable
        automated mechanism to use here. Perhaps checking <img src="...">
        and <a href="..."> attributes in the extracted HTML to ensure they
        point to the expected resources would be a start?

        This test requires the webbrowser module, to display the extracted
        page, and Tkinter, to ask the user whether it rendered correctly.
        If these are unavailable or fail to work, the test will be skipped.
        """

        try:
            import tkinter as tk
            import tkinter.messagebox as mb

            # Import these after Tkinter so we don't waste time loading them
            # if that import failed
            import time
            import webbrowser

            # Create a root window so we can use tkMessageBox, then immediately
            # withdraw it since we don't need it in its own right
            root = tk.Tk()
            root.withdraw()

            with tempfile.TemporaryDirectory() as tmp_dir:
                output_path = os.path.join(tmp_dir, "Wikipedia.html")

                # Extract the archive, and assert that it succeeded
                self.archive.extract(output_path)
                self.assertTrue(os.path.isfile(output_path))

                # Open the converted page
                webbrowser.open(output_path)

                # Wait for the user's browser to open
                time.sleep(15)

                # Ask the user to confirm that the page rendered correctly
                self.assertTrue(mb.askyesno(
                    "WebArchive Extraction Test",
                    "pywebarchive just extracted a sample .webarchive file "
                    "and opened the converted page in your default browser.\n"
                    "\n"
                    "If everything went well, you should see the main page "
                    "of the English Wikipedia, showing a featured article on "
                    "P. G. Wodehouse.\n"
                    "\n"
                    "Did the page display correctly?"
                ))

        except (ImportError) as err:
            self.skipTest(err)

        except (tk.TclError, webbrowser.Error) as err:
            # If an ImportError occurred, tk is likely undefined, so we have
            # to handle its exceptions in a separate block
            self.skipTest(err)
