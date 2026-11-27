# Changelog

## [Unreleased]

### Added

- Add a double-click Windows launcher that sets up the app's Python dependencies on first run.
- Add a manual GitHub Actions build that packages and uploads a standalone Windows executable.
- Filter trades by departure port after scanning markets.
- View stock and estimated single-crate prices for the selected port in the Port Market tab.
- Explain market and trade tables in the README and add hover help for controls, tabs, and table headings.
- Save player inputs locally and restore them on startup.
- Report total scan time and log the time spent querying regions, reading memory, matching signatures, and loading markets.
- Add offline regression tests and Ruff configuration for the Python 3.9 minimum.

### Changed

- Refresh the desktop UI with a dark theme and a wider trade table.
- Move market scanning off the UI thread and search for fixed bytes before checking the full signature.
- Separate the desktop UI, market logic, and player settings.

### Fixed

- Hide placeholder product slots from the market and trade tables while preserving scan offsets.
- Give scan status its own row so it does not overlap the departure-port selector.

## [v1.3.0] - 2025-10-13
### Added
- Sortable Columns. 
    Primary Sort on Origin and Destination Columns
    Secondary Sort on $Profit, $/Pound, and $/Item metrics
- Clean up and refactoring

## [v1.2.0] - 2025-10-12
### Added
- Support the 3 new Al Ankh islands. Old Ankh Town, Mirage Island and Saffron Island
- 2 New tradable items. Salt and Saffron

## [v1.1.0] - 2025-07-02
### Added
- Support for 2 new islands in latest Sailwind version
- 3 new tradeable items

### Fixed
- Fixed Emeralch Arch trades not showing because of a misname
- Removed Unneeded Library PSutil

## [v1.0.0] - 2025-06-29
### Added
- Initial release of Sailwind Market Watcher
- Trade route table and player settings input
