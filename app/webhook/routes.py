from flask import Blueprint, request, jsonify
import json
import logging
from app.models.webhook_event import WebhookEvent

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

webhook = Blueprint('webhook', __name__, url_prefix='/webhook')

@webhook.route('/receiver', methods=['POST'])
def receiver():
    """
    GitHub webhook receiver endpoint
    Handles Push, Pull Request, and Merge events
    """
    try:
        # Get the GitHub event type from headers
        event_type = request.headers.get('X-GitHub-Event')
        if not event_type:
            logger.warning("No X-GitHub-Event header found")
            return jsonify({'error': 'Missing event type header'}), 400
        
        # Get JSON payload
        payload = request.get_json()
        if not payload:
            logger.warning("No JSON payload received")
            return jsonify({'error': 'No JSON payload'}), 400
        
        logger.info(f"Received GitHub webhook: {event_type}")
        
        # Process different event types
        webhook_event = None
        
        if event_type == 'push':
            # Handle push events
            webhook_event = WebhookEvent.from_github_push(payload)
            logger.info(f"Processing push event from {webhook_event.author} to {webhook_event.to_branch}")
            
        elif event_type == 'pull_request':
            # Handle pull request events
            action = payload.get('action')
            
            if action == 'opened':
                # Pull request opened
                webhook_event = WebhookEvent.from_github_pull_request(payload)
                logger.info(f"Processing pull request from {webhook_event.author}: {webhook_event.from_branch} -> {webhook_event.to_branch}")
                
            elif action == 'closed' and payload['pull_request'].get('merged'):
                # Pull request merged
                webhook_event = WebhookEvent.from_github_merge(payload)
                logger.info(f"Processing merge event from {webhook_event.author}: {webhook_event.from_branch} -> {webhook_event.to_branch}")
            
            else:
                logger.info(f"Ignoring pull request action: {action}")
                return jsonify({'message': f'Ignored pull request action: {action}'}), 200
        
        else:
            logger.info(f"Ignoring event type: {event_type}")
            return jsonify({'message': f'Event type {event_type} not handled'}), 200
        
        # Save the webhook event to MongoDB
        if webhook_event:
            event_id = webhook_event.save()
            logger.info(f"Webhook event saved successfully with ID: {event_id}")
            
            return jsonify({
                'message': 'Webhook processed successfully',
                'event_id': str(event_id),
                'event_type': event_type
            }), 200
        
        return jsonify({'message': 'No event processed'}), 200
        
    except ValueError as e:
        logger.error(f"Validation error: {str(e)}")
        return jsonify({'error': f'Validation error: {str(e)}'}), 400
    
    except Exception as e:
        logger.error(f"Unexpected error processing webhook: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@webhook.route('/test', methods=['POST'])
def test_receiver():
    """
    Test endpoint for manual testing
    """
    try:
        # Create a test event
        test_event = WebhookEvent(
            request_id='test-123',
            author='TestUser',
            action='PUSH',
            to_branch='main',
            timestamp=None  # Will use current time
        )
        
        event_id = test_event.save()
        logger.info(f"Test event created with ID: {event_id}")
        
        return jsonify({
            'message': 'Test event created successfully',
            'event_id': str(event_id)
        }), 200
        
    except Exception as e:
        logger.error(f"Error creating test event: {str(e)}")
        return jsonify({'error': 'Failed to create test event'}), 500