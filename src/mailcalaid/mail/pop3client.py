import poplib
import email.utils
import email.header
import logging
from typing import Generator
from mailcalaid.mail.mailclient import MailClient, Message

logger = logging.getLogger(__name__)

class Pop3Client(MailClient):
  client: poplib.POP3

  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)

  def open(self):
    if self.ssl:
      pop3client = poplib.POP3_SSL(host=self.host, port=self.port, timeout=self.timeout)
    else:
      pop3client = poplib.POP3(host=self.host, port=self.port, timeout=self.timeout)
    pop3client.user(self.user)
    pop3client.pass_(self.password)
    self.client = pop3client

  def close(self):
    self.client.quit()

  @property
  def total_messages(self) -> int:
    return self.client.stat()[0]

  def total_size(self) -> int:
    """Total size of all messages in mailbox"""
    return self.client.stat()[1]

  def _fetch_message(self, msg_id:int, headeronly: bool) -> bytes:
    code, lines, octets = self.client.top(msg_id, 0) if headeronly else self.client.retr(msg_id)
    logger.debug("fetch message %d response code %s, octets %d", msg_id, code, octets)
    return b'\r\n'.join(lines)

  def _mark_deleted(self, msg_id: int):
    return self.client.dele(msg_id)

  def _flush(self):
    self.close()
    self.open()

  def unmark_all_deleted(self):
    """Unmark all deleted messages"""
    self.client.rset()
