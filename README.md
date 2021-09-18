**pywebarchive** is a Python 3 module for reading Apple's [webarchive](https://en.wikipedia.org/wiki/Webarchive) format.

The webarchive format is used by [Safari](https://www.apple.com/safari/) to save complete web pages -- including external resources like images, scripts, and style sheets -- in a single file. The archived page is both functionally and source-identical to the original: Not only does it display the same, but the underlying code matches byte for byte. However, because webarchive is a proprietary format, the archived page can only be opened in Safari.

pywebarchive allows other applications, including on non-Apple platforms, to process webarchive files. Applications can read archived content directly, or "extract" the webarchive by converting it to a standard HTML page. (The latter preserves function, but loses source-identicality.)

pywebarchive is stable enough for everyday use, but be aware that its support for the webarchive format is a work in progress. In particular, you may encounter issues with pages containing complex code or advanced HTML5 features.


## Webarchive Extractor

**Webarchive Extractor** is a tool to convert webarchives to standard HTML pages that can be opened in any web browser. This allows Windows and Linux/Unix users to open webarchive files, since Safari is not available on those platforms. Both graphical and command-line versions are available.

* Builds for Windows are available on the [releases page on GitHub](https://github.com/bmjcode/pywebarchive/releases).  These are standalone executables that run on Windows 7 and higher.
* The source code is included with pywebarchive.


## Information for Developers

Even though the software is called pywebarchive, the actual module you import is just `webarchive`.

Here's a simple demonstration of converting a webarchive to a standard HTML page:

```python
import webarchive
archive = webarchive.open("example.webarchive")
archive.extract("example.html")
```

The [command-line extractor tool](extractor.py) is basically just a fancy interface around the above code. If you're looking to integrate webarchive support in your own application, you might find the [unit tests](webarchive/test.py) more interesting, since they go more into what's actually inside the archive.

For detailed documentation, try `python3 -m pydoc webarchive`.
