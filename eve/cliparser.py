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




if __name__ == '__main__':
    class TestClass:
        def f1(self, a):
            print(f'TestClass.f1({a})')

        def f2(self, a, b):
            print(f'TestClass.f2({a}, {b})')

    def f3(a, b):
        print(f'f3({a}, {b})')


    test = TestClass()

    parser = CliParser()
    parser.add_command_class(test, TestClass.f1, ['test', 'f1'], {'a': 'haha'}, 'call member function f1 with default args')
    parser.add_command_class(test, TestClass.f1, ['test', 'f1', '[a]'], {}, 'call member function f1 of test')
    parser.add_command_class(test, TestClass.f2, ['test', 'f2', '[a]', '[b]'], {}, 'call member function f2 of test')
    parser.add_command(f3, ['test', 'f3', '[a]', '[b]'], {}, 'call function f3')
    
    parser.dump()

    while True:
        line = input('cmd> ')
        if line.startswith('exit'):
            break
        tokens = line.strip().split(' ')
        parser.call(tokens)

