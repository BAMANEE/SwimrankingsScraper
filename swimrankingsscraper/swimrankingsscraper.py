"""
SwimrankingsScraper: A web scraper for Swimrankings.net to retrieve information about athletes, meets, and results.

Dependencies:
- requests
- BeautifulSoup (bs4)
- urllib.parse

Usage:
1. Create an instance of SwimrankingsScraper.
2. Use the instance to get information about athletes, meets, and results.

Example:
    scraper = SwimrankingsScraper()
    clubs = scraper.get_club('65929')
    swimmers = clubs.list_athletes()
    for swimmer in swimmers:
        athlete = scraper.get_athlete(swimmer['athlete_id'])
        coefficients = athlete.get_im_coefficients()
        print(f"{swimmer['athlete_name']}: {coefficients['100m Medley coefficient']}, {coefficients['200m Medley coefficient']}")

Classes:
- SwimrankingsScraper: Main class for the Swimrankings web scraper.
- SessionManager: Manages the HTTP session and enforces request rate limits.
- ScraperMixin: A mixin class providing common functionality for other scraper classes.
- Athlete: Represents an athlete and provides methods to retrieve personal bests and meet information.
- Meet: Represents a swimming meet and provides methods to retrieve information about clubs, events, and results.
- Result: Represents a swimming result and provides methods to retrieve information about the result.
- Meets: Represents a list of meets and provides methods to retrieve information about the meets.
- Club: Represents a club and provides methods to retrieve information about club members.

Functions:
- convert_time_to_seconds: Converts a time string to seconds.

Attributes:
- BASE_URL: The base URL for the Swimrankings website.

Usage Notes:
- Ensure that the required dependencies (requests, BeautifulSoup, urllib) are installed.
- The provided example demonstrates how to use the scraper to retrieve information about athletes and their Individual Medley coefficients.

"""

import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs
from datetime import datetime
import unicodedata
import time
import re

BASE_URL = 'https://www.swimrankings.net/index.php?'

def convert_time(time_str):
    # Remove trailing 'M' if it exists
    if time_str[-1] == 'M':
        time_str = time_str[:-1]

    # Parse the time string using datetime
    col_count = time_str.count(':')
    if col_count == 2:
        time_format = '%H:%M:%S.%f'
    elif col_count == 1:
        time_format = '%M:%S.%f'
    else:
        time_format = '%S.%f'
    time = datetime.strptime(time_str, time_format).time()
    total_second = time.second + time.minute * 60 + time.hour * 3600 + time.microsecond / 1000000
    return total_second

class SessionManager:
    """
    Manages an HTTP session, tracks request history, and enforces request rate limits.

    Attributes:
    - `session`: An instance of `requests.Session` for making HTTP requests.
    - `request_history`: A list to track the timestamp of each request.
    - `last_updated`: Timestamp of the last request.
    - `max_requests_per_second`: Maximum allowed requests per second.
    - `max_per`: Timeframe in seconds within which the maximum requests are allowed.

    Methods:
    - `add_request()`: Adds a request timestamp to the request history.
    - `check_request_rate_limit()`: Checks and enforces the request rate limit.
    - `get_session()`: Retrieves the requests session.

    Usage Example:
    ```python
    manager = SessionManager()
    manager.add_request()
    manager.check_request_rate_limit()
    session = manager.get_session()
    ```

    Rate Limiting:
    - The rate limit is defined by `max_requests_per_second` within the timeframe of `max_per` seconds.
    - If the rate limit is reached, the function pauses execution to comply with the limit.

    Note:
    - Ensure to call `add_request()` before making each request.
    - Use `get_session()` to obtain the requests session for making HTTP requests.
    """
    def __init__(self, max_requests_per_timeframe=(15, 30)):
        self.session = requests.Session()
        self.request_history = []
        self.last_updated = None
        self.max_requests_per_second = max_requests_per_timeframe[0]
        self.max_per = max_requests_per_timeframe[1]

    def add_request(self):
        """
        Adds a request timestamp to the request history.
        """
        request_time = time.time()
        self.request_history.append(request_time)

    def check_request_rate_limit(self):
        """
        Checks and enforces the request rate limit.
        """
        current_time = time.time()
        window_start_time = current_time - self.max_per
        valid_requests = [t for t in self.request_history if t > window_start_time]

        if len(valid_requests) >= self.max_requests_per_second:
            time_to_wait = valid_requests[0] + self.max_per - current_time
            # print(f"Request rate limit reached. Waiting for {time_to_wait:.2f} seconds.")
            time.sleep(time_to_wait)
            self.request_history = [t for t in self.request_history if t > window_start_time + time_to_wait]

    def get_session(self):
        """
        Retrieves the requests session.

        Returns:
        - requests.Session: The requests session.
        """
        return self.session


