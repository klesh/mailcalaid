"""
Holiday
"""
from typing import Dict, Tuple, Generator
from datetime import date, datetime, timezone, time,timedelta, tzinfo
from abc import ABC, abstractmethod, abstractproperty
from functools import cached_property
from urllib import request
import json
import logging
import os
from mailcalaid.common import get_config_dir

logger = logging.getLogger(__name__)

class HolidayBook(ABC):
  """ Holiday Book for a country

  :param str cache_dir: cache directory for caching holiday data
  :param int workhours_start: start hour of work hours
  :param int workhours_end: end hour of work hours
  """
  holidays: Dict[date, Tuple[bool, str]]
  cache_dir: str
  workhours_start: time
  workhours_end: time

  def __init__(
    self,
    cache_dir:str="",
    workhours_start:time=time(hour=9),
    workhours_end:time=time(hour=18),
  ):
    if not cache_dir:
      cache_dir = os.path.join(get_config_dir(), "holiday")
    self.holidays = dict()
    self.cache_dir = cache_dir
    os.makedirs(cache_dir, exist_ok=True)
    s = self.sanitize_filename(self.country)
    if not s:
      raise Exception("country name is empty")
    self.cache_file = os.path.join(cache_dir, f"{s}.json")
    if os.path.exists(self.cache_file):
      try:
        self.load()
      except:
        pass
    self.workhours_start = workhours_start
    self.workhours_end = workhours_end

  @staticmethod
  def sanitize_filename(filename: str) -> str:
    return "".join(c for c in filename if c.isalnum() or c in (" ", ".", "_", "-"))

  @abstractmethod
  def load_year(self, year: int) -> Generator[Tuple[date, bool, str], None, None]:
    """Load holidays from some APIs for a given year
    """
    pass

  @abstractproperty
  def timezone(self) -> tzinfo:
    """Timezone
    """
    pass

  @abstractproperty
  def country(self) -> str:
    """Country code"""
    pass

  def mark(self, d: date, is_holiday: bool, name: str):
    """Mark a date as holiday or not"""
    self.holidays[d] = (is_holiday, name)

  def check(self, dt: date|datetime=None) -> Tuple[bool, str]:
    """Check if a date is holiday or not"""
    d = self.normalize_date(dt)
    self.ensure_year(d.year)
    mark = self.holidays.get(d.date())
    if mark:
      return mark
    is_weekend = d.weekday() in (5, 6)
    name = "weekend" if is_weekend else ""
    return is_weekend, name

  def is_holiday(self, dt: date|datetime=None) -> bool:
    is_holiday, _ = self.check(dt)
    return is_holiday

  def is_workhour(self, dt: date|datetime=None, extend:timedelta=None) -> bool:
    """Check if a datetime is work hour or not"""
    dt = self.normalize_date(dt)
    is_holiday, _ = self.check(dt)
    start = datetime.combine(dt.date(), self.workhours_start, tzinfo=self.timezone)
    end = datetime.combine(dt.date(), self.workhours_end, tzinfo=self.timezone) 
    if extend:
      start -= extend
      end += extend
    return not is_holiday and start <= dt < end

  def normalize_date(self, dt: date | datetime) -> datetime:
    """Normalize a date or datetime to a datetime with timezone
    timezone would be converted if given datetime has a different timezone to this book"""
    if isinstance(dt, datetime):
      dt = dt.astimezone(self.timezone)
    elif isinstance(dt, date):
      dt = datetime(dt.year, dt.month, dt.day, tzinfo=self.timezone)
    if dt is None:
      dt = datetime.now().astimezone()
    return dt

  def ensure_year(self, year):
    """Ensure holiday data for a given year is loaded, if not, load it from API"""
    for d in self.holidays.keys():
      if d.year == year:
        return
    logger.info("loading holiday data for %d", year)
    for d, is_holiday, name in self.load_year(year):
      self.mark(d, is_holiday, name)
    self.save()

  def next_workday(self, dt: date|datetime=None) -> datetime:
    """Get next workday"""
    dt = self.normalize_date(dt)
    while True:
      dt += timedelta(days=1)
      if not self.is_holiday(dt):
        return dt.date()

  def latest_workday(self, dt: date|datetime=None) -> datetime:
    """Get latest workday"""
    dt = self.normalize_date(dt)
    while True:
      if not self.is_holiday(dt):
        return dt.date()
      dt -= timedelta(days=1)

  def save(self):
    """Save holiday data to cache file"""
    holidays = dict()
    for d, mark in self.holidays.items():
      holidays[d.isoformat()] = mark
    with open(self.cache_file, "w", encoding="utf8") as f:
      json.dump(holidays, f, indent=2, ensure_ascii=False)

  def load(self):
    """Load holiday data from cache file"""
    with open(self.cache_file, "r", encoding="utf8") as f:
      holidays = json.load(f)
      for d, mark in holidays.items():
        self.holidays[date.fromisoformat(d)] = tuple(mark)


