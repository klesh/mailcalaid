import json
import re
import time
import logging
import os
from urllib import request
from string import Template
from datetime import datetime, timedelta
from mailcalaid.mail import MailClient, ImapClient, Pop3Client
from configparser import ConfigParser

logging.basicConfig(format='[%(asctime)s] %(name)s: %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

dry_run = False

config_datetime_fmt="%Y-%m-%d %H:%M:%S"
config_dir = os.getenv("CONFIG_DIR", "config" )

config_file = os.path.join(config_dir, "mail2bot.ini")
config = ConfigParser(interpolation=None)
config.read(config_file, encoding="utf-8")

state_file = os.path.join(config_dir, "mail2bot_state.ini")
state = ConfigParser(interpolation=None)
if os.path.exists(state_file):
  state.read(state_file, encoding="utf-8")
else:
  state.add_section("state")
  state["state"]["previous_started_at"] = ""

general_config = config["general"]
interval = general_config.getint("interval", 60)
workhours_start = general_config.getint("workhours_start", 9)
workhours_end = general_config.getint("workhours_end", 18)
cache_dir = general_config.get("cahce_dir", "cache")

server_config = config["imap"]
proto=server_config["proto"]
host=server_config["host"]
port=int(server_config["port"])
user=server_config["user"]
passwd=server_config["passwd"]
ssl=server_config.getboolean("ssl", True)

filter_config = config["filter"]
subject_keyword = filter_config.get("subject_keyword")
fromaddrs = filter_config.get("fromaddrs")
if fromaddrs:
  fromaddrs = set(fromaddrs.split(","))
ignore_realnames = filter_config.get("ignore_realnames")
if ignore_realnames:
  ignore_realnames = set(filter(lambda x:x,  ignore_realnames.split("\n")))

bothook_config = config["bothook"]
link_re = re.compile(bothook_config["link_re"], re.M)
bothook_url=bothook_config["bothook_url"]
bothook_headers = {}
bothook_headers_config = config["bothook request headers"]
if bothook_headers_config:
  for header in bothook_headers_config:
    bothook_headers[header] = bothook_headers_config[header] 
bothook_body_tpl = bothook_config["bothook_body"]
bothook_body_tpl =  Template(bothook_body_tpl)

def notify_bothook(detail):
  subject = detail.subject.replace("\r\n", "")
  localdate = datetime.fromtimestamp(detail.date.timestamp())
  link = link_re.search(detail.text)
  if not link:
    logger.error(f"failed to extract the link:\n{detail.text}")
    return
  realname, fromaddr = detail.sender_addr
  body = (bothook_body_tpl.substitute(
    subject=subject,
    subject_json=json.dumps(subject),
    date=localdate,
    link=link.group().strip(),
    realname=realname,
    fromaddr=fromaddr,
  ))
  req = request.Request(
    url=bothook_url,
    method="POST",
    data=body.encode("utf-8"),
  )
  for header in bothook_headers:
    req.add_header(header, bothook_headers[header])
  with request.urlopen(req) as res:
    logger.info(f"notify for {subject} status: {res.status}")


def checkmail(previous_started_at: datetime) -> datetime:
  kwargs = dict(
    host=host,
    port=port,
    user=user,
    password=passwd,
    ssl=ssl,
  )
  client = ImapClient(**kwargs) if proto=="imap" else Pop3Client(**kwargs)
  for msg in client.fetch_messages_after(previous_started_at, headeronly=True):
    if subject_keyword not in msg.subject:
      continue
    realname, fromaddr = msg.sender_addr
    if fromaddr not in fromaddrs:
      continue
    if realname in ignore_realnames:
      continue
    if dry_run:
      logger.info(f"would notify for {msg.date} {msg.subject}")
    else:
      notify_bothook(client.fetch_message(msg.msg_id))
  client.close()

state_config = state["state"]
def stateful_checkmail():
  previous_started_at = state_config.get("previous_started_at")
  if previous_started_at :
    previous_started_at = datetime.strptime(previous_started_at, config_datetime_fmt)
  if not previous_started_at:
    previous_started_at = datetime.today()-timedelta(days=1)
  if not previous_started_at.tzinfo:
    previous_started_at = previous_started_at.replace(tzinfo=datetime.now().astimezone().tzinfo)
  logger.info("start checking new mails since %s", previous_started_at)
  started_at = datetime.now()
  try:
    checkmail(previous_started_at)
    state_config["previous_started_at"] = started_at.strftime(config_datetime_fmt)
    if not dry_run:
      with open(state_file, "w", encoding="utf8") as f:
        state.write(f)
    logger.info("done checking new mails, next since would be %s", started_at)
  except Exception:
    logger.exception("failed to check new mails")



import argparse
parser = argparse.ArgumentParser()
parser.add_argument("--dry-run", action="store_true", default=False)
args = parser.parse_args()
dry_run = args.dry_run

from mailcalaid.cal.holiday import ChinaHolidayBook
cn_holiday_book=None
if not dry_run:
  cn_holiday_book = ChinaHolidayBook(
    cache_dir=cache_dir,
    workhours_start=timedelta(hours=workhours_start),
    workhours_end=timedelta(hours=workhours_end),
  )
while True:
  if dry_run or cn_holiday_book.is_workhour():
    stateful_checkmail()
  time.sleep(interval)