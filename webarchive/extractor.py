#!/usr/bin/env python3

"""Webarchive extractor implementation."""

import os
import sys

from .webarchive import WebArchive


__all__ = ["Extractor"]


def Extractor(archive):
    """Do not use. Functionality moved to WebArchive.extract().

    This is present to maintain backwards compatibility with the
    poorly-thought-out API in version 0.1.0, the first public release.
    """

    return archive


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

    # Extract the archive
    archive = WebArchive(archive_path)
    archive.extract(output_path)
