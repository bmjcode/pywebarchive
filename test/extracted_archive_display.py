#!/usr/bin/env python3

"""Test that an extracted WebArchive displays correctly.

This complements the webarchive module's unit tests, which confirm
that individual components work correctly, by demonstrating that
they also collectively function as intended.
"""

import os
import sys
import tempfile
import webbrowser
import textwrap
import time

# Absolute path to this source file
# (we need this for the webarchive import)
SOURCE_PATH = os.path.realpath(__file__)
SOURCE_DIR = os.path.dirname(SOURCE_PATH)
SOURCE_PARENT = os.path.dirname(SOURCE_DIR)

# Import our local copy of the webarchive module
sys.path.insert(0, SOURCE_PARENT)
import webarchive


# Directory containing sample data
SAMPLE_DATA_DIR = os.path.join(SOURCE_PARENT, "webarchive", "sample_data")

# Path to our sample archive
# Source: https://en.wikipedia.org/wiki/Main_Page (CC BY-SA)
SAMPLE_ARCHIVE_PATH = os.path.join(SAMPLE_DATA_DIR, "Wikipedia.webarchive")


def run_test():
    with tempfile.TemporaryDirectory() as tmp_dir:
        output_path = os.path.join(tmp_dir, "Wikipedia.html")
        assert (not os.path.exists(output_path))

        # Load our sample archive
        archive = webarchive.open(SAMPLE_ARCHIVE_PATH)

        # Extract the archive, and assert that it succeeded
        archive.extract(output_path)
        assert os.path.isfile(output_path)

        # Open the converted page
        webbrowser.open(output_path)

        # Tell the user what to expect if the page rendered correctly
        print(textwrap.dedent("""\
            If the archive extracted correctly, your web browser should
            display the main page of the English Wikipedia with a featured
            article on P. G. Wodehouse."""))

        # Wait a few seconds for the browser to open and finish rendering
        # before we clean up the temporary directory
        time.sleep(10)


if __name__ == "__main__":
    run_test()
#!/usr/bin/env python3

"""Test that an extracted WebArchive displays correctly.

This complements the webarchive module's unit tests, which confirm
that individual components work correctly, by demonstrating that
they also collectively function as intended.
"""

import os
import sys
import tempfile
import webbrowser
import textwrap
import time

# Absolute path to this source file
# (we need this for the webarchive import)
SOURCE_PATH = os.path.realpath(__file__)
SOURCE_DIR = os.path.dirname(SOURCE_PATH)
SOURCE_PARENT = os.path.dirname(SOURCE_DIR)

# Import our local copy of the webarchive module
sys.path.insert(0, SOURCE_PARENT)
import webarchive


# Directory containing sample data
SAMPLE_DATA_DIR = os.path.join(SOURCE_PARENT, "webarchive", "sample_data")

# Path to our sample archive
# Source: https://en.wikipedia.org/wiki/Main_Page (CC BY-SA)
SAMPLE_ARCHIVE_PATH = os.path.join(SAMPLE_DATA_DIR, "Wikipedia.webarchive")


def run_test():
    with tempfile.TemporaryDirectory() as tmp_dir:
        output_path = os.path.join(tmp_dir, "Wikipedia.html")
        assert (not os.path.exists(output_path))

        # Load our sample archive
        archive = webarchive.open(SAMPLE_ARCHIVE_PATH)

        # Extract the archive, and assert that it succeeded
        archive.extract(output_path)
        assert os.path.isfile(output_path)

        # Open the converted page
        webbrowser.open(output_path)

        # Tell the user what to expect if the page rendered correctly
        print(textwrap.dedent("""\
            If the archive extracted correctly, your web browser should
            display the main page of the English Wikipedia with a featured
            article on P. G. Wodehouse."""))

        # Wait a few seconds for the browser to open and finish rendering
        # before we clean up the temporary directory
        time.sleep(10)


if __name__ == "__main__":
    run_test()
