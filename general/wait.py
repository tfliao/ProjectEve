#!/usr/bin/python
# vim: ts=4:sw=4:expandtab
import argparse
import subprocess
import datetime
import time
import os

from cmdbase import CmdBase

class Wait(CmdBase):

    version = '1.0.0'
    desc = "Wait until process with given pid ends"

    def __init__(self, prog = None, prefix = None, loggername = None):
        CmdBase.__init__(self, prog, self.version, self.desc, prefix=prefix, loggername=loggername)
        self._add_required('ps')

    def __run_ps(self):
        cmd = ['ps', 'ao', 'pid,command']
        lines = []
        try:
            self.logdebug("run cmd: " + str(cmd))
            lines = subprocess.check_output(cmd).decode().split('\n')
        except subprocess.CalledProcessError:
            return []
        return lines


    def __check_pid(self, pid):
        for line in self.__run_ps():
            if len(line) == 0:
                continue
            p = line[0:5]
            c = line[6:]
            if p != '  PID' and int(p) == pid:
                return (int(p), c)

        return None

    def __target_to_pid(self):
        args = self._args
        target = args.target
        if not args.command:
            return int(target)
        else:
            mypid = os.getpid();
            cands = []
            for line in self.__run_ps():
                if len(line) == 0:
                    continue
                p = line[0:5]
                c = line[6:]
                if p != '  PID' and int(p) != mypid and c.find(target) != -1:
                    cands.append(line)

            if len(cands) == 0:
                return -1
            if len(cands) == 1:
                return int(cands[0][0:5])
            else:
                for cand in cands:
                    print(cand)
                r = self.prompt('More than one process match, please specify one')
                return int(r)

    def _run(self):
        args = self._args
        pid = self.__target_to_pid()
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
        # eve wait <target>
        #   target: pid
        #           cmd if -c given
        parser.add_argument('target', help='specify target (pid or cmd) to wait')
        parser.add_argument('--command', '-c', action='store_true', default=False,
                            help='wait process match cmd')
        parser.add_argument('--nofail', action='store_true', default=False,
                            help='no fail if process not exists in the beginning')
        parser.add_argument('--delay', '-d', default=10, type=int,
                            help='delay between checks')
        parser.add_argument('--timeout', '-t', default=0, type=int,
                            help='maximum wait time (default: 0)')

if __name__ == '__main__':
    Comic('Comic').run()

