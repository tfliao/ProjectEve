#!/usr/bin/python
# vim: set expandtab:

import re

class CliParser:
    class BadTokenFormatException(Exception):
        def __init__(self, message):
            super(message)

    class CmdToken:
        CONST_TOKEN = 'const'
        VAR_TOKEN = 'var' # target, type, ... properties will be set
        RE_VAR_PATTERN = r'@(\w+)(\(\w+\))?(...)?'

        KEY_TARGET = 'target'
        KEY_TYPE = 'type'
        KEY_DYNAMIC_LENGTH = 'dleng'

        def __init__(self, token, desc = "", args = {}, hidden = True, func = None):
            self.token = token
            self.desc = desc
            self.func = func
            self.args = args
            self.hidden = hidden

            self.children = {}

            self.type = CliParser.CmdToken.CONST_TOKEN
            self.props = None
            self.__parse_token_type(token)

        def __parse_token_type(self, token):
            if not token.startswith('@'):
                return
            self.type = CliParser.CmdToken.VAR_TOKEN
            m = re.match(__class__.RE_VAR_PATTERN, token)
            if m is None:
                raise CliParser.BadTokenFormatException(f'token {token} is illegal')
            self.props = {
                __class__.KEY_TARGET: m.group(1),
                __class__.KEY_TYPE: 'str' if m.group(2) is None else m.group(2),
                __class__.KEY_DYNAMIC_LENGTH: m.group(3) is not None
            }

    """
    A Cmd Tree that help to walk through cmd line
    """


    def __default_helper_func(self, cmdline_matched, cmdtoekn, cmdline):
        """
        when cmdline matchs no rules, this function will be called
        `cmdline_matched`: prefix of cmdline that match with some rules
        `cmdtoken`: the last token for cmdline matched
        `cmdline`: the full cmdline that passed
        """

        # format:
        """
            cmdline_matched
            possible candidates:
                cmdtoken.child[].token  cmdtoken.child[].desc
                ...
        """
        pass


    def __init__(self):
        self.root = CliParser.CmdToken("(root)")
        self.cmdline_matched = []
        self.cmdline = []
    

    def validate_command(self, tokens):
        # TODO: add some checks for tokens, raise when failure
        pass


    def add_command(self, inst, func, tokens, default_args = {}, description="", hidden=False):
        self.validate_command(tokens)

        node = self.root
        for token in tokens:
            if token not in node.children:
                node.children[token] = CliParser.CmdToken(token)
            node = node.children[token]
            node.hidden &= hidden

        if inst is not None:
            default_args['self'] = inst
        node.desc = description
        node.args = default_args
        node.func = func
        node.hidden = hidden
    
    def dump_r(self, node, lv = 0):
        print(f"{'  '*lv}{node.token} | func: {node.func}, args: {node.args}, desc: {node.desc}, hidden: {node.hidden}, type: {node.type}({node.props})")
        for child in node.children.values():
            self.dump_r(child, lv+1)

    def dump(self):
        print("loaded commands: ")
        self.dump_r(self.root)
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
    5. allow some commands to be hidden, which won't be shown in help

* show helpful messages when command line matchs no rules
* show candidates of commands when passing special token (e.g. ? like cisco console)
* interactive console for all function above
    * provide shell-like experience
        1. arrows (up/down/left/right)
        2. ^C to clean current command, type exit to leave

"""