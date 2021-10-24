#!/usr/bin/python
# vim: set expandtab:

import os, sys
import psutil
import importlib
import time
import logging
import signal

import eve.common
from cmdbase import CmdBase
from eve.database import EveDB
from eve.cliparser import CliParser

class PollingJob:
    def __init__(self, progname):
        self._dbfile = None
        self._dbconn = None
        self.logger = None
        self._prog = progname
        pass

    def set_logger(self, logger):
        self.logger = logger

    def process_one(self):
        raise "No implement in base class"

    ### start of db facilities ##
    def set_dbfile(self, dbfile):
        self._dbfile = dbfile
    
    def _db(self):
        if self._dbconn is None:
            if self._dbfile is None:
                self._dbfile = eve.common.db_filepath()
            self._dbconn = EveDB(self._dbfile)
            self._dbconn.set_namespace(self._prog)
        return self._dbconn
    ### end of db facilities ##

PROGNAME='polling_service'

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
    def setdaemoninfo(cls, pid, cmdline):
        db = cls.__getdbconn()
        db.evedb_set('{}.pid'.format(PROGNAME), pid)
        db.evedb_set('{}.cmdline'.format(PROGNAME), cmdline)

    @classmethod
    def getdaemoninfo(cls):
        db = cls.__getdbconn()
        pid = db.evedb_get('{}.pid'.format(PROGNAME))
        cmdline = db.evedb_get('{}.cmdline'.format(PROGNAME))
        return (pid, cmdline)

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

    @classmethod
    def consume_job_change(cls, jobname):
        cls.setupdb()
        db = cls.__getdbconn()
        rows = db.table_select(cls.__table, {'jobname': jobname})
        if len(rows) == 0:
            return False
        else:
            record = rows[0]
            record['interval'] = record['new_interval']
            record['enable'] = record['new_enable']
        db.table_update(cls.__table, record)
        return True


class PollingServiceJob(PollingJob):
    def __init__(self):
        PollingJob.__init__(self, PROGNAME)
        self.daemon = None
        pass

    def set_daemon(self, daemon):
        self.daemon = daemon

    def process_one(self):
        self.logger.debug('TODO: check database for any updates')
        pass

