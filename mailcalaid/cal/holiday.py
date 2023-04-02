from typing import Dict, Tuple, Generator
from datetime import date, datetime
from zoneinfo import ZoneInfo
from abc import ABC, abstractmethod, abstractproperty
from functools import cached_property
from urllib import request
import json
import logging
import os

logger = logging.getLogger(__name__)

class HolidayBook(ABC):
  holidays: Dict[date, Tuple[bool, str]]
  cache_dir: str
  workhours_start: int
  workhours_end: int

  def __init__(self, cache_dir:str, workhours_start:int=9, workhours_end:int=18):
    self.holidays = dict()
    self.cache_dir = cache_dir
    os.makedirs(cache_dir, exist_ok=True)
    s = self.timezone.replace("/", "-")
    self.cache_file = os.path.join(cache_dir, f"{s}.json")
    if os.path.exists(self.cache_file):
      try:
        self.load()
      except:
        pass
    self.workhours_start = workhours_start
    self.workhours_end = workhours_end

  @abstractproperty
  def timezone(self) -> str:
    pass

  @abstractmethod
  def load_year(self, year: int) -> Generator[Tuple[date, bool, str], None, None]:
    pass

  @cached_property
  def tzinfo(self):
    return ZoneInfo(self.timezone)

  def mark(self, d: date, is_holiday: bool, name: str):
    self.holidays[d] = (is_holiday, name)

  def check(self, dt: date|datetime=None) -> Tuple[bool, str]:
    d = self.normalize_date(dt)
    self.ensure_year(d.year)
    mark = self.holidays.get(d.date())
    if mark:
      return mark
    is_weekend = d.weekday() in (5, 6)
    name = "weekend" if is_weekend else ""
    return is_weekend, name

  def is_workhour(self, dt: date|datetime=None) -> bool:
    dt = self.normalize_date(dt)
    is_holiday, _ = self.check(dt)
    return not is_holiday and self.workhours_start <= dt.hour < self.workhours_end

  def normalize_date(self, dt: date | datetime) -> datetime:
    if isinstance(dt, date):
      dt = datetime(dt.year, dt.month, dt.day, tzinfo=self.tzinfo)
    if isinstance(dt, datetime):
      dt = dt.astimezone(self.tzinfo)
    if dt is None:
      dt = datetime.now()
    return dt

  def ensure_year(self, year):
    for d in self.holidays.keys():
      if d.year == year:
        return
    logger.info("loading holiday data for %d", year)
    for d, is_holiday, name in self.load_year(year):
      self.mark(d, is_holiday, name)
    self.save()

  def save(self):
    holidays = dict()
    for d, mark in self.holidays.items():
      holidays[d.isoformat()] = mark
    with open(self.cache_file, "w") as f:
      json.dump(holidays, f, indent=2, ensure_ascii=False)

  def load(self):
      with open(self.cache_file, "r") as f:
        holidays = json.load(f)
        for d, mark in holidays.items():
          self.holidays[date.fromisoformat(d)] = tuple(mark)


class ChinaHolidayBook(HolidayBook):

  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)

  @property
  def timezone(self):
    return "Asia/Shanghai"

  def load_year(self, year: int) -> Generator[Tuple[date, bool, str], None, None]:
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:77.0) Gecko/20100101 Firefox/77.0'}
    req = request.Request(f"https://timor.tech/api/holiday/year/{year}", headers=headers)

    with request.urlopen(req) as res:
      data = json.load(res)
      for item in data["holiday"].values():
        yield date.fromisoformat(item["date"]), item["holiday"], item["name"]



if __name__ == "__main__":
  # cn_holiday_book = HolidayBook("Asia/Shanghai")
  # cn_holiday_book.mark(date(2021, 1, 1), True, "元旦")
  # print(cn_holiday_book.check(datetime(2023,1,1,0,0,0, tzinfo=ZoneInfo("Asia/Shanghai")))) 
  # print(cn_holiday_book.check(datetime(2023,1,1,8,0,0, tzinfo=ZoneInfo("America/Los_Angeles")))) 
  logging.basicConfig(format='[%(asctime)s] %(name)s: %(message)s', level=logging.INFO)
  cn_holiday_book = ChinaHolidayBook("cache")
  print(cn_holiday_book.check())
  print(cn_holiday_book.is_workhour())

  