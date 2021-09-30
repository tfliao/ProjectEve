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
            super().__init__(message)

    class CmdTreeBuildException(Exception):
        def __init__(self, message):
            super().__init__(message)

    class CmdTreeParseException(Exception):
        def __init__(self, message):
            super().__init__(message)

    class CmdToken:
        RE_VAR_PATTERN = r'@\s*(\w+)\s*(\((\w+)\))?\s*(...)?'
        ACCEPT_TYPE = {'bool', 'str', 'int'}

        @classmethod
        def register_extra_type(cls, type):
            cls.ACCEPT_TYPE.add(type)

        def __init__(self, token):
            self.desc = self.func = self.args = self.extra = None # shut up the PEP8

            self.hidden = True
            self.const_children = {}
            self.var_child = None

            self.token = token
            self.props = None
            self.type = self.__parse_token_type(token)

        def setup(self, desc = "", args = {}, hidden = True, func = None, extra = None):
            self.desc = desc
            self.func = func
            self.args = args
            self.hidden = hidden
            self.extra = None

        def __parse_token_type(self, token):
            if not token.startswith('@'):
                return TOKEN_TYPE_CONST

            m = re.match(__class__.RE_VAR_PATTERN, token)
            if m is None:
                raise CliParser.BadTokenFormatException(f'token {token} is illegal')

            target = m.group(1)
            type = ('str' if m.group(3) is None else m.group(3)).lower()
            if type not in __class__.ACCEPT_TYPE:
                raise CliParser.BadTokenFormatException(f'type {type} is not supported')

            listable = m.group(4) is not None
            self.props = {
                KEY_TARGET: target,
                KEY_TYPE: type,
                KEY_LIST: listable
            }
            self.token = f'@{target}({type})' +  ('...' if listable else '')
            return TOKEN_TYPE_VAR

    """
    default functions
    """
    @staticmethod
    def __bad_command_handler(parse_info):
        print('Command not found / Incomplete command.')

    @staticmethod
    def __help_command_handler(parse_info):
        cmdline = parse_info['cmdline'][:parse_info['match_cnt']]
        print(f'Given cmdline: {cmdline}')
        print(f' candidates:')
        for cnode in parse_info['const_nodes']:
            if not cnode.hidden:
                print(f'\t{cnode.token}\t{cnode.desc}')
        vnode = parse_info['variable_node']
        if vnode is not None:
            if not vnode.hidden:
                print(f'\t{vnode.token}\t{vnode.desc}')

    """
    init
    """
    def __init__(self):
        self.root = CliParser.CmdToken("(root)")
        self.keyword_help = 'help'
        self.cmd_handler = {
            'bad': CliParser.__bad_command_handler,
            'help': CliParser.__help_command_handler
        }
        self.cast_fn = self.__init_cast_fn()

    """
    private helper functions
    """
    def __init_cast_fn(self):
        return {
            'str': lambda x : x,
            'int': lambda x: int(x, 16 if x.startswith('0x') else 10),
            'bool': lambda x: x.lower() in ['true', '1', 'yes', 'y', 't']
        }

    def __capture_arg(self, node, token, args):
        target = node.props[KEY_TARGET]
        type = node.props[KEY_TYPE]
        value = self.cast_fn[type](token)
        if node.props[KEY_LIST]:
            value = args.get(target, []) + [value]
        args[target] = value
        return node

    def __find_child(self, node, token, args):
        # list type will capture all following args
        if node.type == TOKEN_TYPE_VAR and node.props[KEY_LIST]:
            return self.__capture_arg(node, token, args)

        # check const children first
        prefix_children = []
        for ctoken, cnode in node.const_children.items():
            if ctoken == token:
                return cnode
            if ctoken.startswith(token):
                prefix_children.append(cnode)

        # one const child solely matched the prefix
        if len(prefix_children) == 1:
            return prefix_children[0]

        # check variable child
        if node.var_child is None:
            return None

        return self.__capture_arg(node.var_child, token, args)

    def __call_cmd_handler(self, type, node, cmdline, match_cnt):
        parse_info = {
            'handle_type': type,
            'cmdline': cmdline,
            'match_cnt': match_cnt,
            'node': node,
            'variable_node': node.var_child,
            'const_nodes': node.const_children.values(),
        }
        assert(type in self.cmd_handler)
        self.cmd_handler[type](parse_info)

    """
    APIs here
    """
    def register_type_caster(self, type, type_fn):
        """
        register customized type by providing it casting fn (from str to `type`)
        `type`: name of type to register
        `type_fn`: cast function from str
        """
        CliParser.CmdToken.register_extra_type(type)
        self.cast_fn[type] = type_fn

    def register_bad_command_handler(self, bad_cmd_fn):
        """
        regiser handler when encounter bad command,
        bad_cmd_fn expect to accept the following arguments:
            `parse_info`: {
                `handle_type`: "bad", indicate which bad_cmd_handler is called
                `cmdline`: list of str, the full command from user
                `match_cnt`: indicate # of token matchs some of rule
                `node`: CliParser.CmdToken, which is last node matchs user's input
                `variable_node`: CliParser.CmdToken, Noneable, child node that store input to some named args
                `const_nodes`: list of CliParser.CmdToken, all children that match fixed str
            }
        """
        self.cmd_handler['bad'] = bad_cmd_fn

    def register_help_command_handler(self, help_cmd_fn):
        """
        regiser handler when read help command,
        help_cmd_fn expect to accept the following arguments:
            `parse_info`; same with bad_cmd_fn, but `handler_type` is 'help'
        """
        self.cmd_handler['help'] = help_cmd_fn

    def add_command(self, inst, func, tokens, default_args = {}, description="", hidden=False, extra=None):
        """
        add a command with the cmdline tokens to match and the func to execute

        `inst`, `func`: handler function expected to be a member of class,
                        thus (class instance - `inst`, member function `func`) defines func for a command
        `tokens`: list of str that be used to match user's input, a token start with @ will capture user's input and pass it to handler function
        `default_args`: predefine some arguments for handler function
        `description`: description that used in auto-generating help message
        `hidden`: indicate this command should be hidden from help message
        `extra`: extra information that can be used in customized help/bad_cmd message
        """
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
                        raise CliParser.CmdTreeBuildException(f"Conflicted variable token given [{node.var_child.token}] vs [{cmd_token.token}]")
                    node = node.var_child
                else:
                    node.var_child = cmd_token
                    node = node.var_child
            node.hidden &= hidden

        if inst is not None:
            default_args['self'] = inst
        node.setup(description, default_args, hidden, func, extra)

    def invoke(self, tokens):
        """
        invoke command with user-input `tokens`
        """
        args = {}
        match_cnt = 0
        node = self.root
        for token in tokens:
            # check if match help keyword
            if token.lower() == self.keyword_help:
                self.__call_cmd_handler('help', node, tokens, match_cnt)
                return

            # find most matching child
            next = self.__find_child(node, token, args)
            if next is None:
                self.__call_cmd_handler('bad', node, tokens, match_cnt)
                return
            match_cnt += 1
            node = next

        if node.func is None:
            # stop in no executable node
            self.__call_cmd_handler('bad', node, tokens, match_cnt)
        else:
            args = dict(node.args, **args)
            node.func(**args)

