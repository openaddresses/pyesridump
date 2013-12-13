import requests
import json

base_url = 'http://gisweb.co.aitkin.mn.us/arcgis/rest/services/MapLayers/MapServer/3'
output_file = 'output.geojson'

metadata = requests.get(base_url, params={'f': 'json'}).json()
bounds = metadata['extent']
fields = metadata['fields']
geom_type = metadata['geometryType']
saved = set()

bbox_file = open('bboxes.geojson', 'w')
bbox_file.write("""{
    "type": "FeatureCollection",
    "features": [\n""")

# Look for a field that to use as the deduping ID
oid_field = next(field['name'] for field in fields if field['type'] == 'esriFieldTypeOID')

if oid_field:
    print "Using '%s' as the OID field to dedupe." % oid_field
else:
    print "WARNING: Couldn't find the OID field to dedupe on, so you'll have duplicate data probably."

cells_x = 3
cells_y = 3
total_cells = cells_x * cells_y
x_step = (bounds['xmax'] - bounds['xmin']) / cells_x
y_step = (bounds['ymax'] - bounds['ymin']) / cells_y

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
        print "I don't know how to convert esrijson of type '%s'." % geom_type

    return geojson

def fetch_features(url, bounds):

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

    args = {
        'geometry': geometry,
        'geometryType': 'esriGeometryPolygon',
        'spatialRel': 'esriSpatialRelIntersects',
        'returnCountOnly': 'false',
        'returnIdsOnly': 'false',
        'returnGeometry': 'true',
        'outSR': 4326,
        'outFields': '*',
        'f': 'json'
    }

    resp = requests.get(base_url + '/query', params=args)
    return resp.json()['features']

def write_features(features, saved):
    for feature in features:
        attrs = feature['attributes']

        oid = attrs.get(oid_field)

        if oid in saved:
            continue

        geom = feature['geometry']

        f.write(json.dumps({
            "type": "Feature",
            "properties": attrs,
            "geometry": esrijson2geojson(geom_type, geom)
        }))
        f.write(',\n')

        saved.add(oid)

def split_bbox(bbox):
    (x1, y1, x2, y2) = bbox
    half_width = (x2 - x1) / 2.0
    half_height = (y2 - y1) / 2.0
    return [
        (x1,                y1,                 x1 + half_width,    y1 + half_height),
        (x1 + half_width,   y1,                 x2,                 y1 + half_height),
        (x1,                y1 + half_height,   x1 + half_width,    y2),
        (x1 + half_width,   y1 + half_height,   x2,                 y2),
    ]

def scrape_a_bbox(bbox, saved):
    features = fetch_features(base_url, bbox)

    if len(features) == metadata['maxRecordCount']:
        print "Retrieved exactly the maximum record count. Splitting this box and retrieving the children."

        bboxes = split_bbox(bbox)

        for child_bbox in bboxes:
            scrape_a_bbox(child_bbox, saved)
    else:
        bbox_file.write(json.dumps({
            "type": "Feature",
            "properties": {},
            "geometry": {
                "type": "Polygon",
                "coordinates": [[
                    [bbox[0], bbox[1]],
                    [bbox[0], bbox[3]],
                    [bbox[2], bbox[3]],
                    [bbox[2], bbox[1]],
                    [bbox[0], bbox[1]]
                ]]
            }
        }))
        bbox_file.write(',\n')

        write_features(features, saved)

i = 0

f = open(output_file, 'w')
f.write("""{
    "type": "FeatureCollection",
    "features": [\n""")

for x in xfrange(bounds['xmin'], bounds['xmax'], x_step):
    for y in xfrange(bounds['ymin'], bounds['ymax'], y_step):
        bbox = (x, y, x + x_step, y + y_step)

        scrape_a_bbox(bbox, saved)

        i += 1
        print "%s/%s cells, %s features." % (i, total_cells, len(saved))

f.write("]\n}\n")

bbox_file.write("]\n}\n")
