import logging
import requests
import json
import socket
import time
from six.moves.urllib.parse import urlencode

from esridump import esri2geojson
from esridump.errors import EsriDownloadError
from esridump.state import DumperMode, DumperState, GeoQuery


def handle_esri_errors(response, logger, error_message, dont_throw_on_error_return):
    if response.status_code != 200:
        raise EsriDownloadError('{}: {} HTTP {} {}'.format(
            response.request.url,
            error_message,
            response.status_code,
            response.text,
        ))

    try:
        data = response.json()
    except:
        logger.error("Could not parse response from {} as JSON:\n\n{}".format(
            response.request.url,
            response.text,
        ))
        raise

    if dont_throw_on_error_return:
        return data

    error = data.get('error')
    if error:
        raise EsriDownloadError("{}: {} {}" .format(
            error_message,
            error['message'],
            ', '.join(error['details']),
        ))

    return data


def simple_requester(method, url, logger, timeout, error_message, dont_throw_on_error_return=True, **kwargs):
    try:
        logger.debug("%s %s, args %s", method, url, kwargs.get('params') or kwargs.get('data'))
        resp = requests.request(method, url, timeout=timeout, **kwargs)
    except requests.exceptions.SSLError:
        logger.warning("Retrying %s without SSL verification", url)
        resp = requests.request(method, url, timeout=timeout, verify=False, **kwargs)

    return handle_esri_errors(resp, logger, error_message, dont_throw_on_error_return)




