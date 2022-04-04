# pywebarchive's Internals

This document provides a brief overview of how pywebarchive works and is organized internally. It is intended mainly for other programmers interested in working on pywebarchive's code.


## Design goals

pywebarchive's purpose is to convert webarchive files to standard HTML pages, which we refer to as "extracting" the webarchive. It follows the [Unix philosophy](https://en.wikipedia.org/wiki/Unix_philosophy) of "do one thing and do it well"; anything unrelated to this purpose is deliberately omitted.

The `webarchive` Python module that does the actual work is available for other programmers to use, since it might also be useful for other purposes. However, supporting other applications is a secondary concern.

pywebarchive aims to be small, simple, and self-contained. The `webarchive` module has no dependencies outside the Python standard library. The included extractor applications can use certain external libraries (see [README.md](README.md) or their source code for specifics), but these are generally optional.

Maintaining backwards compatibility is important, because other developers have better things to do than work around breaking changes in our code. To date, the only such change in pywebarchive's history was the removal of the clumsy and hastily-improvised API from our (little-used) very first release. Even then, this API's deprecation was announced well in advance, and we maintained compatibility code for nearly three years just to be safe.


## Coding style

pywebarchive aims to follow the guidelines in [PEP 8](https://peps.python.org/pep-0008/), with the following additional rules:

* String literals should use double quotes as is standard for American English, except for things like `'"'` that would require awkward escaping. (The PEP allows either single or double quotes.)
* Strings should be formatted using `str.format()` rather than `printf`-style formatting using the `%` operator. (The PEP does not take a stance on this, but the former has been identified elsewhere as the [preferred method](https://stackoverflow.com/questions/13451989/pythons-many-ways-of-string-formatting-are-the-older-ones-going-to-be-depre) for new code.)
* Line breaks should always come before binary operators, since they're easier to match with their operands that way. (The PEP allows either before or after, but recommends the latter for new code.)

pywebarchive's source code is well-commented. As a general rule, comments should be provided for anything that's not *immediately* obvious to someone looking at the code for the first time. Since it's especially easy for programmers to assume something is more obvious than it is, it's better to be explicit and err on the side of over-commenting. Comments explaining complex logic should use block formatting and full sentences.

The rules for comments also apply to docstrings. *All* classes, methods, and independent functions should include a docstring clearly explaining what they do and how to use them. That even applies to things that are only used internally, since people working on pywebarchive itself need to understand how those things work.


## Testing

pywebarchive includes extensive unit tests in [webarchive/test.py](webarchive/test.py). All new code should include tests for both expected behavior (ensuring things do work correctly when they should, such as a property returning the correct value) and any forseeable abnormal circumstances (checking that these are safely handled, such as raising an exception when trying to extract an archive with no resources).

In addition to unit tests, each new version of pywebarchive is manually tested before release with various webarchives saved by Safari from real-world sites. Unit tests can only prove converted pages *should* display correctly in theory; this manual check ensures they actually *do* in practice.

One weakness of the current test code is that it mainly tests for expected behavior; for example, pywebarchive could use more tests to confirm safe handling of invalidly-formatted webarchive files. Test coverage may also be limited for some components implemented before unit testing became pywebarchive's standard practice.


## Code organization

### Extractor applications

**[extractor.py](extractor.py)** is a command-line tool to convert webarchive files to standard HTML pages. It has no dependencies outside the standard library, and should run on any platform where Python is available. It also serves as the testbed for new features in the `webarchive` module like single-file extraction mode.

**[extractor-gui.py](extractor-gui.py)** is a graphical version of the above using Tkinter. This is the version that's provided pre-built for Microsoft Windows. It does not provide as many advanced `webarchive` module features as the command-line extractor, but is more complex internally because it uses a GUI toolkit and threading.

### The `webarchive` module

**[webarchive/\_\_init\_\_.py](webarchive/__init__.py)** mainly exports the public interfaces defined in other source modules.

**[webarchive/exceptions.py](webarchive/exceptions.py)** provides the `WebArchiveError` class, which is the exception raised when an error specific to pywebarchive occurs.

**[webarchive/test.py](webarchive/test.py)** provides unit tests for the `webarchive` module.

**[webarchive/util.py](webarchive/util.py)** provides various utility classes and functions for internal use. Among other things, these include functions for rewriting URL references to an archive's subresources (one of the more complex aspects of extracting a webarchive).

**[webarchive/webarchive.py](webarchive/webarchive.py)** defines the `WebArchive` class, which represents the contents of a webarchive file.

**[webarchive/webresource.py](webarchive/webresource.py)** defines the `WebResource` class, which represents an individual resource within a `WebArchive`.
