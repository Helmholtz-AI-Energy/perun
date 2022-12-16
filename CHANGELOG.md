# Changelog

<!--next-version-placeholder-->

## v0.1.0-beta.18 (2022-12-16)
### Fix
* Endless action triggers, I remebered why that was there in the first place ([`672ee64`](https://github.com/Helmholtz-AI-Energy/perun/commit/672ee64867dda36fe2f8931c3d901a8d96d4f838))

## v0.1.0-beta.17 (2022-12-07)
### Feature
* Poetry hooks and installer configuration ([`6b222e1`](https://github.com/Helmholtz-AI-Energy/perun/commit/6b222e150a4ba179bf10178c36ceb7372c9d8e69))
* Net io counters from psutil ([`341c186`](https://github.com/Helmholtz-AI-Energy/perun/commit/341c1869c4cf4f1284068aadfb87422cc93a52b7))

### Fix
* Missing system path on cli monitor ([`c2b7b31`](https://github.com/Helmholtz-AI-Energy/perun/commit/c2b7b3131b3940c0c8b0092e75c0412bc5e8fa99))
* README title image url ([`fd5b2b8`](https://github.com/Helmholtz-AI-Energy/perun/commit/fd5b2b880bcbf176ea3fe1f02275d86188ea48db))
* Cmd line argument parsing for monitor subcommand ([`57e8744`](https://github.com/Helmholtz-AI-Energy/perun/commit/57e87440ccdd86a673f0769ad73abf4512025e73))

## v0.1.0-beta.16 (2022-09-20)
### Fix
* Catching influxdb import error ([`851bfb4`](https://github.com/Helmholtz-AI-Energy/perun/commit/851bfb4a574b8cab91ff08540b3090c3af337efe))

## v0.1.0-beta.15 (2022-09-19)
### Fix
* Relaxed dependencies (will tighten them later) ([`6509481`](https://github.com/Helmholtz-AI-Energy/perun/commit/650948170150eee242ae9bc78d1ea6bb1e9285b4))

## v0.1.0-beta.14 (2022-09-19)
### Fix
* Removed RAM_POWER from psutil backend ([`9ef751f`](https://github.com/Helmholtz-AI-Energy/perun/commit/9ef751f3784dcf1b065be79adc950d4bb0f0e22f))

## v0.1.0-beta.13 (2022-09-02)
### Feature
* Psutil backend ([`7d3aa61`](https://github.com/Helmholtz-AI-Energy/perun/commit/7d3aa61a4164463bec88343e2efb139464bc30ae))

## v0.1.0-beta.12 (2022-08-30)
### Feature
* Energy conversion to euro and co2e ([#17](https://github.com/Helmholtz-AI-Energy/perun/issues/17)) ([`ee89583`](https://github.com/Helmholtz-AI-Energy/perun/commit/ee8958357298780e285412360c33856a13ee49d5))

## v0.1.0-beta.11 (2022-08-29)
### Feature
* Configuration files ([#16](https://github.com/Helmholtz-AI-Energy/perun/issues/16)) ([`1035763`](https://github.com/Helmholtz-AI-Energy/perun/commit/1035763c2e66f2973180bceca52b7c0ef04d6f8b))

## v0.1.0-beta.10 (2022-08-24)
### Feature
* Serial hdf5 support ([#15](https://github.com/Helmholtz-AI-Energy/perun/issues/15)) ([`e9caa69`](https://github.com/Helmholtz-AI-Energy/perun/commit/e9caa69948eec4f6baf98807d7e4bcaf81700e8a))

## v0.1.0-beta.9 (2022-08-23)


## v0.1.0-beta.8 (2022-08-22)
### Feature
* Horeka options in cli and monitor decorator ([#13](https://github.com/Helmholtz-AI-Energy/perun/issues/13)) ([`0fde3cd`](https://github.com/Helmholtz-AI-Energy/perun/commit/0fde3cdcf8c489ff1b8ba4a985778c0e92a06cc6))

## v0.1.0-beta.7 (2022-08-17)
### Fix
* Extra typing imports for 3.8 support ([#12](https://github.com/Helmholtz-AI-Energy/perun/issues/12)) ([`28367a7`](https://github.com/Helmholtz-AI-Energy/perun/commit/28367a747015288e7a5bb09f3cdc97c96d0e4680))

## v0.1.0-beta.6 (2022-08-15)
### Documentation
* Expanded usage documentation ([`e2c0c2d`](https://github.com/Helmholtz-AI-Energy/perun/commit/e2c0c2dae77100a68fcab9c875f9c22efce4d149))

## v0.1.0-beta.5 (2022-08-11)
### Fix
* Missing report after monitor ([`5234a96`](https://github.com/Helmholtz-AI-Energy/perun/commit/5234a96292de553b57f4aaa82deb90153fe41ffc))

## v0.1.0-beta.4 (2022-08-11)
### Documentation
* Updated readme ([`75d10bb`](https://github.com/Helmholtz-AI-Energy/perun/commit/75d10bbbef942695c8505bb5863a71ae523fbe54))

## v0.1.0-beta.3 (2022-08-11)
### Fix
* Missing pyyaml dependency ([`3b8e74a`](https://github.com/Helmholtz-AI-Energy/perun/commit/3b8e74a3318bcac43398db3f86cc9be9da75ce5a))

## v0.1.0-beta.2 (2022-08-11)


## v0.1.0-beta.1 (2022-08-11)
### Feature
* Text, json and yaml reports ([`9503751`](https://github.com/Helmholtz-AI-Energy/perun/commit/95037516594189959fbfb2b2894d18cdba7b5819))
* Experiment run postprocessing ([`5e78804`](https://github.com/Helmholtz-AI-Energy/perun/commit/5e7880431aa513754ab6e61f2a9e30daac8aed69))
* Perun module emulates cli ([`8bfd029`](https://github.com/Helmholtz-AI-Energy/perun/commit/8bfd0290d453e51776b0e6df59743cd96e800bfe))
* Perun monitor decorator ([`167165c`](https://github.com/Helmholtz-AI-Energy/perun/commit/167165cbbcbea1ff3b2f566b5543c259ed73e5ad))
* Cmdline monitoring ([`d66bf8a`](https://github.com/Helmholtz-AI-Energy/perun/commit/d66bf8a751243e71fada5687dc2fe146de5612bc))
* Intel and nvida backends ([`b720d49`](https://github.com/Helmholtz-AI-Energy/perun/commit/b720d495c8a3dc1b77113a3febc8bda4f6b8c575))
* Initial commit ([`c8620bc`](https://github.com/Helmholtz-AI-Energy/perun/commit/c8620bc5e0f745323e5409b2dda4d26e5ef2ff21))

### Fix
* Semantic-release action ([`90caf3d`](https://github.com/Helmholtz-AI-Energy/perun/commit/90caf3d6817e42c21ad1f9d30a32038fe96c0362))
