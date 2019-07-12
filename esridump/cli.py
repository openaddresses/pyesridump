import argparse
import email.parser
from six.moves import urllib
import logging
import json
import sys

from esridump import EsriDumper

def _collect_headers(strings):
    headers = {}
    parser = email.parser.Parser()

    for string in strings:
        headers.update(dict(parser.parsestr(string)))

    return headers

def _collect_params(strings):
    params = {}

    for string in strings:
        params.update(dict(urllib.parse.parse_qsl(string)))

    return params

def _parse_args(args):
    parser = argparse.ArgumentParser(
        description="Convert a single Esri feature service URL to GeoJSON")
    parser.add_argument("url",
        help="Esri layer URL")
    parser.add_argument("outfile",
        type=argparse.FileType('w'),
        help="Output file name (use - for stdout)")
    parser.add_argument("--proxy",
        help="Proxy string to send requests through ie: https://example.com/proxy.ashx?<SERVER>")
    parser.add_argument("--jsonlines",
        action='store_true',
        default=False,
        help="Output newline-delimited GeoJSON Features instead of a FeatureCollection")
    parser.add_argument("-v", "--verbose",
        action='store_const',
        dest='loglevel',
        const=logging.DEBUG,
        default=logging.INFO,
        help="Turn on verbose logging")
    parser.add_argument("-q", "--quiet",
        action='store_const',
        dest='loglevel',
        const=logging.WARNING,
        default=logging.INFO,
        help="Turn off most logging")
    parser.add_argument("-f", "--fields",
        help="Specify a comma-separated list of fields to request from the server")
    parser.add_argument("--no-geometry",
        dest='request_geometry',
        action='store_false',
        default=True,
        help="Don't request geometry for the feature so the server returns attributes only")
    parser.add_argument("-H", "--header",
        action='append',
        dest='headers',
        default=[],
        help="Add an HTTP header to send when requesting from Esri server")
    parser.add_argument("-p", "--param",
        action='append',
        dest='params',
        default=[],
        help="Add a URL parameter to send when requesting from Esri server")
    parser.add_argument("-t", "--timeout",
        type=int,
        default=30,
        help="HTTP timeout in seconds, default 30")
    parser.add_argument("--paginate-oid",
        dest='paginate_oid',
        action='store_true',
        default=False,
        help="Turn on paginate by OID regardless of normal pagination support")

    return parser.parse_args(args)

def main():
    args = _parse_args(sys.argv[1:])
    headers = _collect_headers(args.headers)
    params = _collect_params(args.params)

    logger = logging.getLogger('cli')
    logger.setLevel(args.loglevel)
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    requested_fields = args.fields.split(',') if args.fields else None

    dumper = EsriDumper(args.url,
        extra_query_args=params,
        extra_headers=headers,
        fields=requested_fields,
        request_geometry=args.request_geometry,
        proxy=args.proxy,
        timeout=args.timeout,
        parent_logger=logger,
        paginate_oid=args.paginate_oid)

    if args.jsonlines:
        for feature in dumper:
            args.outfile.write(json.dumps(feature))
            args.outfile.write('\n')
    else:
        args.outfile.write('{"type":"FeatureCollection","features":[\n')
        feature_iter = iter(dumper)
        try:
            feature = next(feature_iter)
            while True:
                args.outfile.write(json.dumps(feature))
                feature = next(feature_iter)
                args.outfile.write(',\n')
        except StopIteration:
            args.outfile.write('\n')
        args.outfile.write(']}')

if __name__ == '__main__':
    main()