class SwimrankingsScraper:
    """
    Main class for the Swimrankings web scraper.

    Attributes:
    - `url` (str): The base URL for the Swimrankings website.
    - `sessionManager` (SessionManager): An instance of SessionManager for managing HTTP requests.

    Methods:
    - `__init__()`: Initializes the SwimrankingsScraper with the base URL and a requests session.
    - `get_athlete(athlete_id)`: Retrieves an Athlete instance for the specified athlete ID.
    - `get_meet(meet_id)`: Retrieves a Meet instance for the specified meet ID.
    - `get_results(result_id)`: Retrieves a Result instance for the specified result ID.
    - `get_meets()`: Retrieves a Meets instance.
    - `get_club(club_id)`: Retrieves a Club instance for the specified club ID.

    Usage Example:
    ```python
    scraper = SwimrankingsScraper()
    athlete_instance = scraper.get_athlete('4292888')
    meet_instance = scraper.get_meet('123456')
    result_instance = scraper.get_results('789012')
    meets_instance = scraper.get_meets()
    club_instance = scraper.get_club('987654')
    ```

    Details:
    - The class provides methods to obtain instances for Athlete, Meet, Result, Meets, and Club.
    - These instances allow accessing various functionalities related to athletes, meets, and results.
    - The SessionManager is used for handling HTTP requests.
    - Instantiate this class to start using the Swimrankings web scraper functionalities.
    """
    def __init__(self):
        """
        Initializes the SwimrankingsScraper with the base URL and a requests session.
        """
        self.url = BASE_URL
        self.sessionManager = SessionManager()

    def get_athlete(self, athlete_id):
        """
        Retrieves an Athlete instance for the specified athlete ID.

        Parameters:
        - `athlete_id` (str): The ID of the athlete.

        Returns:
        - `Athlete`: An Athlete instance.
        """
        return Athlete(athlete_id, self.sessionManager)

    def get_meet(self, meet_id):
        """
        Retrieves a Meet instance for the specified meet ID.

        Parameters:
        - `meet_id` (str): The ID of the meet.

        Returns:
        - `Meet`: A Meet instance.
        """
        return Meet(meet_id, self.sessionManager)

    def get_result(self, result_id):
        """
        Retrieves a Result instance for the specified result ID.

        Parameters:
        - `result_id` (str): The ID of the result.

        Returns:
        - `Result`: A Result instance.
        """
        return Result(result_id, self.sessionManager)
    
    def get_meets(self):
        """
        Retrieves a Meets instance.

        Returns:
        - `Meets`: A Meets instance.
        """
        return Meets(self.sessionManager)
    
    def get_club(self, club_id):
        """
        Retrieves a Club instance for the specified club ID.

        Parameters:
        - `club_id` (str): The ID of the club.

        Returns:
        - `Club`: A Club instance.
        """
        return Club(club_id, self.sessionManager)


