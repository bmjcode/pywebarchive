#!/usr/bin/env python3

"""WebArchive class implementation."""

import os
import sys
import io
import plistlib

from .webresource import WebResource


__all__ = ["WebArchive"]


class WebArchive(object):
    """Webarchive file reader.

    Pass the name of a .webarchive file as the constructor's path argument.
    """

    # WebMainResource
    # WebSubresources
    # WebSubframeArchives

    __slots__ = ["_main_resource", "_subresources", "_subframe_archives"]

    def __init__(self, path):
        """Return a new WebArchive."""

        self._main_resource = None
        self._subresources = []
        self._subframe_archives = []

        if path:
            # Read data from the specified webarchive file
            with io.open(path, "rb") as fp:
                archive = plistlib.load(fp)

                # Extract the main resource
                self._main_resource = WebResource(archive["WebMainResource"])

                # Extract subresources
                for res in archive["WebSubresources"]:
                    self._subresources.append(WebResource(res))

                # TODO: Process WebSubframeArchives

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
