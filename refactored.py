from flask import Flask
from flask_sqlalchemy import SQLAlchemy
import os
import googlemaps
import math
from typing import List, Dict, Tuple, Any
import json
import requests
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
class Person:
    """
    Represents a person with their location and transport mode
    """
    def __init__(self, name: str, location: str, transport_mode: str):
        self.name = name
        self.location = location
        self.transport_mode = transport_mode
        self.geocoded_location = None  # Will be populated by geocoding
    
    def __repr__(self):
        return f"Person(name={self.name}, location={self.location}, mode={self.transport_mode})"

class Meeting(db.Model):
    """
    Updated Meeting model to handle multiple people
    """
    id = db.Column(db.Integer, primary_key=True)
    meeting_data = db.Column(db.Text)  # JSON string storing all people data
    meeting_point = db.Column(db.String(100))
    place_type = db.Column(db.String(50))
    
    def set_people_data(self, people: List[Person]):
        """Store people data as JSON"""
        people_data = []
        for person in people:
            people_data.append({
                'name': person.name,
                'location': person.location,
                'transport_mode': person.transport_mode
            })
        self.meeting_data = json.dumps(people_data)
    
    def get_people_data(self) -> List[Person]:
        """Retrieve people data from JSON"""
        if not self.meeting_data:
            return []
        people_data = json.loads(self.meeting_data)
        return [Person(p['name'], p['location'], p['transport_mode']) for p in people_data]

class Place:
    def __init__(self, name: str, address: str, rating: float, total_ratings: int, 
                 business_image_link: str, embed_link: str, latitude: float, longitude: float):
        self.name = name
        self.address = address
        self.rating = rating
        self.total_ratings = total_ratings
        self.business_image_link = business_image_link
        self.embed_link = embed_link
        self.latitude = latitude
        self.longitude = longitude
        
        # Dictionary to store travel times from each person
        self.travel_times = {}  # {person_name: travel_time_seconds}
        
        # Calculated metrics
        self.max_travel_time = 0
        self.total_travel_time = 0
        self.travel_time_variance = 0
        self.fairness_score = 0  # Lower is better (less variance in travel times)

    def add_travel_time(self, person_name: str, travel_time: int):
        """Add travel time for a specific person"""
        if travel_time is not None:
            self.travel_times[person_name] = travel_time
    
    def calculate_metrics(self):
        """Calculate various metrics for ranking this place"""
        if not self.travel_times:
            return
        
        times = list(self.travel_times.values())
        self.max_travel_time = max(times)
        self.total_travel_time = sum(times)
        
        # Calculate variance (measure of fairness)
        mean_time = self.total_travel_time / len(times)
        self.travel_time_variance = sum((t - mean_time) ** 2 for t in times) / len(times)
        
        # Fairness score combines variance and max time
        self.fairness_score = (self.travel_time_variance + (self.max_travel_time * 0.1))/10000

    def __repr__(self):
        return (f"Place(name={self.name}, address={self.address}, rating={self.rating}, "
                f"total_ratings={self.total_ratings}, travel_times={self.travel_times}, "
                f"fairness_score={self.fairness_score:.2f})")

# Helper functions
def geocode(address: str) -> str | None:
    """
    Geocodes one address (string) into a set of coordinates
    
    Returns a string of latitude and longitude
    """
    result = gmaps.geocode(address)
    if result:
        location = result[0]['geometry']['location']
        return f"{location['lat']},{location['lng']}"
    return None

# Add to your class definitions
geocoding_cache = {}  # Simple in-memory cache

