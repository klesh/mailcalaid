from dataclasses import dataclass
from datetime import datetime, timezone
from functools import cached_property
from typing import Tuple, Generator, Callable, List, Union, Optional
from abc import ABC, abstractmethod, abstractproperty
import email.utils
import email.header
import email.message
import logging

logger = logging.getLogger(__name__)

@dataclass
class Message:
  msg_id: str
  msg: bytes

  def first_by_type(self, content_type: str) -> str:
    if self.message.is_multipart():
      for part in self.message.walk():
        if part.get_content_type() == content_type and "attachment" not in part.get("Content-Disposition", ""):
          return part.get_payload(decode=True).decode()
    else:
      return self.message.get_payload(decode=True).decode()

  @cached_property
  def message(self) -> email.message.Message:
    return email.message_from_bytes(self.msg)

  @cached_property
  def plain(self) -> str:
    return self.first_by_type("text/plain")

  @cached_property
  def html(self) -> str:
    return self.first_by_type("text/html")

  @cached_property
  def text(self)  -> str:
    return self.plain or self.html

  @cached_property
  def sender_addr(self) -> Tuple[str, str]:
    return email.utils.parseaddr(self.sender)

  @cached_property
  def sender(self):
    return decode_header(self.message["From"])

  @cached_property
  def to(self):
    return decode_header(self.message["To"])

  @cached_property
  def cc(self):
    return decode_header(self.message["Cc"])

  @cached_property
  def bcc(self):
    return decode_header(self.message["Bcc"])

  @cached_property
  def subject(self):
    return decode_header(self.message["Subject"]).replace("\r\n", "")

  @cached_property
  def date(self):
    d = email.utils.parsedate_to_datetime(decode_header(self.message["Date"]))
    if d.tzinfo is None:
      d = d.replace(tzinfo=timezone.utc)
    return d


def decode_header(header):
  # print("header", type(header), header)
  if not header:
    return
  value, charset = email.header.decode_header(header)[0]
  if isinstance(value, bytes):
    if charset:
      value = value.decode(charset)
    else:
      value = str(value)
  return value


class MailClient(ABC):
  # def _fetch_messages(msg_id: int|List[int], msg_id_end: int, headeronly: bool) -> yield (msg_id, msg_bytes)
  _fetch_messages: Callable[[Union[int,List[int]], int, bool], Generator[Tuple[int, bytes], None, None]] = None
  # def _fetch_messages(id: int, headeronly: bool) -> msg_bytes
  _fetch_message: Callable[[int, bool], bytes] = None

  def __init__(self, host: str, port: int, user: str, password: str, ssl=True, batch_size=100, dry_run=False):
    self.host = host
    self.port = port
    self.user = user
    self.password = password
    self.ssl = ssl
    self.batch_size = batch_size
    self.dry_run = dry_run
    if self._fetch_message is None and self._fetch_messages is None:
      raise Exception("either _fetch_messages or _fetch_message must be implemented")
    self.open()

  @abstractmethod
  def open(self):
    pass

  @abstractmethod
  def close(self):
    pass

  @abstractproperty
  def total_messages(self) -> int:
    pass

  @abstractmethod
  def _mark_deleted(self, msg_id: int):
    pass

  def mark_deleted(self, msg_id: int):
    logger.info("mark message %s as deleted", msg_id)
    if not self.dry_run:
      self._mark_deleted(msg_id)

  @abstractmethod
  def _flush(self):
    pass

  def flush(self):
    logger.info("flushing")
    if not self.dry_run:
      self._flush()

  @abstractmethod
  def _fetch_message(self, msg_id:int, headeronly: bool) -> bytes:
    pass

  def fetch_message(self, msg_id: int=1, headeronly=False):
    logger.debug("fetching message %s, headeronly: %s", msg_id, headeronly)
    return Message(msg_id, self._fetch_message(msg_id, headeronly=headeronly))

  def fetch_messages(self,
    msg_id: Union[int,  List[int]],
    msg_id_end: int,
    headeronly=False,
  ) -> Generator[Message, None, None]:
    logger.debug("fetching messages %s - %s headeronly: %s", msg_id, msg_id_end, headeronly)
    if isinstance(msg_id, list):
      for i in msg_id:
        yield Message(i, self._fetch_message(i, headeronly=headeronly))
    else:
      step = 1 if msg_id < msg_id_end else -1
      for i in range(msg_id, msg_id_end + step, step):
        yield Message(i, self._fetch_message(i, headeronly=headeronly))

  def fetch_messages_after(self, dt: datetime, headeronly=True) -> Generator[Message, None, None]:
    for msg in self.fetch_messages(self.total_messages, 1, headeronly=headeronly):
      if msg.date < dt:
        logger.debug("stop fetching because message %s date %s < %s", msg.msg_id, msg.date, dt)
        return
      else:
        logger.debug("message %s date %s", msg.msg_id, msg.date)
      yield msg

  def fetch_messages_before(self, dt: datetime, headeronly=True) -> Generator[Message, None, None]:
    for msg in self.fetch_messages(1, self.total_messages, headeronly=headeronly):
      if msg.date > dt:
        logger.debug("stop fetching because message %s date %s > %s", msg.msg_id, msg.date, dt)
        return
      else:
        logger.debug("message %s date %s", msg.msg_id, msg.date)
      yield msg
  
  def mark_deleted_before(self, dt: datetime):
    for msg in self.fetch_messages_before(dt):
      self.mark_deleted(msg.msg_id)
  
  def mark_deleted_after(self, dt: datetime):
    for msg in self.fetch_messages_after(dt):
      self.mark_deleted(msg.msg_id)
  
  def mark_deleted_keep(self, keep:int):
    def batch():
      total = self.total_messages
      msg_id_end = total - keep
      if msg_id_end > self.batch:
        msg_id_end = self.batch 
      if msg_id_end < 1:
        return False
      logger.info(f"total {total}, deleting 1 to {msg_id_end} messages")
      for msg_id in range(msg_id_end, 0, -1):
        if msg_id % 10 == 0:
          logging.debug("mark deleted %s",  msg_id)
        self.mark_deleted(msg_id)
      self.flush()
      return True
    while batch():
      pass