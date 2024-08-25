from flask import Flask, redirect, render_template, request, url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import helpers
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
        locA = request.form['locationa']
        locB = request.form['locationb']

        transportA = request.form['transport']
        transportB = request.form['transport2']

        place_type = request.form['places']
        results = None
        error = None

        try:
            results = helpers.get_all_locations_classes(locA, locB, transportA, transportB, place_type)

        except ValueError as e:
            error = str(e)

        return render_template('route.html', places=results, error=error, transport_a=transportA, transport_b=transportB, api_key=GOOG_API_KEY)

    else:
        return render_template('search.html')

if __name__ == "__main__":
    app.run(debug=True)
