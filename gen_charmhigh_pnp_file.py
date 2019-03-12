#!/usr/bin/env python3

import sys
import argparse
import collections
import re
import datetime
import os

parser = argparse.ArgumentParser(description=
    "Generate a DPV file to be used with the Charmhigh Pick and Place machine. "
    "Parts in the machine can be specified by arguments or by a stack file.")
parser.add_argument('csv', metavar='POS.csv',
    help="footprint position CSV file as exported from KiCad (7 columns: "
         "part ref, part name, footprint, x-pos, y-pos, rotation, layer), "
         "columns separated by comma (','), first line is ignored")
parser.add_argument('-v', '--verbose', action='store_const', const=True,
    default=False, help="print debug information to check validity of files")
parser.add_argument('-o', '--output', metavar='OUT.dpv',
    help="specify the output filename (default is same base name as CSV file)")
parser.add_argument('-s', '--stack', metavar='PART:NUM', action='append',
    help="specify that the part PART is found in stack number NUM")
parser.add_argument('-f', '--feed', metavar='PART:FEED', action='append',
    help="specify the feed distance FEED in mm for the part PART (default 4)")
parser.add_argument('-e', '--head', metavar='PART:HEAD', action='append',
    help="specify that the part PART should be picked up by head number HEAD "
         "(either 1 or 2, default is 1)")
parser.add_argument('-r', '--rotation', metavar='PART:ROT', action='append',
    help="specify the rotation offset ROT in degrees for part PART with a "
         "non-standard orientation (i.e. not EIA-481-E compliant)")
parser.add_argument('--stackfile', metavar='STACK.csv',
    help="specify the parts in the machine in a CSV file, which has up to 5 "
         "columns: part name, stack number, feed, head number, rotation offset"
         " (columns separated by comma ',', options override this file); "
         "note that parts will be placed in the order they appear in this file")
parser.add_argument('-m', '--mark', metavar='X,Y', action='append',
    help="specify the coordinates of a calibration mark")
parser.add_argument('-l', '--layer', metavar='{top|bottom}',
    help="specify whether the parts of the top or bottom layer shall be placed"
         " (auto-detected from the first part in the position file by default)")
args = parser.parse_args()

def parse_stack_num(stack_str):
    if stack_str in [ str(val) for val in range(1, 61) ]:
        return int(stack_str)
    raise ValueError("stack number must within [1,60]")

def parse_feed(feed_str):
    if feed_str in [ '2', '4', '8', '12', '16', '24' ]:
        return int(feed_str)
    raise ValueError("feed must be one of (2, 4, 8, 12, 16, 24)")

def parse_head(head_str):
    if head_str in [ '1', '2' ]:
        return int(head_str)
    raise ValueError("head must be either 1 or 2")

def parse_rotation(rot_str):
    try:
        return float(rot_str)
    except ValueError:
        raise ValueError("rotation offset must be float value")

# build the machine stack, first from the stack file, then from the options:
machine_stack = collections.OrderedDict()

if args.stackfile:
    with open(args.stackfile) as sf:
        for lino, line in enumerate(sf):
            if line.strip()[0] != '#':
                cols = [ col.strip() for col in line.strip().split(',') ]
                if len(cols) < 2:
                    raise ValueError(f"{sf.name}:{lino} to few columns")
                try:
                    stack_num = parse_stack_num(cols[1])
                    feed = parse_feed(cols[2]) if len(cols) >= 3 else 4
                    head = parse_head(cols[3]) if len(cols) >= 4 else 1
                    rotation = parse_rotation(cols[4]) if len(cols) >= 5 else 0
                except ValueError as verr:
                    raise ValueError(f"{sf.name}:{lino} {str(verr)}")
                machine_stack[cols[0]] = [ stack_num, feed, head, rotation ]

