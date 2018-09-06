#!/usr/bin/python3
# vim: set expandtab:

import os, sys
import importlib
import configparser

# eve [module] <feature> feature_args ...
class Eve:
    _script = None
    _modules = {}
    _classes = {}
    _config = {}

    _eve_cfg_def = '.eve.cfg'
    _eve_cfg_key = 'EVE_CFG'
    _eve_cfg = None

    _eve_system_str = 'system'
    _eve_system_desc = 'eve system operations'

    def __init__(self):
        script_dir=os.path.dirname(os.path.realpath(sys.argv[0]))
        sys.path.append(script_dir)

        self._eve_cfg = os.environ.get(self._eve_cfg_key, self._eve_cfg_def)
        if not self._eve_cfg.startswith('/'):
            self._eve_cfg = '{}/{}'.format(script_dir, self._eve_cfg)

        self._script = os.path.basename(__file__)
        self.__load_config()

    def run(self):
        cls = self.__parse()
        if cls is not None:
            self.__exec(cls)
        pass

    ### helper functions ###
    def is_help(self, arg):
        return arg in ['?', '-h', '--help']

    def is_module(self, arg):
        return arg in self._modules.keys()

    def is_class(self, arg, module = None):
        if arg not in self._classes.keys():
            return False
        cls = self._classes[arg]
        if module is not None:
            return module in cls['modules']
        return True
    ### end of helper functions ###

    def __load_config(self):
        self._config['modules'] = []

        parser = configparser.ConfigParser()
        parser.read(self._eve_cfg)
        if 'modules' in parser:
            for m in parser['modules']:
                if parser['modules'][m]:
                    self._config['modules'].append(m)
        for m in self._config['modules']:
            mod_class = m + '.classes'
            mod = {'name': m,
                   'desc': None,
                   'classes': [] }
            if m in parser:
                mod['desc'] = parser[m].get('desc', None)
            self._modules[m] = mod

            if mod_class in parser:
                for c in parser[mod_class]:
                    if c not in self._classes:
                        cls = { 'name': c,
                                'classname': parser[mod_class][c],
                                'modules': [] }
                        self._classes[c] = cls
                    self._classes[c]['modules'].append(m)
                    self._modules[m]['classes'].append(c)
        pass

    def __system(self):
        args = sys.argv
        if len(args) == 2 or self.is_help(args[2]):
            self.__help_system()
        elif args[2] == 'scan':
            self.__system_scan()
        else:
            self.__help_system()

    # eve system <cr> | ? | -h | --help | (unknown feature)
    def __help_system(self):
        features = ['scan']
        print('Usage: {} {} ({}) ' \
            .format(self._script, self._eve_system_str, '|'.join(features)))
        pass

    def __system_scan(self):
        writer = configparser.RawConfigParser()
        writer.add_section('modules')
        for m in self._config['modules']:
            writer.set('modules', m, 'True')

        modules = map(__import__, self._config['modules'])
        for m in modules:
            writer.add_section(m.__name__)
            writer.set(m.__name__, "desc", m.__desc__)

            mod_classes = m.__name__ + ".classes"
            writer.add_section(mod_classes)

            classes = m.__all__
            for k, v in m.__classmap__.items():
                if k in classes:
                    writer.set(mod_classes, k, v)
        with open(self._eve_cfg, "w") as configfile:
            writer.write(configfile)

    def __parse(self):
        args = sys.argv
        if len(args) == 1 or self.is_help(args[1]):
            self.__help()
            return None
        elif args[1] == self._eve_system_str:
            self.__system()
            return None
        elif self.is_module(args[1]):
            prefix = '{} {}'.format(args[0], args[1])
            if len(args) == 2 or self.is_help(args[2]):
                self.__help_module(args[1])
                return None
            elif self.is_class(args[2]):
                cls = self._classes[args[2]]
                cls['prefix'] = prefix
                cls['module'] = args[1]
                del cls['modules']
                sys.argv.pop(0)
                sys.argv.pop(0)
                return cls
            else:
                self.__help_module(args[1],
                        'Unknown class "{}" in module "{}"'
                        .format(args[2], args[1]))
                return None
        elif self.is_class(args[1]):
            cls = self._classes[args[1]]
            if len(cls['modules']) == 1:
                cls['prefix'] = args[0]
                cls['module'] = cls['modules'][0]
                del cls['modules']
                sys.argv.pop(0)
                return cls
            else:
                self.__help('class "{}" belong to multiple modules: {}'
                            .format(cls['name'], ', '.join(cls['modules'])))
                return None
        else:
            self.__help('Unknown module/class "{}"'.format(args[1]))
            return None

    def __exec(self, cls):
        m = importlib.import_module('{}.{}'.format(cls['module'], cls['name']))
        c = getattr(m, cls['classname'])(cls['name'], cls['prefix'], cls['classname'])
        c.run()

    # eve <cr> | ? | --help | -h | (unknown module)
    def __help(self, msg = None):
        if msg:
            print(msg)
        print('Usage: {} [module] feature args ... '.format(self._script))
        print
        print('Availiable modules:')
        print('{:>10} : {}'.format(self._eve_system_str, self._eve_system_desc))
        for m in self._modules.values():
            print('{:>10} : {}'.format(m['name'], m['desc']))
        pass

    # eve module <cr> | ? | -h | --help | (unknown feature)
    def __help_module(self, module, msg = None):
        if msg:
            print(msg)
        print('Usage: {} {} feature args ... '.format(self._script, module))
        print
        print('Availiable features in {}:'.format(module))
        for c in self._modules[module]['classes']:
            print('   {}'.format(c))
        pass

if __name__ == '__main__':
    Eve().run()

