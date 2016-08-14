''' Convenience utility for converting ESRI feature service to GeoJSON.
'''
from __future__ import absolute_import, division, print_function
import logging; _L = logging.getLogger('openaddr.util.esri2geojson')

from argparse import ArgumentParser
from os.path import dirname, join, basename, splitext, exists
from tempfile import mkdtemp
from .cache import EsriRestDownloadTask
import email.parser

def _collect_headers(strings):
    headers, parser = {}, email.parser.Parser()
    
    for string in strings:
        headers.update(dict(parser.parsestr(string)))
    
    return headers

def _collect_params(strings):
    params = {}
    
    for string in strings:
        params.update(dict(urllib.parse.parse_qsl(string)))
    
    return params

def esri2geojson(esri_url, output_path, headers={}, params={}):
    ''' Convert single ESRI feature service URL to GeoJSON file.
    '''
    task = EsriRestDownloadTask('esri', params=params, headers=headers)
    task.download(esri_url, output_path)
    
parser = ArgumentParser(description='Convert single ESRI feature service URL to GeoJSON file.')

parser.add_argument('esri_url', help='Required ESRI source URL.')
parser.add_argument('geojson_path', help='Required output GeoJSON filename.')

parser.add_argument('-l', '--logfile', help='Optional log file name.')

parser.add_argument('-v', '--verbose', help='Turn on verbose logging',
                    action='store_const', dest='loglevel',
                    const=logging.DEBUG, default=logging.INFO)

parser.add_argument('-q', '--quiet', help='Turn off most logging',
                    action='store_const', dest='loglevel',
                    const=logging.WARNING, default=logging.INFO)

parser.add_argument('-H', '--header', default=[], help='Add an HTTP header for ESRI server',
                    action='append', dest='header')

parser.add_argument('-p', '--param', default=[], help='Add a URL parameter for ESRI server',
                    action='append', dest='param')

def main():
    args = parser.parse_args()
    
    headers, params = _collect_headers(args.header), _collect_params(args.param)

    return esri2geojson(args.esri_url, args.geojson_path, headers, params)

if __name__ == '__main__':
    exit(main())
