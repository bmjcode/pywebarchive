# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.5.2] - 2023-09-24
### Changed
* Improved handling of empty attribute values (`<img alt="">`) and valueless attributes (`<iframe seamless>`).

## [0.5.1] - 2022-10-08
### Fixed
* Document the function of the `WebResource.frame_name` property.

## [0.5.0] - 2022-04-16
### Added
* More complete documentation for the `WebArchive` and `WebResource` classes.
* Documentation on [pywebarchive's internals](INTERNALS.md).
* Unit test for subresource URLs occurring as literal text.
### Changed
* Massively overhaul the [README](README.md).
* Improved the documentation for the `webarchive` module.
* Expanded and clarified various code comments.
* Use a `with` clause for proper cleanup in [test/extracted\_archive\_display.py](test/extracted_archive_display.py).
* Rename `WebArchive.extract()`'s `single_file` argument to the more descriptive `embed_subresources` *(potentially backwards-incompatible change)*.
### Fixed
* Raise a `WebArchiveError` when attempting to extract a webarchive with no main resource.
* Raise a `WebArchiveError` when attempting to convert a webarchive with no main resource to HTML.
* Return the correct value for `WebArchive.resource_count()` if no main resource is present.
### Removed
* The unnecessary `<!-- Processed by pywebarchive -->` tag previously added to extracted pages.

## [0.4.1] - 2022-03-26
### Fixed
* Call `close()` in `WebArchive.__exit__()`.

## [0.4.0] - 2022-03-26
### Added
* Context manager (`with` statement) support in the `WebArchive` class.
* The `WebArchive.close()` method.
* The `WebArchive.parent` property.
* Support for the `mode` argument in `webarchive.open()` (though only read mode remains implemented).
### Changed
* Further cleaned up internal APIs.
* Improved module documentation.
### Fixed
* Ensure an encoding is always specified when creating a text `WebResource`.
* Removed duplicated code in [test/extracted\_archive\_display.py](test/extracted_archive_display.py).

## [0.3.3] - 2021-11-05
### Added
* Unit tests for HTML- and CSS-rewriting logic.
* Build script for the Windows version of Webarchive Extractor.
### Changed
* Clean up the `WebResource` class's internal API.
* Do not force a newline after the doctype in `HTMLRewriter.handle_decl()`.
* Moved `test_extracted_archive_display` from the unit tests to a separate script.
* Removed `test_extracted_archive_display`'s dependency on Tkinter.
### Fixed
* Rewrite URLs in inline CSS code when extracting.

## [0.3.2] - 2021-09-26
### Added
* The module version number in `webarchive.__version__`.
* Initial support for command-line arguments in `extractor-gui.py`.
* The `--version` argument in `extractor.py` and `extractor-gui.py`.
### Changed
* Further code cleanup.
* Give more descriptive names to various internals.
### Fixed
* Support HTML subresources.
* Handle non-HTML subresources incorrectly served as `text/html`.
* Update the module description in `setup.py` to match its documentation.
* Specify a text encoding in `WebArchiveTest.test_webarchive_to_html()` so the test will pass on Windows.
* Make `webbrowser` an optional dependency in `extractor.py` to match `extractor-gui.py`.

## [0.3.1] - 2021-09-25
### Added
* Unit test for `WebArchive.to_html()`.
### Changed
* Massively expanded module documentation.
* Don't delete the `srcset` attribute from `<img>`.
* Embed style sheets in single-file mode using data URIs rather than `<style>`.
* Cleaned up various internals.
### Fixed
* Handle `srcset` entries without a width or pixel density descriptor.
* Embed subresources recursively when calling `WebResource.to_data_uri()` on an archive's main resource.
* Don't escape HTML entities in a `<script>` or `<style>` block.
* Correctly handle non-HTML main resources.

## [0.3.0] - 2021-07-18
### Added
* Experimental support for extracting webarchives to single-file HTML documents.
  * External scripts and style sheets are replaced with inline content.
  * External images are embedded using data URIs.
* New command-line options for `extractor.py`:
  * `-s` / `--single-file` to extract archive contents to a single HTML file.
  * `-o` / `--open-page` to open the extracted webpage when finished.
* New `WebArchive` class methods:
  * `get_local_path()` returns the basename of the file created when a specified subresource is extracted.
  * `get_subframe_archive()` returns the subframe archive corresponding to a specified URL.
  * `get_subresource()` returns the subresource corresponding to a specified URL.
  * `to_html()` returns the archive's contents as a single-file HTML document.
* The `WebResource.archive` property, which identifies a given resource's parent `WebArchive`.
* The `WebArchiveError` exception.
### Changed
* Moved the development status up to beta.
### Fixed
* Correctly handle "empty" tags like `<img />` in XHTML documents.
* Fixed local resource paths for extracted subframe archives.
### Removed
* The `Extractor` class, included only for backwards compatibility with the poorly thought-out 0.1.0 API.

## [0.2.4] - 2020-02-22
### Added
* Unit tests.
### Changed
* `extractor-gui.py` can now open converted files on non-Windows platforms.

## [0.2.3] - 2019-09-02
### Changed
* Code cleanup release; no user-visible changes.

## [0.2.2] - 2018-10-21
### Fixed
* Various bugfixes, mainly involving subframe archives.

## [0.2.1] - 2018-10-20
### Added
* Graphical extraction tool.
* Support for subframe archives.
### Fixed
* Various bugfixes.

**Note**: Version 0.2.0 was pulled shortly after posting due to problems with its `setup.py` script.

## [0.1.1] - 2018-10-19
### Added
* The `open()` function as the preferred way to open a WebArchive.
### Changed
* Moved extraction into the main `WebArchive` class.
* Massive internal cleanup.
### Deprecated
* The `Extractor` class from the poorly thought-out initial API.

## [0.1.0] - 2018-10-16
### Added
* Initial public release.

[Unreleased]: https://github.com/bmjcode/pywebarchive/compare/v0.5.2...HEAD
[0.5.2]: https://github.com/bmjcode/pywebarchive/compare/v0.5.1...v0.5.2
[0.5.1]: https://github.com/bmjcode/pywebarchive/compare/v0.5.0...v0.5.1
[0.5.0]: https://github.com/bmjcode/pywebarchive/compare/v0.4.1...v0.5.0
[0.4.1]: https://github.com/bmjcode/pywebarchive/compare/v0.4.0...v0.4.1
[0.4.0]: https://github.com/bmjcode/pywebarchive/compare/v0.3.3...v0.4.0
[0.3.3]: https://github.com/bmjcode/pywebarchive/compare/v0.3.2...v0.3.3
[0.3.2]: https://github.com/bmjcode/pywebarchive/compare/v0.3.1...v0.3.2
[0.3.1]: https://github.com/bmjcode/pywebarchive/compare/v0.3.0...v0.3.1
[0.3.0]: https://github.com/bmjcode/pywebarchive/compare/v0.2.4...v0.3.0
[0.2.4]: https://github.com/bmjcode/pywebarchive/compare/v0.2.3...v0.2.4
[0.2.3]: https://github.com/bmjcode/pywebarchive/compare/v0.2.2...v0.2.3
[0.2.2]: https://github.com/bmjcode/pywebarchive/compare/v0.2.1...v0.2.2
[0.2.1]: https://github.com/bmjcode/pywebarchive/compare/v0.1.1...v0.2.1
[0.1.1]: https://github.com/bmjcode/pywebarchive/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/bmjcode/pywebarchive/releases/tag/v0.1.0
