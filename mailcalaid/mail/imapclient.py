import logging
import imaplib
import re
from datetime import datetime
from typing import Generator, Union, List
from mailcalaid.mail.mailclient import MailClient, Message

logger = logging.getLogger(__name__)

# Ref https://www.rfc-editor.org/rfc/rfc3501#section-6.4.5

class ImapClient(MailClient):
  MSG_HEADER = '(BODY.PEEK[HEADER])'
  MSG_FULL = '(RFC822)'
  client: imaplib.IMAP4
  mailbox: str = "INBOX"

  def open(self):
    if self.ssl:
      self.client = imaplib.IMAP4_SSL(host=self.host, port=self.port)
    else:
      self.client = imaplib.IMAP4(host=self.host, port=self.port)
    code, resp = self.client.login(self.user, self.password)
    if code != 'OK':
      raise Exception(resp[0].decode())
    self.select(self.mailbox)

  def close(self):
    self.flush()
    self.client.close()

  @property
  def total_messages(self) -> int:
    return self.select(self.mailbox)

  def list_mailboxes(self) -> Generator[dict, None, None]:
    list_response_pattern = re.compile(
      r'\((?P<flags>.*?)\) "(?P<delimiter>.*)" (?P<name>.*)'
    )
    code, resp = self.client.list()
    if code != 'OK':
        raise Exception(resp[0].decode())
    for line in resp:
      mailbox = list_response_pattern.match(line.decode()).groupdict()
      yield mailbox

  def select(self, mailbox: str) -> int:
    code, resp = self.client.select('"%s"' % mailbox)
    if code != 'OK':
      raise Exception(resp[0].decode())
    self.mailbox = mailbox
    return int(resp[0].decode())
  
  def _fetch_message(self, msg_id:int, headeronly: bool) -> bytes:
    message_parts = self.MSG_HEADER if headeronly else self.MSG_FULL
    code, resp = self.client.fetch(str(msg_id), message_parts)
    if code != 'OK':
        raise Exception(resp[0].decode())
    logger.debug("fetch messags %s, response length: %d", msg_id, len(resp)) 
    return resp[0][1]

  def search(self, criterion: str):
    code, resp = self.client.search(None, criterion)
    if code != 'OK':
      raise Exception(resp[0].decode())
    return resp[0].decode().split() if resp[0] else None

  def _mark_deleted(self, msg_id: int):
    code, resp = self.client.store(msg_id, "+FLAGS", "(\\Deleted)")
    if code != 'OK':
      raise Exception(resp[0].decode())

  def _unmark_deleted(self, msg_id: int):
    code, resp = self.client.store(msg_id, "-FLAGS", "(\\Deleted)")
    if code != 'OK':
      raise Exception(resp[0].decode())

  def _flush(self):
    code, resp = self.client.expunge()
    if code != 'OK':
      raise Exception(resp[0].decode())
