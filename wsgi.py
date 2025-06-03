import os
from app import create_app

# Create the Flask application instance for production
app = create_app(os.environ.get('FLASK_CONFIG', 'production'))

if __name__ == "__main__":
    # Get port from Render's environment variable
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)