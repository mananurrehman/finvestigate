from flask import Blueprint, render_template

main = Blueprint('main', __name__)

@main.route('/')
def index():
    return render_template('home.html')

@main.route('/about')
def about():
    return render_template('about.html')

@main.route('/how-to-use')
def how_to_use():
    return render_template('how_to_use.html')

@main.route('/contact')
def contact():
    return render_template('contact.html')