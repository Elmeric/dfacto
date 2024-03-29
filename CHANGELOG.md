All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog], and this project adheres
to [Semantic Versioning].

## [Unreleased]

## [1.2.0] - 2023-08-03

### Fixed
- Old invoices are no more updated when editing the invoice global parameters

### Changed
- Add a settings editor
- Add an invoice global parameters editor

### Miscellaneous
- Bump all dependencies to their latest version

## [1.1.1] - 2023-07-20

### Fixed
- Fix wrong path to translation files in production mode

## [1.1.0] - 2023-07-18

### Fixed
- ESC key do no more close the application if production mode

### Changed
- Ask for the UI language to use at startup if none set in the settings file

### Documentation

### Miscellaneous
- Separate general initializations outside the gui modules
- Refactor code to support strings internationalization and currency, date and number localization
- Bump all dependencies to their latest version

## [1.0.0] - 2023-06-20

- First release.


[unreleased]: https://github.com/Elmeric/dfacto/compare/v1.2.0...HEAD
[1.2.0]: https://github.com/Elmeric/dfacto/compare/v1.1.1...v1.2.0
[1.1.1]: https://github.com/Elmeric/dfacto/compare/v1.1.0...v1.1.1
[1.1.0]: https://github.com/Elmeric/dfacto/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/Elmeric/dfacto/compare/v0.0.1...v1.0.0

[Keep a Changelog]: https://keepachangelog.com/en/1.0.0/
[Semantic Versioning]: https://semver.org/spec/v2.0.0.html
