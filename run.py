import os
import logging
from app import create_app

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Create Flask app
config_name = os.environ.get('FLASK_CONFIG', 'default')
app = create_app(config_name)

if __name__ == '__main__':
    # Get port from environment variable or default to 5000
    port = int(os.environ.get('PORT', 5000))
    
    # Get host from environment variable or default to localhost
    host = os.environ.get('HOST', '127.0.0.1')
    
    # Get debug mode from environment variable or default to True for development
    debug = os.environ.get('FLASK_DEBUG', 'True').lower() == 'true'
    
    print(f"Starting GitHub Webhook Monitor on {host}:{port}")
    print(f"Webhook endpoint: http://{host}:{port}/webhook/receiver")
    print(f"Web interface: http://{host}:{port}/")
    print(f"API endpoint: http://{host}:{port}/api/events")
    
    app.run(
        host=host,
        port=port,
        debug=debug,
        threaded=True
    )