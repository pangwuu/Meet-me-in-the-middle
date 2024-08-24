from flask import Flask, render_template, url_for

app = Flask(__name__)

@app.route('/')
def index():
    return render_template("landing.html")

# Route for search page
@app.route('/search')
def search():
    return render_template('search.html')

# Route for About page
@app.route('/route')
def route():
    return render_template('route.html')

if __name__ == "__main__":
    app.run(debug=True)
