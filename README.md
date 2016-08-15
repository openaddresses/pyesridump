esri-dump
=========

Scrapes an Esri REST endpoint and writes a GeoJSON file.

## Usage

### Command line

This module will install a command line utility called `esri2geojson` that accepts an Esri REST layer endpoint URL and a filename to write the output GeoJSON to:

```bash
esri2geojson http://cookviewer1.cookcountyil.gov/ArcGIS/rest/services/cookVwrDynmc/MapServer/11 cookcounty.geojson
```

You can write to `stdout` by using the special output filename of `-` (a single dash character).

You can also pass in the `--jsonlines` option to write newline-separated (`\n`) lines of GeoJSON features, which you can then pipe into other applications.

### Python module

You can use this module in your code to get GeoJSON Feature-shaped Python `dicts` into your code:

```python
import json
from esridump.dumper import EsriDumper

d = EsriDumper('http://example.com/arcgis/rest/services/Layer/MapServer/1')

# Iterate over each feature
for feature in d.iter():
    print(json.dumps(feature))

d = EsriDumper('http://example.com/arcgis/rest/services/Layer/MapServer/2')

# Or get all features in one list
all_features = d.get_all()
```

## Methodology

The module will do its best to find the most efficient method of retrieving data from the Esri server, given [the capabilities of the server](http://resources.arcgis.com/en/help/arcgis-rest-api/index.html#/Query_Feature_Service_Layer/02r3000000r1000000/). There are several strategies we use to get the data, described here in most to least efficient order:

### `resultOffset` Pagination

In ArcGIS REST API version 10.3, Esri added support for pagination directly with the `resultOffset` and `resultRecordCount` parameters. Unfortunately, most servers don't support this feature because the backend SQL engine must also be configured to support it. So far, it seems that only the Esri-hosted layers support this feature reliably.

### `objectId` Field Chunking

In ArcGIS REST API version 10.0, Esri added support for the server to return an exhaustive list of object IDs for all features in a layer. Once this list of object IDs is retrieved, we break it into chunks of `maxRecordCount` queries using the `objectIds` parameter.

### `objectId` Statistics `where`-clauses

In ArcGIS REST API version 10.1, Esri added support for performing various statistical queries on the server without requiring the client to download the whole dataset. On servers that support this and don't respond to the `objectIds` queries, we will use a minimum and maximum statistics query to find the minimum and maximum values for the `objectId` column, then build chunks of `where`-clauses that narrow the range down to `objectId`s between two fenceposts.

### Geometry Quadtree Queries

When a server does not support any of these methods, we'll make recursive quad-tree queries using bounding envelopes. We start with a query for the layer's entire `extent`. If the server returns exactly the `maxRecordCount` number of features, we split that `extent` into 4 equal rectangles and query those. If those smaller queries return `maxRecordCount` features, we split the rectangle again and continue until the server returns something less than the `maxRecordCount`.

## See Also
This Python module was extracted from OpenAddresses [`machine`](http://github.com/openaddresses/machine), which was inspired by code from [`koop`](https://github.com/koopjs/koop). A similar node/JavaScript module is available in [`esri-dump`](https://github.com/openaddresses/esri-dump).
