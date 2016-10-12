from os import dirname, realpath
REDIS_HOST = 'localhost'
REDIS_PORT = 6379
REDIS_DB = 0
INTERVAL = 60
REPORT_DIR = '/opt/puppetlabs/server/data/puppetserver/reports'
APP_DIR = dirname(realpath(__file__))
ROOT_DIR = APP_DIR.split("/")[-1]
CUR_PREFIX = 'curreport'
HIST_PREFIX = 'histreport'
HIST_REPORTS = 3
"""
The number of seconds old a report can be before we alert
"""
REPORT_WARN = 3600
REPORT_ERROR = 7200

# Debug
FLASK_HOST = '0.0.0.0'
FLASK_PORT = 8000
DEBUG = False
THREADED = True
