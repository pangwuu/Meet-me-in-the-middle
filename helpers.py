from flask import Flask
from flask_sqlalchemy import SQLAlchemy
import os
import googlemaps
from typing import List
import json
from geopy.distance import distance
import math, random
import urllib.parse


app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///meetingpoints.db'
db = SQLAlchemy(app)

# APIKEY
GOOG_API_KEY = os.environ.get("GOOG_API_KEY")

# Initialize Google Maps client
gmaps = googlemaps.Client(key=GOOG_API_KEY)

# Models
class Meeting(db.Model):
    """
    Holds a meeting object, which stores both locations, 
    both forms of transport, as well as an oprional meeting point and place type
    both forms of transport, as well as an oprional meeting point and place type
    """
    id = db.Column(db.Integer, primary_key=True)
    location_a = db.Column(db.String(100))
    location_b = db.Column(db.String(100))
    mode_a = db.Column(db.String(20))
    mode_b = db.Column(db.String(20))
    meeting_point = db.Column(db.String(100))
    place_type = db.Column(db.String(50))

class Place:
    def __init__(self, name: str, address: str, rating: float, total_ratings: int, business_image_link: str, time_from_a: int, time_from_b: int, embed_link: str, latitude: float, longitude: float):
        self.name = name
        self.address = address
        self.rating = rating
        self.total_ratings = total_ratings
        # This can potentially be empty - think of the consequences
        self.business_image_link = business_image_link
        
        # Get the time from this location from location a and location b
        self.time_from_a = time_from_a
        self.time_from_b = time_from_b
        self.embed_link = embed_link
        
        # Add latitude and longitude
        self.latitude = latitude
        self.longitude = longitude

    def __repr__(self):
        return (f"Place(name={self.name}, address={self.address}, rating={self.rating}, "
                f"total_ratings={self.total_ratings}, business_image_link={self.business_image_link}, "
                f"time_from_a={self.time_from_a}, time_from_b={self.time_from_b}, "
                f"latitude={self.latitude}, longitude={self.longitude})")

# Helper functions
def geocode(address):
    """
    Geocodes one address (string) into a set of coordinates
    
    Returns a string of lattitude and longitude
    """
    result = gmaps.geocode(address)
    if result:
        location = result[0]['geometry']['location']
        return f"{location['lat']},{location['lng']}"
    return None

def get_midpoints(coord_a, coord_b, num_points=5):
    """
    Returns num_points (5 as default) points equidistant to each other,
    along the way from coord_a and coord_b.

    This does NOT use any APIs and is a straight line distance, like ratio division.

    Params:
        coord_a, coord_b (str): The locations you wish to find the midpoints from
    
    Returns:
        midpoints (List[str]): A list of midpoints each consisting of a
        string that contain the lattitude and longitude of each location
    """
    lat_a, lng_a = map(float, coord_a.split(','))
    lat_b, lng_b = map(float, coord_b.split(','))
    
    midpoints = []
    for i in range(1, num_points + 1):
        ratio = i / (num_points + 1)
        lat_m = lat_a + ratio * (lat_b - lat_a)
        lng_m = lng_a + ratio * (lng_b - lng_a)
        midpoints.append(f"{lat_m},{lng_m}")
    
    return midpoints

def get_sq_midpoints(coord_a, coord_b, num_points=10):
    """
    Returns num_points (10 as default) points equidistant to each other, 
    along the way from 25% to 75% of the route between coord_a and coord_b.

    This does NOT use any APIs and is a straight line distance, like ratio division.

    Params:
        coord_a, coord_b (str): The locations you wish to find the midpoints from
    
    Returns:
        midpoints (List[str]): A list of midpoints each consisting of a
        string that contains the latitude and longitude of each location
    """
    lat_a, lng_a = map(float, coord_a.split(','))
    lat_b, lng_b = map(float, coord_b.split(','))
    
    midpoints = []
    start_ratio = 0.25
    end_ratio = 0.75
    
    for i in range(1, num_points + 1):
        # Calculate the ratio within the specified range (25% to 75%)
        ratio = start_ratio + (end_ratio - start_ratio) * (i / (num_points + 1))
        lat_m = lat_a + ratio * (lat_b - lat_a)
        lng_m = lng_a + ratio * (lng_b - lng_a)
        midpoints.append(f"{lat_m},{lng_m}")
    
    return midpoints

