import os
from flask import Flask, jsonify
from flask_cors import CORS

def create_app(test_config=None):
    """Create and configure the Flask application"""
    app = Flask(__name__, instance_relative_config=True)
    CORS(app)  # Enable CORS for all routes
    
    # Ensure the instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass
        
    if test_config is None:
        # Load the instance config, if it exists, when not testing
        app.config.from_mapping(
            SECRET_KEY='dev',
            DATABASE=os.path.join(app.instance_path, 'ml_app.sqlite'),
        )
    else:
        # Load the test config if passed in
        app.config.update(test_config)

    # Error handlers
    @app.errorhandler(400)
    def bad_request(error):
        return jsonify({"error": "Bad Request", "message": str(error)}), 400

    @app.errorhandler(404)
    def not_found(error):
        return jsonify({"error": "Not Found", "message": str(error)}), 404

    @app.errorhandler(500)
    def internal_error(error):
        return jsonify({"error": "Internal Server Error", "message": str(error)}), 500

    @app.errorhandler(Exception)
    def handle_exception(error):
        app.logger.error(f"Unhandled exception: {str(error)}")
        return jsonify({
            "error": "Internal Server Error",
            "message": "An unexpected error occurred"
        }), 500

    # Initialize database
    from .database import db
    db.init_app(app)
    
    # Register blueprints
    from .api import bp as api_bp
    app.register_blueprint(api_bp)

    from . import routes
    app.register_blueprint(routes.bp)

    # Initialize database and questions if running with the Flask CLI
    if os.environ.get('FLASK_RUN_FROM_CLI'):
        with app.app_context():
            db.init_db()

    return app