def batch_geocode_people(people: List[Person]) -> List[Person]:
    """
    Optimized geocoding with caching and reduced API calls
    """
    # Check cache first
    uncached_people = []
    for person in people:
        if person.location in geocoding_cache:
            person.geocoded_location = geocoding_cache[person.location]
        else:
            uncached_people.append(person)
    
    # Batch geocode remaining locations
    if uncached_people:
        # Google Geocoding API supports batch requests, but Python client doesn't expose it well
        # So we'll optimize by reducing individual calls through better error handling
        for person in uncached_people:
            try:
                result = gmaps.geocode(person.location)
                if result:
                    location = result[0]['geometry']['location']
                    coord_string = f"{location['lat']},{location['lng']}"
                    person.geocoded_location = coord_string
                    geocoding_cache[person.location] = coord_string
                else:
                    # Try a simplified version of the address
                    simplified = person.location.split(',')[0]  # Just use first part
                    result = gmaps.geocode(simplified)
                    if result:
                        location = result[0]['geometry']['location']
                        coord_string = f"{location['lat']},{location['lng']}"
                        person.geocoded_location = coord_string
                        geocoding_cache[person.location] = coord_string
                    else:
                        raise ValueError(f"Could not geocode location for {person.name}: {person.location}")
            except Exception as e:
                print(f"Geocoding error for {person.name}: {e}")
                raise
    
    return people

def clear_geocoding_cache():
    """Clear the geocoding cache (useful for testing or memory management)"""
    global geocoding_cache
    geocoding_cache.clear()

def get_geographic_centroid(coords: List[str]) -> str:
    """
    Given a list of coordinates (lat,lng strings), return the geographic centroid
    (center point on a sphere) as a "lat,lng" string.

    This is more accurate than a flat average, especially over long distances.

    Params:
        coords (List[str]): List of coordinates as strings in "lat,lng" format

    Returns:
        centroid (str): Centroid as "lat,lng"
    """
    if not coords:
        raise ValueError("Coordinate list is empty")

    x_total = 0.0
    y_total = 0.0
    z_total = 0.0

    for coord in coords:
        lat_deg, lng_deg = map(float, coord.split(','))
        lat_rad = math.radians(lat_deg)
        lng_rad = math.radians(lng_deg)

        # Convert to Cartesian coordinates
        x = math.cos(lat_rad) * math.cos(lng_rad)
        y = math.cos(lat_rad) * math.sin(lng_rad)
        z = math.sin(lat_rad)

        x_total += x
        y_total += y
        z_total += z

    n = len(coords)
    x_avg = x_total / n
    y_avg = y_total / n
    z_avg = z_total / n

    # Convert back to lat/lng
    hyp = math.sqrt(x_avg ** 2 + y_avg ** 2)
    lat_rad = math.atan2(z_avg, hyp)
    lng_rad = math.atan2(y_avg, x_avg)

    lat_deg = math.degrees(lat_rad)
    lng_deg = math.degrees(lng_rad)

    return f"{lat_deg},{lng_deg}"

def get_search_area_points(people: List[Person], num_points: int = 20, radius_ratio: float = 0.15) -> List[str]:
    """
    Generate search points around the geographic centroid of all people's locations.
    This replaces the midpoint-based approach for multiple people.
    
    Args:
        people: List of Person objects with geocoded locations
        num_points: Number of search points to generate
        radius_ratio: Radius as a ratio of the maximum distance from centroid
    
    Returns:
        List of coordinate strings for searching
    """
    # Get all coordinates
    coords = [person.geocoded_location for person in people if person.geocoded_location]
    
    if len(coords) < 2:
        raise ValueError("Need at least 2 valid locations")
    
    # Calculate centroid
    centroid = get_geographic_centroid(coords)
    centroid_lat, centroid_lng = map(float, centroid.split(','))
    
    # Calculate maximum distance from centroid to any person
    max_distance = 0
    for coord in coords:
        lat, lng = map(float, coord.split(','))
        dist = math.sqrt((lat - centroid_lat) ** 2 + (lng - centroid_lng) ** 2)
        max_distance = max(max_distance, dist)
    
    # Generate search radius
    search_radius = radius_ratio * max_distance
    
    # Generate random points around the centroid
    search_points = [centroid]  # Include the centroid itself
    
    for _ in range(num_points - 1):
        # Random angle and distance
        angle = random.uniform(0, 2 * math.pi)
        distance = random.uniform(0, search_radius)
        
        # Calculate new point
        lat = centroid_lat + distance * math.cos(angle)
        lng = centroid_lng + distance * math.sin(angle)
        search_points.append(f"{lat},{lng}")
    
    return search_points

