pywebarchive is software for reading Apple's [webarchive](https://en.wikipedia.org/wiki/Webarchive) format. It consists of two pieces:

* **Webarchive Extractor** converts webarchive files to standard pages you can open in any browser.
* **The `webarchive` Python module** is the code "under the hood" that makes the Extractor work. It's available for other applications to use, too.

pywebarchive is open-source software released under the permissive [MIT License](LICENSE). Development takes place [on GitHub](https://github.com/bmjcode/pywebarchive).


## Features

* Available for Windows, macOS, and Linux
* Converts webarchive files to plain HTML
* Handles images, scripts, and style sheets
* Converted pages display just like they would in Safari (apart from normal cross-browser rendering differences)


## Downloads

File | Size | Description
---- | ---- | -----------
[Webarchive.Extractor.exe](https://github.com/bmjcode/pywebarchive/releases/download/v0.4.1/Webarchive.Extractor.exe) | 7.3 MB | Webarchive Extractor for 32-bit Windows
[Webarchive.Extractor.x64.exe](https://github.com/bmjcode/pywebarchive/releases/download/v0.4.1/Webarchive.Extractor.x64.exe) | 8.0 MB | Webarchive Extractor for 64-bit Windows
[pywebarchive-0.4.1.zip](https://github.com/bmjcode/pywebarchive/archive/refs/tags/v0.4.1.zip) | | source code (zip)
[pywebarchive-0.4.1.tar.gz](https://github.com/bmjcode/pywebarchive/archive/refs/tags/v0.4.1.tar.gz) | | source code (tar.gz)

The Windows version of Webarchive Extractor runs on Windows 7 and higher. It is a portable application -- it doesn't require installation, and won't write to Application Data or the Windows Registry.

On macOS and Linux (and Windows with [Python](https://www.python.org/) installed), you can run Webarchive Extractor directly from the source code. Both command-line ([extractor.py](extractor.py)) and graphical ([extractor-gui.py](extractor-gui.py)) versions are included.

If you're a Python developer, you can also [install the `webarchive` module from PyPI](https://pypi.org/project/pywebarchive/) using `pip install pywebarchive`. Note the module you `import` is just `webarchive`, but the package you *install* is `pywebarchive`; this is because an [unrelated project](https://pypi.org/project/webarchive/) already claimed the shorter package name.


## Requirements

* Python 3
* Tkinter (only required by [extractor-gui.py](extractor-gui.py))
* [userpaths](https://pypi.org/project/userpaths/) (optional; used by [extractor-gui.py](extractor-gui.py) if available)


## More information

Webarchive is the default format for the "Save As" command in Apple's Safari browser. (Other Apple software also uses it internally for various purposes.) Its main advantage is that it can save all the content on a webpage -- including external media like images, scripts, and style sheets -- in a single file. However, the webarchive format is proprietary and not publicly documented, and most other browsers cannot open webarchive files. pywebarchive solves this by converting webarchive files to standard HTML pages, which can be opened in any browser or editor.

The name "pywebarchive" simply reflects that this is webarchive-handling software written in the Python programming language.

pywebarchive follows the [Unix philosophy](https://en.wikipedia.org/wiki/Unix_philosophy) of "do one thing and do it well". With that in mind, pywebarchive deliberately omits all features unrelated to its purpose of converting webarchive files so other browsers can open them. In particular, pywebarchive does *not* support writing webarchive files, and there are no plans to add this in a future release.

[pywebarchive's internals](INTERNALS.md) are fairly well-documented. The code includes extensive comments explaining how it works and why it does various things the way it does. In addition, pywebarchive features dozens of [unit tests](webarchive/test.py) to ensure the code actually does what we think it does, which is further confirmed by manual testing before each release.
