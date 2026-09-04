# Changelog

## 1.2.0 [#14](https://github.com/singer-io/tap-onfleet/pull/14)
- Streams the credentials cannot access (HTTP 403) are now excluded from the catalog during discovery instead of raising an error.
- Added unit tests for discovery access-checking (`tests/unittests/test_discovery.py`).
- Bumped `requests` from `2.33.1` to `2.34.2`.

## 1.1.0
- Updated python version. [#11](https://github.com/singer-io/tap-onfleet/pull/11)
- Added unit and integration tests.

## 1.0.2
  * Bump dependencies [#10](https://github.com/singer-io/tap-onfleet/pull/10)

## 1.0.1
  * Dependabot update [#6](https://github.com/singer-io/tap-onfleet/pull/6)

## 1.0.0
  * Releasing from Beta --> GA