machine_stack_options = [
    (args.stack,    'stack',    parse_stack_num, 0),
    (args.feed,     'feed',     parse_feed,      1),
    (args.head,     'head',     parse_head,      2),
    (args.rotation, 'rotation', parse_rotation,  3)
]
for opt, opts, func, idx in machine_stack_options:
    if opt:
        for optarg in opt:
            fields = optarg.split(':')
            if len(fields) != 2:
                raise ValueError(f"option '--{opts} {optarg}': invalid syntax")
            if fields[0] not in machine_stack:
                machine_stack[fields[0]] = [ None, 4, 1, 0 ]
            try:
                machine_stack[fields[0]][idx] = func(optarg)
            except ValueError as verr:
                raise ValueError(f"option '--{opts} {optarg}': {str(verr)}")

# parse calibration marks:
calib_marks = []
if args.mark:
    for m in args.mark:
        coords = m.split(',')
        if len(coords) != 2:
            raise ValueError(f"option '--mark {m}': invalid syntax")
        try:
            xpos = float(coords[0])
            ypos = float(coords[1])
        except ValueError:
            raise ValueError(f"option '--mark {m}': invalid syntax")
        calib_marks.append((xpos, ypos))

# check whether a layer was specified:
layer = None
if args.layer:
    if args.layer == 't' or args.layer == 'top':
        layer = 'top'
    elif args.layer == 'b' or args.layer == 'bottom':
        layer = 'bottom'
    else:
        raise ValueError(f"option '--layer {args.layer}': invalid value")

################################################################################
# PARSE CSV FILE:
#
parts = []
missing_parts = []
with open(args.csv) as inf:
    next(inf) # skip header line
    for lnum, line in enumerate(inf, 2):
        cells = [ c.strip().strip('"').strip() for c in line.split(',') ]
        if len(cells) != 7:
            raise ValueError(f"{inf.name},{lnum}: 7 columns are expected")

        part_num = cells[0]
        part_name = cells[1]
        footprint = cells[2]
        pos = (float(cells[3]), float(cells[4]))
        orient = float(cells[5])
        part_layer = cells[6]

        # check whether the part number is valid:
        num_mobj = re.match('^([A-Z]+)([0-9]+)$', part_num)
        if num_mobj is None:
            raise ValueError(f"{inf.name},{lnum}: invalid part number")

        # unambiguously identify capacitors, inductances and resistors:
        units = { 'C': 'F', 'L': 'H', 'R': 'Ohm' }
        if num_mobj.group(1) in units:
            if re.match('^[0-9]+[GMkmunpf]?[0-9]*$', part_name):
                part_name += units[part_num[0]]

        # check whether this part belongs to the top or bottom layer:
        if part_layer != 'top' and part_layer != 'bottom':
            raise ValueError(f"{inf.name},{lnum}: layer (column 7) must be "
                              "either 'top' or 'bottom'")
        if layer == None:
            layer = part_layer

        # add part (except DNP parts), check whether the part is in the stack:
        if part_layer == layer and not part_name.startswith('DNP'):
            if part_name in machine_stack:
                _, _, _, rotation = machine_stack[part_name]
                idx = list(machine_stack.keys()).index(part_name)
                parts.append((part_num, part_name, pos, orient + rotation, idx))
            elif part_name not in missing_parts:
                print(f"\x1b[33mWarning: part {part_name} "
                      f"is not in machine stack, skipping\x1b[0m")
                missing_parts.append(part_name)

parts.sort(key=lambda tup: tup[4]) # same order as in 'machine_stack'

# inform the user about parts in the machine stack which are not used:
for p in set(machine_stack) - set([ p[1] for p in parts ]):
    print(f"\x1b[34mInfo: part {p} in the machine stack is not used\x1b[0m")

################################################################################
# TRANSFORM COORDINATES ACCORDING TO BOARD ORIENTATION:
#

# check which board corner is the origin (based on sign of part coordinates):
x_pos = all(part[2][0] >= 0. for part in parts)
x_neg = all(part[2][0] <= 0. for part in parts)
y_pos = all(part[2][1] >= 0. for part in parts)
y_neg = all(part[2][1] <= 0. for part in parts)
if (not x_pos and not x_neg) or (not y_pos and not y_neg):
    raise ValueError("The origin of the board must be in a corner, "
            "i.e. all parts must be on the same side of the x axis and y axis")

