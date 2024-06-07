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
  """Message wraps email.message.Message and provides some useful properties

  :param str msg_id: message id
  :param bytes msg: message bytes
  """
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
    d = self.message["Date"]
    if not d:
      d = self.message["Received"].split(";")[1].strip()
    if not d:
      logger.warning("no date header found\n%s", self.msg)
      return None
    try:
      d = email.utils.parsedate_to_datetime(decode_header(d))
      if d.tzinfo is None:
        d = d.replace(tzinfo=timezone.utc)
      return d
    except Exception as e:
      logger.warning("failed to parse date %s: %s", d, e)
      return None


def decode_header(header):
  # print("header", type(header), header)
  if not header:
    return ""
  value, charset = email.header.decode_header(header)[0]
  if isinstance(value, bytes):
    if charset:
      try:
        value = value.decode(charset)
      except Exception as e:
        logger.warning("failed to decode header %s: %s", header, e)
        value = value.decode("utf-8", errors="replace")
    else:
      value = str(value)
  return value


class MailClient(ABC):
  """Abstract mail client

  :param str host: mail server host
  :param int port: mail server port
  :param str user: mail server user
  :param str password: mail server password
  :param bool ssl: use ssl when connecting to mail server
  :param int batch_size: batch size when processing messages
  :param bool dry_run: dry run mode
  """

  def __init__(self, host: str, port: int, user: str, password: str, ssl=True, batch_size=100, dry_run=False, timeout=60):
    self.host = host
    self.port = port
    self.user = user
    self.password = password
    self.ssl = ssl
    self.batch_size = batch_size
    self.dry_run = dry_run
    self.timeout = timeout
    if self._fetch_message is None and self._fetch_messages is None:
      raise Exception("either _fetch_messages or _fetch_message must be implemented")
    self.open()

  @abstractmethod
  def open(self):
    """Open connection to mail server"""
    pass

  @abstractmethod
  def close(self):
    """Close connection to mail server"""
    pass

  @abstractproperty
  def total_messages(self) -> int:
    """Total number of messages in mailbox"""
    pass

  @abstractmethod
  def _mark_deleted(self, msg_id: int):
    pass

  def mark_deleted(self, msg_id: int):
    """Mark message as deleted"""
    logger.info("mark message %s as deleted", msg_id)
    if not self.dry_run:
      self._mark_deleted(str(msg_id))

  @abstractmethod
  def _flush(self):
    pass

  def flush(self):
    """Flush deleted messages"""
    logger.info("flushing")
    if not self.dry_run:
      self._flush()

  @abstractmethod
  def _fetch_message(self, msg_id:int, headeronly: bool) -> bytes:
    pass

  def fetch_message(self, msg_id: int=1, headeronly=False):
    """Fetch message

    :param int msg_id: message id
    :headeronly bool: fetch only header
    """
    logger.debug("fetching message %s, headeronly: %s", msg_id, headeronly)
    return Message(msg_id, self._fetch_message(msg_id, headeronly=headeronly))

  def fetch_messages(self,
    msg_id: Union[int,  List[int]],
    msg_id_end: int,
    headeronly=False,
  ) -> Generator[Message, None, None]:
    """Fetch messages
    
    :param int|list msg_id: message id or list of message ids
    :param int msg_id_end: optional, end message id
    :param bool headeronly: fetch only header
    """
    logger.debug("fetching messages %s - %s headeronly: %s", msg_id, msg_id_end, headeronly)
    if isinstance(msg_id, list):
      for i in msg_id:
        yield Message(i, self._fetch_message(i, headeronly=headeronly))
    else:
      step = 1 if msg_id < msg_id_end else -1
      for i in range(msg_id, msg_id_end + step, step):
        yield Message(i, self._fetch_message(i, headeronly=headeronly))

  def fetch_messages_after(self, dt: datetime, headeronly=True) -> Generator[Message, None, None]:
    """Fetch messages after date
    
    :param datetime dt: date
    :param bool headeronly: fetch only header
    """
    for msg in self.fetch_messages(self.total_messages, 1, headeronly=headeronly):
      if msg.date < dt:
        logger.debug("stop fetching because message %s date %s < %s", msg.msg_id, msg.date, dt)
        return
      else:
        logger.debug("message %s date %s", msg.msg_id, msg.date)
      yield msg

  def fetch_messages_before(self, dt: datetime, headeronly=True) -> Generator[Message, None, None]:
    """Fetch messages before date
    
    :param datetime dt: date
    :param bool headeronly: fetch only header
    """
    for msg in self.fetch_messages(1, self.total_messages, headeronly=headeronly):
      if msg.date > dt:
        logger.debug("stop fetching because message %s date %s > %s", msg.msg_id, msg.date, dt)
        return
      else:
        logger.debug("message %s date %s", msg.msg_id, msg.date)
      yield msg
  
  def mark_deleted_before(self, dt: datetime):
    """Mark messages before date as deleted """
    for msg in self.fetch_messages_before(dt):
      self.mark_deleted(msg.msg_id)
  
  def mark_deleted_after(self, dt: datetime):
    """Mark messages after date as deleted"""
    for msg in self.fetch_messages_after(dt):
      self.mark_deleted(msg.msg_id)
  
  def mark_deleted_keep(self, keep:int):
    """Mark messages as deleted while keeping the last n messages"""
    def batch():
      total = self.total_messages
      msg_id_end = total - keep
      if msg_id_end > self.batch_size:
        msg_id_end = self.batch_size
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

  def mark_deleted_all(self):
    """Mark all messages as deleted"""
    for msg_id in range(1, self.total_messages + 1):
      self.mark_deleted(msg_id)

  def unmark_deleted(self, msg_id: int):
    """Unmark message as deleted"""
    self.unmark_deleted(msg_id)