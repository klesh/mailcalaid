# mailcalaid

A Python library to provide aid to accomplish tasks related to mail and calendar.


# usage

## maidaid

Help
```powershell
py -m mailcalaid.mailaid help [subcommand]
```

Setup mail server / account
```powershell
$env:MAIL_PROTO = "imap"
$env:MAIL_HOST = "imap.qq.com"
$env:MAIL_PORT = "993"
$env:MAIL_USER = "xxxxx@qq.com"
$env:MAIL_PASSWD = "???????"
$env:MAIL_SSL = "true"
```

List mailboxes (imap only)
```powershell
# (imap only)
py -m mailcalaid.mailaid mailboxes
```

List messages
```powershell
# get first page
py -m mailcalaid.mailaid list
# set page size to 100 and fetch the 2nd page
py -m mailcalaid.mailaid list --page-size 100 2
```

Show message
```powershell
# show oldest message
py -m mailcalaid.mailid show 1
# show newest message
py -m mailcalaid.mailid show -1
```

Backup messages
```powershell
# backup messages 1~20 from INBOX as `mbox` file
py -m mailcalaid.mailid download --id 1 --id-end 20 backup.mbox
# backup all messages from "Sent Messages"
py -m mailcalaid.mailid --mailbox "Sent Messages" download --all sent.mbox
```

Delete messages
```powershell
# (imap only) delete all message in "Sent Messages"
py -m mailcalaid.mailid --mailbox "Sent Messages" delete --all
# keep certain amount of newest messages and delete the rest
py -m mailcalaid.mailid delete --keep 700
# delete messages before given date
py -m mailcalaid.mailid delete --before "2023-01-01"
# delete messages after given date
py -m mailcalaid.mailid delete --after "2023-01-01"
```

Debugging options
```powershell
# print debugging log
py -m mailcalaid.mailid --debug <command> ...
# readonly mode, swallow all writing/deleting operations
py -m mailcalaid.mailid --dry-run <command> ...
# specify target mailbox (imap only)
py -m mailcalaid.mailid --mailbox "mailboxname" <command> ...
```