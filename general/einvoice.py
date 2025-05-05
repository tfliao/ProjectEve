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
                        help="parse einvoce aggregated file(s), output to @\{outfile\}_meta.csv, and @\{outfile\}_detial.csv")

        cp.invoke(self._args.params)

    def do_parse(self, files, outfile=None):
        all_metas = []
        all_details = []
        for file in files:
            (metas, details) = self.parse_file(file)
            all_metas += metas
            all_details += details

        if outfile is None:
            csv_writer = csv.writer(sys.stdout)
            csv_writer.writerows(all_metas)
            csv_writer.writerows(all_details)
        else:
            with open(outfile+"_meta.csv", encoding='utf-8', mode="a", newline='') as meta_file:
                csv_writer = csv.writer(meta_file)
                csv_writer.writerows(all_metas)

            with open(outfile+"_detail.csv", encoding='utf-8', mode="a", newline='') as detail_file:
                csv_writer = csv.writer(detail_file)
                csv_writer.writerows(all_details)

    def parse_file(self, filepath, encoding='utf-8'):
        result_metas = []
        result_details = []
        last_meta = None

        try:
            with open(filepath, encoding=encoding) as file:
                csvfile = csv.reader(file, delimiter='|')
                for row in csvfile:
                    if row[0] == 'M':
                        row = row[1:]
                        result_metas.append(row)
                        last_meta = row
                    elif row[0] == 'D':
                        if last_meta is None:
                            raise
                        if last_meta[1] != row[1] and last_meta[5] != row[1]:
                            print("einvoice_id mismatch: " + last_meta[5] +" vs " + row[1])
                            raise
                        row[0] = row[1] # change column for einvoice_id
                        row[1] = last_meta[2] # copy date
                        result_details.append(row)
                    else:
                        # ignore header
                        pass
        except UnicodeDecodeError:
            if encoding == 'utf-8':
                return self.parse_file(filepath, 'big5')
            raise

        return (result_metas, result_details)

if __name__ == '__main__':
    Einvoice('Einvoice').run()

