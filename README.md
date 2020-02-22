**pywebarchive** is a Python 3 module for reading Apple's `.webarchive` files. It includes Webarchive Extractor, a tool to convert those files to standard HTML pages that you can open in any browser.

pywebarchive is stable enough for everyday use. It remains in alpha because its support for the `.webarchive` format is a work in progress; in particular, some pages using advanced HTML5 features may not convert perfectly.


## Webarchive Extractor

**Builds for Windows are available on the [releases page on GitHub](https://github.com/bmjcode/pywebarchive/releases).** These are standalone executables that run on Windows 7 and higher. On other platforms, Webarchive Extractor is included with the pywebarchive source code.


## Information for Developers

Here's an example of how to use the `webarchive` module:

```python
import webarchive
archive = webarchive.open("example.webarchive")
archive.extract("example.html")
```

For detailed documentation, try `python3 -m pydoc webarchive`.

The source distribution also includes two webarchive extraction tools:
* `extractor.py` is a command-line version.
* `extractor-gui.py` is a GUI version using Tkinter.
