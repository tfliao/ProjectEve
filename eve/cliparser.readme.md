# main feature:
* define command with (tokens, func, desc)

# details:
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
    4. match prefix
        * e.g.
            ["set", "filesystem", "@fstype"], handle_set_filesystem(fstype)
            if no other possible token start with files*
            > set files ext4 # prefix
    5. allow some commands to be hidden, which won't be shown in help
    6. optional token (globally)
        e.g. -v for verbse, which can present anywhere

* show helpful messages when command line matchs no rules

# TODOS:
* show candidates of commands when passing special token (e.g. ? like cisco console)
* interactive console for all function above
    * provide shell-like experience
        1. arrows (up/down/left/right)
        2. ^C to clean current command, type exit to leave

