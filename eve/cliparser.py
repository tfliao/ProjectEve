#!/usr/bin/python
# vim: set expandtab:

import re

TOKEN_TYPE_CONST = 'const'
TOKEN_TYPE_VAR = 'var' # target, type, ... properties will be set

KEY_TARGET = 'target'
KEY_TYPE = 'type'
KEY_LIST = 'list'

class CliParser:
    class BadTokenFormatException(Exception):
        def __init__(self, message):
            super(message)

    class CmdTreeException(Exception):
        def __init__(self, message):
            super(message)

    class CmdToken:
        RE_VAR_PATTERN = r'@\s*(\w+)\s*(\(\w+\))?\s*(...)?'

        def __init__(self, token, desc = "", args = {}, hidden = True, func = None):
            self.desc = desc
            self.func = func
            self.args = args
            self.hidden = hidden

            self.const_children = {}
            self.var_child = None

            self.token = token
            self.props = None
            self.type = self.__parse_token_type(token)

        def __parse_token_type(self, token):
            if not token.startswith('@'):
                return TOKEN_TYPE_CONST

            m = re.match(__class__.RE_VAR_PATTERN, token)
            if m is None:
                raise CliParser.BadTokenFormatException(f'token {token} is illegal')

            target = m.group(1)
            type = 'str' if m.group(2) is None else m.group(2)
            listable = m.group(3) is not None
            self.props = {
                KEY_TARGET: target,
                KEY_TYPE: type,
                KEY_LIST: listable
            }
            self.token = f'@{target}({type})' +  ('...' if listable else '')
            return TOKEN_TYPE_VAR

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
        print(f'Given cmdline: {cmdline}')
        print(f'Matched cmdline: {cmdline_matched}')
        print(f'possible candidates:')
        for ctoken, cnode in cmdtoekn.const_children.items():
            print(f'\t{cnode.token}\t{cnode.desc}')
        if cmdtoekn.var_child is not None:
            child = cmdtoekn.var_child
            print(f'\t{child.token}\t{child.desc}')
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

    def add_command(self, inst, func, tokens, default_args = {}, description="", hidden=False):
        node = self.root
        for token in tokens:
            cmd_token = CliParser.CmdToken(token)
            if cmd_token.type == TOKEN_TYPE_CONST:
                if cmd_token.token not in node.const_children:
                    node.const_children[cmd_token.token] = cmd_token
                node = node.const_children[cmd_token.token]
            else:
                if node.var_child is not None:
                    if node.var_child.token != cmd_token.token:
                        raise CliParser.CmdTreeException(f"Conflicted variable token given [{node.var_child.token}] vs [{cmd_token.token}]")
                    node = node.var_child
                else:
                    node.var_child = cmd_token
                    node = node.var_child
            node.hidden &= hidden

        if inst is not None:
            default_args['self'] = inst
        node.desc = description
        node.args = default_args
        node.func = func
        node.hidden = hidden

    def dump_r(self, node, lv = 0):
        print(f"{'  '*lv}{node.token} | func: {node.func}, args: {node.args}, desc: {node.desc}")
        for child in node.const_children.values():
            self.dump_r(child, lv+1)
        if node.var_child is not None:
            self.dump_r(node.var_child, lv+1)

    def dump(self):
        print("loaded commands: ")
        self.dump_r(self.root)
        print("end of commands")

    def __cast_arg(self, token, type):
        if type == 'str':
            return token
        if type == 'int':
            base = 16 if token.startswith('0x') else 10
            return int(token, base)
        raise Exception("Unknown type")

    def __find_child(self, node, token, args):
        prefix_children = []
        for ctoken, cnode in node.const_children.items():
            if ctoken == token:
                return cnode
            if ctoken.startswith(token):
                prefix_children.append(cnode)

        if node.var_child is None:
            return None

        cnode = node.var_child
        target = cnode.props[KEY_TARGET]
        value = self.__cast_arg(token, cnode.props[KEY_TYPE])
        if cnode.props[KEY_LIST]:
            value = args.get(target, []) + [value]

        args[target] = value
        return cnode

    def call(self, tokens):
        self.cmdline = tokens
        self.cmdline_matched = []

        args = {}
        node = self.root
        for token in tokens:
            next = self.__find_child(node, token, args)
            if next is None:
                self.__default_helper_func(self.cmdline_matched, node, tokens)
                return

            node = next
            self.cmdline_matched.append(node.token)

        if node.func is None:
            self.__default_helper_func(self.cmdline_matched, node, tokens)
        else:
            args = dict(node.args, **args)
            node.func(**args)

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