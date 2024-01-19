import json
from enum import Enum
from pprint import pformat

import jsonschema


class DumperStateMeta(type):
     def __call__(cls, mode, *args, **kwargs):
         if cls is DumperState:
             return mode.value(mode, *args, **kwargs)
         return type.__call__(cls, mode, *args, **kwargs)

class DumperState(metaclass=DumperStateMeta):
    __params_schema = None

    def __init__(self, mode, metadata,
                 params=None,
                 other_info=None,
                 **kwargs):
        self.mode = mode
        if params is None and other_info is None:
            raise Exception('one of params or other_info needs to be provided')
        if params is not None and other_info is not None:
            raise Exception("both params or other_info can't be be provided")

        if params is not None:
            self.params = params
            self.validate_params()
        else:
            self.get_params_from_info(other_info)
        self.metadata = metadata

    def encode(self):
        return json.dumps({
            'mode': self.mode.name,
            'metadata': self.metadata,
            'params': self.params
        })

    def get_params_from_info(self, other_info):
        raise NotImplementedError

    def already_covered(self, feature):
        raise NotImplementedError

    def update(self, feature, *args):
        raise NotImplementedError

    def decode(saved_str):
        data = json.loads(saved_str)
        mode = DumperMode[data['mode']]
        params = data['params']
        metadata = data['metadata']
        return DumperState(mode, metadata, params=params)

    def get_state(mode, rest, metadata, **kwargs):
        return DumperState(mode, metadata,
                           params=None,
                           other_info=rest,
                           **kwargs)

    def raise_validation_error(self, msg):
        raise Exception(f'For {self.mode.name}: {msg}')

    def validate_params(self):
        schema = self.__class__.__params_schema
        if schema is None:
            return

        try:
            jsonschema.validate(self.params, schema)
        except jsonschema.exceptions.ValidationError as ex:
            self.raise_validation_error(ex.message)

    def get_required_info(self):
        raise NotImplementedError

    def update_from_geojson(self, f):
        raise NotImplementedError

    def update_state_from_output_file(self, output_file):
        with open(output_file, 'r') as fp:
            for line in fp:
                f = json.loads(line.strip())
                self.update_from_geojson(f)

    def __str__(self):
        rep = f'<{self.mode.name}>\n'
        rep += 'metadata:\n'
        rep += f'{pformat(self.metadata)}\n'
        rep += 'params:\n'
        rep += f'{pformat(self.params)}\n'
        return rep

    def desc_short(self):
        rep = f'<{self.mode.name}>\n'
        return rep


class NoDataDumperState(DumperState):
    def validate_params(self):
        if len(self.params) != 0:
            self.raise_validation_error('params expected to be empty')

    def get_params_from_info(self, other_info):
        self.params = {}


class ResultOffsetDumperState(DumperState):
    __params_schema = {
        "type" : "object",
        "required": [ "row_count", "start_with", 'query_args_pagination_support' ],
        "properties": {
            "row_count": {
                "description": "number of records in the layer",
                "type": "integer",
                "minimum": 0
            },
            "start_with": {
                "description": "count of records already handled",
                "type": "integer",
                "minimum": 0
            },
            "query_args_pagination_support": {
                "description": "whether pagination is supported with query_args enabled",
                "type": "boolean"
            }
        }
    }

    def validate_params(self):
        super().validate_params()
        row_count = self.params['row_count']
        start_with = self.params['start_with']
        if start_with >= row_count:
            self.raise_validation_error(f'{start_with=} is expected to be smaller than {row_count=}')


    def get_params_from_info(self, other_info):
        self.params = {
            'start_with': other_info[0],
            'row_count': other_info[1],
            'query_args_pagination_support': other_info[2]
        }

    def already_covered(self, feature):
        return False

    def update(self, feature, *args):
        self.params['start_with'] += 1

    def update_state_from_output_file(self, output_file):
        with open(output_file, 'r') as fp:
            self.params['start_with'] = 0
            for line in fp:
                self.params['start_with'] += 1

    def get_required_info(self):
        return (self.params['start_with'], self.params['row_count'], self.params['query_args_pagination_support'])

    def desc_short(self):
        desc = super().desc_short()
        desc += f'params: < {self.params} >\n'
        return desc


