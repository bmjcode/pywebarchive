**pywebarchive** is a Python module for reading Apple's `.webarchive` files. It is currently in the very early stages of development.

It provides the `webarchive` module, which consists of two main classes:

* `WebArchive`, to read `.webarchive` files
* `Extractor`, to extract a `WebArchive` to a standard HTML document

Individual resources (i.e., files) in a `WebArchive` are represented by `WebResource` objects.

pywebarchive requires Python 3; there are no current plans to add Python 2 support.

Example usage:

```python
from webarchive import WebArchive, Extractor

archive = WebArchive("example.webarchive")

extractor = Extractor(archive)
extractor.extract("example.html")
```

For detailed documentation, try `python -m pydoc webarchive`.
