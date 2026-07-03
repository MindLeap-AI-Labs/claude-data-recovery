# Security Policy

## Reporting a vulnerability

Please use GitHub's private vulnerability reporting feature for this repository.

Do not open a public issue containing:

- Claude conversation exports
- Email addresses, phone numbers, account UUIDs, or authentication details
- Memories or project instructions
- Attachment contents
- Generated `index.html` or `normalized_data.json` files

When possible, reproduce parser issues with a minimal synthetic fixture.

## Supported versions

Security fixes are applied to the latest release and the `main` branch.

## Data handling

Claude Data Recovery is designed to run locally and makes no network requests. Generated output contains recovered user data and should be protected like the original export.
