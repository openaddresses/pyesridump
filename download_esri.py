import requests
import json
from shapely.geometry import MultiPolygon
import shapely.speedups

base_url = 'http://rest.lakecountyil.gov/ArcGIS/rest/services/MapsOnline_Public/MapServer/6/query'

sr = 102100
fields = 'OBJECTID,PLA_NUMBER,PLA_NUMSUF,PLA_DIRECT,PLA_NAME,PLA_TYPE,PLA_SUFFIX'
min_x = -9818339.8047
max_x = -9769252.5764
min_y = 5183812.7058
max_y = 5235532.6064

cells_x = 50
cells_y = 50

output_file = 'lake_county_addrs.osm'

x_step = (max_x - min_x) / cells_x
y_step = (max_y - min_y) / cells_y

def xfrange(start, stop=None, step=None):
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

road_types = {
    'ALY': 'Alley',
    'AVE': 'Avenue',
    'BLVD': 'Boulevard',
    'BND': 'Bend',
    'CIR': 'Circle',
    'CRES': 'Crescent',
    'CT': 'Court',
    'CV': 'Cove',
    'DR': 'Drive',
    'FLDS': 'Fields',
    'HWY': 'Highway',
    'IS': 'Island',
    'LN': 'Lane',
    'PARK': 'Park',
    'PASS': 'Pass',
    'PATH': 'Path',
    'PKWY': 'Parkway',
    'PL': 'Place',
    'PLZ': 'Plaza',
    'PT': 'Point',
    'RD': 'Road',
    'RDG': 'Ridge',
    'ROW': 'Row',
    'RUN': 'Run',
    'SQ': 'Square',
    'ST': 'Street',
    'TER': 'Terrace',
    'TRL': 'Trail',
    'VW': 'View',
    'WAY': 'Way',
    'XING': 'Crossing',
}

dirs = {
    'N': 'North',
    'NE': 'Northeast',
    'NW': 'Northwest',
    'W': 'West',
    'E': 'East',
    'S': 'South',
    'SE': 'Southeast',
    'SW': 'Southwest',
}

def to_osm_tags(attrs):
    if not (attrs and attrs['PLA_NUMBER'] and attrs['PLA_NUMBER'] != '0' and attrs['PLA_NUMBER'] != ' '):
        return None

    house_num = attrs['PLA_NUMBER'].strip()
    house_suffix = attrs.get('PLA_NUMSUF')
    if house_suffix and house_suffix != ' ':
        house_num += ' ' + house_suffix

    direction = None
    if attrs['PLA_DIRECT'] and attrs['PLA_DIRECT'] != ' ':
        direction = dirs[attrs['PLA_DIRECT']]

    street = attrs['PLA_NAME'].strip().title()

    street_type = None
    if attrs['PLA_TYPE'] and attrs['PLA_TYPE'] != ' ':
        street_type = road_types[attrs['PLA_TYPE']]

    street_suffix = None
    if attrs['PLA_SUFFIX'] and attrs['PLA_SUFFIX'] != ' ':
        street_suffix = dirs[attrs['PLA_SUFFIX']]

    streetname = []
    if direction:
        streetname.append(direction)
    streetname.append(street)
    if street_type:
        streetname.append(street_type)
    if street_suffix:
        streetname.append(street_suffix)
    streetname = ' '.join(streetname)

    tags = {
        'addr:housenumber': house_num,
        'addr:street': streetname,
        'addr:street:name': street,
        'addr:street:type': street_type,
    }
    if direction:
        tags['addr:street:prefix'] = direction
    return tags

shapely.speedups.enable()

saved = set()
node_id = -1
i = 0

f = open(output_file, 'w')
f.write('<osm version="0.6">\n')
for x in xfrange(min_x, max_y, x_step):
    for y in xfrange(min_y, max_y, y_step):
        bbox = (x, y, x + x_step, y + y_step)

        geometry = json.dumps({
            "rings": [
                [
                    [bbox[0], bbox[1]],
                    [bbox[0], bbox[3]],
                    [bbox[2], bbox[3]],
                    [bbox[2], bbox[1]],
                    [bbox[0], bbox[1]]
                ]
            ]
        })

        args = {
            'geometry': geometry,
            'geometryType': 'esriGeometryPolygon',
            'inSR': sr,
            'spatialRel': 'esriSpatialRelIntersects',
            'returnCountOnly': 'false',
            'returnIdsOnly': 'false',
            'returnGeometry': 'true',
            'outSR': 4326,
            'outFields': fields,
            'f': 'json'
        }

        resp = requests.get(base_url, params=args)
        for feature in resp.json()['features']:
            attrs = feature['attributes']

            oid = int(attrs['OBJECTID'])

            if oid in saved:
                continue

            geom = feature['geometry']
            outer = geom['rings'][0]
            inners = geom['rings'][1:]
            shape = MultiPolygon([(outer, inners)])

            try:
                tags = to_osm_tags(attrs)
            except KeyError, e:
                print "%s %s" % (shape.centroid, attrs)
                raise e

            if not tags:
                continue

            f.write('<node id="%s" lat="%0.7f" lon="%0.7f" visible="true">\n' % (node_id, shape.centroid.y, shape.centroid.x))
            for (k,v) in tags.iteritems():
                f.write(' <tag k="%s" v="%s"/>\n' % (k, v))
            f.write('</node>\n')
            saved.add(oid)
            node_id = node_id - 1
        i += 1
        print "%s/%s done" % (i, (cells_x * cells_y))
f.write('</osm>\n')
