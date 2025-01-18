#!/usr/bin/python3
import eve.common
import csv
import sys
from cmdbase import CmdBase
from eve.database import EveDB
from eve.cliparser import CliParser

class Einvoice(CmdBase):
    version = '1.0.0'
    desc = 'operations to einvoice from nat.gov.tw '

    def __init__(self, prog = None, prefix = None, loggername = None):
        CmdBase.__init__(self, prog, self.version, self.desc, prefix=prefix, loggername=loggername)

    def _prepare_parser(self, parser):
        parser.add_argument('params', nargs='*', default=[])

    def _run(self):
        cp = CliParser()
        cp.add_command(['parse', 'from', '@files...'], 
                        inst=self, func=Einvoice.do_parse,
                        help="parse einvoce aggregated file(s), output to stdout")
        cp.add_command(['parse', 'to', '@outfile', 'from', '@files...' ],
                        inst=self, func=Einvoice.do_parse,
                        help="parse einvoce aggregated file(s), output to @outfile")

        cp.invoke(self._args.params)

    def do_parse(self, files, outfile=None):
        rows = []
        for file in files:
            rows += self.parse_file(file)

        if outfile is None:
            outfile = sys.stdout
        else:
            outfile = open(outfile, encoding='utf-8', mode="a", newline='')
        
        csv_writer = csv.writer(outfile)
        csv_writer.writerows(rows)

        outfile.close()

    def parse_file(self, filepath):
        result_rows = []
        last_row = None
        with open(filepath, encoding='utf-8') as file:
            csvfile = csv.reader(file, delimiter='|')
            for row in csvfile:
                if row[0] == 'M':
                    if last_row is not None:
                        last_row[8] = '\n'.join(last_row[8])
                        last_row[9] = '\n'.join(last_row[9])
                        result_rows.append(last_row)
                    last_row = row[1:]
                    last_row.append([])
                    last_row[8] = []
                    last_row[9] = []
                elif row[0] == 'D':
                    if last_row is None:
                        raise
                    last_row[8].append(row[2])
                    last_row[9].append(row[3])
                else:
                    # ignore header
                    pass
        if last_row is not None:
            last_row[8] = '\n'.join(last_row[8])
            last_row[9] = '\n'.join(last_row[9])
            result_rows.append(last_row)
        return result_rows

if __name__ == '__main__':
    Einvoice('Einvoice').run()

