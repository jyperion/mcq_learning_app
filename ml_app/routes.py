from flask import Blueprint, render_template

bp = Blueprint('main', __name__)

@bp.route('/')
def index():
    """Serve the main application page"""
    return render_template('index.html')