"""
main feature:

* define command with (tokens, func, desc)

details:
* special format in tokens, which support the following behaviors
    [v] 1. pass token (string) as args with some name
        * e.g.
            ["set", "feature", "@enable"], handle_set_feature(enable)
            > set feature true
            pass string "true" as argument "enable" in handle_set_feature
    [v] 2. allow single token that accept dynamic number of args in command
        * e.g.
            ["show", "slot", "@idlist..."], handle_show_slot(idlist)
            > show slot 1 2 3
            pass list of string ["1", "2", "3"] as argument "idlist" in handle_show_slot
    [v] 3. type check/convert for arguments
        * e.g.
            ["show", "slot", "@idlist(int)..."], handle_show_slot(idlist)
            > show slot 1 2 3
            pass list of int [1, 2, 3] as argument "idlist" in handle_show_slot
    [v] 4.1 match prefix
    4.2 match abbreviation
        * e.g.
            ["set", "fs|filesystem", "@fstype"], handle_set_filesystem(fstype)
            all the following commands matchs, if no other possible token start with files*
            > set fs ext4 # abbreviation
            > set files ext4 # prefix
    [v] 5. allow some commands to be hidden, which won't be shown in help

v show helpful messages when command line matchs no rules
v show candidates of commands when passing special token (e.g. ? like cisco console)

* interactive console for all function above
    * provide shell-like experience
        1. arrows (up/down/left/right)
        2. ^C to clean current command, type exit to leave

"""