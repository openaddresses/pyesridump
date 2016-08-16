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

    if args.jsonlines:
        for feature in dumper.iter():
            args.outfile.write(json.dumps(feature))
            args.outfile.write('\n')
    else:
        args.outfile.write('{"type":"FeatureCollection","features":[\n')
        feature_iter = dumper.iter()
        try:
            feature = feature_iter.next()
            while True:
                args.outfile.write(json.dumps(feature))
                feature = feature_iter.next()
                args.outfile.write(',\n')
        except StopIteration:
            args.outfile.write('\n')
        args.outfile.write(']}')

if __name__ == '__main__':
    main()
