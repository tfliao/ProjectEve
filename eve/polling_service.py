#!/usr/bin/python
# vim: set expandtab:

import os, psutil
import importlib
import time

import eve.common
from cmdbase import CmdBase
from eve.database import EveDB
from eve.cliparser import CliParser

class PollingJob:
    def __init__(self, progname):
        self._dbfile = None
        self._dbconn = None
        self._prog = progname
        pass

    def process_one(self):
        raise "No implement in base class"

    ### start of db facilities ##
    def set_dbfile(self, dbfile):
        self._dbfile = dbfile
    
    def _db(self):
        if self._dbconn is None:
            if self._dbfile is None:
                raise
            self._dbconn = EveDB(self._dbfile)
            self._dbconn.set_namespace(self._prog)
        return self._dbconn
    ### end of db facilities ##

PROGNAME='pollingservice'

class PollingServiceDBHelper:
    __table = 'jobs'
    __table_version = '1'
    __schema = [
        {
            'name': 'jobname',
            'type': 'text',
            'primary': True
        }, {
            'name': 'enable',
            'type': 'integer'
        }, {
            'name': 'new_enable',
            'type': 'integer'
        }, {
            'name': 'interval',
            'type': 'integer'
        }, {
            'name': 'new_interval',
            'type': 'integer'
        }, {
            'name': 'status',
            'type': 'text' # (good|err),<note>
        }
    ]

    __dbconn = None

    @classmethod
    def __getdbconn(cls):
        if cls.__dbconn is None:
            dbfile = eve.common.db_filepath()
            cls.__dbconn = EveDB(dbfile)
            cls.__dbconn.set_namespace(PROGNAME)
        return cls.__dbconn

    @classmethod
    def setupdb(cls, db = None):
        if cls.__dbconn is not None:
            return
        if db is not None:
            cls.__dbconn = db
        db = cls.__getdbconn()
        if db.table_version(cls.__table) != cls.__table_version:
            db.table_create(cls.__table, cls.__schema, cls.__table_version)

    @classmethod
    def update_job(cls, jobname, enable = None, interval = None):
        cls.setupdb()
        db = cls.__getdbconn()
        rows = db.table_select(cls.__table, {'jobname': jobname})
        if len(rows) == 0:
            # new job
            if enable is None or interval is None:
                return False
            record = {'jobname': jobname,
                       'enable': None, 'new_enable': int(enable),
                       'interval': None, 'new_interval': interval,
                       'status': 'good,new'}
        else:
            record = rows[0]
            if enable is not None:
                record['new_enable'] = int(enable)
            if interval is not None:
                record['new_interval'] = interval
        db.table_update(cls.__table, record)
        return True

    @classmethod
    def update_jobstatus(cls, jobname, status):
        cls.setupdb()
        db = cls.__getdbconn()
        rows = db.table_select(cls.__table, {'jobname': jobname})
        if len(rows) == 0:
            return False
        else:
            record = rows[0]
            record['status'] = status
        db.table_update(cls.__table, record)
        return True
    
    @classmethod
    def get_jobstatus(cls):
        cls.setupdb()
        db = cls.__getdbconn()
        rows = db.table_select(cls.__table)
        return rows

class PollingServiceJob(PollingJob):
    def __init__(self):
        PollingJob.__init__(self, PROGNAME)
        self.daemon = None
        pass

    def set_daemon(self, daemon):
        self.daemon = daemon

    def process_one(self):
        print('TODO: check database for any updates')
        pass

