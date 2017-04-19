#!/usr/bin/env python
from flask import Flask, render_template, jsonify
import sys
import os
import gc
from time import time, strftime, gmtime, timezone
from msgpack import unpackb
import datetime
import redis
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__),
                                             os.path.pardir)))
import settings

"""
Generally, we will add use msgpack for compressing data, which is nice,
but because of how the unpack code works, we need to disable normal
python garbage collection for the command. e.g.
gc.disable()
var = unpackb(<msgpack data>)
gc.enable()
At small scales, this doesn't really matter, but as the size of the project
increases, we can see performance problems if we don't do this.
"""

app = Flask(__name__)
app.config.from_object(settings)
app.template_folder = "%s/templates" % settings.APP_DIR

# Use a single redis connection
conn = redis.Redis(settings.REDIS_HOST, settings.REDIS_PORT,
                   settings.REDIS_DB)

def _get_hosts():
    # Get a list of hosts that have reports from redis 
    hosts = conn.hgetall('hosts')
    gc.disable()
    hosts = unpackb(hosts['hosts'])
    gc.enable()
    hosts = [h['host'] for h in hosts]
    return hosts


@app.route('/historical/<hostname>/<version>/', methods=['GET'])
@app.route('/historical/<hostname>/<version>', methods=['GET'])
@app.route('/historical/<hostname>/', methods=['GET'])
@app.route('/historical/<hostname>', methods=['GET'])
def historical(hostname, version=0):
    """
    We're using a list in redis for historical reports
    only keeping 'x' number of reports and relying on
    redis to "age out" the extra reports as new ones 
    come in
    """
    try:
        version = int(version)
    except Exception, e:
        return jsonify({'error': str(e)})

    hosts = _get_hosts()
    if hostname not in hosts:
        return jsonify({})
    key = "%s:%s" % (settings.HIST_PREFIX, hostname)
    rep = conn.lindex(key, version)
    if not rep:
        return jsonify({'error': 'report missing or removed'})
    rep = eval(rep)
    gc.disable()
    rep = unpackb(rep['report'])
    gc.enable()
    return jsonify(rep)


@app.route('/details/<hostname>/', methods=['GET'])
@app.route('/details/<hostname>', methods=['GET'])
def details(hostname):
    # fetch a full report for a specific host
    hosts = _get_hosts()
    details = {}
    if hostname not in hosts:
         return jsonify({'error': "invalid hostname",
                         'time': (time() + timezone)}), 501
    details = conn.hgetall("%s:%s" % (settings.CUR_PREFIX, hostname))
    gc.disable()
    details = unpackb(details['report'])
    gc.enable()
    del details['resource_statuses']
    return jsonify(details)


@app.route('/', methods=['GET'])
def show_reports():
    cur_t = time() + timezone
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
                 'environment': r['report']['environment'],
                 'time': t, 'epoch': float(r['time'])}
        if all(v not in value['status'] for v in ['failed', 'error']):
            changes = r['report']['metrics']['changes']
            value['change_count'] = changes['values'][0][2],
        reports.append(value)
    warning = cur_t - settings.REPORT_WARN
    error = cur_t - settings.REPORT_ERROR
    return render_template("index.html", reports=reports, warn=warning,
                           error=error)

if __name__ == '__main__':
    app.run(host=settings.FLASK_HOST, port=settings.FLASK_PORT, debug=True)