if args.verbose:
    print("The auxiliary axis origin is in the "
          f"{'lower' if y_pos else 'upper'} {'left' if x_pos else 'right'} "
          "corner of the board.")

# convert all part coordinates such that board origin is in lower left corner:
parts_conv = []
for part_num, part_name, pos, orient, _ in parts:
    px, py = pos
    if x_pos:
        pos = (px, py) if y_pos else (-py, px)
        orient += 0 if y_pos else 90
    else:
        pos = (py, -px) if y_pos else (-px, -py)
        orient += 270 if y_pos else 180

    # when placing parts on the bottom layer, the x and y axis are inverted:
    if layer == 'bottom':
        pos = (pos[1], pos[0])
        orient += 0 # TODO figure out how to rotate parts on the bottom layer

    while orient > 180:
        orient -= 360
    parts_conv.append((part_num, part_name, pos, orient))

# verify that everything has been successfully transformed:
assert all(part[2][0] >= 0. for part in parts_conv), "negative x coordinate"
assert all(part[2][1] >= 0. for part in parts_conv), "negative y coordinate"

################################################################################
# WRITE MACHINE FILE:
#
outpath = args.output if args.output else args.csv[:-4] + '.dpv'
with open(outpath, 'w') as outf:
    outf.write('separated\r\n')
    outf.write(f"FILE,{os.path.basename(outpath)}\r\n")
    outf.write(f"PCBFILE,{os.path.basename(args.csv)}\r\n")
    date_str = datetime.datetime.now().strftime("%Y/%m/%d")
    time_str = datetime.datetime.now().strftime("%H:%M:%S")
    outf.write(f"DATE,{date_str}\r\nTIME,{time_str}\r\n")
    outf.write('PANELYPE,0\r\n\r\n') # TODO figure out how to use panels

    outf.write('Table,No.,ID,DeltX,DeltY,FeedRates,Note,Height,Speed,Status,'
               'SizeX,SizeY\r\n\r\n')
    for num, part_name in enumerate(machine_stack):
        stack_num, feed, _, _ = machine_stack[part_name]
        outf.write(f"Station,{num},{stack_num},0,0,{feed},{part_name},0.5,0,6,"
                    "0,0\r\n\r\n")
    outf.write('\r\n\r\n')

    outf.write('Table,No.,ID,DeltX,DeltY\r\n\r\n')
    outf.write('Panel_Coord,0,1,0,0\r\n\r\n')
    outf.write('\r\n\r\n')

    outf.write('Table,No.,ID,PHead,STNo.,DeltX,DeltY,Angle,Height,Skip,Speed,'
               'Explain,Note\r\n\r\n')
    for num, part in enumerate(parts_conv):
        pnum, pname, pos, orient = part
        stack_num, _, head, _ = machine_stack[pname]
        outf.write(f"EComponent,{num},{num+1},{head},{stack_num},{pos[0]:.2f},"
                   f"{pos[1]:.2f},{orient:.1f},0.5,6,0,{pnum},{pname}\r\n\r\n")
    outf.write('\r\n\r\n')

    outf.write('Table,No.,ID,CenterX,CenterY,IntervalX,IntervalY,NumX,NumY,'
               'Start\r\n\r\n')
    outf.write('\r\n\r\n')

    outf.write('Table,No.,nType,nAlg,nFinished\r\n\r\n')
    outf.write('PcbCalib,0,1,0,1\r\n\r\n')

    outf.write('Table,No.,ID,offsetX,offsetY,Note\r\n\r\n')
    for idx, calib in enumerate(calib_marks):
        outf.write(f"CalibPoint,{idx},{idx+1},{calib[0]},{calib[1]},Mark1\r\n")
    outf.write('\r\n')

    outf.write('Table,No.,DeltX,DeltY,AlphaX,AlphaY,BetaX,BetaY,DeltaAngle'
               '\r\n\r\n')
    outf.write('CalibFator,0,112.7,79.37,0.999545,-0.0034923,0.00360968,'
               '1.00062,-0.19997\r\n\r\n') # TODO understand the CalibFator