def find_nearby_places(location, place_type, radius=1500, max_results=8):
    """
    Optimized version that's smarter about radius increases
    """
    try:
        places = gmaps.places_nearby(location=location, radius=radius, type=place_type)
        results = places.get('results', [])
        
        # If we have enough results, return them
        if len(results) >= max_results:
            return {"results": results[:max_results]}
        
        # If not enough results, try ONE larger radius instead of multiple increases
        if len(results) < max_results and radius < 5000:
            larger_radius = min(radius * 2, 5000)  # Double radius but cap at 5km
            places = gmaps.places_nearby(location=location, radius=larger_radius, type=place_type)
            results = places.get('results', [])
        
        return {"results": results[:max_results]}
        
    except Exception as e:
        print(f"Error in places search: {e}")
        return {"results": []}


def find_places_optimized(people: List[Person], place_type: str, max_results: int = 10) -> dict:
    """
    Optimized version that uses fewer API calls by:
    1. Single search from centroid with larger radius
    2. Fallback to multiple points only if needed
    """
    coords = [person.geocoded_location for person in people if person.geocoded_location]
    centroid = get_geographic_centroid(coords)
    
    # Calculate appropriate radius based on spread of people
    max_distance_km = 0
    centroid_lat, centroid_lng = map(float, centroid.split(','))
    
    for coord in coords:
        lat, lng = map(float, coord.split(','))
        # Convert to kilometers (rough approximation)
        distance_km = math.sqrt((lat - centroid_lat) ** 2 + (lng - centroid_lng) ** 2) * 111
        max_distance_km = max(max_distance_km, distance_km)
    
    # Use radius that covers the spread plus some buffer
    radius = min(max(int(max_distance_km * 1000 * 0.3), 1000), 5000)  # 30% of spread, min 1km, max 5km
    
    # Single API call with larger radius
    places_data = find_nearby_places(centroid, place_type, radius=radius, max_results=max_results*2)
    
    # If we don't have enough results, only then do additional searches
    if len(places_data.get('results', [])) < max_results:
        # Generate fewer search points (2-3 instead of 5)
        additional_points = get_search_area_points(people, num_points=3, radius_ratio=0.2)
        
        for point in additional_points[1:]:  # Skip centroid (already searched)
            additional_data = find_nearby_places(point, place_type, radius=1000, max_results=3)
            
            # Merge results, avoiding duplicates
            existing_place_ids = {p.get('place_id') for p in places_data.get('results', [])}
            for place in additional_data.get('results', []):
                if place.get('place_id') not in existing_place_ids:
                    places_data.setdefault('results', []).append(place)
    
    return places_data

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
    """
    From a place's data, returns an image link for the place
    """
    if place_data.get('photos'):
        photo_reference = place_data['photos'][0]['photo_reference']
        return get_place_photo_url(photo_reference)
    return None

