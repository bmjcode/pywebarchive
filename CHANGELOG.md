# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]
### Added
* Support for extracting webarchives to single-file HTML documents.
  * External scripts and style sheets are replaced with inline content.
  * External images are embedded using data URIs.
### Changed
* Made single-file extraction mode the default.

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
### Changed
* API improvements and bugfixes; no new features added.

## [0.1.0] - 2018-10-16
### Added
* Initial public release.

[Unreleased]: https://github.com/bmjcode/pywebarchive/compare/v0.2.4...HEAD
[0.2.4]: https://github.com/bmjcode/pywebarchive/compare/v0.2.3...v0.2.4
[0.2.3]: https://github.com/bmjcode/pywebarchive/compare/v0.2.2...v0.2.3
[0.2.2]: https://github.com/bmjcode/pywebarchive/compare/v0.2.1...v0.2.2
[0.2.1]: https://github.com/bmjcode/pywebarchive/compare/v0.1.1...v0.2.1
[0.1.1]: https://github.com/bmjcode/pywebarchive/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/bmjcode/pywebarchive/releases/tag/v0.1.0
