#!/usb/bin/python3

import sys
import getopt

def usage():
    print("Wrong usage!")

def main():
    try:
        opts, args = getopt.getopt(sys.argv[1:], "ho:i:", ["help", "output=", "input="])
    except getopt.GetoptError as err:
        # print help information and exit:
        print(err)  # will print something like "option -a not recognized"
        usage()
        sys.exit(2)

    inp    = None
    output = None
    
    for o, a in opts:
        if o in ('-i', '--input'):
            inp = a
        elif o in ('-o', '--output'):
            ouput = a
        else:
            usage()
            sys.exit(2)
    
    if inp == None:
        usage()
        sys.exit(2)

    if output == None:
        output = sys.stdout
    else:
        output = open(output, "w")
    
    with open(inp, "r") as i:
        print(",,,,,,,,,,", file=output)
        for line in i:
            values = line.strip().split(",")
            if len(values) != 7:
                continue;
            try:
                deg = float(values[5])
            except:
                continue;
            if "C" in values[0] or "R" in values[0] or "D" in values[0]:
                deg = (deg + 90) % 360
            if "Q" in values[0]:
                deg = (deg - 90) % 360

            print("{},{},{},{},{},{},{},{},{},{},{}".format(values[0], values[2], values[3], values[4], values[3], values[4], values[3], values[4], values[6], deg, values[1]), file=output)

if __name__ == "__main__":
    main()