def find_best_midpoint(coord_a, coord_b, midpoints, mode_a, mode_b):
    """
    Returns the midpoint that minimises the travel time difference from both coordinates.

    Args:
        coord_a (str): Coordinates of the first location
        coord_b (str): Coordinates of the second location
        midpoints (List[str]): A set of points between coord_a and coord_b.
        Usually obtained from get_midpoints
        mode_a, mode_b (str): Transport modes for both people. Valid options are "driving",
        "bicycling", "walking" and "transit"
    """
    
    # Distance matrix code found here:
    # https://github.com/googlemaps/google-maps-services-python/blob/master/googlemaps/distance_matrix.py
    matrix_a = gmaps.distance_matrix(origins=[coord_a], destinations=midpoints, mode=mode_a)
    matrix_b = gmaps.distance_matrix(origins=[coord_b], destinations=midpoints, mode=mode_b)
    
    min_diff = float('inf')
    best_midpoint = None
    
    for i, midpoint in enumerate(midpoints):
        element_a = matrix_a['rows'][0]['elements'][i]
        element_b = matrix_b['rows'][0]['elements'][i]
        if element_a['status'] == 'OK':
            time_a = element_a['duration']['value']
        else:
            continue
        if element_b['status'] == 'OK':
            time_b = element_b['duration']['value']
        else:
            continue

        diff = abs(time_a - time_b)
        
        if diff < min_diff:
            min_diff = diff
            best_midpoint = midpoint
    
    return best_midpoint
    
def find_nearby_places(location, place_type, radius=100, max_results=3):
    """
    Returns a group of max_results nearby places to a certain coordinate.

    Returns a list of json data which can be parsd using the parse_places module
    """
    places = gmaps.places_nearby(location=location, radius=radius, type=place_type)
    results = places.get('results', [])
    
    while len(results) < max_results and radius <= 1600:
        radius *= 2
        places = gmaps.places_nearby(location=location, radius=radius, type=place_type)
        results.extend(places.get('results', []))
        results = list({place['place_id']: place for place in results}.values())  # Remove duplicates
    
    return {"results": results[:max_results]}

def get_place_photo_url(photo_reference, max_width=300, max_height=200):
    base_url = "https://maps.googleapis.com/maps/api/place/photo"
    params = {
        "maxwidth": max_width,
        "maxheight": max_height,
        "photoreference": photo_reference,
        "key": GOOG_API_KEY
    }
    return f"{base_url}?{urllib.parse.urlencode(params)}"

def get_business_image(place_data):
    '''
    From a place's data, returns an image link for the place
    '''
    if place_data.get('photos'):
        photo_reference = place_data['photos'][0]['photo_reference']
        return get_place_photo_url(photo_reference)
    return None

def get_travel_times_matrix(a, b, m_list, mode_a, mode_b):
    """
    Calculate travel times from points A and B to multiple midpoints M using specified modes of transport.
    
    :param a: Starting point A (string address or lat,lng)
    :param b: Starting point B (string address or lat,lng)
    :param m_list: List of midpoints M (list of string addresses or lat,lng)
    :param mode_a: Mode of transport from A to M (string: 'driving', 'walking', 'bicycling', or 'transit')
    :param mode_b: Mode of transport from B to M (string: 'driving', 'walking', 'bicycling', or 'transit')
    :return: Two lists of travel times in seconds (times_a_to_m, times_b_to_m)
    """
    # Step 1: Geocode all addresses
    geocoded_a = geocode(a)
    geocoded_b = geocode(b)
    geocoded_m_list = [geocode(m) for m in m_list]

    # Step 2: Use Distance Matrix API for A to all M
    matrix_a = gmaps.distance_matrix(
        origins=[geocoded_a],
        destinations=geocoded_m_list,
        mode=mode_a
    )

    # Step 3: Use Distance Matrix API for B to all M
    matrix_b = gmaps.distance_matrix(
        origins=[geocoded_b],
        destinations=geocoded_m_list,
        mode=mode_b
    )

    # Step 4: Extract travel times
    times_a_to_m = []
    times_b_to_m = []

    for i in range(len(geocoded_m_list)):
        element_a = matrix_a['rows'][0]['elements'][i]
        element_b = matrix_b['rows'][0]['elements'][i]

        # Check if a route was found
        if element_a['status'] == 'OK':
            times_a_to_m.append(element_a['duration']['value'])
        else:
            times_a_to_m.append(None)  # or you could use a large number like float('inf')

        if element_b['status'] == 'OK':
            times_b_to_m.append(element_b['duration']['value'])
        else:
            times_b_to_m.append(None)  # or you could use a large number like float('inf')

    return times_a_to_m, times_b_to_m

def get_embed_link(lat, lng):
    return f"https://www.google.com/maps/embed/v1/place?q={lat},{lng}&key={GOOG_API_KEY}"

def create_embed_link_from_place(place_name):
    return f"https://www.google.com/maps/embed/v1/place?q={place_name.replace(' ', '+')}&key={GOOG_API_KEY}"


