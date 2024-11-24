from flask import Blueprint
from . import questions, concepts, stats, practice, sessions

bp = Blueprint('api', __name__, url_prefix='/api')

# Register question-related routes
bp.register_blueprint(questions.bp, url_prefix='/questions')
bp.register_blueprint(concepts.bp, url_prefix='/concepts')
bp.register_blueprint(stats.bp, url_prefix='/stats')
bp.register_blueprint(practice.bp, url_prefix='/practice')
bp.register_blueprint(sessions.bp, url_prefix='/session')