class ScraperMixin:
    """
    A mixin class providing common functionality for other scraper classes.

    Attributes:
    - `sessionManager` (SessionManager): The SessionManager instance for making HTTP requests.
    - `page_content` (BeautifulSoup or None): The HTML content of the last fetched page, parsed with BeautifulSoup.
    - `update_interval` (int): The minimum time interval (in seconds) between consecutive updates.
    - `last_updated` (float): The timestamp of the last page update.

    Methods:
    - `__init__(sessionManager, update_interval=60, max_requests_per_minute=30)`: Initializes the ScraperMixin with a requests session.
    - `_update_page_content(params)`: Updates the page content with the HTML content of a page with the specified parameters.
    - `_get_page_content(params)`: Retrieves the HTML content of a page with the specified parameters.

    Usage Example:
    ```python
    session_manager = SessionManager()
    mixin_instance = ScraperMixin(session_manager, update_interval=120)
    params = {'param1': 'value1', 'param2': 'value2'}
    html_content = mixin_instance._get_page_content(params)
    ```

    Details:
    - This mixin class is designed to be used in conjunction with other scraper classes.
    - It provides a common set of methods for fetching and updating page content.
    - `sessionManager` is required for making HTTP requests, and `update_interval` sets the minimum time between updates.
    - Use `_get_page_content(params)` to retrieve HTML content, and `_update_page_content(params)` to force an update.
    - The page content is stored in the `page_content` attribute, parsed with BeautifulSoup.
    - Implement this mixin in other scraper classes to share common functionality.
    """
    def __init__(self, sessionManager, update_interval=60):
        """
        Initializes the ScraperMixin with a requests session.

        Parameters:
        - `sessionManager` (SessionManager): The requests session to be used for making HTTP requests.
        - `update_interval` (int): The minimum time interval (in seconds) between consecutive updates.
        """
        self.sessionManager = sessionManager
        self.last_request = None
        self.page_content = None
        self.update_interval = update_interval
        self.last_updated = None

    def _update_page_content(self, params):
        """
        Updates the page content with the HTML content of a page with the specified parameters.

        Parameters:
        - `params` (dict): The parameters to be included in the request.
        """
        try:
            self.sessionManager.check_request_rate_limit()
            page = self.sessionManager.get_session().get(BASE_URL, params=params)
            page.raise_for_status()  # Raise HTTPError for bad requests
            self.page_content =  BeautifulSoup(page.content, "lxml")
            self.last_updated = time.time()
            self.sessionManager.add_request()
            if self.page_content.find('body') is None:
                raise requests.RequestException("Empty response")
        except requests.RequestException as e:
            print(f"Error fetching data: {e}") 

    def _get_page_content(self, params):
        """
        Retrieves the HTML content of a page with the specified parameters.

        Parameters:
        - `params` (dict): The parameters to be included in the request.

        Returns:
        - `str` or `None`: The HTML content of the page or `None` if an error occurs.
        """
        if self.last_updated is None or params != self.last_request or time.time() - self.last_updated > self.update_interval:
            self._update_page_content(params)
        self.last_request = params
        return self.page_content


