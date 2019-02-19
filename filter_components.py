#!/usr/bin/env python3

import sys
import argparse
import re

class CustomAction(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        if not 'ordered_args' in namespace:
            setattr(namespace, 'ordered_args', [])
        namespace.ordered_args.append((self.dest, values))

parser = argparse.ArgumentParser(description=
    "Filter parts in a KiCad footprint position CSV file.")
parser.add_argument('csv', metavar='POS.csv',
    help="footprint position CSV file as exported from KiCad (7 columns: "
         "part ref, part name, footprint, x-pos, y-pos, rotation, layer), "
         "columns separated by comma (','), first line is ignored")
parser.add_argument('-o', '--output', metavar='OUT.csv',
    help="specify the output filename")
parser.add_argument('-a', '--all', metavar='TYPE', action=CustomAction,
    help="specify a part type of which all shall be included (e.g. use '-a C' "
         "to include all capacitors); use '-a *' to include every part")
parser.add_argument('-n', '--none', metavar='TYPE', action=CustomAction,
    help="specify a part type of which none shall be included")
parser.add_argument('-i', '--include', metavar='{PART_NAME|PART_NUM|RANGE}',
    action=CustomAction, help="specify parts which shall be included, either "
           "by giving a part name, a part number or a range of part numbers (a"
           " range is specified by 'BEGIN:END', where BEGIN and END are part "
           "numbers; e.g. 'C49:C122' selects all capacitors from C49 to C122)")
parser.add_argument('-e', '--exclude', metavar='{PART_NAME|PART_NUM|RANGE}',
    action=CustomAction, help="specify parts which shall be excluded, either "
           "by giving a part name, a part number or a range of part numbers")
args = parser.parse_args()

PARTNUM_REGEX = '^([A-Z]+)([0-9]+)$'

################################################################################
# READ INPUT FILE:
#
parts = []
with open(args.csv) as inf:
    header_line = next(inf)
    for lnum, line in enumerate(inf, 2):
        cells = [ c.strip().strip('"').strip() for c in line.split(',') ]
        if len(cells) != 7:
            raise ValueError(f"{inf.name},{lnum}: 7 columns are expected")

        # parse part number:
        mobj_num = re.match(PARTNUM_REGEX, cells[0])
        if mobj_num is None:
            raise ValueError(f"{inf.name},{lnum}: invalid part number")

        p_type = mobj_num.group(1)
        p_num = int(mobj_num.group(2))

        parts.append((p_type, p_num, cells[1], line))

################################################################################
# FILTER PARTS:
#
def parse_part_spec(pstr, opt):
    fields = pstr.split(':')
    if len(fields) == 1:
        mobj = re.match(PARTNUM_REGEX, fields[0])
        if mobj:
            return (mobj.group(1), [ int(mobj.group(2)) ])
        else:
            return fields[0]
    elif len(fields) == 2:
        mbeg = re.match(PARTNUM_REGEX, fields[0])
        mend = re.match(PARTNUM_REGEX, fields[1])
        if mbeg is None or mend is None or mbeg.group(1) != mend.group(1):
            raise ValueError(f"option '--{opt} {pstr}': invalid range")
        prange = range(int(mbeg.group(2)), int(mend.group(2)) + 1)
        return (mbeg.group(1), list(prange))
    else:
        raise ValueError(f"option '--{opt} {pstr}': invalid syntax")

incl_parts = set()
if 'ordered_args' in args:
    for arg, argval in args.ordered_args:
        if arg == 'all':
            if argval == '*':
                incl_parts |= set(parts) # add all parts
            else:
                incl_parts |= set([ p for p in parts if p[0] == argval ])

        elif arg == 'none':
            incl_parts -= set([ p for p in parts if p[0] == argval ])

        elif arg == 'include' or arg == 'exclude':
            ps = parse_part_spec(argval, arg)
            if isinstance(ps, tuple):
                p_type, p_nums = ps
                ps = [ p for p in parts if p[0] == p_type and p[1] in p_nums ]
            else:
                ps = [ p for p in parts if p[2] == ps ]

            if arg == 'include':
                incl_parts |= set(ps)
            else:
                incl_parts -= set(ps)

# convert part set to list and sort by part number:
incl_parts = sorted(list(incl_parts), key=lambda tup: (tup[0], tup[1]))

################################################################################
# WRITE OUTPUT FILE:
#
outf = open(args.output, 'w') if args.output else sys.stdout
outf.write(header_line)
for _, _, _, line in incl_parts:
    outf.write(line)
outf.close()