class EsriDumper(object):
    def __init__(self, url, parent_logger=None,
                 extra_query_args=None, extra_headers=None,
                 timeout=None, fields=None, request_geometry=True,
                 outSR=None, proxy=None,
                 start_with=None, geometry_precision=None,
                 paginate_oid=False, max_page_size=None,
                 state=None, update_state=False,
                 requester=simple_requester, use_only_get=False,
                 json_arg='json',
                 pause_seconds=10, requests_to_pause=5,
                 num_of_retry=5, output_format='geojson'):
        self._layer_url = url
        self._query_params = extra_query_args or {}
        self._headers = extra_headers or {}
        self._http_timeout = timeout or 30
        self._fields = fields or None
        self._outSR = outSR or '4326'
        self._request_geometry = request_geometry
        self._proxy = proxy or None
        self._startWith = start_with or 0
        self._precision = geometry_precision or 7
        self._paginate_oid = paginate_oid
        self._max_page_size = max_page_size or 1000
        self._page_size = None
        self._state = state
        self._query_index = 1
        self._metadata = None
        self._update_state = update_state
        self._requester = requester
        self._use_only_get = use_only_get 
        self._json_arg = json_arg

        self._pause_seconds = pause_seconds
        self._requests_to_pause = requests_to_pause
        self._num_of_retry = num_of_retry

        if output_format not in ('geojson', 'esrijson'):
            raise ValueError(f'Invalid output format. Expecting "geojson" or "esrijson", got {output_format}')

        self._output_format = output_format

        if parent_logger:
            self._logger = parent_logger.getChild('esridump')
        else:
            self._logger = logging.getLogger('esridump')

    def _request(self, method, url, error_message, **kwargs):
        if method == 'POST' and self._use_only_get:
            method = 'GET'

        if method == 'POST':
            if 'params' in kwargs:
                kwargs['data'] = kwargs['params']
                del kwargs['params']
 
        if self._proxy:
            url = self._proxy + url
            params = kwargs.pop('params', None)
            if params:
                url += '?' + urlencode(params)
        return self._requester(method, url, self._logger, self._http_timeout, error_message, **kwargs)

    def _build_url(self, url=None):
        return self._layer_url + url if url else self._layer_url

    def _build_query_args(self, query_args=None):
        if query_args:
            complete_args = query_args
        else:
            complete_args = {}

        override_args = dict(**self._query_params)

        override_where = override_args.get('where')
        requested_where = query_args.get('where')
        if override_where and requested_where and requested_where != '1=1':
            # AND the where args together if the user is trying to override
            # the where param and we're trying to get 'all the rows'
            override_args['where'] = '({}) AND ({})'.format(
                requested_where,
                override_where,
            )

        complete_args.update(override_args)

        return complete_args

    def _build_headers(self, headers=None):
        complete_headers = dict(**self._headers)
        if headers:
            complete_headers.update(headers)
        return complete_headers


    def can_handle_pagination(self, query_fields):
        check_args = self._build_query_args({
            'resultOffset': 0,
            'resultRecordCount': 1,
            'where': '1=1',
            'returnGeometry': 'false',
            'outFields': ','.join(query_fields),
            'f': self._json_arg,
        })
        headers = self._build_headers()
        query_url = self._build_url('/query')

        try:
            data = self._request('POST', query_url,
                                 "Could not parse response from pagination check as JSON",
                                 dont_throw_on_error_return=True,
                                 headers=headers,
                                 params=check_args)
        except:
            return False

        return data.get('error') and data['error']['message'] != "Failed to execute query."

    def get_metadata(self):
        if self._metadata is not None:
            return self._metadata

        if self._state is not None:
            self._metadata = self._state.metadata
            return self._metadata

        query_args = self._build_query_args({
            'f': self._json_arg,
        })
        headers = self._build_headers()
        url = self._build_url()
        metadata_json = self._request('GET', url,
                                      "Could not retrieve layer metadata",
                                      params=query_args,
                                      headers=headers)
        self._metadata = metadata_json
        return metadata_json

    def get_page_size(self):
        if self._page_size is None:
            metadata = self.get_metadata()
            self._page_size = min(self._max_page_size, metadata.get('maxRecordCount', 500))
        return self._page_size

    def get_feature_count(self):
        query_args = self._build_query_args({
            'where': '1=1',
            'returnCountOnly': 'true',
            'f': self._json_arg,
        })
        headers = self._build_headers()
        url = self._build_url('/query')
        count_json = self._request('GET', url,
                                   "Could not retrieve row count",
                                   params=query_args,
                                   headers=headers)
        count = count_json.get('count')
        if count is None:
            raise EsriDownloadError("Server doesn't support returnCountOnly")
        return count_json['count']

    def _find_oid_field_name(self, metadata):
        oid_field_name = metadata.get('objectIdField')
        if not oid_field_name:
            for f in metadata['fields']:
                if f.get('type') == 'esriFieldTypeOID':
                    oid_field_name = f['name']
                elif f['name'].lower() == 'objectid':
                    oid_field_name = f['name']
                else:
                    break

        return oid_field_name

    def _get_layer_min_max(self, oid_field_name):
        """ Find the min and max values for the OID field. """
        query_args = self._build_query_args({
            'f': self._json_arg,
            'outFields': '',
            'outStatistics': json.dumps([
                dict(statisticType='min', onStatisticField=oid_field_name,
                     outStatisticFieldName='THE_MIN'),
                dict(statisticType='max', onStatisticField=oid_field_name,
                     outStatisticFieldName='THE_MAX'),
            ], separators=(',', ':'))
        })
        headers = self._build_headers()
        url = self._build_url('/query')

        metadata = self._request('GET', url,
                                 "Could not retrieve min/max oid values",
                                 params=query_args,
                                 headers=headers)

        # Some servers (specifically version 10.11, it seems) will respond with SQL statements
        # for the attribute names rather than the requested field names, so pick the min and max
        # deliberately rather than relying on the names.
        min_max_values = metadata['features'][0]['attributes'].values()
        min_value = min(min_max_values)
        max_value = max(min_max_values)
        query_args = self._build_query_args({
            'where': '{} = {} OR {} = {}'.format(
                oid_field_name,
                min_value,
                oid_field_name,
                max_value
            ),
            'returnIdsOnly': 'true',
            'f': self._json_arg,
        })
        headers = self._build_headers()
        url = self._build_url('/query')
        oid_data = self._request('GET', url,
                                 "Could not check min/max values",
                                 params=query_args,
                                 headers=headers)
        if not oid_data or not oid_data.get('objectIds') or min_value not in oid_data['objectIds'] or max_value not in oid_data['objectIds']:
            raise EsriDownloadError('Server returned invalid min/max')

        return (int(min_value), int(max_value))

    def _get_layer_oids(self):
        query_args = self._build_query_args({
            'where': '1=1',  # So we get everything
            'returnIdsOnly': 'true',
            'f': self._json_arg,
        })
        url = self._build_url('/query')
        headers = self._build_headers()
        oid_data = self._request('GET', url,
                                 "Could not retrieve object IDs",
                                 params=query_args,
                                 headers=headers)
        oids = oid_data.get('objectIds')
        if not oids:
            raise EsriDownloadError("Server doesn't support returnIdsOnly")
        return oids

    def _fetch_bounded_features(self, envelope):
        query_args = self._build_query_args({
            'geometry': json.dumps(envelope),
            'geometryType': 'esriGeometryEnvelope',
            'spatialRel': 'esriSpatialRelIntersects',
            'returnCountOnly': 'false',
            'returnIdsOnly': 'false',
            'returnGeometry': self._request_geometry,
            'outSR': self._outSR,
            'outFields': '*',
            'f': self._json_arg,
        })
        headers = self._build_headers()
        url = self._build_url('/query')
        features = self.run_query(url, headers, query_args, verb='GET')
        return features

    def _split_envelope(self, envelope):
        half_width = (envelope['xmax'] - envelope['xmin']) / 2.0
        half_height = (envelope['ymax'] - envelope['ymin']) / 2.0
        return [
            dict(
                xmin=envelope['xmin'],
                ymin=envelope['ymin'],
                xmax=envelope['xmin'] + half_width,
                ymax=envelope['ymin'] + half_height,
            ),
            dict(
                xmax=envelope['xmin'] + half_width,
                ymin=envelope['ymin'],
                xmin=envelope['xmax'],
                ymax=envelope['ymin'] + half_height,
            ),
            dict(
                xmin=envelope['xmin'],
                ymax=envelope['ymin'] + half_height,
                xmax=envelope['xmin'] + half_width,
                ymin=envelope['ymax'],
            ),
            dict(
                xmax=envelope['xmin'] + half_width,
                ymax=envelope['ymin'] + half_height,
                xmin=envelope['xmax'],
                ymin=envelope['ymax'],
            ),
        ]


    def _scrape_an_envelope(self, envelope, key):
        explored = self._state.params['explored_tree'].get(key, GeoQuery.NOT_PRESENT.name)
        explored = GeoQuery[explored]
        if explored == GeoQuery.EXPLORED:
            return

        max_records = self.get_page_size()
        if explored in [GeoQuery.OPEN, GeoQuery.NOT_PRESENT]:
            features = self._fetch_bounded_features(envelope)
            self._state.update(None, key, GeoQuery.OPEN)

            num_features = len(features)
            if num_features < max_records:
                for feature in features:
                    yield feature
                self._state.update(None, key, GeoQuery.EXPLORED)
                return

        self._logger.info(
            "Retrieved maximum record count or more records. Splitting this box and retrieving the children.")

        self._state.update(None, key, GeoQuery.SPLIT)
        envelopes = self._split_envelope(envelope)

        for i, child_envelope in enumerate(envelopes):
            new_key = f'{key}{i}'
            for feature in self._scrape_an_envelope(child_envelope, new_key):
                yield feature

        self._state.update(None, key, GeoQuery.EXPLORED)

    def _is_oid_field_returned(self, oid, oid_field_name, query_fields):
        query_args = self._build_query_args({
            'where': '{} = {}'.format(
                oid_field_name,
                oid,
            ),
            'outFields': ','.join(query_fields or ['*']),
            'returnGeometry': self._request_geometry,
            'outSR': self._outSR,
            'f': self._json_arg,
        })
        headers = self._build_headers()
        url = self._build_url('/query')
        data = self._request('POST', url,
                             f"unable to retrieve feature with {oid}",
                             params=query_args,
                             headers=headers)
        if data is None or data.get('features') is None or len(data.get('features')) != 1:
            raise EsriDownloadError('Unable to query for oid field')

        feature = data['features'][0]
        attrs = feature.get('attributes')
        if attrs is not None:
            oid_ret = attrs.get(oid_field_name)
            if oid_ret == oid:
                return True
        return False


    def pick_iteration_method(self):
        query_fields = self._fields
        metadata = self.get_metadata()

        row_count = None
        try:
            row_count = self.get_feature_count()
            if row_count == 0:
                return DumperMode.NO_DATA, (), None
        except EsriDownloadError:
            self._logger.info("Source does not support feature count")

        query_fields_pagination_support = True
        if not self._paginate_oid and row_count is not None and (metadata.get('supportsPagination') or
                                                                 (metadata.get('advancedQueryCapabilities') and metadata['advancedQueryCapabilities']['supportsPagination'])):
            # If the layer supports pagination, we can use resultOffset/resultRecordCount to paginate

            # There's a bug where some servers won't handle these queries in combination with a list of
            # fields specified. We'll make a single, 1 row query here to check if the server supports this
            # and switch to querying for all fields if specifying the fields fails.
            if query_fields and not self.can_handle_pagination(query_fields):
                self._logger.info(
                    "Source does not support pagination with fields specified, so querying for all fields.")
                query_fields_pagination_support = False
            return DumperMode.RESULT_OFFSET, (self._startWith, row_count, query_fields_pagination_support), None

        # If not, we can still use the `where` argument to paginate
        oid_field_name = self._find_oid_field_name(metadata)

        if not oid_field_name:
            raise EsriDownloadError(
                "Could not find object ID field name for deduplication")

        oid_field_returned = None
        if metadata.get('supportsStatistics'):
            # If the layer supports statistics, we can request maximum and minimum object ID
            # to help build the pages
            try:
                (oid_min, oid_max) = self._get_layer_min_max(oid_field_name)
                if self._update_state:
                    oid_field_returned = self._is_oid_field_returned(oid_min, oid_field_name, query_fields)
                if oid_field_returned == True or oid_field_returned is None:
                    return DumperMode.OID_WHERE_CLAUSE, (oid_field_name, oid_min - 1, oid_max), None
            except EsriDownloadError:
                self._logger.exception(
                    "Finding max/min from statistics failed. Trying OID enumeration.")

        try:
            oids = sorted(map(int, self._get_layer_oids()))
            if len(oids) == 0:
                return DumperMode.NO_DATA, (), None

            if self._update_state:
                if oid_field_returned is None:
                    oid_field_returned = self._is_oid_field_returned(oids[0], oid_field_name, query_fields)
            if oid_field_returned is not False:
                return DumperMode.OID_ENUMERATION, (oid_field_name, oids), None
        except EsriDownloadError:
            self._logger.info("Unable to get OID list, Falling back to geo queries", exc_info=True)

        if oid_field_returned is False:
            raise EsriDownloadError(
                "Object ID field not returned in queries for deduplication")
        # Use geospatial queries when none of the ID-based methods will work
        return DumperMode.GEO_QUERIES, (oid_field_name,), oid_field_returned
 
    def get_page_args(self, mode, rest):
        page_size = self.get_page_size()
        query_fields = self._fields
        page_args = []
        if mode is DumperMode.RESULT_OFFSET:
            start_with, row_count, query_fields_pagination_support = rest
            if not query_fields_pagination_support:
                query_fields = None
            for offset in range(start_with, row_count, page_size):
                query_args = self._build_query_args({
                    'resultOffset': offset,
                    'resultRecordCount': page_size,
                    'where': '1=1',
                    'geometryPrecision': self._precision,
                    'returnGeometry': self._request_geometry,
                    'outSR': self._outSR,
                    'outFields': ','.join(query_fields or ['*']),
                    'f': self._json_arg,
                })
                page_args.append(query_args)
        elif mode is DumperMode.OID_WHERE_CLAUSE:
            oid_field_name, done_till, oid_max = rest
            for page_min in range(done_till, oid_max, page_size):
                page_max = min(page_min + page_size, oid_max)
                query_args = self._build_query_args({
                    'where': '{} > {} AND {} <= {}'.format(
                        oid_field_name,
                        page_min,
                        oid_field_name,
                        page_max,
                    ),
                    'geometryPrecision': self._precision,
                    'returnGeometry': self._request_geometry,
                    'outSR': self._outSR,
                    'outFields': ','.join(query_fields or ['*']),
                    'f': self._json_arg,
                })
                page_args.append(query_args)
        elif mode is DumperMode.OID_ENUMERATION:
            oid_field_name, oids = rest
            for i in range(0, len(oids), page_size):
                oid_chunk = oids[i:i+page_size]
                page_min = oid_chunk[0]
                page_max = oid_chunk[-1]
                query_args = self._build_query_args({
                    'where': '{} >= {} AND {} <= {}'.format(
                        oid_field_name,
                        page_min,
                        oid_field_name,
                        page_max,
                    ),
                    'geometryPrecision': self._precision,
                    'returnGeometry': self._request_geometry,
                    'outSR': self._outSR,
                    'outFields': ','.join(query_fields or ['*']),
                    'f': self._json_arg,
                })
                page_args.append(query_args)
        else:
            raise Exception(f'Unexpected mode for prefetching queries: {mode.name}') 

        return page_args

    def run_query(self, query_url, headers, query_args, verb='POST'):
        download_exception = None
        data = None

        #  try to do a request "num_of_retry" to increase the probability of fetching data successfully
        for retry in range(self._num_of_retry):
            try:
                # pause every number of "requests_to_pause", that increase the probability for server response
                if self._query_index % self._requests_to_pause == 0:
                    time.sleep(self._pause_seconds)
                    self._logger.info(
                        "pause for %s seconds", self._pause_seconds)

                data = self._request(verb, query_url,
                                     "Could not retrieve this chunk of objects",
                                     headers=headers,
                                     params=query_args)
                # reset the exception state.
                download_exception = None
                # get out of retry loop, as the request succeeded
                break
            except socket.timeout as e:
                raise EsriDownloadError(
                    "Timeout when connecting to URL", e)
            except ValueError as e:
                raise EsriDownloadError("Could not parse JSON", e)
            except Exception as e:
                download_exception = EsriDownloadError(
                    "Could not connect to URL", e)
                # increase the pause time every retry, to increase the probability of fetching data successfully
                time.sleep(self._pause_seconds * (retry + 1))
                self._logger.info("retry pause {0}".format(retry))

        if download_exception:
            raise download_exception

        error = data.get('error')
        if error:
            raise EsriDownloadError("Problem querying ESRI dataset with args {}. Server said: {}".format(
                query_args, error['message']))

        self._query_index += 1
        features = data.get('features')
        return features


    def __iter__(self):
        metadata = self.get_metadata()
        if self._state is not None:
            mode = self._state.mode
            rest = self._state.get_required_info()
        else:
            mode, rest, oid_field_returned = self.pick_iteration_method()
            self._state = DumperState.get_state(mode, rest, metadata)

        if mode is DumperMode.NO_DATA:
            return

        if mode is DumperMode.GEO_QUERIES:
            #TODO: check exceededTransferLimit
            bounds = metadata['extent']
            for feature in self._scrape_an_envelope(bounds, "0"):
                if self._state.already_covered(feature):
                    continue
                self._state.update(feature)
                if self._output_format == 'geojson':
                    yield esri2geojson(feature)
                else:
                    yield feature
            return

        page_args = self.get_page_args(mode, rest)
        self._logger.info(
            "Built {} requests using {} method".format(len(page_args), mode.name))

        query_url = self._build_url('/query')
        headers = self._build_headers()
        for query_args in page_args:
            features = self.run_query(query_url, headers, query_args)
            for feature in features:
                if self._update_state:
                    #if self._state.already_covered(feature):
                    #    continue
                    self._state.update(feature)
                if self._output_format == 'geojson':
                    yield esri2geojson(feature)
                else:
                    yield feature