class Athlete(ScraperMixin):
    """
    Represents an athlete and provides methods to retrieve information about the athlete's personal bests and meets.

    Attributes:
    - `athlete_id` (str): The ID of the athlete.
    - `sessionManager` (SessionManager): The SessionManager instance for making HTTP requests.
    - `update_interval` (int): The minimum time interval (in seconds) between consecutive updates.

    Methods:
    - `__init__(athlete_id, sessionManager, update_interval=60)`: Initializes the Athlete with an athlete ID and a requests session.
    - `list_personal_bests() -> list`: Retrieves a list of personal bests for the athlete.
    - `list_meets() -> list`: Retrieves a list of meets in which the athlete has participated.

    Usage Example:
    ```python
    session_manager = SessionManager()
    athlete_instance = Athlete('athlete_id_here', session_manager, update_interval=120)
    personal_bests = athlete_instance.list_personal_bests()
    meets = athlete_instance.list_meets()
    ```

    Details:
    - This class inherits from `ScraperMixin` to leverage common functionality for making HTTP requests.
    - `athlete_id` is required to identify the athlete.
    - `sessionManager` is needed for making HTTP requests, and `update_interval` sets the minimum time between updates.
    - Use `list_personal_bests()` to retrieve a list of personal bests, represented as dictionaries.
    - The personal bests data includes event name, course length, time, result ID, and result URL.
    - In case of an error or no data, an empty list is returned.
    - Use `list_meets()` to retrieve a list of meets in which the athlete has participated.
    - The meets data includes meet ID, meet date, meet city, and meet name.
    - In case of an error or no data, an empty list is returned.
    """
    def __init__(self, athlete_id, sessionManager, update_interval=60):
        """
        Initializes the Athlete with an athlete ID and a requests session.

        Parameters:
        - `athlete_id` (str): The ID of the athlete.
        - `sessionManager` (SessionManager): The requests session to be used for making HTTP requests.
        - `update_interval` (int): The minimum time interval (in seconds) between consecutive updates.
        """
        super().__init__(sessionManager, update_interval)
        self.athlete_id = athlete_id

    def list_personal_bests(self, season="") -> list:
        """
        Retrieves a list of personal bests for the athlete.

        Returns:
        - `list`: A list of dictionaries containing information about each personal best.
        """
        params = {'page': 'athleteDetail', 'athleteId': self.athlete_id, 'pbest': season}
        try:
            soup = self._get_page_content(params)
            table = soup.find('table', {'class': 'athleteBest'})
        except AttributeError:
            return []

        data = []
        for row in table.find_all('tr', {'class': ['athleteBest0', 'athleteBest1']}):
            event_cell = row.find('td', {'class': 'event'})
            event_name = event_cell.find('a').get_text(strip=True)
            course_cell = row.find('td', {'class': 'course'})
            course_length = course_cell.get_text(strip=True)
            time_cell = row.find('td', {'class': ['time', 'swimtimeImportant']})
            time = convert_time(time_cell.get_text(strip=True))
            result_url = time_cell.find('a')['href']
            result_id = int(parse_qs(urlparse(result_url).query)['id'][0])
            fina_points = row.find('td', {'class': 'code'}).get_text(strip=True)
            data.append({'result_id': result_id, 'event_name': event_name, 'course_length': course_length, 'time': time, 'FINA Points': fina_points})
        return data

    def list_meets(self) -> list:
        """
        Retrieves a list of meets in which the athlete has participated.

        Returns:
        - `list`: A list of dictionaries containing information about each meet.
        """
        params = {'page': 'athleteDetail', 'athleteId': self.athlete_id, 'athletePage': 'MEET'}
        try:
            soup = self._get_page_content(params)
            table = soup.find('table', {'class': 'athleteMeet'})
        except AttributeError:
            return []

        data = []
        for row in table.find_all('tr', {'class': ['athleteMeet0', 'athleteMeet1']}):
            date_cell = row.find('td', {'class': 'date'})
            meet_date = unicodedata.normalize("NFKD", date_cell.get_text(strip=True))
            city_cell = row.find('td', {'class': 'city'})
            meet_city = city_cell.find('a').get_text(strip=True)
            meet_name = city_cell.find('a')['title']
            meet_url = city_cell.find('a')['href']
            meet_id = int(parse_qs(urlparse(meet_url).query)['meetId'][0])
            data.append({'meet_id': meet_id, 'meet_date': meet_date, 'meet_city': meet_city, 'meet_name': meet_name})
        return data

