#!/usr/bin/env python
from flask import Flask, render_template
import sys
import os
import gc
from time import time, strftime, gmtime
from msgpack import unpackb
import datetime
import redis
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__),
                                             os.path.pardir)))
import settings

app = Flask(__name__)
app.config.from_object(settings)
app.template_folder = "%s/templates" % settings.APP_DIR

conn = redis.Redis(settings.REDIS_HOST, settings.REDIS_PORT,
                   settings.REDIS_DB)


def _decode_datetime(obj):
    if b'__datetime__' in obj:
        obj = datetime.datetime.strptime(obj["as_str"],
                                         "%Y%m%dT%H:%M:%S.%f")
    return obj


def _get_hosts():
    hosts = conn.hgetall('hosts')
    gc.disable()
    hosts = unpackb(hosts['hosts'])
    gc.enable()
    hosts = [h['host'] for h in hosts]
    return hosts


@app.route('/upload/<hostname>/', methods=['POST'])
@app.route('/upload/<hostname>', methods=['POST'])
def upload_report(hostname):
    pass


@app.route('/details/<hostname>/', methods=['GET'])
@app.route('/details/<hostname>', methods=['GET'])
def details(hostname):
    hosts = _get_hosts()
    details = {}
    if hostname not in hosts:
        details = {'error': "invalid hostname",
                   'time': time()}
    else:
        details = conn.hgetall("%s:%s" % (settings.CUR_PREFIX, hostname))
        gc.disable()
        details['report'] = unpackb(details['report'])
        gc.enable()
    return render_template("details.html", details=details)


@app.route('/', methods=['GET'])
def show_reports():
    hosts = _get_hosts()
    reports = []
    for h in hosts:
        rkey = "%s:%s" % (settings.CUR_PREFIX, h)
        r = conn.hgetall(rkey)
        t = strftime("%Y-%m-%d %H:%M:%S", gmtime(float(r['time'])))
        gc.disable()
        r['report'] = unpackb(r['report'])
        gc.enable()
        value = {'host': r['report']['host'],
                 'status': r['report']['status'],
                 'time': t}
        reports.append(value)
    return render_template("index.html", reports=reports)

if __name__ == '__main__':
    app.run(host=settings.FLASK_HOST, port=settings.FLASK_PORT, debug=True)
