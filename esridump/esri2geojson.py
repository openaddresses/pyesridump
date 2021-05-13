from itertools import tee
from functools import partial
from shapely.geometry import shape, mapping
from shapely.ops import transform
import pyproj

def esri2geojson(esrijson_feature, srid = 'epsg:4326'):
    response = dict(type="Feature", geometry=None, properties=None)

    geojson_geometry = convert_esri_geometry(esrijson_feature.get('geometry'))
    if geojson_geometry:
        if srid != 'epsg:4326':
            project = partial(
                pyproj.transform,
                pyproj.Proj(srid),
                pyproj.Proj('epsg:4326'),
            )

            geojson_geometry = mapping(transform(lambda x, y: (y, x), transform(project, shape(geojson_geometry))))

        response['geometry'] = geojson_geometry


    esri_attributes = esrijson_feature.get('attributes')
    if esri_attributes:
        response['properties'] = esri_attributes

    return response


def convert_esri_geometry(esri_geometry):
    if esri_geometry is None:
        return esri_geometry
    elif 'x' in esri_geometry or 'y' in esri_geometry:
        return convert_esri_point(esri_geometry)
    elif 'points' in esri_geometry:
        return convert_esri_multipoint(esri_geometry)
    elif 'paths' in esri_geometry:
        return convert_esri_polyline(esri_geometry)
    elif 'rings' in esri_geometry:
        return convert_esri_polygon(esri_geometry)

def convert_esri_point(esri_geometry):
    x_coord = esri_geometry.get('x')
    y_coord = esri_geometry.get('y')

    if x_coord and y_coord:
        return {
            "type": "Point",
            "coordinates": [x_coord, y_coord]
        }
    else:
        return None

def convert_esri_multipoint(esri_geometry):
    points = esri_geometry.get('points')

    if len(points) == 1:
        return {
            "type": "Point",
            "coordinates": points[0]
        }
    else:
        return {
            "type": "MultiPoint",
            "coordinates": points
        }

def convert_esri_polyline(esri_geometry):
    paths = esri_geometry.get('paths')

    if len(paths) == 1:
        return {
            "type": "LineString",
            "coordinates": paths[0]
        }
    else:
        return {
            "type": "MultiLineString",
            "coordinates": paths
        }

def convert_esri_polygon(esri_geometry):
    rings = esri_geometry.get('rings')

    def ensure_closed_ring(ring):
        first = ring[0]
        last = ring[-1]

        if first != last:
            # Trickery here to not modify the passed-in list
            ring = list(ring)
            ring.append(ring[0])

        return ring

    def is_valid_ring(ring):
        return not (len(ring) == 3 and ring[0] == ring[2])

    clean_rings = [
        ensure_closed_ring(ring)
        for ring in filter(is_valid_ring, rings)
    ]

    if len(clean_rings) == 1:
        return {
            "type": "Polygon",
            "coordinates": clean_rings
        }
    elif len(clean_rings) == 0:
        return None
    else:
        return decode_polygon(clean_rings)

def decode_polygon(esri_rings):
    coords = []
    outer_ring_index = -1

    for ring in esri_rings:
        try:
            if ring_is_clockwise(ring):
                coords.append([ring])
                outer_ring_index += 1
            else:
                coords[outer_ring_index].append(ring)
        except IndexError:
            # Skip over rings that are in an unexpected order
            continue

    if len(coords) == 1:
        return {
            "type": "Polygon",
            "coordinates": coords[0]
        }
    else:
        return {
            "type": "MultiPolygon",
            "coordinates": coords
        }

def ring_is_clockwise(ring):
    """
    Determine if polygon ring coordinates are clockwise. Clockwise signifies
    outer ring, counter-clockwise an inner ring or hole. this logic was found
    at http://stackoverflow.com/questions/1165647/how-to-determine-if-a-list-of-polygon-points-are-in-clockwise-order
    this code taken from http://esri.github.com/geojson-utils/src/jsonConverters.js by James Cardona (MIT lisense)
    """
    total = 0
    for (pt1, pt2) in pairwise(ring):
        total += (pt2[0] - pt1[0]) * (pt2[1] + pt1[1])
    return total >= 0

def pairwise(iterable):
    "s -> (s0,s1), (s1,s2), (s2, s3), ..."
    a, b = tee(iterable)
    next(b, None)
    return zip(a, b)