def parse_places(json_data: str) -> List[Place]:
    """
    Function to parse JSON and create Place objects out of each of them.
    """
    places = []
    
    # Parse the JSON data
    data = json.dumps(json_data)
    data = json.loads(data)
    
    # Extract places list
    results = data.get('results', [])
    
    # Create Place objects for each result
    for result in results:
        name = result.get('name')
        address = result.get('vicinity')
        rating = result.get('rating', 0.0)  # Default to 0.0 if not available
        total_ratings = result.get('user_ratings_total', 0)  # Default to 0 if not available
        link = get_business_image(result)
        
        # Extract latitude and longitude
        location = result.get('geometry', {}).get('location', {})
        latitude = location.get('lat', 0.0)  # Default to 0.0 if not available
        longitude = location.get('lng', 0.0)  # Default to 0.0 if not available
        embed_link = create_embed_link_from_place(name)
        
        # Create a Place object and add it to the list. Travel times are currently -1 as it indicates that they have not been found
        place = Place(name, address, rating, total_ratings, link, -1, -1, embed_link, latitude, longitude)
        places.append(place)

    return places


def get_midpoints_around_midpoint(coord_a, coord_b, num_points=10, radius_ratio=0.1):
    """
    Returns num_points (10 as default) points within a radius around the midpoint
    between coord_a and coord_b, with the radius being a percentage of the direct
    distance between the two points.

    This does NOT use any APIs and is a straight line distance, like ratio division.

    Params:
        coord_a, coord_b (str): The locations you wish to find the midpoints from.
        num_points (int): The number of points to generate.
        radius_ratio (float): The radius as a percentage of the direct distance between the points.

    Returns:
        midpoints (List[str]): A list of midpoints each consisting of a
        string that contains the latitude and longitude of each location.
    """
    lat_a, lng_a = map(float, coord_a.split(','))
    lat_b, lng_b = map(float, coord_b.split(','))
    
    # Calculate the midpoint
    mid_lat = (lat_a + lat_b) / 2
    mid_lng = (lng_a + lng_b) / 2
    
    # Calculate the distance between the two points
    dist_lat = lat_b - lat_a
    dist_lng = lng_b - lng_a
    distance = math.sqrt(dist_lat ** 2 + dist_lng ** 2)
    
    # Radius of the circle around the midpoint
    radius = radius_ratio * distance
    
    midpoints = []
    
    for _ in range(num_points):
        # Random angle in radians
        angle = random.uniform(0, 2 * math.pi)
        # Random distance from midpoint within the radius
        random_distance = random.uniform(0, radius)
        
        # Calculate the new point
        lat_m = mid_lat + random_distance * math.cos(angle)
        lng_m = mid_lng + random_distance * math.sin(angle)
        
        midpoints.append(f"{lat_m},{lng_m}")
    
    return midpoints

def get_middle_locations(location_a: str, location_b: str, mode_a: str, mode_b: str, location_type: str):
    """
    A combination of all the above helper functions to locate 10
    places roughly equidistant in travel time between the two original locations,
    assuming the person starting from location_a utilises mode_a of transport

    Args:
        location_a, location_b (str): The original two locations that are being met from
        mode_a, mode_b (str): The two modes of transport both people are using
        location_type (str): The location type for the meetup. Full list here:
        https://developers.google.com/maps/documentation/places/web-service/supported_types

    Returns:
        A dictionary with {'results': [{Result 1}, {Result 2}...]}. 
        Each result is a location.
    """

    # This will be dependant on travel options
    geocoded_a = geocode(location_a)
    if geocoded_a is None:
        raise ValueError("Location a could not be geocoded")
    geocoded_b = geocode(location_b)
    if geocoded_b is None:
        raise ValueError("Location b could not be geocoded")
    
    if mode_a == mode_b:
        # Real midpoint is probably near the middle - tune performance by using less points
        midpoints = get_midpoints(geocoded_a, geocoded_b)
    else:
        midpoints = get_midpoints(geocoded_a, geocoded_b, num_points=10)
    
    if midpoints is None:
        raise ValueError
    
    best = find_best_midpoint(geocoded_a, geocoded_b, midpoints, mode_a, mode_b)
    if best is None:
        raise ValueError("Best location could not be found")
    nearby = find_nearby_places(best, location_type, max_results=5)
    return nearby

def add_location_data(location_a: str, location_b: str, locations_classes: List[Place], mode_a: str, mode_b: str):
    """
    Adds expected travel times from location a to all the proposed meeting points, and does the same with location b
    Modifies already existing Place objects
    """
    
    a_to_m, b_to_m = get_travel_times_matrix(location_a, location_b, locations_classes, mode_a, mode_b)

    for n in range(len(locations_classes)):
        locations_classes[n].time_from_a = a_to_m[n]
        locations_classes[n].time_from_b = b_to_m[n]
        
    return locations_classes

def get_all_locations_classes(location_a: str, location_b: str, mode_a: str, mode_b: str, location_type: str):
    """
    Full wrapper function that takes in four user inputs, and returns a list of 6 recommended Place objects
    """

    locations_classes = parse_places(get_middle_locations(location_a, location_b , mode_a, mode_b, location_type))
    updated_locations_classes = add_location_data(location_a, location_b, locations_classes, mode_a, mode_b)
    sorted_places = sorted(updated_locations_classes, key=lambda place: abs(place.time_from_a - place.time_from_b))
    return sorted_places