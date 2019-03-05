#!/usr/bin/python
# vim: ts=4:sw=4:expandtab
import argparse
import subprocess
import os

from cmdbase import CmdBase

class Connect(CmdBase):

    version = '1.0.0'
    desc = "Connect to another server via ssh"

    __table = 'server'
    __table_version = 1
    __table_schema = [
                {
                    'name': 'mach',
                    'type': 'text',
                    'primary': True
                }, {
                    'name': 'addr',
                    'type': 'text'
                }, {
                    'name': 'user',
                    'type': 'text'
                }, {
                    'name': 'port',
                    'type': 'integer'
                }
            ]


    def __init__(self, prog = None, prefix = None, loggername = None):
        CmdBase.__init__(self, prog, self.version, self.desc, prefix=prefix, loggername=loggername)
        self._add_required('ssh-copy-id')
        self._add_required('scp')
        self._add_required('ssh')

    def __setup_database(self):
        db = self._db()
        if db.table_version(self.__table) != str(self.__table_version):
            db.table_create(self.__table, self.__table_schema, self.__table_version)
        pass

    def __run_list(self):
        db = self._db()
        res = db.table_select(self.__table)
        print('{:12} {}'.format('machine', 'target'))
        print('------------ ------------')
        for r in res:
            target = self.__build_target_str(r['user'], r['addr'], r['port'])
            print('{:12} {}'.format(r['mach'], target))
        self.loginfo('Total {} alias(es) in db'.format(len(res)))
        return 0

    def __run_alias(self):
        args = self._args
        db = self._db()

        addr = args.alias
        user = args.user if args.user is not None else '-'
        port = args.port if args.port is not None else 22
        target = self.__build_target_str(user, addr, port)

        if '@' in addr:
            user, addr = addr.split('@')

        db.table_update(self.__table, {'mach': args.machine, 'user': user, 'addr': addr, 'port': port})
        self.loginfo('Alias [{}] = [{}]'.format(args.machine, target))

        if args.copykey:
            self.__copy_key(user, addr, port)
        return 0

    def __run_refresh(self):
        args = self._args
        db = self._db()

        res = db.table_select(self.__table, {'mach': args.machine})
        if len(res) == 0:
            self.logerror('No record with mach=[{}] found in db'.format(args.machine))
            return 1

        r = res[0]
        addr = r['addr']
        user = r['user']
        port = r['port']

        self.__copy_key(user, addr, port)

        return 0

    def __run_connect(self):
        args = self._args
        db = self._db()

        res = db.table_select(self.__table, {'mach': args.machine})
        if len(res) == 0:
            self.logerror('No record with mach=[{}] found in db'.format(args.machine))
            return 1

        r = res[0]
        addr = r['addr']
        user = r['user']
        port = r['port']

        if args.copykey:
            self.__copy_key(user, addr, port)

        target = self.__build_target_str(user, addr, port)
        self.loginfo('Connect to {}'.format(target))

        server = '{}@{}'.format(user, addr) if user != '-' else addr
        cmdline = ['ssh', '-p', str(port), server]

        self.logdebug('Run command: {}'.format(cmdline))
        try:
            subprocess.run(cmdline)
        except subprocess.CalledProcessError as e:
            self.logerror('Failed to connect to {}, error: {}'.format(target, str(e)))
            return 1

        return 0


    def __build_target_str(self, user, addr, port):
        target = '{}:{}'.format(addr, port)
        if user != '-':
            target = '{}@{}'.format(user, target)
        return target

    def __copy_key(self, user, addr, port):
        # ssh-copy-id -i ~/.ssh/id_rsa.pub root@{target}
        keyfile = os.path.expanduser('~/.ssh/id_rsa.pub')
        target = '{}@{}'.format(user, addr) if user != '-' else addr
        cmdline = ['ssh-copy-id', '-i', keyfile, '-p', str(port), target]
        self.loginfo('Copying ~/.ssh/id_rsa.pub to server')
        self.logdebug('Run command: {}'.format(cmdline))
        r = subprocess.call(cmdline)
        if r != 0:
            hostfile = os.path.expanduser('~/.ssh/known_hosts')
            cmdline = ["ssh-keygen", "-f", hostfile, "-R", addr]
            self.loginfo('Removing mismatch key in ~/.ssh/known_hosts')
            self.logdebug('Run command: {}'.format(cmdline))
            out = subprocess.check_output(cmdline)
            if 'not found in' not in out.decode('utf-8'):
                self.loginfo('Remove key successful, copy it again')
                self.__copy_key(user, addr, port)
        pass

    def _run(self):
        args = self._args


        self.__setup_database()
        if args.list or args.machine == 'list':
            return self.__run_list()
        elif args.alias is not None:
            return self.__run_alias()
        elif args.refresh:
            return self.__run_refresh()
        else:
            return self.__run_connect()

    def _prepare_parser(self, parser):
        # eve connect <machine> # connect to server
        #                      --alias ip --port port --user user # setup alias
        #                           --copykey # copy key before connect or after alias
        #                      --list # list servers

        parser.add_argument('machine', help='specify machine to connect, given "list" will list all alias in db')
        parser.add_argument('--alias', '-a', metavar='addr', help='make an alias of machine')
        parser.add_argument('--list', '-l', default=False, action='store_true', help='list exists aliases')
        parser.add_argument('--refresh', '-r', default=False, action='store_true', help='refresh ssh key')
        parser.add_argument('--port', '-p', type=int, help='specify port, store with alias, or overwrite when connect')
        parser.add_argument('--user', '-u', help='specify user in remote server')
        parser.add_argument('--copykey', default=False, action='store_true', help='copy ssh key to remote server')

if __name__ == '__main__':
    Connect('Connect').run()

