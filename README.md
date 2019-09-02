**pywebarchive** is a Python 3 module for reading Apple's `.webarchive` files and extracting them to standard HTML documents. It's currently considered alpha-status code; the API is reasonably feature-complete, but it needs further testing, and likely still contains a few bugs.

Example usage:

```python
import webarchive
archive = webarchive.open("example.webarchive")
archive.extract("example.html")
```

For detailed documentation, try `python3 -m pydoc webarchive`.

The source distribution also includes two webarchive extraction tools:
* `extractor.py` is a command-line version.
* `extractor-gui.py` is a GUI version using Tkinter.