class PollingDaemon:
    SERVICE_JOB_NAME = 'eve.polling_service#PollingServiceJob'
    SERVICE_JOB_INTERVAL = 30

    def __init__(self, loglevel = 'DEBUG'):
        self.logger = None
        self.jobs = {} # jobname => obj

        self.__init_logger(loglevel)
        service_job = self.__create_job(__class__.SERVICE_JOB_NAME)
        if service_job is None:
            raise Exception()
        service_job.set_daemon(self)
        self.__save_job(__class__.SERVICE_JOB_NAME, service_job, __class__.SERVICE_JOB_INTERVAL)
        self.__load_jobs()

    def __init_logger(self, level):
        logger = logging.getLogger('PollingDaemon')
        try:
            logger.setLevel(level)
        except ValueError as e:
            sys.stderr.write(str(e) + ', fallback to INFO\n')
            logger.setLevel(logging.INFO)

        handler = logging.StreamHandler(sys.stdout)
        logformat = '[%(name)s][%(asctime)s][%(levelname)s] %(message)s'
        formatter = logging.Formatter(logformat)
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        self.logger = logger

    def logger(self):
        return self.logger

    def __load_jobs(self):
        for job in PollingServiceDBHelper.get_jobstatus():
            if job['status'].startswith('err'):
                self.logger.debug('skip creating err jobs')
                continue
            r = self.new_job(job['jobname'], job['new_interval'])

            if not r:
                PollingServiceDBHelper.update_jobstatus(job['jobname'], 'err,create')
            else:
                PollingServiceDBHelper.update_jobstatus(job['jobname'], 'good,loaded')
                PollingServiceDBHelper.consume_job_change(job['jobname'])

    def __create_job(self, jobname):
        if jobname in self.jobs:
            self.logger.debug('job[{}] already exists in joblist'.format(jobname))
            return None
        try:
            mod, cls = jobname.split('#')
            module = importlib.import_module(mod)
            inst = getattr(module, cls)()
            inst.set_logger(self.logger)
            self.logger.info('job[{}] created'.format(jobname))
            return inst
        except Exception as e:
            self.logger.error('job[{}] creation failed, ex: {}'.format(jobname, e))
            return None

    def __save_job(self, jobname, cls, interval):
        self.jobs[jobname] = {
            'name': jobname,
            'inst': cls,
            'interval': interval,
            'next_ts': time.monotonic(),
            'healthy': True
        }
        self.logger.info('job[{}] saved in joblist'.format(jobname))
        return True

    def new_job(self, jobname, interval):
        if not isinstance(interval, int):
            self.looger.error('polling interval should be integer')
            return False
        inst = self.__create_job(jobname)
        if inst is None:
            return False
        return self.__save_job(jobname, inst, interval)

    def run(self):
        while True:
            for job in self.jobs.values():
                if not job['healthy']:
                    continue
                if time.monotonic() > job['next_ts']:
                    self.logger.debug('>> job[{}]'.format(job['name']))
                    succ = True
                    try:
                        job['inst'].process_one()
                    except:
                        succ = False
                        pass
                    if succ:
                        job['next_ts'] = time.monotonic() + job['interval']
                        self.logger.debug('<< job[{}]'.format(job['name']))
                    else:
                        job['healthy'] = False
                        self.logger.error('<< job[{}] finished with exception, mark as error'.format(job['name']))
                        PollingServiceDBHelper.update_jobstatus(job['name', 'err,exception'])
            self.jobs = {k: v for k, v in self.jobs.items() if v['healthy']}
            time.sleep(1)

    @staticmethod
    def sighdr(sig, frame):
        print('Receive signal, stop now')
        PollingServiceDBHelper.setdaemoninfo("", "")
        os._exit(0)

    def run_daemon(self):
        r = os.fork()
        if r < 0:
            return False
        if r > 0:
            print('daemon start running in pid[{}]'.format(r))
            return True

        # child process here
        pid = os.getpid()
        signal.signal(signal.SIGUSR1, PollingDaemon.sighdr)
        cmdline = ' '.join(psutil.Process(pid).cmdline())
        PollingServiceDBHelper.setdaemoninfo(pid, cmdline)
        self.run()

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

        cp.add_command(['start'],            inst=self, func=PollingServiceCLI.start,     help="start polling service")
        cp.add_command(['start', 'debug'],   inst=self, func=PollingServiceCLI.start,     help="start polling service in foreground mode", default_args={'debug': True})
        cp.add_command(['stop'],             inst=self, func=PollingServiceCLI.stop,      help="stop polling service")
        cp.add_command(['restart'],          inst=self, func=PollingServiceCLI.restart,   help="restart polling service")
        cp.add_command(['status'],           inst=self, func=PollingServiceCLI.status,    help="show status of polling service")
        cp.add_command(['jobstatus'],        inst=self, func=PollingServiceCLI.jobstatus, help="show status of polling jobs")

        cp.add_command(['dummyjob'],         inst=self, func=PollingServiceCLI.dummyjob,  help='insert dummy job')

        cp.invoke(self._args.params)

    def dummyjob(self):
        PollingServiceAPI.add_job(TestJob, 5)

    def __is_running(self):
        pid, cmdline = PollingServiceDBHelper.getdaemoninfo()
        if pid is None or len(pid) == 0:
            return False

        try:
            process = psutil.Process(int(pid))
        except:
            return False

        proc_cmdline = ' '.join(process.cmdline())
        return proc_cmdline == cmdline

    def start(self, debug = False):
        if self.__is_running():
            self.loginfo('polling service already started')
            return True
        if not debug:
            return PollingDaemon('INFO').run_daemon()
        else:
            return PollingDaemon('DEBUG').run()

    def stop(self):
        if not self.__is_running():
            return True
        db = self._db()
        pid, _ = PollingServiceDBHelper.getdaemoninfo()
        os.kill(int(pid), signal.SIGUSR1)
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
        if not isinstance(polling_job, type):
            polling_job = type(polling_job)
        return '#'.join([polling_job.__module__, polling_job.__name__])

    @staticmethod
    def add_job(polling_job, interval, enable = True):
        jobname = PollingServiceAPI.__to_jobname(polling_job)
        return PollingServiceDBHelper.update_job(jobname, interval = interval, enable = enable)

    @staticmethod
    def enable_job(polling_job, enable=True):
        jobname = PollingServiceAPI.__to_jobname(polling_job)
        return PollingServiceDBHelper.update_job(jobname, enable = enable)
    
    @staticmethod
    def set_job_interval(polling_job, interval):
        jobname = PollingServiceAPI.__to_jobname(polling_job)
        return PollingServiceDBHelper.update_job(jobname, interval = interval)

class TestJob(PollingJob):
    def __init__(self):
        PollingJob.__init__(self, PROGNAME)
        pass

    def process_one(self):
        self.logger.debug('[pid{}] wakeup, ts: {}'.format(os.getpid(), time.monotonic()))
