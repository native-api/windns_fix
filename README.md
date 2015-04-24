Workaround for win2008/win2012 DNS server startup bug: errors 404,407,408 at system startup.

See https://www.google.ru/search?q=win2008+win2012+dns+error+404+407+408 for the bug discussion.
For specific links, see e.g. http://forums.petri.com/showthread.php?t=62255 and https://social.technet.microsoft.com/Forums/ru-RU/374112f8-f8a5-4eb8-8682-2a54b2de601f .
This is for the case when there's nothing special on the server (no multihoming, virtualization etc.) -
the cause appears to be that TCP/IP is not fully functional when its driver reports it has started.

The scripts searches DNS server event log for the specific errors and restarts its service if there are.

# Installation

* Install Python 2.7 and modules: pywin32, iso8601
* Copy the script to what will be its working directory (the log will be placed alongside the script)
* Install the service to run delayed and as Local System: `(path)\dns_fix.py --startup=delayed install`
* start the service and check the log to confirm it works as expected (the service exits after finishing its work)
