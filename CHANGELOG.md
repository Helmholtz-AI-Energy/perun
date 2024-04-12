# CHANGELOG


## v0.6.1 (2024-03-19)


### Ci

* ci: semantic release configuration ([`3273893`](https://github.com/Helmholtz-AI-Energy/perun/commit/3273893629297eabdb1d799d74273a31b97f0e9b))


### Documentation

* docs: upgraded changelog generator config ([`1713ae7`](https://github.com/Helmholtz-AI-Energy/perun/commit/1713ae75eb49296e57718899e0dbafd2b3169277))

* docs: update changelog ([`e982a41`](https://github.com/Helmholtz-AI-Energy/perun/commit/e982a41aef50dee0aa7f65ffedf3829cf9b7c8c7))

* docs: upgraded changelog generator config ([`7969885`](https://github.com/Helmholtz-AI-Energy/perun/commit/79698852c6c2609457d023771fe8517d3d7a71aa))

* docs: update changelog ([`fda6c9c`](https://github.com/Helmholtz-AI-Energy/perun/commit/fda6c9c01a21995410473183f7c65f373ae4c479))

* docs: post-release merge ([`e1416ed`](https://github.com/Helmholtz-AI-Energy/perun/commit/e1416ed2d54ea267cd6237f6f3aa215b7cd0f13d))


### Fix

* fix: more control over MPI initialization (#113) ([`cad182c`](https://github.com/Helmholtz-AI-Energy/perun/commit/cad182ce7f99ff9188deeb020e4cbde5973b7eb2))

* fix: fixed configuration hierarchy (#112) ([`978a364`](https://github.com/Helmholtz-AI-Energy/perun/commit/978a364e2c6ca9c7d175b4ff41832add5d28a3e6))

* fix: cli `--app_name` argument gets priority ([`03eb84e`](https://github.com/Helmholtz-AI-Energy/perun/commit/03eb84edb1506162a8d20450c012bf34adb3efd0))

* fix: fixed configuration hierarchy (#112) ([`b19e845`](https://github.com/Helmholtz-AI-Energy/perun/commit/b19e8459c6d204b54bfbdc54aeb32a867ebcb158))

* fix: cli `--app_name` argument gets priority ([`fa4c5d2`](https://github.com/Helmholtz-AI-Energy/perun/commit/fa4c5d248fb6e11b275f5f97852ef2e1afdf7b77))


## v0.6.0 (2024-03-18)


### Build

* build(deps): bump pillow from 10.0.1 to 10.2.0 in /examples/torch_mnist (#103) ([`c58c831`](https://github.com/Helmholtz-AI-Energy/perun/commit/c58c831e785f54ecc2a148c27f40d4837f816581))

* build: pre-commit autoupdate (#102) ([`0af0896`](https://github.com/Helmholtz-AI-Energy/perun/commit/0af0896dd946fde192e00bc1018cfaebc4732783))

* build(deps): bump jinja2 from 3.1.2 to 3.1.3 in /examples/torch_mnist (#101) ([`5907f17`](https://github.com/Helmholtz-AI-Energy/perun/commit/5907f17edf1b6d141953b087020f1c2e556e6255))


### Ci

* ci: pre-commit cff validation hook (#98) ([`5b6aab1`](https://github.com/Helmholtz-AI-Energy/perun/commit/5b6aab1e7a25f3e44a048f93cd17ba9b96b358ba))


### Feature

* feat: Monitor Decorator is back! (#106) ([`8253416`](https://github.com/Helmholtz-AI-Energy/perun/commit/825341694ed403988c393d4d541a53b6e13da480))

* feat: Postprocess Callback (#100) ([`aecaaa5`](https://github.com/Helmholtz-AI-Energy/perun/commit/aecaaa5cc1d2ce29ae7acb231d6e135b5482d365))


### Fix

* fix: changed psutil memory reading from active to used (#109) ([`1838f2b`](https://github.com/Helmholtz-AI-Energy/perun/commit/1838f2b5a4b516604dee1714946c552fb574fcaf))


## v0.5.0 (2023-10-25)


### Ci

* ci: release action security corrections (#96) ([`a02a4c1`](https://github.com/Helmholtz-AI-Energy/perun/commit/a02a4c135a5f32f20dc4942254244d00988d8969))

* ci: Non main branch referenced in release workflow ([`9f95fd3`](https://github.com/Helmholtz-AI-Energy/perun/commit/9f95fd346dd61b984b1438f5b172b51631b4dff5))

* ci: new release pipeline (#84) ([`97e1464`](https://github.com/Helmholtz-AI-Energy/perun/commit/97e14649a71f6cb95fbd5d0cf8c2e8a73f29fb3e))


### Documentation

* docs: Create CITATION.cff and citation section in README ([`910228f`](https://github.com/Helmholtz-AI-Energy/perun/commit/910228fcefd3811299c789169c08c6ad4a0ef764))

* docs: Torch MNIST example scripts with instructions (#63) ([`fc07d2f`](https://github.com/Helmholtz-AI-Energy/perun/commit/fc07d2f02f5278721cdbab8a0f39a40a6ca7128d))


### Feature

* feat: better overhead power integration (#95) ([`4a0c984`](https://github.com/Helmholtz-AI-Energy/perun/commit/4a0c98457dd8d661829b0f6e0799ea8509e262ca))

* feat: sorted text output by host/function (#83) ([`56959e6`](https://github.com/Helmholtz-AI-Energy/perun/commit/56959e68d6428888dcf48d43c514bfaa626411ef))

* feat: ROCM Backend (#82) ([`229f1e2`](https://github.com/Helmholtz-AI-Energy/perun/commit/229f1e2e6c019a2d4e6100610102b4be4b4b9a16))


### Fix

* fix: explicit utf-8 encoding in text report (#90) ([`e14b8a8`](https://github.com/Helmholtz-AI-Energy/perun/commit/e14b8a837ba741ecfca3c20a4c40fc8c31c330d1))

* fix: Better error handling in MPI context (#86) ([`93e50fb`](https://github.com/Helmholtz-AI-Energy/perun/commit/93e50fbe06a17e0c405e9628081d8569336265a1))

* fix: regions don&#39;t stop warmup rounds ([`73cd82a`](https://github.com/Helmholtz-AI-Energy/perun/commit/73cd82a829c4ad19201be48b8b06f1db1f0971cf))

* fix: another typo ([`f6537cc`](https://github.com/Helmholtz-AI-Energy/perun/commit/f6537ccbfd293dac5972e96cf2e2f85a14819cc2))

* fix: typo in text report ([`320cbe0`](https://github.com/Helmholtz-AI-Energy/perun/commit/320cbe061010147e7df65163a711ad7384879e09))


### Refactor

* refactor: Click -&gt; Argparse (#80) ([`8755b73`](https://github.com/Helmholtz-AI-Energy/perun/commit/8755b7365324db6451f2ce3a97bee6bc5ab0918b))

## v0.4.0 (2023-08-18)


### Feature

* feat: Perun Singleton Class ([`574b340`](https://github.com/Helmholtz-AI-Energy/perun/commit/574b3408ad5e9d7ce9cde5d16ae7ae95e9c53b83))


## v0.3.3 (2023-07-24)


### Ci

* ci: persist credentials ([`b75d939`](https://github.com/Helmholtz-AI-Energy/perun/commit/b75d9397de9eb3d654892b974123a58af4f307eb))

* ci: let&#39;s try with a personal access token (classic) ([`3d891bd`](https://github.com/Helmholtz-AI-Energy/perun/commit/3d891bd8f5aea00e8386256caa97dd2cf689fff8))

* ci: configured permission for checkout actions ([`9130762`](https://github.com/Helmholtz-AI-Energy/perun/commit/913076252923cb5ccac8023f737d2712fbd08389))

* ci: pedantic configuration files ([`fda1c2f`](https://github.com/Helmholtz-AI-Energy/perun/commit/fda1c2fdfbef93ccc365fe84fca9a3fb29bca8d1))

* ci: lets try some renaming ([`5290eb4`](https://github.com/Helmholtz-AI-Energy/perun/commit/5290eb442ef6cb84fd29865bc3e81929b40756f2))

* ci: invalid github token reference in semantic release action ([`6b0ff2d`](https://github.com/Helmholtz-AI-Energy/perun/commit/6b0ff2da22b96b4d6df9abea2e1dd35e5e150910))

* ci: missing permission in semantic_release.yml ([`53db22d`](https://github.com/Helmholtz-AI-Energy/perun/commit/53db22d3d225557be9226f2169db4cc7045d812d))

* ci: corrected semantic release action path ([`74cc31d`](https://github.com/Helmholtz-AI-Energy/perun/commit/74cc31d1e3f05bea153c387ab9d489ee0a081f3f))

* ci: updated semantic_release.yml ([`c7950b1`](https://github.com/Helmholtz-AI-Energy/perun/commit/c7950b1c9f9049464039ec8d944d0446e556da65))

* ci: updated semantic_release.yml ([`27c4b8a`](https://github.com/Helmholtz-AI-Energy/perun/commit/27c4b8abe1aeaf558ed0f78f272ea2c832792d3d))


### Documentation

* docs: completed fair-software badge ([`9b00eda`](https://github.com/Helmholtz-AI-Energy/perun/commit/9b00edab1995715cdf5a70dc6ac864edb4d87942))

* docs: OpenSSF badge ([`bebc329`](https://github.com/Helmholtz-AI-Energy/perun/commit/bebc3296fbcaf621c5af34aaf6326c8c5b9a8e8e))


### Fix

* fix: nvidia-ml-py compatibility ([`ab2335f`](https://github.com/Helmholtz-AI-Energy/perun/commit/ab2335f48d6de965aba19924500e5398455d804d))


## v0.3.2 (2023-06-02)


### Fix

* fix: overflow in byte calculation ([`bf375de`](https://github.com/Helmholtz-AI-Energy/perun/commit/bf375de8bd8170ddc67fa92fd250553d93b4b0d2))

* fix: closing rapl files to early ([`e570531`](https://github.com/Helmholtz-AI-Energy/perun/commit/e5705319b400b31a69b033f804d69c947d88a25f))


## v0.3.1 (2023-06-01)


### Documentation

* docs: updated fair badge ([`827557d`](https://github.com/Helmholtz-AI-Energy/perun/commit/827557d5ffd0828cb168577d471219fe1e7fcee1))

* docs: Zenodo badge ([`c1043c5`](https://github.com/Helmholtz-AI-Energy/perun/commit/c1043c563166aedeef51da4c5c64ea8323836d31))


### Fix

* fix: backends init and closed twice ([`406739c`](https://github.com/Helmholtz-AI-Energy/perun/commit/406739c34cf540b2177770022a82f84b1a1b60e3))


## v0.3.0 (2023-05-31)


### Documentation

* docs: link to docs in README ([`77613ab`](https://github.com/Helmholtz-AI-Energy/perun/commit/77613ab72657ed00537417572f2a170917577567))

* docs: rtd setup ([`d3ef35b`](https://github.com/Helmholtz-AI-Energy/perun/commit/d3ef35bf1393f4c45982e5f163a9445cd83d2062))

* docs: readthedocs documentation with sphinx (#51) ([`ef02fe9`](https://github.com/Helmholtz-AI-Energy/perun/commit/ef02fe93c705f0c89bc8855b16678817904c6ce6))

* docs: fair-software badge (#47) ([`34585cd`](https://github.com/Helmholtz-AI-Energy/perun/commit/34585cd8f3d353c1e2591a498004677a8315864c))


### Feature

* feat: extra host metadata ([`f576046`](https://github.com/Helmholtz-AI-Energy/perun/commit/f57604625e3072391e76a55945dce63d72e038b2))


### Fix

* fix: env configuration for decorator ([`2f5626f`](https://github.com/Helmholtz-AI-Energy/perun/commit/2f5626f9b0e20c77cd14cefe17f812cf41cb1ba9))

* fix: intel rapl file managment changes ([`9fa33d3`](https://github.com/Helmholtz-AI-Energy/perun/commit/9fa33d388fd6f3868173733634250c021fd3aa1c))

* fix: SLURM integration changes (#52) ([`e563c19`](https://github.com/Helmholtz-AI-Energy/perun/commit/e563c19a7593fe6f2bda863c96d0ecbdeed206cb))


### Refactor

* refactor: clean dependencies, removed pretty-table (#54) ([`0a48301`](https://github.com/Helmholtz-AI-Energy/perun/commit/0a48301f196ad656d5aa6895dc7c6395dcfdf5bb))


## v0.2.0 (2023-03-28)


### Documentation

* docs: update README.md ([`7880070`](https://github.com/Helmholtz-AI-Energy/perun/commit/7880070307497cb213effd2d1387afbd88435e99))


### Fix

* fix: process start_event not set, rapl psys gets ignored ([`19b62ef`](https://github.com/Helmholtz-AI-Energy/perun/commit/19b62efc247030b2ef9e5bce4a2315573b3560da))


## v0.1.1 (2023-03-22)


### Feature

* feat: summary with co2 and price in text report ([`52dfe0a`](https://github.com/Helmholtz-AI-Energy/perun/commit/52dfe0ad47d5ee20ad295c0f693c9cb525c4dd0e))


### Fix

* fix: removed bench minimal configuration option ([`f946f71`](https://github.com/Helmholtz-AI-Energy/perun/commit/f946f71b6a62d151e232cdc288ae2f68680511f2))

* fix: removed bench minimal configuration option ([`8115bfc`](https://github.com/Helmholtz-AI-Energy/perun/commit/8115bfc0473ab8bca0c618d3149f09212ed5a7e2))


## v0.1.0 (2023-03-17)


### Ci

* ci: test action trigger on anything except on release ([`ea76a8c`](https://github.com/Helmholtz-AI-Energy/perun/commit/ea76a8cb9baa5afaf57f308133151ff0dcb7dd34))

* ci: corrected release ci ([`d08ef68`](https://github.com/Helmholtz-AI-Energy/perun/commit/d08ef68748077ab6ef5ca97dd086736a5ddadd9e))


### Refactor

* refactor: Better, more customizable output configurations, including CB mode and MPI/SLURM metadata (#31) ([`a09a4dd`](https://github.com/Helmholtz-AI-Energy/perun/commit/a09a4ddae7ee2463b13522aae18ba16580c2c6f0))


## v0.1.0-beta.18 (2022-12-16)


### Fix

* fix: endless action triggers, I remebered why that was there in the first place ([`672ee64`](https://github.com/Helmholtz-AI-Energy/perun/commit/672ee64867dda36fe2f8931c3d901a8d96d4f838))


## v0.1.0-beta.17 (2022-12-07)


### Ci

* ci: semantic release triggers on pre-relase branch ([`4e65b61`](https://github.com/Helmholtz-AI-Energy/perun/commit/4e65b61b352f363ee1da8212cc9f8a5d4962a56d))

* ci: updated pre-commit ([`d274aa0`](https://github.com/Helmholtz-AI-Energy/perun/commit/d274aa0fdb4d30baeb4282f88752713311573f2e))


### Feature

* feat: poetry hooks and installer configuration ([`6b222e1`](https://github.com/Helmholtz-AI-Energy/perun/commit/6b222e150a4ba179bf10178c36ceb7372c9d8e69))

* feat: net io counters from psutil ([`341c186`](https://github.com/Helmholtz-AI-Energy/perun/commit/341c1869c4cf4f1284068aadfb87422cc93a52b7))


### Fix

* fix: Missing system path on cli monitor ([`c2b7b31`](https://github.com/Helmholtz-AI-Energy/perun/commit/c2b7b3131b3940c0c8b0092e75c0412bc5e8fa99))

* fix: README title image url ([`fd5b2b8`](https://github.com/Helmholtz-AI-Energy/perun/commit/fd5b2b880bcbf176ea3fe1f02275d86188ea48db))

* fix: cmd line argument parsing for monitor subcommand ([`57e8744`](https://github.com/Helmholtz-AI-Energy/perun/commit/57e87440ccdd86a673f0769ad73abf4512025e73))


### Refactor

* refactor: semantic release action triggers ([`6b3dfde`](https://github.com/Helmholtz-AI-Energy/perun/commit/6b3dfde7924c0affd38adf24b988789cf2d490dd))

* refactor: semantic release branch change to pre-release ([`700b0c9`](https://github.com/Helmholtz-AI-Energy/perun/commit/700b0c94b3748e988ec5dacc363096ff3cbe3e4a))

* refactor: pre-commit default stage changed to commit ([`afe0f74`](https://github.com/Helmholtz-AI-Energy/perun/commit/afe0f748c54b647f7a7360c2eb1d18bc7dc1c097))

* refactor: split getAssignedDevices into 2 functions ([`d21129b`](https://github.com/Helmholtz-AI-Energy/perun/commit/d21129b7d6eb68c63863895a935dc1cf79ad75c8))


### Style

* style: flake8 corrections ([`889ca87`](https://github.com/Helmholtz-AI-Energy/perun/commit/889ca870d8eba520740613b2eee7e7fd464cdfc8))


### Test

* test: mocked backend, tested assignedDevices ([`9aa805d`](https://github.com/Helmholtz-AI-Energy/perun/commit/9aa805d5d2e8c0b709d640f6a8663f6120532a2c))

* test: cli showconf tests, new pre-commit configuration ([`bfc2f40`](https://github.com/Helmholtz-AI-Energy/perun/commit/bfc2f40c653a56c1ce992ee9d228ff6fcb67d728))


## v0.1.0-beta.16 (2022-09-20)


### Fix

* fix: catching influxdb import error ([`851bfb4`](https://github.com/Helmholtz-AI-Energy/perun/commit/851bfb4a574b8cab91ff08540b3090c3af337efe))


## v0.1.0-beta.15 (2022-09-19)


### Fix

* fix: relaxed dependencies (will tighten them later) ([`6509481`](https://github.com/Helmholtz-AI-Energy/perun/commit/650948170150eee242ae9bc78d1ea6bb1e9285b4))


## v0.1.0-beta.14 (2022-09-19)


### Fix

* fix: removed RAM_POWER from psutil backend ([`9ef751f`](https://github.com/Helmholtz-AI-Energy/perun/commit/9ef751f3784dcf1b065be79adc950d4bb0f0e22f))


## v0.1.0-beta.13 (2022-09-02)


### Feature

* feat: psutil backend ([`7d3aa61`](https://github.com/Helmholtz-AI-Energy/perun/commit/7d3aa61a4164463bec88343e2efb139464bc30ae))


## v0.1.0-beta.12 (2022-08-30)


### Feature

* feat: energy conversion to euro and co2e (#17) ([`ee89583`](https://github.com/Helmholtz-AI-Energy/perun/commit/ee8958357298780e285412360c33856a13ee49d5))


## v0.1.0-beta.11 (2022-08-29)


### Feature

* feat: configuration files (#16) ([`1035763`](https://github.com/Helmholtz-AI-Energy/perun/commit/1035763c2e66f2973180bceca52b7c0ef04d6f8b))


## v0.1.0-beta.10 (2022-08-24)


### Feature

* feat: serial hdf5 support (#15) ([`e9caa69`](https://github.com/Helmholtz-AI-Energy/perun/commit/e9caa69948eec4f6baf98807d7e4bcaf81700e8a))


## v0.1.0-beta.9 (2022-08-23)


### Refactor

* refactor: device uses numpy types and no pyrapl dependency ([`f6ba3e9`](https://github.com/Helmholtz-AI-Energy/perun/commit/f6ba3e92a95cd9e6114008225ff73485349e72c7))


## v0.1.0-beta.8 (2022-08-22)


### Ci

* ci: semantic_release_action only activates on code change ([`202234a`](https://github.com/Helmholtz-AI-Energy/perun/commit/202234a94e1a2669dc2d10cb635177242f4afab9))

* ci: v3 ([`e2f38e5`](https://github.com/Helmholtz-AI-Energy/perun/commit/e2f38e5281ea510694f6f58b04824cb8a589ea65))

* ci: second try to avoid endless release actions ([`168c130`](https://github.com/Helmholtz-AI-Energy/perun/commit/168c13058f0b3dbc13dfa86b55b60e52f27b1fc5))

* ci: block endless release action chains ([`5684b1f`](https://github.com/Helmholtz-AI-Energy/perun/commit/5684b1fd312fadc080d8bb30946a8f5879c80a66))


### Feature

* feat: horeka options in cli and monitor decorator (#13) ([`0fde3cd`](https://github.com/Helmholtz-AI-Energy/perun/commit/0fde3cdcf8c489ff1b8ba4a985778c0e92a06cc6))


## v0.1.0-beta.7 (2022-08-17)


### Ci

* ci: semantic-release credential fix ([`f429ae8`](https://github.com/Helmholtz-AI-Energy/perun/commit/f429ae8ec221e6d96d0298677122843bcc0073a1))


### Fix

* fix: extra typing imports for 3.8 support (#12) ([`28367a7`](https://github.com/Helmholtz-AI-Energy/perun/commit/28367a747015288e7a5bb09f3cdc97c96d0e4680))


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


### Fix

* fix: missing pyyaml dependency ([`3b8e74a`](https://github.com/Helmholtz-AI-Energy/perun/commit/3b8e74a3318bcac43398db3f86cc9be9da75ce5a))


## v0.1.0-beta.2 (2022-08-11)


### Chore

* chore: extra information in pyproject.toml ([`a01b696`](https://github.com/Helmholtz-AI-Energy/perun/commit/a01b6961d854f39197ee480e195d003ae8e573d8))


## v0.1.0-beta.1 (2022-08-11)


### Ci

* ci: semantic-release ([`8a94df0`](https://github.com/Helmholtz-AI-Energy/perun/commit/8a94df0a0ebe307fcaf34f05bec4a9c7836efc1f))


### Feature

* feat: text, json and yaml reports ([`9503751`](https://github.com/Helmholtz-AI-Energy/perun/commit/95037516594189959fbfb2b2894d18cdba7b5819))

* feat: experiment run postprocessing ([`5e78804`](https://github.com/Helmholtz-AI-Energy/perun/commit/5e7880431aa513754ab6e61f2a9e30daac8aed69))

* feat: perun module emulates cli ([`8bfd029`](https://github.com/Helmholtz-AI-Energy/perun/commit/8bfd0290d453e51776b0e6df59743cd96e800bfe))

* feat: perun monitor decorator ([`167165c`](https://github.com/Helmholtz-AI-Energy/perun/commit/167165cbbcbea1ff3b2f566b5543c259ed73e5ad))

* feat: cmdline monitoring ([`d66bf8a`](https://github.com/Helmholtz-AI-Energy/perun/commit/d66bf8a751243e71fada5687dc2fe146de5612bc))

* feat: intel and nvida backends ([`b720d49`](https://github.com/Helmholtz-AI-Energy/perun/commit/b720d495c8a3dc1b77113a3febc8bda4f6b8c575))

* feat: initial commit ([`c8620bc`](https://github.com/Helmholtz-AI-Energy/perun/commit/c8620bc5e0f745323e5409b2dda4d26e5ef2ff21))


### Fix

* fix: semantic-release action ([`90caf3d`](https://github.com/Helmholtz-AI-Energy/perun/commit/90caf3d6817e42c21ad1f9d30a32038fe96c0362))
