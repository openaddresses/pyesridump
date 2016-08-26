def esri2geojson(esrijson_feature):
    response = dict(type="Feature", geometry=None, properties=None)

    geojson_geometry = convert_esri_geometry(esrijson_feature.get('geometry'))
    if geojson_geometry:
        response['geometry'] = geojson_geometry

    esri_attributes = esrijson_feature.get('attributes')
    if esri_attributes:
        response['properties'] = esri_attributes

    return response

def convert_esri_geometry(esri_geometry):
    if 'x' in esri_geometry or 'y' in esri_geometry:
        return convert_esri_point(esri_geometry)
    elif 'points' in esri_geometry:
        return convert_esri_multipoint(esri_geometry)
    elif 'paths' in esri_geometry:
        return convert_esri_polyline(esri_geometry)
    elif 'rings' in esri_geometry:
        return convert_esri_polygon(esri_geometry)
    elif esri_geometry is None:
        return esri_geometry

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
    return {
        "type": "MultiPoint",
        "coordinates": [
            point for point in esri_geometry['points']
        ]
    }

def convert_esri_polyline(esri_geometry):
    paths = esri_geometry.get('paths')

    if len(paths) == 1:
        return {
            "type": "LineString",
            "coordinates": [
                point for point in paths[0]
            ]
        }
    else:
        return {
            "type": "MultiLineString",
            "coordinates": [
                [
                    point for point in path
                ]
                for path in paths
            ]
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
            "coordinates": [
                [
                    point for point in clean_rings[0]
                ]
            ]
        }
    elif len(clean_rings) == 0:
        return None
    else:
        return {
            "type": "MultiPolygon",
            "coordinates": [
                [
                    point for point in ring
                ]
                for ring in clean_rings
            ]
        }
