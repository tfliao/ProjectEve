# ProjectEve

Project Eve an interface to write a command.

In eve system, all command inherit cmdbase, which provide basic feature for command line interface, a simple log system for easily writing logs, and a simple interface to manipulate local sqlite database.

## Requirement
1. python3

## setup
1. clone Project Eve `git clone https://github.com/tfliao/ProjectEve.git`
2. link eve.py to your bin path `ln -s /path/to/ProjectEve/eve.py /path/to/bin/path/eve`
3. if config file not exists, eve will generate on from template (eve.cfg.default)
    * in case new module/class added to eve syetem, your need to run this command to make eve be able to find them.

## Usage
`eve [module] (class) args ... `
* if no two modules have same class, module can be ignore

## Development

### Module structure
A module is a folder under ProjectEve (submodule in python). And some attributes must configurated in __init__.py to make eve understand the module.
```
__desc__ = "<description of this module>"
__all__ = ["filename", "of", "classes", "in", "module"]
__classmap__ = {
        'filename': 'ClassName',
        ...
    }
__alias__ = {
        'shortname': 'filename'
    }
```

### Writing a new command (class)
All command need to inherit CmdBase to get standard controll flow and shared utility functions. A classical command will look like:
```
#!/usr/bin/python3
from cmdbase import CmdBase
class Command(CmdBase):
    version = ''
    desc = ''
    def __init__(self, prog = None, prefix = None, loggername = None):
        CmdBase.__init__(self, prog, self.version, self.desc, prefix=prefix, loggername=loggername)
        self._add_required('external-program')

    def _prepare_parser(self, parser):
        # add new options for argparse

    def _run(self):
        args = self._args
        # main logic goes here
```
* `__init__`: constructor, pass through arguments to CmdBase
* `_add_required`: add external program dependency, eve will check before running into cmd logic
* `_prepare_parser`: add extra options for parse
* `_run`: if nothing wrong during parsing, this function will do the main logic according to option, return value will become exitcode
* `args = self._args`: in most case, you need only to access this member to get the parsed result for further operations

After this functions implemented, add this function to `__init__.py` and rescan, so that eve can know this class.