class Meet(ScraperMixin):
    """
    Represents a swimming meet and provides methods to retrieve information about clubs, events, and results.

    Attributes:
    - `meet_id` (str): The ID of the meet.
    - `sessionManager` (SessionManager): The SessionManager instance for making HTTP requests.
    - `update_interval` (int): The minimum time interval (in seconds) between consecutive updates.

    Methods:
    - `__init__(meet_id, sessionManager, update_interval=60)`: Initializes the Meet with a meet ID and a requests session.
    - `list_clubs() -> list`: Retrieves a list of clubs that participated in the meet.
    - `list_events() -> list`: Retrieves a list of events that took place in the meet.
    - `list_races(event_id, gender) -> list`: Retrieves a list of different races within the same event in the meet.
    - `list_results(event_id, gender, race_id) -> list`: Retrieves a list of results for a specific event in the meet.

    Usage Example:
    ```python
    session_manager = SessionManager()
    meet_instance = Meet('meet_id_here', session_manager, update_interval=120)
    clubs = meet_instance.list_clubs()
    events = meet_instance.list_events()
    races = meet_instance.list_races('event_id_here', 'gender_here')
    results = meet_instance.list_results('event_id_here', 'gender_here', race_id_here)
    ```

    Details:
    - This class inherits from `ScraperMixin` to leverage common functionality for making HTTP requests.
    - `meet_id` is required to identify the meet.
    - `sessionManager` is needed for making HTTP requests, and `update_interval` sets the minimum time between updates.
    - Use `list_clubs()` to retrieve a list of clubs that participated in the meet.
    - The clubs data includes club ID and club name.
    - In case of an error or no data, an empty list is returned.
    - Use `list_events()` to retrieve a list of events that took place in the meet.
    - The events data includes event ID, event gender, and event name.
    - In case of an error or no data, an empty list is returned.
    - Use `list_races(event_id, gender)` to retrieve a list of different races within the same event in the meet.
    - The races data includes race ID and race name.
    - In case of an error or no data, an empty list is returned.
    - Use `list_results(event_id, gender, race_id)` to retrieve a list of results for a specific event in the meet.
    - The results data includes result ID, athlete name, club name, swim time, and split times.
    - In case of an error or no data, an empty list is returned.
    """

    def __init__(self, meet_id, session, update_interval=60):
        """
        Initializes the Meet with a meet ID and a requests session.

        Parameters:
        - meet_id (str): The ID of the meet.
        - session (requests.Session): The requests session to be used for making HTTP requests.
        """
        super().__init__(session, update_interval)
        self.meet_id = meet_id

    def list_clubs(self):
        """
        Retrieves a list of clubs that participated in the meet.

        Returns:
        - list: A list of dictionaries containing information about each club.
        """
        params = {'page': 'meetDetail', 'meetId': self.meet_id}
        try:
            soup = self._get_page_content(params)
            table = soup.find('table', {'class': 'meetSearch'})
        except AttributeError:
            return []

        data = []
        for row in table.find_all('tr', {'class': ['meetResult0', 'meetResult1']}):
            club_cell = row.find('td', {'class': 'club'})
            club_url = club_cell.find('a')['href']
            club_id = parse_qs(urlparse(club_url).query)['clubId'][0]
            club_name = club_cell.find('a').get_text(strip=True)

            data.append({'club_id': club_id, 'club_name': club_name})

        return data

    def list_events(self):
        """
        Retrieves a list of events that took place in the meet.

        Returns:
        - list: A list of dictionaries containing information about each event.
        """
        params = {'page': 'meetDetail', 'meetId': self.meet_id} 
        try:
            soup = self._get_page_content(params)
            table = soup.find('table', {'class': 'navigation'})
        except AttributeError:
            return []
        data = []
        # Add Men's events
        search_text = "Men's events: "
        menu = table.find(lambda tag: tag.name == 'td' and tag['class'][0] == 'navigation' and search_text in tag.text)
        for item in menu.find_all('option'):
            if item['value'] != "0":
                data.append({'event_id': item['value'], 'event_gender': '1', 'event_name': item.get_text(strip=True)})
        # Add Women's events
        search_text = "Women's events: "
        menu = table.find(lambda tag: tag.name == 'td' and tag['class'][0] == 'navigation' and search_text in tag.text)
        for item in menu.find_all('option'):
            if item['value'] != "0":
                data.append({'event_id': item['value'], 'event_gender': '2', 'event_name': item.get_text(strip=True)})
        return data

    def list_races(self, event_id, gender):
        """
        Retrieves a list of different races within the same event in the meet.

        Parameters:
        - event_id (str): The ID of the event.
        - gender (str): 1 for male, 2 for female.

        returns:
        - list: A list of dictionaries containing information about each race.
        """
        params = {'page': 'meetDetail', 'meetId': self.meet_id, 'gender': gender, 'styleId': event_id}
        try:
            soup = self._get_page_content(params)
            tables = soup.find_all('table', {'class': 'meetResult'})
        except AttributeError:
            return []
        races = []
        for (id, table) in enumerate(tables):
            head = table.find('tr', {'class': 'meetResultHead'})
            name_cell = head.find('th', {'class': 'event'})
            name = unicodedata.normalize("NFKD", name_cell.get_text(strip=True))
            races.append({'race_id': id+1, 'race_name': name})
        return races           


    def list_results(self, event_id, gender, race_id):
        """
        Retrieves a list of results for a specific event in the meet.

        Parameters:
        - event_id (str): The ID of the event.
        - gender (str): 1 for male, 2 for female.
        - race_id (int): a number coronsponding with a specific race.

        Returns:
        - list: A list of dictionaries containing information about each result.
        """
        params = {'page': 'meetDetail', 'meetId': self.meet_id, 'gender': gender, 'styleId': event_id}
        try:
            soup = self._get_page_content(params)
            tables = soup.find_all('table', {'class': 'meetResult'})
        except AttributeError:
            return []
        results = []
        for row in tables[race_id-1].find_all('tr', {'class': ['meetResult0', 'meetResult1']}):
            name_cell = row.find('td', {'class': 'name'})
            name = name_cell.find('a').get_text(strip=True)
            name_url = name_cell.find('a')['href']
            athlete_id = parse_qs(urlparse(name_url).query)['athleteId'][0]
            club_cell = row.find_all('td', {'class': 'name'})[1]
            club_name = club_cell.find('a').get_text(strip=True)
            time_cell = row.find('td', {'class': 'swimtime'})
            time = time_cell.find('a').get_text(strip=True)
            try:
                split_times_rough = time_cell.find('a')['onmouseover']
            except KeyError:
                split_times_rough = ""
            pattern = r"<td class=\\'split1\\'>(.*?)<\/td>"
            split_times = re.findall(pattern, split_times_rough)
            result_url = time_cell.find('a')['href']
            result_id = parse_qs(urlparse(result_url).query)['id'][0]
            results.append({'result_id': result_id, 'athlete_id': athlete_id, 'name': name, 'club_name': club_name, 'time': time, 'split_times': split_times})
        return results




