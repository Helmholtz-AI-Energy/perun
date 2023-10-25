# CHANGELOG




## v0.5.0 (2023-10-25)


### Feature

* feat: ROCM Backend (#82)

* feat: rocm backend

* fix: amd gpu correct handle

* [pre-commit.ci] pre-commit autoupdate (#81)

updates:
- [github.com/commitizen-tools/commitizen: 3.6.0 → 3.10.0](https://github.com/commitizen-tools/commitizen/compare/3.6.0...3.10.0)
- [github.com/psf/black: 23.7.0 → 23.9.1](https://github.com/psf/black/compare/23.7.0...23.9.1)
- [github.com/pre-commit/pre-commit-hooks: v4.4.0 → v4.5.0](https://github.com/pre-commit/pre-commit-hooks/compare/v4.4.0...v4.5.0)

Co-authored-by: pre-commit-ci[bot] &lt;66853113+pre-commit-ci[bot]@users.noreply.github.com&gt;
Co-authored-by: JuanPedroGHM &lt;juanpedroghm@gmail.com&gt;

---------

Co-authored-by: pre-commit-ci[bot] &lt;66853113+pre-commit-ci[bot]@users.noreply.github.com&gt; ([`229f1e2`](https://github.com/Helmholtz-AI-Energy/perun/commit/229f1e2e6c019a2d4e6100610102b4be4b4b9a16))


### Fix

* fix: another typo ([`f6537cc`](https://github.com/Helmholtz-AI-Energy/perun/commit/f6537ccbfd293dac5972e96cf2e2f85a14819cc2))


### Refactor

* refactor: Click -&gt; Argparse (#80) ([`8755b73`](https://github.com/Helmholtz-AI-Energy/perun/commit/8755b7365324db6451f2ce3a97bee6bc5ab0918b))

## v0.4.0 (2023-08-18)


### Feature

* feat: Perun Singleton Class


BREAKING CHANGE:
Rework of main perun modules to enable regions.
Deprecated old monitor decorator in favour of &#39;function monitoring&#39;
Changes to output files, always produces a hdf5, and an optional second file (default text report)

Individual Commits
* wip: created perun class, created singleton decorator, removed backend decorator
* wip: removed _cached_sensors_config from coordination, handled by perun class
* wip: perun class progress, removed decorator
* wip: decorator is back on (sadly), started export command refactoring
* refactor: export command and configuration options (removed depth and raw options)
* refactor: changed api, removed bench prefix, commeted decorator out
* fix: corrections in suprocess and backends
* refactor: return to single file that acumulates everything, but slightly different
* fix: intel_rapl dram max value, wrong overwriting of hdf5 file
* wip: regions
* feat: regions
* fix: overlapping id correction
* refactor: metadata storage
* feat: actual regions
* refactor: io formating
* fix: io fixes
* fix: regions metric units, dependencies
* fix: gpu utilization and memory
* fix: formatting
* fix: missing total run node.
* wip:update docs
* docs: updated docs
* test: updated tests
* ci: appeasing mypy
* [pre-commit.ci] auto fixes from pre-commit.com hooks for more information, see https://pre-commit.ci
* ci: pydocstyle ignores docs/
---------

Co-authored-by: io3047@kit.edu &lt;io3047@hkn1990.localdomain&gt;
Co-authored-by: pre-commit-ci[bot] &lt;66853113+pre-commit-ci[bot]@users.noreply.github.com&gt; ([`574b340`](https://github.com/Helmholtz-AI-Energy/perun/commit/574b3408ad5e9d7ce9cde5d16ae7ae95e9c53b83))


## v0.3.3 (2023-07-24)


### Documentation

* docs: OpenSSF badge ([`bebc329`](https://github.com/Helmholtz-AI-Energy/perun/commit/bebc3296fbcaf621c5af34aaf6326c8c5b9a8e8e))


## v0.3.2 (2023-06-02)


## v0.3.1 (2023-06-01)


### Documentation

* docs: updated fair badge ([`827557d`](https://github.com/Helmholtz-AI-Energy/perun/commit/827557d5ffd0828cb168577d471219fe1e7fcee1))

* docs: Zenodo badge ([`c1043c5`](https://github.com/Helmholtz-AI-Energy/perun/commit/c1043c563166aedeef51da4c5c64ea8323836d31))


## v0.3.0 (2023-05-31)


### Documentation

* docs: fair-software badge (#47)

* docs: fair-software action

* docs: added fair badge to readme

* docs: more badges

* fix: badge formating

* docs: downloads badge

* ci: limit fair action to pushes to main ([`34585cd`](https://github.com/Helmholtz-AI-Energy/perun/commit/34585cd8f3d353c1e2591a498004677a8315864c))


### Feature

* feat: extra host metadata ([`f576046`](https://github.com/Helmholtz-AI-Energy/perun/commit/f57604625e3072391e76a55945dce63d72e038b2))


## v0.2.0 (2023-03-28)


### Documentation

* docs: update README.md

* 0.1.1

0.1.1 [skip ci]

* docs: updated readme

* docs: data structure image

* docs: code snipet correction

---------

Co-authored-by: github-actions &lt;github-actions@github.com&gt; ([`7880070`](https://github.com/Helmholtz-AI-Energy/perun/commit/7880070307497cb213effd2d1387afbd88435e99))


## v0.1.1 (2023-03-22)


## v0.1.0 (2023-03-17)


### Ci

* ci: test action trigger on anything except on release ([`ea76a8c`](https://github.com/Helmholtz-AI-Energy/perun/commit/ea76a8cb9baa5afaf57f308133151ff0dcb7dd34))


## v0.1.0-beta.18 (2022-12-16)


## v0.1.0-beta.17 (2022-12-07)


### Test

* test: mocked backend, tested assignedDevices ([`9aa805d`](https://github.com/Helmholtz-AI-Energy/perun/commit/9aa805d5d2e8c0b709d640f6a8663f6120532a2c))


## v0.1.0-beta.16 (2022-09-20)


## v0.1.0-beta.15 (2022-09-19)


### Fix

* fix: relaxed dependencies (will tighten them later) ([`6509481`](https://github.com/Helmholtz-AI-Energy/perun/commit/650948170150eee242ae9bc78d1ea6bb1e9285b4))


## v0.1.0-beta.14 (2022-09-19)


## v0.1.0-beta.13 (2022-09-02)


## v0.1.0-beta.12 (2022-08-30)


## v0.1.0-beta.11 (2022-08-29)


## v0.1.0-beta.10 (2022-08-24)


## v0.1.0-beta.9 (2022-08-23)


## v0.1.0-beta.8 (2022-08-22)


### Ci

* ci: v3

python-semantic-release
Github needs a better action editor ([`e2f38e5`](https://github.com/Helmholtz-AI-Energy/perun/commit/e2f38e5281ea510694f6f58b04824cb8a589ea65))


## v0.1.0-beta.7 (2022-08-17)


## v0.1.0-beta.6 (2022-08-15)


### Documentation

* docs: expanded usage documentation ([`e2c0c2d`](https://github.com/Helmholtz-AI-Energy/perun/commit/e2c0c2dae77100a68fcab9c875f9c22efce4d149))


## v0.1.0-beta.5 (2022-08-11)


### Fix

* fix: missing report after monitor ([`5234a96`](https://github.com/Helmholtz-AI-Energy/perun/commit/5234a96292de553b57f4aaa82deb90153fe41ffc))


## v0.1.0-beta.4 (2022-08-11)


### Documentation

* docs: updated readme ([`75d10bb`](https://github.com/Helmholtz-AI-Energy/perun/commit/75d10bbbef942695c8505bb5863a71ae523fbe54))


## v0.1.0-beta.3 (2022-08-11)


## v0.1.0-beta.2 (2022-08-11)


## v0.1.0-beta.1 (2022-08-11)


### Feature

* feat: text, json and yaml reports ([`9503751`](https://github.com/Helmholtz-AI-Energy/perun/commit/95037516594189959fbfb2b2894d18cdba7b5819))

