import logging; _L = logging.getLogger('openaddr.cache')
from contextlib import contextmanager

import os
import socket
import json
import math

import requests

# HTTP timeout in seconds, used in various calls to requests.get() and requests.post()
_http_timeout = 180

def request(method, url, **kwargs):
    try:
        _L.debug("Requesting %s with args %s", url, kwargs.get('params') or kwargs.get('data'))
        return requests.request(method, url, timeout=_http_timeout, **kwargs)
    except requests.exceptions.SSLError as e:
        _L.warning("Retrying %s without SSL verification", url)
        return rrequest(method, url, timeout=_http_timeout, verify=False, **kwargs)
    except socket.timeout as e:
        raise DownloadError("Timeout when connecting to URL", e)
    except ValueError as e:
        raise DownloadError("Could not parse JSON", e)
    except Exception as e:
        raise DownloadError("Could not connect to URL", e)


class DownloadError(Exception):
    pass


class DownloadTask(object):

    def __init__(self, source_prefix, params={}, headers={}):
        '''
        
            params: Additional query parameters, used by EsriRestDownloadTask.
            headers: Additional HTTP headers.
        '''
        self.source_prefix = source_prefix
        self.headers = {
            'User-Agent': 'openaddresses-extract/1.0 (https://github.com/openaddresses/openaddresses)',
        }
        self.headers.update(dict(**headers))
        self.query_params = dict(**params)

    def download(self, source_urls, workdir, conform):
        raise NotImplementedError()

