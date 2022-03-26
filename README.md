**pywebarchive** is software for reading Apple's [webarchive](https://en.wikipedia.org/wiki/Webarchive) format.

A webarchive stores a complete web page -- including external media like images, scripts, and style sheets -- in a single file. It is most notable as the default format for the [Safari](https://www.apple.com/safari/) browser's "Save As" command, though other Apple software also uses it for various purposes.

pywebarchive consists of two main components: Webarchive Extractor, a tool to convert webarchives to standard HTML documents; and the `webarchive` Python module, which is the code "under the hood" that makes it all work.


## Webarchive Extractor

Webarchive Extractor converts webarchives to standard HTML documents. It allows opening webarchives on Windows and Linux/Unix systems, where Safari is not available.

### Downloads
File | Size | Description
---- | ---- | -----------
[Webarchive.Extractor.exe](https://github.com/bmjcode/pywebarchive/releases/download/v0.3.3/Webarchive.Extractor.exe) | 7.4 MB | Windows (32-bit, standalone)
[Webarchive.Extractor.x64.exe](https://github.com/bmjcode/pywebarchive/releases/download/v0.3.3/Webarchive.Extractor.x64.exe) | 8.1 MB | Windows (64-bit, standalone)
[pywebarchive-0.3.3.zip](https://github.com/bmjcode/pywebarchive/archive/refs/tags/v0.3.3.zip) | | source code (zip)
[pywebarchive-0.3.3.tar.gz](https://github.com/bmjcode/pywebarchive/archive/refs/tags/v0.3.3.tar.gz) | | source code (tar.gz)

### Notes
The Windows version runs on Windows 7 and higher. It is a standalone executable -- no installation required.

The pywebarchive source code includes both graphical ([extractor-gui.py](extractor-gui.py)) and command-line ([extractor.py](extractor.py)) versions of Webarchive Extractor. The graphical version requires Tkinter, and can optionally use [userpaths](https://github.com/bmjcode/userpaths). The command-line version should run on any system.

### Disclaimer
The download links above are intended for users looking at pywebarchive's GitHub page (https://github.com/bmjcode/pywebarchive). If you are reading this anywhere else, they may no longer point to the current version of pywebarchive; visit the GitHub page to ensure you are getting the latest and greatest.

If you *are* reading this on GitHub, note the download links here are for the most recent stable release. This may be older than the browseable code at the top of the page, which is the latest version in development.


## The `webarchive` module

`webarchive` is a Python module for reading the webarchive format. While its primary function is to power Webarchive Extractor, applications can also use it to examine webarchives directly.

The recommended way to install the `webarchive` module is [through PyPI](https://pypi.org/project/pywebarchive/). For detailed documentation, try `python3 -m pydoc webarchive`.