class Result(ScraperMixin):
    """
    Represents a swimming result and provides methods to retrieve information about the result.

    Attributes:
    - `result_id` (str): The ID of the result.
    - `sessionManager` (SessionManager): The SessionManager instance for making HTTP requests.
    - `update_interval` (int): The minimum time interval (in seconds) between consecutive updates.

    Methods:
    - `__init__(result_id, sessionManager, update_interval=60)`: Initializes the Result with a result ID and a requests session.
    - `get_time() -> str or None`: Retrieves the time recorded for the swimming result.

    Usage Example:
    ```python
    session_manager = SessionManager()
    result_instance = Result('result_id_here', session_manager, update_interval=120)
    result_time = result_instance.get_time()
    ```

    Details:
    - This class inherits from `ScraperMixin` to leverage common functionality for making HTTP requests.
    - `result_id` is required to identify the swimming result.
    - `sessionManager` is needed for making HTTP requests, and `update_interval` sets the minimum time between updates.
    - Use `get_time()` to retrieve the recorded time for the swimming result.
    - The time is returned as a string.
    - In case of an error or no data, None is returned.
    """
    # TDOD: Add more methods to retrieve information about the result. (e.g. splits)

    def __init__(self, result_id, session, update_interval=60):
        """
        Initializes the Result with a result ID and a requests session.

        Parameters:
        - result_id (str): The ID of the result.
        - session (requests.Session): The requests session to be used for making HTTP requests.
        """
        super().__init__(session, update_interval)
        self.result_id = result_id

    def get_time(self):
        """
        Retrieves the time recorded for the swimming result.

        Returns:
        - str: The time recorded for the result.
        """
        params = {'page': 'resultDetail', 'id': self.result_id}
        try:
            soup = self._get_page_content(params)
            data = soup.find('td', {'class': 'swimtimeLarge'}).text
        except AttributeError:
            return None
        return data
    

