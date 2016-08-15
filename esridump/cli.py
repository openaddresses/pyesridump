import argparse
import simplejson as json

from esridump.dumper import EsriDumper

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("url")
    parser.add_argument("outfile", type=argparse.FileType('w'))
    parser.add_argument("--jsonlines", action='store_true', default=False)
    args = parser.parse_args()

    dumper = EsriDumper(args.url)

    if not args.jsonlines:
        args.outfile.write('{"type":"FeatureCollection","features":[\n')

    for feature in dumper.iter():
        args.outfile.write(json.dumps(feature))

        if not args.jsonlines:
            args.outfile.write(',')
        args.outfile.write('\n')

    if not args.jsonlines:
        # args.outfile.seek(-2)
        args.outfile.write(']}')

if __name__ == '__main__':
    main()
