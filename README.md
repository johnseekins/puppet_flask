# puppetflask

# Info
puppetflask is a _very_ simple dashboard to display reports from your puppetmaster host. Should support puppet report versions >= 3.

# Setup
Requires a working Redis instance (to reduce disk requests).

Currently, to make this tool collect data, you'll need to set up a cron running `report_parser.py`.
```
* * * * * root python /opt/puppetflask/report_parser.py > /tmp/puppet-report.log 2>&1
```

## Config
`settings.py` holds the basic configs you'll need to get the service running.