class Meets(ScraperMixin):
    """
    Represents a list of meets and provides methods to retrieve information about the meets.

    Attributes:
    - `sessionManager` (SessionManager): The SessionManager instance for making HTTP requests.
    - `update_interval` (int): The minimum time interval (in seconds) between consecutive updates.

    Methods:
    - `__init__(sessionManager, update_interval=60)`: Initializes the Meets with a requests session.
    - `list_periods() -> List[Dict[str, Union[str, int]]]`: Retrieves a list of periods.
    - `list_nations() -> List[Dict[str, Union[str, int]]]`: Retrieves a list of nations.
    - `list_meets(nation_id=None, period_id='RECENT') -> List[Dict[str, Union[str, int]]]`: Retrieves a list of meets.

    Usage Example:
    ```python
    session_manager = SessionManager()
    meets_instance = Meets(session_manager, update_interval=120)
    recent_meets = meets_instance.list_meets(period_id='RECENT')
    ```

    Details:
    - This class inherits from `ScraperMixin` to leverage common functionality for making HTTP requests.
    - Use `list_periods()` to retrieve a list of periods.
    - Use `list_nations()` to retrieve a list of nations.
    - Use `list_meets()` to retrieve a list of meets, with optional filtering by nation and period.
    - The returned data is in the form of a list of dictionaries, each containing information about a meet.
    - Dictionary keys include 'meet_id', 'meet_date', 'meet_city', 'meet_name', and 'course_length'.
    - 'nation_id' and 'period_id' parameters in `list_meets()` allow optional filtering by nation and period, respectively.
    """

    def __init__(self, session, update_interval=60):
        """
        Initializes the Meets with a requests session.

        Parameters:
        - session (requests.Session): The requests session to be used for making HTTP requests.
        """
        super().__init__(session, update_interval)

    def list_time_periods(self):
        """
        Retrieves a list of periods.

        Returns:
        - list: A list of dictionaries containing information about each time period.
        """
        params = {'page': 'meetSelect', 'nationId': '0', 'selectPage': 'RECENT'}
        try:
            soup = self._get_page_content(params)
            menu = soup.find('select', {'name': 'selectPage'})
        except AttributeError:
            return []
        periods = []
        for item in menu.find_all('option'):
            if item['value'] != "RECENT" and item['value'] != "BYTYPE":
                periods.append({'period_id': item['value'], 'period_name': unicodedata.normalize("NFKD", item.get_text(strip=True))})
        return periods

    def list_nations(self):
        """
        Retrieves a list of nations.

        Returns:
        - list: A list of dictionaries containing information about each nation.
        """
        params = {'page': 'meetSelect', 'nationId': '0', 'selectPage': 'RECENT'}
        try:
            soup = self._get_page_content(params)
            menu = soup.find('select', {'name': 'nationId'})
        except AttributeError:
            return []
        nations = []
        for item in menu.find_all('option'):
            if item['value'] != "$$$":
                nations.append({'nation_id': item['value'], 'nation_name': unicodedata.normalize("NFKD", item.get_text(strip=True))})
        return nations
        

    def list_meets(self, nation_id=None, time_period_id='RECENT'):
        """
        Retrieves a list of meets.

        Parameters:
        - nation_id (str): The ID of the nation. Defaults to None.
        - time_period_id (str): The ID of the time period. Defaults to 'RECENT'.

        Returns:
        - list: A list of dictionaries containing information about each meet.
        """
        params = {'page': 'meetSelect', 'nationId': nation_id, 'selectPage': time_period_id}
        try:
            soup = self._get_page_content(params)
            tables = soup.find_all('table', {'class': 'meetSearch'})
        except AttributeError:
            return []
        meets = []
        for table in tables:
            for row in table.find_all('tr', {'class': ['meetSearch0', 'meetSearch1']}):
                date_cell = row.find('td', {'class': 'date'})
                meet_date = unicodedata.normalize("NFKD", date_cell.get_text(strip=True))
                city_cell = row.find('td', {'class': 'city'})
                meet_city = unicodedata.normalize("NFKD", city_cell.find('a').get_text(strip=True))
                meet_url = city_cell.find('a')['href']
                meet_name = row.find_all('td', {'class': 'name'})[1].find('a').get_text(strip=True)
                course_cell = row.find('td', {'class': 'course'})
                course_length = course_cell.get_text(strip=True)
                meet_id = parse_qs(urlparse(meet_url).query)['meetId'][0]
                meets.append({'meet_id': meet_id, 'meet_date': meet_date, 'meet_city': meet_city, 'meet_name': meet_name, 'course_length': course_length})
        return meets
    
