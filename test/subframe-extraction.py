#!/usr/bin/env python3

"""Test script for subframe archive extraction."""

import os
import sys

# Look for the webarchive module in the parent directory
sys.path.insert(0, "..")

import webarchive

if len(sys.argv) >= 2:
    in_path = sys.argv[1]
    root, base = os.path.split(in_path)
    base, ext = os.path.splitext(base)

else:
    print("Usage: {0} filename.webarchive".format(sys.argv[0]),
          file=sys.stderr)
    sys.exit(1)

archive = webarchive.open(in_path)
sf_num = 1

for subframe_archive in archive.subframe_archives:
    out_path = os.path.join(root,
                            "{0}.subframe{1:03}.html".format(base, sf_num))
    subframe_archive.extract(out_path)

    sf_num += 1
