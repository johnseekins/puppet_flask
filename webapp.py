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

app = Flask(__name__)
app.config.from_object(settings)
app.template_folder = "%s/templates" % settings.APP_DIR

conn = redis.Redis(settings.REDIS_HOST, settings.REDIS_PORT,
                   settings.REDIS_DB)


def _get_hosts():
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
                 'environment': r['report']['environment'],
                 'time': t}
        if all(v not in value['status'] for v in ['failed', 'error']):
            value['change_count'] = r['report']['metrics']['changes']['values'][0][2],
        reports.append(value)
    return render_template("index.html", reports=reports)

if __name__ == '__main__':
    app.run(host=settings.FLASK_HOST, port=settings.FLASK_PORT, debug=True)

