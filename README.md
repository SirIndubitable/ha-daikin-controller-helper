
# Daikin Controller Helper

![maintained](https://img.shields.io/maintenance/yes/2026.svg)
<img alt="GitHub last commit" src="https://img.shields.io/github/last-commit/SirIndubitable/my-daikin-controller">
[![hacs_badge](https://img.shields.io/badge/hacs-custom-yellow.svg)](https://github.com/custom-components/hacs)
[![ha_version](https://img.shields.io/badge/home%20assistant-2025.12.0%2B-green.svg)](https://www.home-assistant.io)
![version](https://img.shields.io/badge/version-0.1.0-yellow.svg)
[![License](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/mit)

<a href="https://www.buymeacoffee.com/sirindubitable" target="_blank"><img src="https://cdn.buymeacoffee.com/buttons/v2/default-violet.png" alt="Buy Me A Coffee" style="height: 40px !important;width: 145px !important;" ></a>

## Overview
Home Assistant integration to make my Daikin MiniSplit unit behave in a sane way.  It will behave like an actual thermostate, where it will stop heaiting after it hits the target temp.

The Daikin this is built for doesn't stop heating or cooling after it hits its target temperature, it seems to just ignore the target temperature value.
This integration will set the HVAC mode of the Daikin to HEAT COOL or OFF depending on the current temperature and target temperatures.

## Disclaimer
This project is not affiliated with or supported by Home Assistant or Daikin. It is community maintained.

## Installation
You can install this card by following one of the guides below:

### With HACS (Recommended)

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=SirIndubitable&repository=my-daikin-controller&category=integration)


1. Click on the three dots in the top right corner of the HACS overview menu.
2. Select **Custom repositories**.
3. Add the repository URL: `https://github.com/SirIndubitable/my-daikin-controller`.
4. Set the type to **Integration**.
5. Click the **Add** button.
6. Search for **Daikin Controller Helper** in HACS and click the **Download** button.

## Configuration

[![Add the integration to my home assistant .](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start?domain=custom_daikin)
