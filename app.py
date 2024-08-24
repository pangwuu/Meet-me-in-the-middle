from flask import Flask, redirect, render_template, request, url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

app = Flask(__name__)

# Allows us to configure our url
@app.route('/')
def index():
    return render_template("landing.html")

# Route for search page
@app.route('/search', methods=['POST','GET'])
def search():
    if request.method == 'POST':
        print("MUST PRINT VALUES FROM form")

        # call helper functions
        return redirect(url_for('route', info='some_info'))

    else:
        return render_template('search.html')

# Route for results page
@app.route('/route')
def route():
    info = request.args.get('info')
    return render_template('route.html')
    # This is the html file which we load up 

if __name__ == "__main__":
    app.run(debug=True)
