# SwimrankingsScraper

> [!IMPORTANT]
> **Discontinued — this scraper no longer works.**
>
> Swimrankings.net now uses Cloudflare protection and requires authentication, which prevents this project's original unauthenticated scraping approach from working. This package is no longer maintained, and there are no plans to restore compatibility.
>
> The source code remains available for reference under the MIT license. **The installation instructions and usage examples below are historical and are not expected to work against the current website.**

## Possible alternative (untested)

[MauroDruwel/Swimrankings](https://github.com/MauroDruwel/Swimrankings) ([PyPI](https://pypi.org/project/swimrankings/)) is a separately maintained Python project that also accesses swimrankings.net. **It has not been tested or verified by this project's maintainer**, including whether it works with the website's current Cloudflare and login restrictions. It is not a drop-in replacement, and no compatibility or continued functionality is guaranteed.

## Historical documentation

A library for getting information from swimrankings.net

### Installation
```
pip install swimrankingsscraper
```

### Development
```bash
uv sync --extra dev
uv run python -m unittest tests/test_swimrankingsscraper.py
```

### Get started


```Python
from swimrankingsscraper import SwimrankingsScraper

# Instantiate a scraper
scraper = SwimrankingsScraper()

# Get an athelete from the scraper
athelete = scraper.get_athlete('4292888')

# Get the meets the athelete participated in
meets = athelete.list_meets()
```