class PollingDaemon:
    SERVICE_JOB_NAME = 'eve.polling_service#PollingServiceJob'
    SERVICE_JOB_INTERVAL = 30

    def __init__(self):
        self.jobs = {} # jobname => obj
        service_job = self.__create_job(__class__.SERVICE_JOB_NAME)
        if service_job is None:
            raise Exception()
        service_job.set_daemon(self)
        self.__save_job(__class__.SERVICE_JOB_NAME, service_job, __class__.SERVICE_JOB_INTERVAL)

    def __create_job(self, jobname):
        if jobname in self.jobs:
            return None
        try:
            mod, cls = jobname.split('#')
            module = importlib.import_module(mod)
            inst = getattr(module, cls)()
            return inst
        except:
            return None

    def __save_job(self, jobname, cls, interval):
        self.jobs[jobname] = {
            'inst': cls,
            'interval': interval,
            'next_ts': time.monotonic()
        }
        return True

    def new_job(self, jobname, interval):
        inst = self.__create_job(jobname)
        if inst is None:
            return False
        return self.__save_job(jobname, inst, interval)

    def run(self):
        while True:
            for job in self.jobs.values():
                if time.monotonic() > job['next_ts']:
                    job['inst'].process_one()
                    job['next_ts'] = time.monotonic() + job['interval']
            time.sleep(1)

class PollingServiceCLI(CmdBase):
    version = '1.0.0'
    desc = 'Shared polling service for project eve'
    
    def __init__(self, prog = None, prefix = None, loggername = None):
        CmdBase.__init__(self, prog, self.version, self.desc, prefix=prefix, loggername=loggername)

    def _prepare_parser(self, parser):
        parser.add_argument('params', nargs='*', default=[])

    def _run(self):
        PollingServiceDBHelper.setupdb(self._db())
        cp = CliParser()

        cp.add_command(['start'],   inst=self, func=PollingServiceCLI.start,   help="start polling service")
        cp.add_command(['stop'],    inst=self, func=PollingServiceCLI.stop,    help="stop polling service")
        cp.add_command(['restart'], inst=self, func=PollingServiceCLI.restart, help="restart polling service")
        cp.add_command(['status'],  inst=self, func=PollingServiceCLI.status,  help="show status of polling service")
        cp.add_command(['jobstatus'],  inst=self, func=PollingServiceCLI.jobstatus,  help="show status of polling jobs")

        cp.invoke(self._args.params)

    def __is_running(self):
        db = self._db()
        pid = db.evedb_get('{}.pid'.format(PROGNAME))
        cmdline = db.evedb_get('{}.cmdline'.format(PROGNAME))
        if pid is None or len(pid) == 0:
            return False

        try:
            process = psutil.Process(int(pid))
        except:
            return False

        proc_cmdline = ' '.join(process.cmdline())
        return proc_cmdline == cmdline

    def start(self):
        if self.__is_running():
            return True
        PollingDaemon().run()
        return False

    def stop(self):
        if not self.__is_running():
            return True
        raise "Not yet implemented"
        return True

    def restart(self):
        self.stop()
        self.start()

    def status(self):
        if self.__is_running():
            print("Polling Service is running")
            return True

        db = self._db()
        err = db.__evedb_get('{}.error'.format(PROGNAME))
        if len(err) != 0:
            print("Polling Service stopped on error {}".format(err))
        else:
            print("Polling Service is not running")
        return True

    def jobstatus(self):
        PollingServiceDBHelper.setupdb(self._db())
        rows = PollingServiceDBHelper.get_jobstatus()
        print('Total {} jobs'.format(len(rows)))
        for row in rows:
            print('{} ... {}'.format(row['jobname'], row['status']))

class PollingServiceAPI:
    @staticmethod
    def __to_jobname(polling_job):
        cls = type(polling_job)
        return '#'.join([cls.__module__, cls.__name__])

    @staticmethod
    def add_job(polling_job, interval, enable = True):
        jobname = PollingServiceAPI.__to_jobname(polling_job)
        return PollingServiceDBHelper.update_job(jobname, interval = interval, enable = enable)

    @staticmethod
    def enable_job(cls, polling_job, enable=True):
        jobname = PollingServiceAPI.__to_jobname(polling_job)
        return PollingServiceDBHelper.update_job(jobname, enable = enable)
    
    @staticmethod
    def set_job_interval(cls, polling_job, interval):
        jobname = PollingServiceAPI.__to_jobname(polling_job)
        return PollingServiceDBHelper.update_job(jobname, interval = interval)