def get_travel_times_optimized(people: List[Person], places: List[Place]) -> List[Place]:
    """
    Optimized travel time calculation with reduced API calls
    """
    if not people or not places:
        return places
    
    # Check if everyone has the same transport mode
    transport_modes = set(person.transport_mode for person in people)
    
    origins = [person.geocoded_location for person in people]
    destinations = [f"{place.latitude},{place.longitude}" for place in places]
    
    if len(transport_modes) == 1:
        # Everyone has same transport mode - single API call
        mode = list(transport_modes)[0]
        try:
            matrix = gmaps.distance_matrix(
                origins=origins,
                destinations=destinations,
                mode=mode
            )
            
            # Process results
            for person_idx, person in enumerate(people):
                for place_idx, place in enumerate(places):
                    element = matrix['rows'][person_idx]['elements'][place_idx]
                    if element['status'] == 'OK':
                        travel_time = element['duration']['value']
                        place.add_travel_time(person.name, travel_time)
                    else:
                        place.add_travel_time(person.name, 9999)
                        
        except Exception as e:
            print(f"Error in distance matrix call: {e}")
            # Fallback to high penalty times
            for person in people:
                for place in places:
                    place.add_travel_time(person.name, 9999)
    
    else:
        # Multiple transport modes - but optimize by checking if we can reduce modes
        # For example, if someone chose "transit" but it's not available, fall back to "walking"
        
        # Group by transport mode but be smarter about it
        mode_groups = {}
        for person in people:
            # Normalize transport modes (e.g., "car" -> "driving")
            normalized_mode = person.transport_mode
            if normalized_mode not in mode_groups:
                mode_groups[normalized_mode] = []
            mode_groups[normalized_mode].append(person)
        
        # Make API calls for each unique mode
        for mode, people_group in mode_groups.items():
            group_origins = [person.geocoded_location for person in people_group]
            
            try:
                matrix = gmaps.distance_matrix(
                    origins=group_origins,
                    destinations=destinations,
                    mode=mode
                )
                
                for person_idx, person in enumerate(people_group):
                    for place_idx, place in enumerate(places):
                        element = matrix['rows'][person_idx]['elements'][place_idx]
                        if element['status'] == 'OK':
                            travel_time = element['duration']['value']
                            place.add_travel_time(person.name, travel_time)
                        else:
                            place.add_travel_time(person.name, 9999)
            
            except Exception as e:
                print(f"Error calculating travel times for mode {mode}: {e}")
                for person in people_group:
                    for place in places:
                        place.add_travel_time(person.name, 9999)
    
    # Calculate metrics for each place
    for place in places:
        place.calculate_metrics()
    
    return places

def get_embed_link(lat, lng):
    return f"https://www.google.com/maps/embed/v1/place?q={lat},{lng}&key={GOOG_API_KEY}"

def create_embed_link_from_place(place_name):
    return f"https://www.google.com/maps/embed/v1/place?q={place_name.replace(' ', '+')}&key={GOOG_API_KEY}"

def parse_places(json_data: dict) -> List[Place]:
    """
    Function to parse JSON and create Place objects out of each of them.
    """
    places = []
    
    # Extract places list
    results = json_data.get('results', [])
    
    # Create Place objects for each result
    for result in results:
        name = result.get('name')
        address = result.get('vicinity')
        rating = result.get('rating', 0.0)
        total_ratings = result.get('user_ratings_total', 0)
        link = get_business_image(result)
        
        # Extract latitude and longitude
        location = result.get('geometry', {}).get('location', {})
        latitude = location.get('lat', 0.0)
        longitude = location.get('lng', 0.0)
        embed_link = create_embed_link_from_place(name)
        
        # Create a Place object
        place = Place(name, address, rating, total_ratings, link, embed_link, latitude, longitude)
        places.append(place)

    return places

def get_middle_locations_multi_person(people: List[Person], location_type: str, max_places: int = 10) -> List[Place]:
    """
    Find meeting places that are relatively fair for all people involved.
    
    Args:
        people: List of Person objects with locations and transport modes
        location_type: Type of place to search for
        max_places: Maximum number of places to return
    
    Returns:
        List of Place objects sorted by fairness score
    """
    # Geocode all locations
    people = batch_geocode_people(people)
    
    # Generate search points around the geographic centroid
    search_points = get_search_area_points(people, num_points=5)  # Reduced for API efficiency
    
    # Find places near each search point
    all_places = []
    place_ids_seen = set()
    
    for point in search_points:
        nearby_places_data = find_nearby_places(point, location_type, max_results=3)
        places = parse_places(nearby_places_data)
        
        # Add unique places only
        for place in places:
            place_key = f"{place.name}_{place.latitude}_{place.longitude}"
            if place_key not in place_ids_seen:
                place_ids_seen.add(place_key)
                all_places.append(place)
    
    # Calculate travel times for all people to all places
    all_places = get_travel_times_optimized(people, all_places)
    
    # Filter out places with invalid travel times for any person
    valid_places = []
    for place in all_places:
        if len(place.travel_times) == len(people) and all(time < 9999 for time in place.travel_times.values()):
            valid_places.append(place)
    
    # Sort by fairness score (lower is better)
    valid_places.sort(key=lambda p: (p.fairness_score, p.max_travel_time))
    
    return valid_places[:max_places]

