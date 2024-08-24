from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
import os
import googlemaps
from geopy.distance import distance

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///meetingpoints.db'
db = SQLAlchemy(app)

# API key
GOOG_API_KEY = os.environ.get('GOOG_API_KEY')

# Initialize Google Maps client
gmaps = googlemaps.Client(key=GOOG_API_KEY)

# Models
class Meeting(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    location_a = db.Column(db.String(100))
    location_b = db.Column(db.String(100))
    mode_a = db.Column(db.String(20))
    mode_b = db.Column(db.String(20))
    meeting_point = db.Column(db.String(100))
    place_type = db.Column(db.String(50))

# Helper functions
def geocode(address):
    result = gmaps.geocode(address)
    if result:
        location = result[0]['geometry']['location']
        return f"{location['lat']},{location['lng']}"
    return None

def get_midpoints(coord_a, coord_b, num_points=3):
    lat_a, lng_a = map(float, coord_a.split(','))
    lat_b, lng_b = map(float, coord_b.split(','))
    
    midpoints = []
    for i in range(1, num_points + 1):
        ratio = i / (num_points + 1)
        lat_m = lat_a + ratio * (lat_b - lat_a)
        lng_m = lng_a + ratio * (lng_b - lng_a)
        midpoints.append(f"{lat_m},{lng_m}")
    
    return midpoints

def find_best_midpoint(coord_a, coord_b, midpoints, mode_a, mode_b):
    origins = [coord_a, coord_b]
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
    places = gmaps.places_nearby(location=location, radius=radius, type=place_type)
    results = places.get('results', [])
    
    while len(results) < max_results and radius <= 2000:
        radius *= 2
        places = gmaps.places_nearby(location=location, radius=radius, type=place_type)
        results.extend(places.get('results', []))
        results = list({place['place_id']: place for place in results}.values())  # Remove duplicates
    
    return results[:max_results]

# Route
@app.route('/find_meeting_point', methods=['POST'])
def find_meeting_point():
    data = request.json
    location_a = data['location_a']
    location_b = data['location_b']
    mode_a = data['mode_a']
    mode_b = data['mode_b']
    place_type = data['place_type']

    # Step 2: Convert locations to coordinates
    coord_a = geocode(location_a)
    coord_b = geocode(location_b)

    if not coord_a or not coord_b:
        return jsonify({"error": "Unable to geocode one or both locations"}), 400

    # Step 3: Get midpoints
    midpoints = get_midpoints(coord_a, coord_b)

    # Step 4: Find best midpoint
    best_midpoint = find_best_midpoint(coord_a, coord_b, midpoints, mode_a, mode_b)

    # Step 5: Find nearby places
    nearby_places = find_nearby_places(best_midpoint, place_type)

    # Create and save meeting
    meeting = Meeting(
        location_a=location_a,
        location_b=location_b,
        mode_a=mode_a,
        mode_b=mode_b,
        meeting_point=best_midpoint,
        place_type=place_type
    )
    db.session.add(meeting)
    db.session.commit()

    return jsonify({
        "meeting_id": meeting.id,
        "best_midpoint": best_midpoint,
        "nearby_places": [
            {
                "name": place['name'],
                "address": place['vicinity'],
                "location": f"{place['geometry']['location']['lat']},{place['geometry']['location']['lng']}"
            }
            for place in nearby_places
        ]
    })

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)