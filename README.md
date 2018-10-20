**pywebarchive** is a Python 3 module for reading Apple's `.webarchive` files and extracting their contents to standard HTML documents. It is currently in the very early stages of development.

Example usage:

```python
import webarchive
archive = webarchive.open("example.webarchive")
archive.extract("example.html")
```

For detailed documentation, try `python -m pydoc webarchive`.
