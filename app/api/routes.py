from flask import Blueprint, jsonify
import logging
from app.models.webhook_event import WebhookEvent

logger = logging.getLogger(__name__)

api = Blueprint('api', __name__, url_prefix='/api')

@api.route('/events', methods=['GET'])
def get_events():
    """
    API endpoint to fetch recent webhook events for the UI
    Returns formatted messages for display
    """
    try:
        # Get recent events from MongoDB
        events = WebhookEvent.get_recent_events(limit=50)
        
        # Format events for display
        formatted_events = []
        for event in events:
            formatted_message = WebhookEvent.format_message(event)
            formatted_events.append({
                'id': str(event['_id']),
                'message': formatted_message,
                'action': event['action'],
                'author': event['author'],
                'timestamp': event['timestamp'].isoformat() if hasattr(event['timestamp'], 'isoformat') else str(event['timestamp'])
            })
        
        logger.info(f"Returning {len(formatted_events)} events")
        
        return jsonify({
            'success': True,
            'events': formatted_events,
            'count': len(formatted_events)
        }), 200
        
    except Exception as e:
        logger.error(f"Error fetching events: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to fetch events',
            'events': [],
            'count': 0
        }), 500

@api.route('/events/count', methods=['GET'])
def get_events_count():
    """
    Get total count of webhook events
    """
    try:
        from app.extensions import get_collection
        collection = get_collection(WebhookEvent.COLLECTION_NAME)
        count = collection.count_documents({})
        
        return jsonify({
            'success': True,
            'count': count
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting events count: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to get events count',
            'count': 0
        }), 500

@api.route('/events/latest', methods=['GET'])
def get_latest_event():
    """
    Get the most recent webhook event
    """
    try:
        events = WebhookEvent.get_recent_events(limit=1)
        
        if events:
            event = events[0]
            formatted_message = WebhookEvent.format_message(event)
            
            return jsonify({
                'success': True,
                'event': {
                    'id': str(event['_id']),
                    'message': formatted_message,
                    'action': event['action'],
                    'author': event['author'],
                    'timestamp': event['timestamp'].isoformat() if hasattr(event['timestamp'], 'isoformat') else str(event['timestamp'])
                }
            }), 200
        else:
            return jsonify({
                'success': True,
                'event': None,
                'message': 'No events found'
            }), 200
            
    except Exception as e:
        logger.error(f"Error fetching latest event: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to fetch latest event'
        }), 500