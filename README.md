# mailcalaid

A Python library/commands to provide aid to accomplish tasks related to mail and calendar.


# Installation

```
pip install git+https://github.com/klesh/mailcalaid.git
```


# Usage


## Libraries

### holiday module

```python
from datetime import timedelta, datetime
from mailcalaid.cal.holiday import NagerDateHolidayBook

us_holiday_book = NagerDateHolidayBook(timedelta(hours=-7), "US")
print("usa today:  is_holiday, name = ", us_holiday_book.check())
usd = datetime(2023, 1, 16, 0, 0, 0, 0, us_holiday_book.timezone)
print("usa ", usd, ":  is_holiday, name = ", us_holiday_book.check(usd))
# usa  2023-01-16 00:00:00-07:00 :  is_holiday, name =  (True, 'Martin Luther King, Jr. Day')
print("usa ", usd, ":  is_workhour = ", us_holiday_book.is_workhour(usd))
# usa  2023-01-16 00:00:00-07:00 :  is_workhour =  False
usd = datetime(2023, 4, 5, 9, 0, 0, 0, us_holiday_book.timezone)
print("usa ", usd, ":  is_holiday, name = ", us_holiday_book.check(usd))
# usa  2023-04-05 09:00:00-07:00 :  is_holiday, name =  (False, '')
print("usa ", usd, ":  is_workhour = ", us_holiday_book.is_workhour(usd))
# usa  2023-04-05 09:00:00-07:00 :  is_workhour =  True
```


## CLI Tool

### maidaid

Manage your remote emails

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


### mail2bot

Monitor new messages that meet certain criterions and send http requests to your bot hook (Slack/Feishu, etc.)

Step 1: Copy configuration folder `examples/mail2bot` to your local file system and set it up according
  1. `mail2bot.ini` is for setting up mail server, message filter and web bot configuration.
  2. `mail2bot_state.ini` is for storing the previous checking time.
Step 2: Test out
```sh
> export CONFIG_DIR=/path/to/mail2bot
> py -m mailcalaid.mail2bot --dry-run
[2023-04-02 20:35:45,817] __main__: start checking new mails since 2023-03-29 16:30:12+08:00
[2023-04-02 20:35:47,003] __main__: would notify for 2023-04-02 01:59:01-07:00 [apache/incubator-devlake] feat(domain): add issue_assignees domain table (PR #4841)
[2023-04-02 20:35:48,494] __main__: would notify for 2023-04-01 17:18:24-07:00 Re: [apache/incubator-devlake] [Feature][Config UI] Showing notifications in browser when a blueprint finishes running (Issue #2251)[2023-04-02 20:35:48,644] __main__: would notify for 2023-04-01 17:18:20-07:00 Re: [apache/incubator-devlake] [Feature][Infra] ApiCollectors to resume collected data from previous failed collection (Issue #3822)
[2023-04-02 20:35:48,818] __main__: would notify for 2023-04-01 17:18:16-07:00 Re: [apache/incubator-devlake] [Feature][gitextractor] solution needed for https disabled orgs (Issue #4392)
[2023-04-02 20:35:48,943] __main__: would notify for 2023-04-01 17:18:13-07:00 Re: [apache/incubator-devlake] [Feature][BitBucket] Support BitBucket server version (Issue #4568)
[2023-04-02 20:35:50,193] __main__: would notify for 2023-04-01 05:34:08-07:00 Re: [apache/incubator-devlake-helm-chart] feat: enable selection of default Nginx ingress vs generic one. (PR #104)
[2023-04-02 20:35:50,624] __main__: would notify for 2023-04-01 05:32:45-07:00 Re: [apache/incubator-devlake-helm-chart] feat: enable selection of default Nginx ingress vs generic one. (PR #104)
[2023-04-02 20:35:51,094] __main__: would notify for 2023-04-01 03:45:12-07:00 Re: [apache/incubator-devlake] fix: Fix failing tests (PR #4840)
[2023-04-02 20:35:57,074] __main__: would notify for 2023-03-31 17:17:39-07:00 Re: [apache/incubator-devlake] [Feature][UI] More robust validation of endpoint URL (Issue #4199)
[2023-04-02 20:35:57,924] __main__: would notify for 2023-03-31 15:05:17-07:00 [apache/incubator-devlake] fix: Fix failing tests (PR #4840)
[2023-04-02 20:36:01,294] __main__: would notify for 2023-03-31 09:14:59-07:00 [apache/incubator-devlake] [Feature][SonarCube Connection] Add support for SonarCloud (Issue #4838)
[2023-04-02 20:36:03,193] __main__: would notify for 2023-03-31 07:34:14-07:00 Re: [apache/incubator-devlake] feat(circleci): add circleci plugin (PR #4803)
[2023-04-02 20:36:03,365] __main__: would notify for 2023-03-31 07:32:20-07:00 Re: [apache/incubator-devlake] feat(circleci): add circleci plugin (PR #4803)
[2023-04-02 20:36:03,494] __main__: would notify for 2023-03-31 06:21:43-07:00 [apache/incubator-devlake] fix: ensure Changelog IDs are numeric (PR #4835)
[2023-04-02 20:36:06,544] __main__: would notify for 2023-03-31 03:40:01-07:00 Re: [apache/incubator-devlake] Fix json arg parsing (PR #4831)
[2023-04-02 20:36:06,694] __main__: would notify for 2023-03-31 03:37:37-07:00 Re: [apache/incubator-devlake] feat(config-ui): support plugin azure devops (PR #4504)
[2023-04-02 20:36:06,864] __main__: would notify for 2023-03-31 03:34:09-07:00 Re: [apache/incubator-devlake] feat(config-ui): support plugin azure devops (PR #4504)
[2023-04-02 20:36:07,484] __main__: would notify for 2023-03-31 03:30:39-07:00 [apache/incubator-devlake] Fix json arg parsing (PR #4831)
[2023-04-02 20:36:07,964] __main__: would notify for 2023-03-31 03:02:40-07:00 Re: [apache/incubator-devlake] [Feature][Docker] Docker images built from `main` (Issue #4785)
[2023-04-02 20:36:08,324] __main__: would notify for 2023-03-31 02:54:46-07:00 Re: [apache/incubator-devlake-helm-chart] feat: enable selection of default Nginx ingress vs generic one. (PR #104)
[2023-04-02 20:36:11,194] __main__: would notify for 2023-03-31 02:13:49-07:00 [apache/incubator-devlake] [Bug][customize] Error occurred when mapping float type field using Customize plugin (Issue #4828)
[2023-04-02 20:36:11,314] __main__: would notify for 2023-03-31 01:56:43-07:00 [apache/incubator-devlake] [Bug][convertIssueChangelogs] parsing "[90]": invalid syntax (Issue #4827)
[2023-04-02 20:36:11,564] __main__: done checking new mails, next since would be 2023-04-02 20:35:45.817328
```
Step 3: Go live
```sh
> export CONFIG_DIR=/path/to/mail2bot
> py -m mailcalaid.mail2bot
```