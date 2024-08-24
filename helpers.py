from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
import os
import googlemaps
from typing import List
import json
from geopy.distance import distance
import requests
import math, random

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
    def __init__(self, name: str, address: str, rating: float, total_ratings: int, business_image_link: str, currently_open: bool):
        self.name = name
        self.address = address
        self.rating = rating
        self.total_ratings = total_ratings
        # This can potentially be empty - think of the consequences
        self.business_image_link = business_image_link
        # currently open
        self.currently_open = currently_open
        # routes estimated time for both
        # This can potentially be empty - think of the consequences
        self.business_image_link = business_image_link
        # routes estimated time for both
        # Get the google link

    def __repr__(self):
        return f"Place(name={self.name}, address={self.address}, rating={self.rating}, total_ratings={self.total_ratings}, latitude={self.latitude}, longitude={self.longitude}, types={self.types})"

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

def get_midpoints(coord_a, coord_b, num_points=10):
    """
    Returns num_points (10 as default) points equidistant to each other, 
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
        time_a = matrix_a['rows'][0]['elements'][i]['duration']['value']
        time_b = matrix_b['rows'][0]['elements'][i]['duration']['value']
        diff = abs(time_a - time_b)
        
        if diff < min_diff:
            min_diff = diff
            best_midpoint = midpoint
    
    return best_midpoint

def find_nearby_places(location, place_type, radius=100, max_results=10):
    """
    Returns a group of max_results nearby places to a certain coordinate.

    Returns a list of json data which can be parsd using the parse_places module
    """
    places = gmaps.places_nearby(location=location, radius=radius, type=place_type)
    results = places.get('results', [])
    
    while len(results) < max_results and radius <= 2000:
        radius *= 2
        places = gmaps.places_nearby(location=location, radius=radius, type=place_type)
        results.extend(places.get('results', []))
        results = list({place['place_id']: place for place in results}.values())  # Remove duplicates
    
    return {"results": results[:max_results]}

def get_place_photo_url(photo_reference, max_width=400):
    base_url = "https://maps.googleapis.com/maps/api/place/photo"
    params = {
        "maxwidth": max_width,
        "photoreference": photo_reference,
        "key": GOOG_API_KEY
    }
    response = requests.get(base_url, params=params)
    return response.url

def get_business_image(place_data):
    '''
    From a place's data, returns an image link for the place
    '''
    if 'photos' in place_data and place_data['photos']:
        photo_reference = place_data['photos'][0]['photo_reference']
        return get_place_photo_url(photo_reference)
    return None  # Return None if no photo is available

# Step 2: Function to parse JSON and create Place objects
def parse_places(json_data: str) -> List[Place]:
    """
    Function to parse JSON and create Place objects out of each of them
    """
    places = []
    
    # Parse the JSON data
    dumped_data = json.dumps(json_data)
    data = json.loads(dumped_data)
    
    # Extract places list
    results = data.get('results', [])
    
    # Create Place objects for each result
    for result in results:
        name = result.get('name')
        address = result.get('formatted_address')
        rating = result.get('rating')
        total_ratings = result.get('user_ratings_total')
        link = get_business_image(result)
        
        # Create a Place object and add it to the list
        place = Place(name, address, rating, total_ratings, link, True)
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
    

def get_middle_locations(location_a: str, location_b: str, mode_a: str, mode_b: str, location_type="cafe"):
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
    
    # This will be dependant on travel options
    if mode_a == mode_b:
        # We will use something which obtains a variety of points at the centre
        midpoints = get_midpoints(geocoded_a, geocoded_b)
    else:
        midpoints = get_midpoints(geocoded_a, geocoded_b)
    
    best = find_best_midpoint(geocoded_a, geocoded_b, midpoints, mode_a, mode_b)
    if best is None:
        raise ValueError("Best location could not be found")
    nearby = find_nearby_places(best, location_type)
    return nearby

try:
    locations = get_middle_locations("Fisher library University of Sydney", "Castle towers", "driving", "driving")
except ValueError as e:
    if str(e) == "Location a could not be geocoded":
        print("Could not geocode location A")
    elif str(e) == "Location b could not be geocoded":
        print("Could not geocode location B")
    elif str(e) == "Best location could not be found":
        print("Could not find a best location")
    else:
        # Re-raise the exception if it's not one of the expected messages
        raise

# make sure json loads into Place objects perfectly
# Deal with route times from BOTH original locations (matrix?)

# for i in locations["results"]:
#     print(f'{i}')

# # Route
# @app.route('/find_meeting_point', methods=['POST'])
# def find_meeting_point():
#     data = request.json
#     location_a = data['location_a']
#     location_b = data['location_b']
#     mode_a = data['mode_a']
#     mode_b = data['mode_b']
#     place_type = data['place_type']

#     # Step 2: Convert locations to coordinates
#     coord_a = geocode(location_a)
#     coord_b = geocode(location_b)

#     if not coord_a or not coord_b:
#         return jsonify({"error": "Unable to geocode one or both locations"}), 400

#     # Step 3: Get midpoints
#     midpoints = get_midpoints(coord_a, coord_b)

#     # Step 4: Find best midpoint
#     best_midpoint = find_best_midpoint(coord_a, coord_b, midpoints, mode_a, mode_b)

#     # Step 5: Find nearby places
#     nearby_places = find_nearby_places(best_midpoint, place_type)

#     # Create and save meeting
#     meeting = Meeting(
#         location_a=location_a,
#         location_b=location_b,
#         mode_a=mode_a,
#         mode_b=mode_b,
#         meeting_point=best_midpoint,
#         place_type=place_type
#     )
#     db.session.add(meeting)
#     db.session.commit()

#     return jsonify({
#         "meeting_id": meeting.id,
#         "best_midpoint": best_midpoint,
#         "nearby_places": [
#             {
#                 "name": place['name'],
#                 "address": place['vicinity'],
#                 "location": f"{place['geometry']['location']['lat']},{place['geometry']['location']['lng']}"
#             }
#             for place in nearby_places
#         ]
#     })

# if __name__ == '__main__':
#     with app.app_context():
#         db.create_all()
#     app.run(debug=True)

# # Models
# class Meeting(db.Model):
#     id = db.Column(db.Integer, primary_key=True)
#     location_a = db.Column(db.String(100))
#     location_b = db.Column(db.String(100))
#     mode_a = db.Column(db.String(20))
#     mode_b = db.Column(db.String(20))
#     meeting_point = db.Column(db.String(100))
#     place_type = db.Column(db.String(50))

# # Helper functions
# def geocode(address):
#     result = gmaps.geocode(address)
#     if result:
#         location = result[0]['geometry']['location']
#         return f"{location['lat']},{location['lng']}"
#     return None

# def get_midpoints(coord_a, coord_b, num_points=3):
#     lat_a, lng_a = map(float, coord_a.split(','))
#     lat_b, lng_b = map(float, coord_b.split(','))
    
#     midpoints = []
#     for i in range(1, num_points + 1):
#         ratio = i / (num_points + 1)
#         lat_m = lat_a + ratio * (lat_b - lat_a)
#         lng_m = lng_a + ratio * (lng_b - lng_a)
#         midpoints.append(f"{lat_m},{lng_m}")
    
#     return midpoints

# def find_best_midpoint(coord_a, coord_b, midpoints, mode_a, mode_b):
#     origins = [coord_a, coord_b]
#     matrix_a = gmaps.distance_matrix(origins=[coord_a], destinations=midpoints, mode=mode_a)
#     matrix_b = gmaps.distance_matrix(origins=[coord_b], destinations=midpoints, mode=mode_b)
    
#     min_diff = float('inf')
#     best_midpoint = None
    
#     for i, midpoint in enumerate(midpoints):
#         time_a = matrix_a['rows'][0]['elements'][i]['duration']['value']
#         time_b = matrix_b['rows'][0]['elements'][i]['duration']['value']
#         diff = abs(time_a - time_b)
        
#         if diff < min_diff:
#             min_diff = diff
#             best_midpoint = midpoint
    
#     return best_midpoint

# def find_nearby_places(location, place_type, radius=100, max_results=10):
#     places = gmaps.places_nearby(location=location, radius=radius, type=place_type)
#     results = places.get('results', [])
    
#     while len(results) < max_results and radius <= 2000:
#         radius *= 2
#         places = gmaps.places_nearby(location=location, radius=radius, type=place_type)
#         results.extend(places.get('results', []))
#         results = list({place['place_id']: place for place in results}.values())  # Remove duplicates
    
#     return results[:max_results]

# # Route
# @app.route('/find_meeting_point', methods=['POST'])
# def find_meeting_point():
#     data = request.json
#     location_a = data['location_a']
#     location_b = data['location_b']
#     mode_a = data['mode_a']
#     mode_b = data['mode_b']
#     place_type = data['place_type']

#     # Step 2: Convert locations to coordinates
#     coord_a = geocode(location_a)
#     coord_b = geocode(location_b)

#     if not coord_a or not coord_b:
#         return jsonify({"error": "Unable to geocode one or both locations"}), 400

#     # Step 3: Get midpoints
#     midpoints = get_midpoints(coord_a, coord_b)

#     # Step 4: Find best midpoint
#     best_midpoint = find_best_midpoint(coord_a, coord_b, midpoints, mode_a, mode_b)

#     # Step 5: Find nearby places
#     nearby_places = find_nearby_places(best_midpoint, place_type)

#     # Create and save meeting
#     meeting = Meeting(
#         location_a=location_a,
#         location_b=location_b,
#         mode_a=mode_a,
#         mode_b=mode_b,
#         meeting_point=best_midpoint,
#         place_type=place_type
#     )
#     db.session.add(meeting)
#     db.session.commit()

#     return jsonify({
#         "meeting_id": meeting.id,
#         "best_midpoint": best_midpoint,
#         "nearby_places": [
#             {
#                 "name": place['name'],
#                 "address": place['vicinity'],
#                 "location": f"{place['geometry']['location']['lat']},{place['geometry']['location']['lng']}"
#             }
#             for place in nearby_places
#         ]
#     })

# # if __name__ == '__main__':
# #     with app.app_context():
# #         db.create_all()
# #     app.run(debug=True)
# if __name__ == '__main__':
#     print(get_equidistant_points_around_midpoint(geocode("Manly Vale"), geocode("Epping"), 5))