class Club(ScraperMixin):
    """
    Represents a club and provides methods to retrieve information about the club's athletes.

    Attributes:
    - `sessionManager` (SessionManager): The SessionManager instance for making HTTP requests.
    - `club_id` (str): The ID of the club.
    - `update_interval` (int): The minimum time interval (in seconds) between consecutive updates.

    Methods:
    - `__init__(sessionManager, club_id, update_interval=60)`: Initializes the Club with a requests session.
    - `list_athletes() -> List[Dict[str, Union[str, int]]]`: Retrieves a list of athletes in the club.

    Usage Example:
    ```python
    session_manager = SessionManager()
    club_instance = Club(session_manager, club_id='123456', update_interval=120)
    club_athletes = club_instance.list_athletes()
    ```

    Details:
    - This class inherits from `ScraperMixin` to leverage common functionality for making HTTP requests.
    - Use `list_athletes()` to retrieve a list of athletes in the club.
    - The returned data is in the form of a list of dictionaries, each containing information about an athlete.
    - Dictionary keys include 'athlete_id' and 'athlete_name'.
    - Athlete information is fetched based on the specified club and gender.
    """
    
    def __init__(self, club_id, session, update_interval=60):
        """
        Initializes the Ranking with a requests session.

        Parameters:
        - session (requests.Session): The requests session to be used for making HTTP requests.
        """
        super().__init__(session, update_interval)
        self.club_id = club_id

    def list_athletes(self, gender=0):
        """
        Retrieves a list of athletes.

        Parameters:
        - gender: 0 for ALL, 1 for Men, 2 for Women. Defaults to 0 this will only return currently active athletes.

        Returns:
        - list: A list of dictionaries containing information about each athlete.
        """
        athlete_gender = ['CURRENT', 'ALL_MEN', 'All_WOMEN'][gender]
        params = {'page': 'rankingDetail', 'clubId': self.club_id, 'stroke': '9', 'athleteGender': athlete_gender}
        try:
            soup = self._get_page_content(params)
            tables = soup.find_all('table', {'class': 'athleteList'})
        except AttributeError:
            return []
        athletes = []
        for table in tables:
            for row in table.find_all('tr', {'class': ['athleteSearch0', 'athleteSearch1']}):
                name_cell = row.find('td', {'class': 'name'})
                name = name_cell.find('a').get_text(strip=True)
                athlete_url = name_cell.find('a')['href']
                athlete_id = parse_qs(urlparse(athlete_url).query)['athleteId'][0]
                # TODO: Add more information about the athlete (Gender)
                athletes.append({'athlete_id': athlete_id, 'athlete_name': name})
        return athletes   


if __name__ == '__main__':
    # Example usage
    scraper = SwimrankingsScraper()
    athelete = scraper.get_athlete('4292888')
    print(athelete.list_personal_bests(season='2024'))