class OIDWhereClauseDumperState(DumperState):
    __params_schema = {
        "type" : "object",
        "required": [ "oid_field_name", "oid_min", "oid_max", "done" ],
        "properties": {
            "oid_field_name": {
                "description": "name of the oid field",
                "type": "string",
            },
            "oid_min": {
                "description": "minimum value of the oid field",
                "type": "integer",
            },
            "oid_max": {
                "description": "maximum value of the oid field",
                "type": "integer",
            },
            "done": {
                "description": "oid field values already seen",
                "type": "array",
                "items": {
                    "type": "integer"
                }
            }
        }
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._done = set(self.params['done'])
        if len(self._done):
            self._done_till = max(self._done)
        else:
            self._done_till = self.params['oid_min'] - 1

    def validate_params(self):
        super().validate_params()
        oid_min = self.params['oid_min']
        oid_max = self.params['oid_max']
        done = self.params['done']
        if oid_min > oid_max:
            self.raise_validation_error(f'{oid_min=} is expected to be smaller than {oid_max=}')
        greater = [ oid for oid in done if oid > oid_max ]
        lesser  = [ oid for oid in done if oid < oid_min ]

        if len(greater):
            self.raise_validation_error(f'some values in done are greater than {oid_max=}: {greater}')
        if len(lesser):
            self.raise_validation_error(f'some values in done are lesser than {oid_min=}: {lesser}')

    def get_params_from_info(self, other_info):
        oid_field_name, done_till, oid_max = other_info 
        self.params = {
            'oid_field_name': oid_field_name,
            'oid_min': done_till + 1,
            'oid_max': oid_max,
            'done': []
        }

    def already_covered(self, feature):
        oid_field_name = self.params['oid_field_name']
        oid = feature['attributes'][oid_field_name]
        return oid in self._done

    def update(self, feature, *args):
        oid_field_name = self.params['oid_field_name']
        oid = feature['attributes'][oid_field_name]
        self.params['done'].append(oid)
        self._done.add(oid)
        if oid > self._done_till:
            self._done_till = oid

    def update_from_geojson(self, f):
        oid_field_name = self.params['oid_field_name']
        oid = f['properties'][oid_field_name]
        self.params['done'].append(oid)
        self._done.add(oid)
        if oid > self._done_till:
            self._done_till = oid

    def get_required_info(self):
        return (self.params['oid_field_name'], self._done_till, self.params['oid_max'])

    def __str__(self):
        rep = super().__str__()
        rep += f'done_till: {self._done_till}'
        return rep

    def desc_short(self):
        desc = super().desc_short()
        desc += f'params: < oid_field_name={self.params["oid_field_name"]}, oid_min={self.params["oid_min"]},\
                            oid_max={self.params["oid_max"]}, done_till={self._done_till},\
                            done_count={len(self.params["done"])} >'
        return desc


class OIDEnumerationDumperState(DumperState):
    __params_schema = {
        "type" : "object",
        "required": [ "oid_field_name", "all_oids", "done" ],
        "properties": {
            "oid_field_name": {
                "description": "name of the oid field",
                "type": "string",
            },
            "all_oids": {
                "description": "all the oid_field values in the layer",
                "type": "array",
                "items": {
                    "type": "integer"
                }
            },
            "done": {
                "description": "oid_field values already seen",
                "type": "array",
                "items": {
                    "type": "integer"
                }
            }
        }
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._done = set(self.params['done'])

    @property
    def oids_left(self):
        return [ oid for oid in self.params['all_oids'] if oid not in self._done ]

    def validate_params(self):
        super().validate_params()
        # TODO: is this really needed?
        all_oids_set = set(self.params['all_oids'])
        done_set = set(self.params['done'])
        extra_in_done = done_set - all_oids_set
        if len(extra_in_done):
            self.raise_validation_error(f'there are some oids in done set which are not in the oid list: {extra_in_done=}')
        
    def get_params_from_info(self, other_info):
        oid_field_name, oids = other_info
        self.params = {
            'oid_field_name': oid_field_name,
            'all_oids': oids,
            'done': []
        }

    def already_covered(self, feature):
        oid_field_name = self.params['oid_field_name']
        oid = feature['attributes'][oid_field_name]
        return oid in self._done

    def update(self, feature, *args):
        oid_field_name = self.params['oid_field_name']
        oid = feature['attributes'][oid_field_name]
        self.params['done'].append(oid)
        self._done.add(oid)
        
    def update_from_geojson(self, f):
        oid_field_name = self.params['oid_field_name']
        oid = f['properties'][oid_field_name]
        self.params['done'].append(oid)
        self._done.add(oid)
 
    def get_required_info(self):
        return (self.params['oid_field_name'], self.oids_left)

    def desc_short(self):
        desc = super().desc_short()
        desc += f'params: < oid_field_name={self.params["oid_field_name"]}, \
                            all_oids_count={len(self.params["all_oids"])}, \
                            done_count={len(self.params["done"])} >'
        return desc


class GeoQuery(Enum):
    NOT_PRESENT = 0
    OPEN = 1
    SPLIT = 2
    EXPLORED = 3

class GeoQueryDumperState(DumperState):
    __params_schema = {
        "type" : "object",
        "required": [ "oid_field_name", "explored_tree", "done" ],
        "properties": {
            "oid_field_name": {
                "description": "name of the oid field",
                "type": "string",
            },
            "explored_tree": {
                "type": "object",
                "description": "bounds tree and their exploration status",
                "patternProperties": {
                    "^[0-3]+$": {
                        "type": "integer",
                        "minimum": 0,
                        "maximum": 3
                    }
                }
            },
            "id_type": {
                "type": "string",
                "description": "what is the type of id used in the 'done' array",
                "enum": ["oid", "hash"]
            },
            "done": {
                "description": "oid_field values already seen",
                "type": "array",
                "items": {
                    "type": "integer"
                }
            }
        }
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._done = set(self.params['done'])

    def get_params_from_info(self, other_info):
        self.params = {
            'oid_field_name': other_info[0],
            'explored_tree': {},
            'done': []
        }

    def get_required_info(self):
        return (self.params['oid_field_name'],)

    def already_covered(self, feature):
        oid_field_name = self.params['oid_field_name']
        val = feature['attributes'][oid_field_name]
        return val in self._done

    def update_explored(self, key, val):
        self.params['explored_tree'][key] = val.name
        if val == GeoQuery.EXPLORED:
            all_keys = list(self.params['explored_tree'].keys())
            for k in all_keys:
                if key == k:
                    continue
                if k.startswith(key):
                    del self.params['explored_tree'][k]
 
    def update(self, feature, *args):
        if feature is None:
            self.update_explored(args[0], args[1])
            return
        oid_field_name = self.params['oid_field_name']
        oid = feature['attributes'][oid_field_name]
        self.params['done'].append(oid)
        self._done.add(oid)

    def update_from_geojson(self, f):
        oid_field_name = self.params['oid_field_name']
        oid = f['properties'][oid_field_name]
        self.params['done'].append(oid)
        self._done.add(oid)
 
    def desc_short(self):
        desc = super().desc_short()
        #TODO: add explored tree depth
        desc += f'params: < oid_field_name={self.params["oid_field_name"]}, \
                            done_count={len(self.params["done"])} >'
        return desc



class DumperMode(Enum):
    NO_DATA = NoDataDumperState
    RESULT_OFFSET = ResultOffsetDumperState
    OID_WHERE_CLAUSE = OIDWhereClauseDumperState
    OID_ENUMERATION = OIDEnumerationDumperState
    GEO_QUERIES = GeoQueryDumperState
