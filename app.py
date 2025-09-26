from flask import Flask, redirect, render_template, request, url_for, jsonify
from flask_sqlalchemy import SQLAlchemy
from refactored import Person, get_all_locations_for_group, get_location_suggestions
import os

app = Flask(__name__)

# APIKEY
GOOG_API_KEY = os.environ.get("GOOG_API_KEY")

# Allows us to configure our url
@app.route('/')
def index():
    return render_template("landing.html")

# Route for search page
@app.route('/search', methods=['POST','GET'])
def search():
    if request.method == 'POST':
        # Get form data for multiple people
        people_data = []
        i = 0
        
        # Extract data for each person
        while f'person_{i}_name' in request.form:
            name = request.form[f'person_{i}_name']
            location = request.form[f'person_{i}_location']
            transport = request.form[f'person_{i}_transport']
            
            if name and location and transport:  # Only add if all fields are filled
                people_data.append({
                    'name': name,
                    'location': location,
                    'transport': transport
                })
            i += 1
        
        place_type = request.form.get('places', 'restaurant')
        sort_method = request.form.get('sort_method', 'fairness')
        
        results = None
        error = None

        try:
            if len(people_data) < 2:
                raise ValueError("Please add at least 2 people to find meeting places.")
            
            # Create Person objects from the form data
            people = []
            for person_data in people_data:
                # Assuming you have a Person class in helpers
                person = Person(
                    person_data['name'], 
                    person_data['location'], 
                    person_data['transport']
                )
                people.append(person)
            
            # Use the new group function
            results = get_all_locations_for_group(people, place_type, sort_method)

        except ValueError as e:
            error = str(e)
        except Exception as e:
            error = f"An error occurred: {str(e)}"
        
        return render_template('route.html', 
                             places=results, 
                             error=error, 
                             people=people_data,
                             api_key=GOOG_API_KEY)

    else:
        return render_template('search.html')

# API endpoint for location autocomplete
@app.route('/api/autocomplete')
def autocomplete():
    query = request.args.get('q', '')
    if not query or len(query) < 3:
        return jsonify([])
    
    try:
        # Use Google Places API for autocomplete
        suggestions = get_location_suggestions(query, GOOG_API_KEY)
        return jsonify(suggestions)
    except Exception as e:
        print(f"Autocomplete error: {e}")
        return jsonify([])

if __name__ == "__main__":
    app.run(debug=True)