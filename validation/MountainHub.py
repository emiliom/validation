from datetime import datetime
import time

import pandas as pd
import requests
import config

BASE_URL = 'https://api.mountainhub.com/timeline'
HEADER = { 'Accept-version': '1' }

def removeEmptyParams(dict):
    """Returns copy of dictionary with empty values removed.

    Keyword arguments:
    dict -- Dictionary to process
    """
    return { k:v for k, v in dict.items() if v is not None }

def dateToTimestamp(date):
    """Converts datetime object to unix timestamp.

    Keyword arguments:
    date -- Datetime object to convert
    """
    if date is None:
        return date
    return int(time.mktime(date.timetuple())) * 1000

def timestampToDate(timestamp):
    """Converts unix timestamp to datettime object.

    Keyword arguments:
    timestamp -- Timestamp to convert
    """
    if timestamp is None:
        return timestamp
    return datetime.fromtimestamp(timestamp / 1000)

def make_box(box):
    """Formats bounding box for use in MountainHub API.

    Keyword arguments:
    box -- Dictionary used to construct box
    """
    if box is None:
        return {}
    return {
        'north_east_lat': box['ymax'],
        'north_east_lng': box['xmax'],
        'south_west_lat': box['ymin'],
        'south_west_lng': box['xmin']
    }

def parse_snow(record):
    """Parses record returned by MountainHub API into standard format.

    Keyword arguments:
    record -- Segment of JSON returned by MountainHub API
    """
    obs = record['observation']
    actor = record['actor']
    details = obs.get('details', [{}])
    snow_depth = details[0].get('snowpack_depth') if len(details) > 0 and details[0] is not None else None
    # Remap record structure
    return {
        'author_name' : actor.get('full_name') or actor.get('fullName'),
        'id' : obs['_id'],
        'timestamp' : int(obs['reported_at']),
        'date' : timestampToDate(int(obs['reported_at'])),
        'lat' : obs['location'][1],
        'long' : obs['location'][0],
        'type' : obs['type'],
        'snow_depth' : float(snow_depth) if (snow_depth is not None and snow_depth != 'undefined')else None
    }

def snow_data(limit=100, start=None, end=None, box=None, filter=True):
    """Retrieves snow data from MountainHub API.

    Keyword arguments:
    limit -- Maximum number of records to return (default 100)
    start -- Start date to return results from
    end -- End date to return results from
    box -- Bounding box to restrict results,
    filter -- Flag indicating whether entries with no snow depth data should be filtered out
    """
    # Build API request
    params = removeEmptyParams({
        'publisher': 'all',
        'obs_type': 'snow_conditions',
        'limit': limit,
        'since': dateToTimestamp(start),
        'before': dateToTimestamp(end),
        **make_box(box)
    })

    # Make request
    response = requests.get(BASE_URL, params=params, headers=HEADER)
    data = response.json()

    if 'results' not in data:
        raise ValueError(data)

    # Parse request
    records = data['results']
    parsed = [ parse_snow(record) for record in records ]

    # Convert to dataframe and drop invalid results if necessary
    df = pd.DataFrame.from_records(parsed)
    if filter:
        df = df.dropna()
    return df
