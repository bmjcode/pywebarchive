# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]
### Changed
* Don't delete the `srcset` attribute from `<img>`.
* Embed style sheets in single-file mode using data URIs rather than `<style>`.
### Fixed
* Handle `srcset` entries without a width or pixel density descriptor.

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

[Unreleased]: https://github.com/bmjcode/pywebarchive/compare/v0.3.0...HEAD
[0.3.0]: https://github.com/bmjcode/pywebarchive/compare/v0.2.4...v0.3.0
[0.2.4]: https://github.com/bmjcode/pywebarchive/compare/v0.2.3...v0.2.4
[0.2.3]: https://github.com/bmjcode/pywebarchive/compare/v0.2.2...v0.2.3
[0.2.2]: https://github.com/bmjcode/pywebarchive/compare/v0.2.1...v0.2.2
[0.2.1]: https://github.com/bmjcode/pywebarchive/compare/v0.1.1...v0.2.1
[0.1.1]: https://github.com/bmjcode/pywebarchive/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/bmjcode/pywebarchive/releases/tag/v0.1.0