def rank_places_by_strategy(places: List[Place], strategy: str = "fairness") -> List[Place]:
    """
    Rank places by different strategies.
    
    Args:
        places: List of Place objects with calculated metrics
        strategy: Ranking strategy ("fairness", "minimize_max", "minimize_total", "rating")
    
    Returns:
        Sorted list of places
    """
    if strategy == "fairness":
        # Minimize variance in travel times (most fair)
        return sorted(places, key=lambda p: p.fairness_score)
    elif strategy == "minimize_max":
        # Minimize the maximum travel time for anyone
        return sorted(places, key=lambda p: p.max_travel_time)
    elif strategy == "minimize_total":
        # Minimize total travel time for everyone
        return sorted(places, key=lambda p: p.total_travel_time)
    elif strategy == "rating":
        # Prioritize highly rated places, then fairness
        return sorted(places, key=lambda p: (-p.rating, p.fairness_score))
    else:
        return places

# Main wrapper function
def get_all_locations_for_group(people: List[Person], location_type: str, 
                               ranking_strategy: str = "fairness", max_results: int = 6) -> List[Place]:
    """
    Full wrapper function that takes in a list of people and returns recommended meeting places.
    
    Args:
        people: List of Person objects
        location_type: Type of place to search for
        ranking_strategy: How to rank the results
        max_results: Maximum number of results to return
    
    Returns:
        List of Place objects ranked by the specified strategy
    """
    if len(people) < 2:
        raise ValueError("Need at least 2 people to find a meeting point")
    
    # Get potential meeting places
    places = get_middle_locations_multi_person(people, location_type, max_places=15)
    
    # Rank according to strategy
    ranked_places = rank_places_by_strategy(places, ranking_strategy)
    
    return ranked_places[:max_results]

# Convenience function for the original two-person interface
def get_all_locations_classes(location_a: str, location_b: str, mode_a: str, mode_b: str, location_type: str):
    """
    Backward compatibility function for two-person meetings
    """
    people = [
        Person("Person A", location_a, mode_a),
        Person("Person B", location_b, mode_b)
    ]
    return get_all_locations_for_group(people, location_type)

def print_meeting_analysis(places: List[Place], people: List[Person]):
    """Print a detailed analysis of meeting options"""
    print(f"\n=== MEETING ANALYSIS FOR {len(people)} PEOPLE ===")
    print(f"People: {[p.name for p in people]}")
    print(f"Found {len(places)} potential meeting places:\n")
    
    for i, place in enumerate(places, 1):
        print(f"{i}. {place.name}")
        print(f"   Address: {place.address}")
        print(f"   Rating: {place.rating}/5 ({place.total_ratings} reviews)")
        print(f"   Travel times:")
        for person_name, time in place.travel_times.items():
            minutes = time // 60
            print(f"     {person_name}: {minutes} minutes")
        print(f"   Max travel time: {place.max_travel_time // 60} minutes")
        print(f"   Total travel time: {place.total_travel_time // 60} minutes")
        print(f"   Fairness score: {place.fairness_score:.2f}")
        print()

def get_location_suggestions(query: str, api_key: str) -> List[Dict[str, Any]]:
    """Get location suggestions using Google Places Autocomplete API"""
    try:
        url = "https://maps.googleapis.com/maps/api/place/autocomplete/json"
        params = {
            'input': query,
            'key': api_key,
            'components': 'country:au',  # Restrict to Australia
            'types': 'address'
        }
        
        response = requests.get(url, params=params)
        response.raise_for_status()
        
        data = response.json()
        suggestions = []
        
        if data.get('status') == 'OK':
            for prediction in data.get('predictions', []):
                suggestions.append({
                    'description': prediction.get('description', ''),
                    'place_id': prediction.get('place_id', '')
                })
        
        return suggestions[:5]  # Return top 5 suggestions
        
    except Exception as e:
        print(f"Error getting location suggestions: {e}")
        return []