class EsriRestDownloadTask(DownloadTask):
    def handle_esri_errors(self, response, error_message):
        if response.status_code != 200:
            raise DownloadError('{}: HTTP {} {}'.format(
                error_message,
                response.status_code,
                response.text,
            ))

        try:
            data = response.json()
        except:
            _L.error("Could not parse response from {} as JSON:\n\n{}".format(
                response.request.url,
                response.text,
            ))
            raise

        error = data.get('error')
        if error:
            raise DownloadError("{}: {} {}" .format(
                error_message,
                error['message'],
                ', '.join(error['details']),
            ))

        return data

    def get_layer_metadata(self, url):
        query_args = dict(**self.query_params)
        query_args.update({'f': 'json'})
        response = request('GET', url, params=query_args, headers=self.headers)
        metadata = self.handle_esri_errors(response, "Could not retrieve field names from ESRI source")
        return metadata

    def get_layer_feature_count(self, url):
        query_args = dict(**self.query_params)
        query_args.update({
            'where': '1=1',
            'returnCountOnly': 'true',
            'f': 'json',
        })
        response = request('GET', url, params=query_args, headers=self.headers)
        count_json = self.handle_esri_errors(response, "Could not retrieve row count from ESRI source")
        return count_json

    def get_layer_min_max(self, url, oid_field_name):
        """ Find the min and max values for the OID field. """
        query_args = dict(**self.query_params)
        query_args.update({
            'f': 'json',
            'outFields': '',
            'outStatistics': json.dumps([
                dict(statisticType='min', onStatisticField=oid_field_name, outStatisticFieldName='THE_MIN'),
                dict(statisticType='max', onStatisticField=oid_field_name, outStatisticFieldName='THE_MAX'),
            ], separators=(',', ':'))
        })
        response = request('GET', url, params=query_args, headers=self.headers)
        metadata = self.handle_esri_errors(response, "Could not retrieve min/max oid values from ESRI source")

        # Some servers (specifically version 10.11, it seems) will
        # respond with SQL statements for the attribute names rather
        # than the requested field names, so pick the min and max
        # deliberately rather than relying on the names.
        min_max_values = metadata['features'][0]['attributes'].values()
        return (min(min_max_values), max(min_max_values))

    def get_layer_oids(self, url):
        query_args = dict(**self.query_params)
        query_args.update({
            'where': '1=1',  # So we get everything
            'returnIdsOnly': 'true',
            'f': 'json',
        })
        response = request('GET', url, params=query_args, headers=self.headers)
        oid_data = self.handle_esri_errors(response, "Could not retrieve object IDs from ESRI source")
        return oid_data

    def can_handle_pagination(self, query_url, query_fields):
        check_args = dict(**self.query_params)
        check_args.update({
            'resultOffset': 0,
            'resultRecordCount': 1,
            'where': '1=1',
            'returnGeometry': 'false',
            'outFields': ','.join(query_fields),
            'f': 'json',
        })
        response = request('POST', query_url, headers=self.headers, data=check_args)

        try:
            data = response.json()
        except:
            _L.error("Could not parse response from pagination check {} as JSON:\n\n{}".format(
                response.request.url,
                response.text,
            ))
            return False

        return data.get('error') and data['error']['message'] != "Failed to execute query."

    def find_oid_field_name(self, metadata):
        oid_field_name = metadata.get('objectIdField')
        if not oid_field_name:
            for f in metadata['fields']:
                if f['type'] == 'esriFieldTypeOID':
                    oid_field_name = f['name']
                    break

        if not oid_field_name:
            raise DownloadError("Could not find object ID field name")

        return oid_field_name

    def field_names_to_request(self, conform):
        ''' Return list of fieldnames to request based on conform, or None.
        '''
        if not conform:
            return None

        fields = set()
        for k, v in conform.items():
            if k in attrib_types:
                if isinstance(v, dict):
                    # It's a function of some sort
                    fields.add(v.get('field'))
                elif isinstance(v, list):
                    # It's a list of field names
                    for f in v:
                        fields.add(f)
                else:
                    fields.add(v)

        if fields:
            return list(filter(None, sorted(fields)))
        else:
            return None
        
    def result_offset_paginate(self, query_url, query_fields, row_count, page_size):
        # There's a bug where some servers won't handle these queries
        # in combination with a list of fields specified. We'll make a
        # single, 1 row query here to check if the server supports
        # this and switch to querying for all fields if specifying the
        # fields fails.
        if (query_fields
            and not self.can_handle_pagination(query_url, query_fields)):
            _L.info("Source does not support pagination with fields specified, so querying for all fields.")
            query_fields = None

        for offset in range(0, row_count, page_size):
            query_args = dict(**self.query_params)
            query_args.update({
                'resultOffset': offset,
                'resultRecordCount': page_size,
                'where': '1=1',
                'geometryPrecision': 7,
                'returnGeometry': 'true',
                'outSR': 4326,
                'outFields': ','.join(query_fields or ['*']),
                'f': 'json',
            })
            response = request('POST', query_url,
                               headers=self.headers, data=query_args)

            data = self.handle_esri_errors(response, "Could not retrieve this chunk of objects from ESRI source")
            yield data

    def where_pagination(self, query_url, query_fields, oid_field_name, page_size):
        (oid_min, oid_max) = self.get_layer_min_max(query_url, oid_field_name)

        for page_min in range(oid_min - 1, oid_max, page_size):
            page_max = min(page_min + page_size, oid_max)
            query_args = dict(**self.query_params)
            query_args.update({
                'where': '{} > {} AND {} <= {}'.format(
                    oid_field_name,
                    page_min,
                    oid_field_name,
                    page_max,
                ),
                'geometryPrecision': 7,
                'returnGeometry': 'true',
                'outSR': 4326,
                'outFields': ','.join(query_fields or ['*']),
                'f': 'json',
            })
            response = request('POST', query_url,
                               headers=self.headers, data=query_args)

            data = self.handle_esri_errors(response, "Could not retrieve this chunk of objects from ESRI source")
            yield data

    def oid_enumeration_pagination(self, query_url, query_fields):
        oid_data = self.get_layer_oids(query_url)
        oids = oid_data['objectIds']

        for i in range(0, len(oids), 100):
            oid_chunk = map(long if PY2 else int, oids[i:i+100])
            query_args = dict(**self.query_params)
            query_args.update({
                'objectIds': ','.join(map(str, oid_chunk)),
                'geometryPrecision': 7,
                'returnGeometry': 'true',
                'outSR': 4326,
                'outFields': ','.join(query_fields or ['*']),
                'f': 'json',
            })
            response = request('POST', query_url, headers=self.headers,
                               data=query_args)
                
            data = self.handle_esri_errors(response, "Could not retrieve this chunk of objects from ESRI source")
            yield data

    def subdivide(self, query_url, query_fields, metadata, page_size):
        oid_field_name = self.find_oid_field_name(metadata)
        seen_features = set()
        
        bounds = metadata['extent']
        bbox = (bounds['xmin'], bounds['ymin'],
                bounds['xmax'], bounds['ymax'])

        for data in self.bbox_features(query_url, query_fields, bbox, page_size):
            data['features'] = [feature for feature in data['features']
                                if feature['attributes'][oid_field_name]
                                not in seen_features]
            yield data

            seen_features.update(feature['attributes'][oid_field_name]
                                 for feature in data['features'])

    def bbox_features(self, query_url, query_fields, bbox, page_size):
        data = self.bbox_query(query_url, query_fields, bbox)

        if len(data['features']) == page_size:
            for sub_bbox in bboxes(bbox, 2):
                yield from self.bbox_features(query_url, query_fields, sub_bbox, page_size)
        else:
            yield data

    def bbox_query(self, query_url, query_fields, bounds):
        geometry = json.dumps({"rings": [[bounds[0], bounds[1]],
                                         [bounds[0], bounds[3]],
                                         [bounds[2], bounds[3]],
                                         [bounds[2], bounds[1]],
                                         [bounds[0], bounds[1]]]})

        print(geometry)

        geometry = json.dumps({
            "rings": [
                [
                    [bounds[0], bounds[1]],
                    [bounds[0], bounds[3]],
                    [bounds[2], bounds[3]],
                    [bounds[2], bounds[1]],
                    [bounds[0], bounds[1]]
                ]
            ]
        })

        query_args = dict(**self.query_params)
        query_args.update({
            'geometry': geometry,
            'geometryType': 'esriGeometryPolygon',
            'spatialRel': 'esriSpatialRelIntersects',
            'geometryPrecision': 7,
            'returnGeometry': 'true',
            'returnIdsOnly': 'false',
            'outSR': 4326,
            'outFields': ','.join(query_fields or ['*']),
            'f': 'json',
        })

        response = request('POST', query_url,
                           headers=self.headers, data=query_args)

        data = self.handle_esri_errors(response, "Could not retrieve this chunk of objects from ESRI source")
        return data
            

    def sniff_paginate_method(self, metadata, query_url):

        if (metadata.get('supportsPagination') or 
            (metadata.get('advancedQueryCapabilities')
             and metadata['advancedQueryCapabilities']['supportsPagination'])):
            # If the layer supports pagination, we can use
            # resultOffset/resultRecordCount to paginate

            return 'result offset'

        if metadata.get('supportsStatistics'):
            # If the layer supports statistics, we can request maximum
            # and minimum object ID to help build the pages
            oid_field_name = self.find_oid_field_name(metadata)

            try:
                (oid_min, oid_max) = self.get_layer_min_max(query_url,
                                                            oid_field_name)
                print(oid_min, oid_max)
                print(query_url)
                return 'where'
            except DownloadError:
                pass

        # If the layer does not support statistics, we can request
        # all the individual IDs and page through them one chunk at
        # a time.
        oid_data = self.get_layer_oids(query_url)
        if 'objectIds' in oid_data:
            return 'oid enumeration'


        # Failing all else, we can use the subdivision method
        return 'subdivision'
        

    def download(self, source_url, output_path, conform=None):
        query_fields = self.field_names_to_request(conform)
        metadata = self.get_layer_metadata(source_url)

        query_url = source_url + '/query'

        # Get the count of rows in the layer
        count_json = self.get_layer_feature_count(query_url)

        row_count = count_json.get('count')
        page_size = metadata.get('maxRecordCount', 500)
        if page_size > 1000:
            page_size = 1000

        oid_field_name = self.find_oid_field_name(metadata)

        _L.info("Source has {} rows".format(row_count))

        paginate_method = self.sniff_paginate_method(metadata, query_url)

        if paginate_method == 'result offset':
            pages = self.result_offset(query_url, query_fields,
                                       row_count, page_size)
            _L.info("Using resultOffset method")
        elif paginate_method == 'where':
            pages = self.where_pagination(query_url, query_fields,
                                          oid_field_name, page_size)
            _L.info("Using OID where clause method")
        elif paginate_method == 'oid enumaration':
            pages = self.oid_enumeration_pagination(query_url, query_fields)
            _L.info("Using OID enumeration method")
        else:
            pages = self.subdivide(query_url, query_fields, metadata, page_size)
            _L.info("Using subdivision method")


        with open_file(output_path, 'w') as f:
            f.write("""{
            "type": "FeatureCollection",
            "features": [\n""")

            start = True
            n_features = 0
            for data in pages:

                error = data.get('error')
                if error:
                    raise DownloadError("Problem querying ESRI dataset with args {}. Server said: {}".format(query_args, error['message']))

                geometry_type = data.get('geometryType')
                features = data.get('features')

                for feature in features:
                    if start:
                        start = False
                    else:
                        f.write(',\n')

                    attrs = feature['attributes']

                    oid = attrs.get(oid_field_name)

                    geom = feature['geometry']

                    f.write(json.dumps({
                        "type": "Feature",
                        "properties": attrs,
                        "geometry": esrijson2geojson(geometry_type, geom)
                    }))
                    n_features += 1
                    print(n_features)

            f.write("]\n}\n")

                        

