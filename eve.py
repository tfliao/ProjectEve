#!/usr/bin/python
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

    def __init__(self):
        self._script = os.path.basename(__file__)
        self.__load_config()
        self.__load_classes()
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

        cfpr = configparser.ConfigParser()
        cfpr.read('eve.conf')
        if 'modules' in cfpr:
            for m in cfpr['modules']:
                if cfpr['modules'][m]:
                    self._config['modules'].append(m)
        pass


    def __load_classes(self):
        modules = map(__import__, self._config['modules'])
        for m in modules:
            mod = {'name': m.__name__,
                   'desc': m.__desc__,
                   'classes': [] }
            self._modules[m.__name__] = mod
            for k, v in m.__classmap__.items():
                self._modules[m.__name__]['classes'].append(k)
                if k not in self._classes:
                    cls = { 'name': k,
                            'classname': v,
                            'modules': [] }
                    self._classes[k] = cls
                self._classes[k]['modules'].append(m.__name__)

    def __parse(self):
        args = sys.argv
        if len(args) == 1 or self.is_help(args[1]):
            self.__help()
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
    Eve()

