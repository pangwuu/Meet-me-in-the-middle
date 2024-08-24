from flask import Flask, redirect, render_template, request, url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import helpers

app = Flask(__name__)

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

        # TOADD: dealing with specific ideas like cafe etc
        # TOADD: Deal with errors such as
        
            # except ValueError as e:
            #     if str(e) == "Location a could not be geocoded":
            #         print("Could not geocode location A")
            #     elif str(e) == "Location b could not be geocoded":
            #         print("Could not geocode location B")
            #     elif str(e) == "Best location could not be found":
            #         print("Could not find a best location")
            #     else:
            #         # Re-raise the exception if it's not one of the expected messages
            #         raise

        results = helpers.get_middle_locations(locA, locB, transportA, transportB)
        return render_template('route.html', output=results)

    else:
        return render_template('search.html')

# Route for results page
@app.route('/route')
def route():
    results = request.args.get('results')
    return render_template('route.html', output=results)

if __name__ == "__main__":
    app.run(debug=True)
