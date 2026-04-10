[![HACS Default](https://img.shields.io/badge/HACS-Default-blue.svg)](https://github.com/hacs/default)
[![GitHub release](https://img.shields.io/github/release/myTselection/delhaize_hacs.svg)](https://github.com/myTselection/delhaize_hacs/releases)
![GitHub repo size](https://img.shields.io/github/repo-size/myTselection/delhaize_hacs.svg)

[![GitHub issues](https://img.shields.io/github/issues/myTselection/delhaize_hacs.svg)](https://github.com/myTselection/delhaize_hacs/issues)
[![GitHub last commit](https://img.shields.io/github/last-commit/myTselection/delhaize_hacs.svg)](https://github.com/myTselection/delhaize_hacs/commits/master)
[![GitHub commit activity](https://img.shields.io/github/commit-activity/m/myTselection/delhaize_hacs.svg)](https://github.com/myTselection/delhaize_hacs/graphs/commit-activity)

# Delhaize Home Assistant integration
Home Assistant custom integration to provide Delhaize SuperPlus and e-deals information. This custom component has been built from the ground up to fetch your Delhaize SuperPlus and e-Deals information and integrate this information into Home Assistant. This integration is built against the public websites provided by [Delhaizee.be](https://dwww.delhaize.be). Sensors will be created for Delhaize loyalty card and points. Automatic activation/registration of [e-Deals](https://www.delhaize.be/nl/my-account/personal-offers) is possible. 

This integration is in no way affiliated with Delhaize.

| :warning: Please don't report issues with this integration to Delhaize, they will not be able to support you. |
| ---------------------------------------------------------------------------------------------------------------------|


<p align="center"><img src="https://raw.githubusercontent.com/myTselection/delhaize_hacs/master/icon.png"/></p>


# Main use case

[Delhaize e-Deals](https://www.delhaize.be/nl/my-account/personal-offers) personal offers allow users to get extra discount and points. But these e-Deals need to manually get activated on regular base before the extra discount is applied. This integration can automatically activate new e-Deals.



## Installation
- [HACS](https://hacs.xyz/): search for delhaize_hacs in the default HACS repo list or use below button to navigate directly to it on your local system and install via HACS. 
   -    [![Open your Home Assistant instance and open the repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg?style=flat-square)](https://my.home-assistant.io/redirect/hacs_repository/?owner=myTselection&repository=delhaize_hacs&category=integration)
- Restart Home Assistant
- Add 'Delhaize' integration via HA Settings > 'Devices and Services' > 'Integrations'
- In the setup configuration, provide your Delhaize username and password

## Integration

### Sensors
- <code>sensor.delhaize_card</code>: sensor with adres linked to location of `origin`
- <code>sensor.delhaize_points</code>: sensor with indication of days on which the city parking is restricted
- <code>sensor.delhaize_superplus</code>: sensor with max amount of minutes is allowed to park during the days and time restricted schedule
- <code>sensor.delhaize_</code>: TODO

    
### Services / Actions / Automation

* TODO

### Markdown example

TODO


## Status
Proof of concept status, still validating and extending functionalities. [Issues](https://github.com/myTselection/delhaize_hacs/issues) section in GitHub.

## Technical pointers
The main logic and API connection related code can be found within source code delhaize_hacs/custom_components/delhaize_hacs:
- [sensor.py](https://github.com/myTselection/delhaize_hacs/blob/master/custom_components/delhaize_hacs/sensor.py)
- [coordinator.py](https://github.com/myTselection/delhaize_hacs/blob/master/custom_components/delhaize_hacs/coordinator.py)
- [delhaizeApi](https://github.com/myTselection/delhaize_hacs/blob/master/custom_components/delhaize_hacs/delhaizeApi/__init__.py)

All other files just contain boilerplat code for the integration to work wtihin HA or to have some constants/strings/translations.

If you would encounter some issues with this custom component, you can enable extra debug logging by adding below into your `configuration.yaml`:

```
logger:
  default: info
  logs:
     custom_components.delhaize_hacs: debug
```