@contextmanager
def open_file(path, mode):
    the_file = open(path, mode)
    try:
        yield the_file
    except:
        the_file.truncate()
        raise
    finally:
        the_file.close()
    
def esrijson2geojson(geom_type, esrijson):
    geojson = {}
    if geom_type == 'esriGeometryPolygon':
        geojson['type'] = 'Polygon'
        geojson['coordinates'] = esrijson['rings']
    elif geom_type == 'esriGeometryPolyline':
        geojson['type'] = 'MultiLineString'
        geojson['coordinates'] = esrijson['paths']
    elif geom_type == 'esriGeometryPoint':
        geojson['type'] = 'Point'
        geojson['coordinates'] = [esrijson['x'], esrijson['y']]
    else:
        print("I don't know how to convert esrijson of type '%s'." % geom_type)

    return geojson


def frange(start, stop=None, step=None):
    """Like range(), but returns list of floats instead

    All numbers are generated on-demand using generators
    """

    if stop is None:
        stop = float(start)
        start = 0.0

    if step is None:
        step = 1.0

    cur = float(start)

    while cur < stop:
        yield cur
        cur += step

def bboxes(bbox, cells_per_side):
    xmin, ymin, xmax, ymax = bbox

    x_step = (xmax - xmin) / cells_per_side
    y_step = (ymax - ymin) / cells_per_side

    for x in frange(xmin, xmax, x_step):
        for y in frange(ymin, ymax, y_step):
            bbox = (x, y, x + x_step, y + y_step)
            yield bbox