class ChinaHolidayBook(HolidayBook):
  """China holiday book based on Timor API"""

  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)

  @cached_property
  def timezone(self) -> tzinfo:
    return timezone(timedelta(hours=8), "CST")

  @property
  def country(self) -> str:
    return "China"

  def load_year(self, year: int) -> Generator[Tuple[date, bool, str], None, None]:
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:77.0) Gecko/20100101 Firefox/77.0'}
    req = request.Request(f"https://timor.tech/api/holiday/year/{year}", headers=headers)

    with request.urlopen(req) as res:
      data = json.load(res)
      for item in data["holiday"].values():
        yield date.fromisoformat(item["date"]), item["holiday"], item["name"]


class NagerDateHolidayBook(HolidayBook):
  """Based on NagareDate API
  Supported Countries: https://date.nager.at/Country

  .. code-block:: text
    us_holiday_book = NagerDateHolidayBook(timedelta(hours=-7), "US", "cache")
    usd = datetime(2023, 1, 16, 0, 0, 0, 0, us_holiday_book.timezone)
    cnd = datetime(2023, 1, 16, 0, 0, 0, 0, cn_holiday_book.timezone)
    print("usa ", usd, ":  is_holiday, name = ", us_holiday_book.check(usd))
    # usa  2023-01-16 00:00:00-07:00 :  is_holiday, name =  (True, 'Martin Luther King, Jr. Day')
    print("usa ", cnd, ":  is_holiday, name = ", us_holiday_book.check(cnd))
    # usa  2023-01-16 00:00:00+08:00 :  is_holiday, name =  (True, 'weekend')

  :param utc_offset: UTC offset
  :param country_code: country code, see https://date.nager.at/Country
  """

  utc_offset: timedelta
  country_code: str

  def __init__(self, utc_offset: timedelta, country_code: str, *args, **kwargs):
    self.utc_offset = utc_offset
    self.country_code = country_code
    super().__init__(*args, **kwargs)

  @cached_property
  def timezone(self):
    return timezone(self.utc_offset, self.country_code)

  @property
  def country(self):
    return self.country_code

  def load_year(self, year: int) -> Generator[Tuple[date, bool, str], None, None]:
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:77.0) Gecko/20100101 Firefox/77.0'}
    req = request.Request(f"https://date.nager.at/api/v3/publicholidays/{year}/{self.country_code}", headers=headers)

    with request.urlopen(req) as res:
      data = json.load(res)
      for item in data:
        yield date.fromisoformat(item["date"]), True, item["name"]



if __name__ == "__main__":
  logging.basicConfig(format='[%(asctime)s] %(name)s: %(message)s', level=logging.INFO)
  cn_holiday_book = ChinaHolidayBook()
  us_holiday_book = NagerDateHolidayBook(timedelta(hours=-7), "US")
  print("cn_holiday_book tz:", cn_holiday_book.timezone.utcoffset(datetime.now()))
  print("us_holiday_book tz:", us_holiday_book.timezone.utcoffset(datetime.now()))
  print("china today:  is_holiday, name = ", cn_holiday_book.check())
  print("china now:  is_workhour = ", cn_holiday_book.is_workhour())
  print("usa today:  is_holiday, name = ", us_holiday_book.check())
  usd = datetime(2023, 1, 16, 0, 0, 0, 0, us_holiday_book.timezone)
  cnd = datetime(2023, 1, 16, 0, 0, 0, 0, cn_holiday_book.timezone)
  print("usa ", usd, ":  is_holiday, name = ", us_holiday_book.check(usd))
  print("usa ", cnd, ":  is_holiday, name = ", us_holiday_book.check(cnd))
  print("usa now:  is_workhour = ", us_holiday_book.is_workhour())
  usd = datetime(2023, 4, 7, 0, 0, 0, 0, us_holiday_book.timezone)
  cnd = datetime(2023, 4, 7, 0, 0, 0, 0, cn_holiday_book.timezone)
  print("usa ", usd, ":  is_holiday, name = ", us_holiday_book.check(usd))
  print("usa ", cnd, ":  is_holiday, name = ", us_holiday_book.check(cnd))
  cnd = datetime(2023, 4, 7, 6, 0, 0, 0, cn_holiday_book.timezone)
  print("usa ", cnd, ":  is_workhours(extend=2) = ", cn_holiday_book.is_workhour(extend=timedelta(hours=2)))
  cnd = date(2023, 4, 4)
  print("latest workday of", cnd, "is", cn_holiday_book.latest_workday(cnd))
  cnd = date(2023, 4, 5)
  print("latest workday of", cnd, "is", cn_holiday_book.latest_workday(cnd))
  print("next workday of", cnd, "is", cn_holiday_book.next_workday(cnd))