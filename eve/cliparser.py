#!/usr/bin/python
# vim: set expandtab:

class CliParser:
    class Command:
        def __init__(self, func, tokens, default_args, desc):
            self.tokens = tokens
            self.func = func
            self.dargs = default_args
            self.desc = desc

    def __init__(self):
        self.commands = []

    def add_command(self, func, tokens, default_args={}, description="", ):
        self.commands.append(CliParser.Command(func, tokens, default_args, description))
        return True
    
    def add_command_class(self, inst, func, tokens, default_args={}, description=""):
        default_args['self'] = inst
        return self.add_command(func, tokens, default_args, description)
    
    def dump(self):
        print("loaded commands: ")
        for cmd in self.commands:
            print(f'tokens: {cmd.tokens}, dargs: {cmd.dargs}, func: {cmd.func}, desc: {cmd.desc}')
        print("end of commands")

    def __test_cmd(self, cmd, tokens):
        args = cmd.dargs
        for i in range(len(tokens)):
            if cmd.tokens[i].startswith('['):
                key = cmd.tokens[i][1:-1]
                args[key] = tokens[i]
            elif tokens[i] != cmd.tokens[i]:
                return None
        return args

    def call(self, tokens):
        for cmd in self.commands:
            if len(tokens) == len(cmd.tokens):
                r = self.__test_cmd(cmd, tokens)
                if r is not None:
                    cmd.func(**r)
                    return
        print('No command matched')


"""
main feature:

* define command with (tokens, func, desc)

details:
* special format in tokens, which support the following behaviors
    1. pass token (string) as args with some name
        * e.g.
            ["set", "feature", "@enable"], handle_set_feature(enable)
            > set feature true
            pass string "true" as argument "enable" in handle_set_feature
    2. allow single token that accept dynamic number of args in command
        * e.g.
            ["show", "slot", "@idlist..."], handle_show_slot(idlist)
            > show slot 1 2 3
            pass list of string ["1", "2", "3"] as argument "idlist" in handle_show_slot
    3. type check/convert for arguments
        * e.g.
            ["show", "slot", "@idlist(int)..."], handle_show_slot(idlist)
            > show slot 1 2 3
            pass list of int [1, 2, 3] as argument "idlist" in handle_show_slot
    4. match prefix, match abbreviation
        * e.g.
            ["set", "fs|filesystem", "@fstype"], handle_set_filesystem(fstype)
            all the following commands matchs, if no other possible token start with files*
            > set fs ext4
            > set files ext4

* show helpful messages when command line matchs no rules
* show candidates of commands when passing special token (e.g. ? like cisco console)
* interactive console for all function above
    * provide shell-like experience
        1. arrows (up/down/left/right)
        2. ^C to clean current command, type exit to leave

"""