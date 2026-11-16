# Security Policy

## Supported Versions

| Version | Supported |
| ------- | --------- |
| 0.x     | Yes       |

## Reporting a Vulnerability

Please do **not** open a public issue for security-sensitive reports.

Use GitHub's private vulnerability reporting:

<https://github.com/23skdu/gcloud_logs_anomaly_detection/security/advisories/new>

Include:

- A description of the issue and its impact
- Steps to reproduce or a proof of concept
- Affected version or commit
- Any suggested remediation

You can expect an acknowledgement within 3 business days and a remediation
timeline after the report has been triaged. Please allow time for a fix and a
release before public disclosure.

## Automated Security Controls

This repository uses the following controls:

- **Dependabot** version updates for Python, Docker, Docker Compose, GitHub
  Actions and pre-commit dependencies
- **Dependabot security updates** and vulnerability alerts
- **CodeQL** code scanning on pushes, pull requests and a weekly schedule
- **Dependency review** on pull requests
- **pip-audit** and **Bandit** in CI
- **Trivy** image scanning before images are pushed to GHCR
- **Secret scanning** with push protection
- **Branch protection** requiring CI checks before merge

## Scope

The following are considered in scope:

- The `gcloud_logs_anomaly_detection` Python package and CLI
- The scripts in `scripts/`
- The Dockerfile and Compose files
- GitHub Actions workflows and repository configuration

Third-party services (Google Cloud, Longbow, Quarrel, Ollama) and their
upstream packages are out of scope unless the issue is caused by this
repository's configuration.
