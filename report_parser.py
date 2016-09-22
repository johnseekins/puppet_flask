#!/usr/bin/env python
import yaml
import sys
import os
import gc
from time import time, mktime, timezone
import scandir
from multiprocessing import Pool, cpu_count
import redis
from msgpack import packb, unpackb
import datetime
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__),
                                             os.path.pardir)))
import settings

conn = redis.Redis(settings.REDIS_HOST, settings.REDIS_PORT,
                   settings.REDIS_DB)


def construct_ruby_object(loader, suffix, node):
    return loader.construct_yaml_map(node)


def construct_ruby_sym(loader, node):
    return loader.construct_yaml_str(node)

yaml.add_multi_constructor(u"!ruby/object:", construct_ruby_object)
yaml.add_constructor(u"!ruby/sym", construct_ruby_sym)


def _encode_datetime(obj):
    if isinstance(obj, datetime.datetime):
        return {'__datetime__': True,
                'as_str': obj.strftime("%Y%m%dT%H:%M:%S.%f")}
    return obj


def _send_to_redis(name, report):
    cur_key = "%s:%s" % (settings.CUR_PREFIX, name)
    if report:
        hist_key = "%s:%s" % (settings.HIST_PREFIX, name)
        packed = packb(report, default=_encode_datetime)
        rtime = mktime(report['time'].timetuple())
        value = {'report': packed, 'time': rtime}
        old_value = conn.lindex(hist_key, 0)
        if old_value:
            old_value = eval(old_value)
        if not old_value or old_value['time'] != report['time']:
            conn.lpush(hist_key, value)
            conn.ltrim(hist_key, 0, (settings.HIST_REPORTS - 1))
    else:
        report = packb({'status': 'report load error'})
        t = time() + timezone
        value = {'report': report, 'time': t}
    conn.hmset(cur_key, value)


def _read_report(host):
    rep_name = "%s:%s" % (settings.CUR_PREFIX, host['host'])
    t = time() + timezone
    or_time = conn.hget(rep_name, 'time')
    if not or_time or t - float(or_time) > settings.INTERVAL:
        latest_report = ""
        r_time = 0
        for report in scandir.scandir(host['report_dir']):
            if not report.name.endswith(".yaml"):
                continue
            if report.stat().st_mtime > r_time:
                r_time = report.stat().st_mtime
                latest_report = report.path
        if not latest_report:
            _send_to_redis(host['host'], {})
        else:
            try:
                with open(latest_report) as f_in:
                    _send_to_redis(host['host'], yaml.load(f_in))
            except Exception, e:
                _send_to_redis(host['host'], e)


def load_hosts():
    old_hosts = conn.hgetall('hosts')
    t = time() + timezone
    if not old_hosts or t - float(old_hosts['time']) > settings.INTERVAL:
        ROOT = settings.REPORT_DIR
        hosts = [{'host': path.name, 'report_dir': path.path} for path in
                 scandir.scandir(ROOT) if path.is_dir()]
        packed = packb(hosts)
        value = {'time': t, 'hosts': packed}
        conn.hmset('hosts', value)
    else:
        gc.disable()
        hosts = unpackb(old_hosts['hosts'])
        gc.enable()


def get_reports():
    hosts = conn.hgetall('hosts')
    gc.disable()
    hosts = unpackb(hosts['hosts'])
    gc.enable()
    procs = Pool(int(cpu_count() / 2))
    procs.map(_read_report, hosts)

# Do an initial load...
load_hosts()
get_reports()
