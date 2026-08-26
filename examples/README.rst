========
Examples
========

This directory contains small, self-contained examples that show how to use
perun in different scenarios:

- ``torch_mnist/`` — monitor a single-process PyTorch MNIST training script.
- ``torchrun/`` — monitor a multi-GPU / multi-node DDP job launched with
  ``torchrun`` or Slurm.
- ``postprocess_callback/`` — forward perun's summarized metrics to MLflow with
  a ``@register_callback`` post-processing hook.
- ``live_callback/`` — stream perun's raw samples to MLflow live, from the
  monitoring subprocess.

A note on dependencies and security alerts
==========================================

The ``requirements.txt`` files in these examples list only the **direct**
dependencies, with loose lower bounds (``>=``) instead of exact pins. These
examples are illustrative and are **not** part of perun's supported, installed
surface, so we intentionally do not track security advisories against them.

If you need a fully reproducible environment for one of the examples, pin exact
versions locally (e.g. ``pip freeze > locked-requirements.txt``) — just keep the
frozen file out of version control so it does not re-introduce advisory noise.

Maintainers: how the examples are excluded from dependency automation
---------------------------------------------------------------------

- **Version-update PRs** are disabled for ``examples/`` via
  ``.github/dependabot.yml`` (Dependabot only watches the root project and the
  GitHub Actions workflows).
- **Security alerts** for a manifest are controlled by repository settings, not
  by ``dependabot.yml``. To stop alerts originating from the example manifests:

  1. Go to **Settings → Code security and analysis**.
  2. Under **Dependabot alerts**, open the alert list and use
     **Dismiss → "used in tests"** (or "won't fix") for advisories that only
     affect files under ``examples/``.
  3. Optionally add a repository ``.github/dependabot.yml`` ignore entry for
     specific packages if a particular advisory keeps reappearing.

  Alternatively, keeping the example requirements limited to direct
  dependencies (as done here) removes the pinned transitive packages that were
  the main source of the alerts in the first place.
