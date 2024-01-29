# SwimrankingsScraper
A library for getting information from swimrankings.net

### Installation
```
pip install swimrankingsscraper
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