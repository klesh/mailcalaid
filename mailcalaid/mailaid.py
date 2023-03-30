import argparse
import os
import logging
from datetime import datetime
from mailcalaid.mail import Pop3Client, ImapClient

def list_command(args):
  msg_id = (args.page - 1) * args.page_size + 1
  msg_id_end = msg_id + args.page_size - 1
  for msg in args.client.fetch_messages(msg_id, msg_id_end, headeronly=not args.full):
    print("{0:3} {1} {2:40} {3}".format(msg.msg_id, msg.date.isoformat(), msg.sender[:38], msg.subject))

def show_command(args):
  msg = args.client.fetch_message(args.id)
  print("-------------------------------------------------")
  print("Subject  ", msg.subject)
  print("Date     ", msg.date)
  print("From     ", msg.sender)
  print()
  print(msg.plain)

def delete_command(args):
  if args.id:
    args.client.mark_deleted(args.id)
  elif args.keep:
    args.client.mark_deleted_keep(args.keep)
  elif args.before:
    args.client.mark_deleted_before(args.before)
  elif args.after:
    args.client.mark_deleted_after(args.after)

parser = argparse.ArgumentParser()
parser.add_argument("--proto", default=os.getenv("MAIL_PROTO"), help="pop3, imap")
parser.add_argument("--host", default=os.getenv("MAIL_HOST"), help="mail server host")
parser.add_argument("--port", default=os.getenv("MAIL_PORT"), type=int, help="mail server port")
parser.add_argument("--user", default=os.getenv("MAIL_USER"), help="mail user")
parser.add_argument("--passwd", default=os.getenv("MAIL_PASSWD"), help="mail password")
parser.add_argument("--ssl", default=os.getenv("MAIL_SSL") or True, action="store_false", help="use ssl")
parser.add_argument("--debug", action="store_true", help="show debugging log")
parser.add_argument("--dry-run", action="store_true", help="swallow all writing/deleting operations")
parser.add_argument("--batch", type=int, default=100, help="batch size when process massive amount of records. e.g. fetching thousands of messages.")

subparsers = parser.add_subparsers(title='subcommands',
                                   description='valid subcommands',
                                   help='additional help')

parser_list = subparsers.add_parser("list", help="list messages")
parser_list.add_argument("page", nargs='?', type=int, default=1, help="page number")
parser_list.add_argument("-s", "--page-size", type=int, default=10, help="page size")
parser_list.add_argument("-f", "--full", action="store_true", help="fetch full message instead of header only")
parser_list.set_defaults(command=list_command)

parser_show = subparsers.add_parser("show", help="show message")
parser_show.add_argument("id", type=int, help="message id")
parser_show.set_defaults(command=show_command)

parser_delete = subparsers.add_parser("delete", help="delete messages")
parser_delete.add_argument("id", nargs='?', help="message id to be deleted")
parser_delete.add_argument("--keep", type=int)
parser_delete.add_argument("--after", type=lambda s: datetime.strptime(s, '%Y-%m-%d').astimezone())
parser_delete.add_argument("--before", type=lambda s: datetime.strptime(s, '%Y-%m-%d').astimezone())
parser_delete.set_defaults(command=delete_command)

def help_command(args):
  if args.name:
    subparsers.choices[args.name].print_help()
  else:
    parser.print_help()
parser_help = subparsers.add_parser("help", help="show help")
parser_help.add_argument("name", nargs='?', help="command name")
parser_help.set_defaults(command=help_command)

args = parser.parse_args()

logging.basicConfig(format='[%(asctime)s] %(name)s: %(message)s', level=logging.DEBUG if args.debug else logging.INFO)

if not (args.host and args.user and args.passwd):
  exit(parser.print_usage())

kwargs= {
  "host": args.host,
  "port": args.port,
  "user": args.user,
  "password": args.passwd,
  "ssl": args.ssl,
  "batch_size": args.batch,
  "dry_run": args.dry_run,
}
if args.proto == "pop3":
  args.client = Pop3Client(**kwargs)
elif args.proto == "imap":
  args.client = ImapClient(**kwargs)

args.command(args)