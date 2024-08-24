from flask import Flask, redirect, render_template, request, url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime


app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///test.db' # three /// means a relative path :), four is absolute
db = SQLAlchemy(app) # Initialise database

class Todo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.String(200), nullable=False)
    completed = db.Column(db.Integer, default=0)
    date_created = db.Column(db.DateTime, default=datetime.utcnow())

    def __repr__(self) -> str:
        return '<Task %r>' & self.id

# Allows us to configure our url
@app.route('/', methods=['POST','GET'])
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
    # This is the html file which we load up
    if request.method == 'POST':
        task_content = request.form['content']
        new_task = Todo(content=task_content)

        try:
            db.session.add(new_task)
            db.session.commit()
            return redirect('/')
        except:
            return "I am a failure"

    else:
        tasks = Todo.query.order_by(Todo.date_created).all()
        return render_template("index.html", tasks=tasks)

@app.route('/backend')
def newroute():
    return render_template("index.html")


@app.route('/delete/<int:id>')
def delete(id):
    task_to_deete = Todo.query.get_or_404(id)
    try:
        db.session.delete(task_to_deete)
        db.session.commit()
        return redirect('/')
    except:
        return 'I couldn\'t delete it'

@app.route('/update/<int:id>')
def update(id):
    task_to_update = Todo.query.get_or_404(id)
    try:
        db.session.delete(task_to_update)
        db.session.commit()
        return redirect('/')
    except:
        return 'I couldn\'t update it'    

if __name__ == "__main__":
    app.run(debug=True)
