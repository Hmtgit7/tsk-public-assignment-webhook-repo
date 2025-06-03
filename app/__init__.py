from flask import Flask, render_template
from flask_cors import CORS
from app.extensions import mongo
from config import config

def create_app(config_name='default'):
    app = Flask(__name__)
    
    # Load configuration
    app.config.from_object(config[config_name])
    
    # Initialize extensions
    mongo.init_app(app)
    CORS(app, origins=app.config['CORS_ORIGINS'])
    
    # Register blueprints
    from app.webhook.routes import webhook
    from app.api.routes import api
    
    app.register_blueprint(webhook)
    app.register_blueprint(api)
    
    # Register main route for UI
    @app.route('/')
    def index():
        return render_template('index.html')
    
    # Health check endpoint
    @app.route('/health')
    def health():
        return {'status': 'healthy', 'message': 'Webhook receiver is running'}, 200
    
    return app