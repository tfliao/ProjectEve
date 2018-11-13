#!/usr/bin/python
# vim: ts=4:sw=4:expandtab
import argparse
import subprocess
import datetime
import time

from cmdbase import CmdBase

class Wait(CmdBase):

    version = '1.0.0'
    desc = "Wait until process with given pid ends"

    def __init__(self, prog = None, prefix = None, loggername = None):
        CmdBase.__init__(self, prog, self.version, self.desc, prefix=prefix, loggername=loggername)

    def __check_pid(self, pid):
        cmd = ['ps', 'ao', 'pid,command']
        lines = []
        try:
            self.logdebug("run cmd: " + str(cmd))
            lines = subprocess.check_output(cmd).decode().split('\n')
        except subprocess.CalledProcessError:
            return 1
        for line in lines:
            if len(line) == 0:
                continue
            p = line[0:5]
            c = line[6:]
            if p != '  PID' and int(p) == pid:
                return (int(p), c)

        return None

    def _run(self):
        args = self._args
        pid = args.pid
        timeout = args.timeout if args.timeout != 0 else 86400
        delay = args.delay

        r = self.__check_pid(pid)
        if r is None:
            self.logerror('process with pid={} not exists or stop already'.format(pid))
            return (0 if args.nofail else 1)
        self.loginfo('start waiting process, pid={}, cmd=[{}]'.format(pid, r[1]))
        cmd = r[1]

        start = datetime.datetime.now()
        last_check = start
        while True:
            now = datetime.datetime.now()
            delta = now - start
            if delta.seconds >= timeout:
                self.loginfo('maximum wait exceed, exit now')
                return (0 if args.nofail else 1)

            delta = now - last_check
            if delta.seconds >= delay:
                r = self.__check_pid(pid)
                last_check = now
                self.logdebug('Check process again now')
                if r is None:
                    self.loginfo('process complete'.format(pid))
                    break
                c = r[1]
                if c != cmd:
                    self.loginfo('another process started with identical pid={}'.format(pid))
                    break
            time.sleep(1)

        return 0

    def _prepare_parser(self, parser):
        # eve wait <pid>
        parser.add_argument('pid', type=int, help='specify pid to wait')
        parser.add_argument('--nofail', action='store_true', default=False,
                            help='no fail if process not exists in the beginning')
        parser.add_argument('--delay', '-d', default=10, type=int,
                            help='delay between checks')
        parser.add_argument('--timeout', '-t', default=0, type=int,
                            help='maximum wait time (default: 0)')

if __name__ == '__main__':
    Comic('Comic').run()

