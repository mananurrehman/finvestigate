from flask import Blueprint, render_template

# Blueprint = mini controller
main = Blueprint('main', __name__)

@main.route('/')
def home():
    return render_template('home.html')