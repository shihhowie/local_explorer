import argparse



parser = argparse.ArgumentParser(description="")
parser.add_argument('-i', '--input_file', type=str, help="Path to the sql output to process")
parser.add_argument('-o', '--output_file', type=str, help="Path to the sql output to process")

args = parser.parse_args()

def check_quote():
    with open(args.input_file) as f:
        prev_line = None
        isbody = False
        with open(args.output_file, "w") as out_f:
            for line in f:
                if line[0]=="(":
                    line = line.rstrip(",\n")
                    if isbody:
                        line = ",\n"+line
                    quote_loc = line.find("'")
                    while quote_loc > -1:
                        # print(quote_loc)
                        if line[quote_loc-1] not in ("(", ",") and line[quote_loc+1] not in (',', ')'):
                            line = line[:quote_loc]+"'"+line[quote_loc:]
                            quote_loc += 1
                        quote_loc = line.find("'", quote_loc+1)
                    isbody = True
                out_f.write(line)

if __name__=="__main__":
    check_quote()