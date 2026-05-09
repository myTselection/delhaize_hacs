[![HACS Default](https://img.shields.io/badge/HACS-Default-blue.svg)](https://github.com/hacs/default)
[![GitHub release](https://img.shields.io/github/release/myTselection/delhaize_hacs.svg)](https://github.com/myTselection/delhaize_hacs/releases)
![GitHub repo size](https://img.shields.io/github/repo-size/myTselection/delhaize_hacs.svg)

# Delhaize Home Assistant integration

Home Assistant custom integration for Delhaize SuperPlus, savings, loyalty points, and personal e-Deals.

This integration talks to the same Delhaize GraphQL endpoint used by the website (`https://www.delhaize.be/api/v1/`). It is not affiliated with Delhaize. Most of it has been created by ChatGPT Codex.

| :warning: Please do not report integration issues to Delhaize. They will not be able to support this custom component. |
| -------------------------------------------------------------------------------------------------------------------- |

## Authentication

Delhaize currently exposes a website login mutation, but the public login page can require captcha and/or MFA. Home Assistant cannot solve Delhaize captcha challenges, so the integration supports three setup paths:

- Username and password: Home Assistant submits the same website login mutation as Delhaize.be.
- Email temporary code: when Delhaize accepts the password step and then requires MFA, Home Assistant asks Delhaize to send the code and shows a second setup form. If Delhaize rejects the password step with `captcha_invalid_error`, no email code is sent and Cookie authentication is required.
- Logged-in browser Cookie header: recommended fallback when Delhaize asks for captcha. Log in to `https://www.delhaize.be/` in a browser, copy the request `Cookie` header from an authenticated request to `/api/v1/`, and paste it into the setup flow.

The integration stores refreshed Delhaize cookies in the Home Assistant config entry so the session can survive restarts as long as Delhaize keeps the session valid.

## Installation

- [HACS](https://hacs.xyz/): search for delhaize_hacs in the default HACS repo list or use below button to navigate directly to it on your local system and install via HACS. 
   -    [![Open your Home Assistant instance and open the repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg?style=flat-square)](https://my.home-assistant.io/redirect/hacs_repository/?owner=myTselection&repository=delhaize_hacs&category=integration)
- Restart Home Assistant.
- Add the `Delhaize` integration from Settings > Devices and services.
- Provide either Delhaize credentials or a logged-in browser Cookie header.
- After setup, use the integration's Configure/Options screen to update language, automatic offer activation, credentials, or the Cookie header.

## Entities

The integration creates sensors for:

- Loyalty points
- Savings
- Personal offers available
- Personal offers total
- Personal offers activated
- Personal offers benefit
- Loyalty profile
- Account

## Services

`delhaize_hacs.activate_personal_offers`

Activates available personal offers for all configured accounts, or for a specific config entry when `entry_id` is provided.

## Debug logging

Add this to `configuration.yaml` when troubleshooting:

```yaml
logger:
  default: info
  logs:
    custom_components.delhaize_hacs: debug
```

## Status

Proof of concept. Delhaize can change its website GraphQL schema, captcha requirements, or cookie behavior at any time.
