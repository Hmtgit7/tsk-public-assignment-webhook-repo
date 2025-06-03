# app/webhook/routes.py 
from flask import Blueprint, request, jsonify, current_app
import json
import logging
import hmac
import hashlib
from app.models.webhook_event import WebhookEvent

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

webhook = Blueprint('webhook', __name__, url_prefix='/webhook')

def verify_github_signature(payload_body, signature, secret):
    """Verify GitHub webhook signature"""
    if not secret:
        logger.warning("No webhook secret configured, skipping signature verification")
        return True
    
    if not signature:
        logger.warning("No signature provided in webhook")
        return False
    
    expected_signature = 'sha256=' + hmac.new(
        secret.encode('utf-8'),
        payload_body,
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(signature, expected_signature)

@webhook.route('/receiver', methods=['POST'])
def receiver():
    """
    GitHub webhook receiver endpoint
    Handles Push, Pull Request, and Merge events with enhanced logging
    """
    try:
        # Get the GitHub event type from headers
        event_type = request.headers.get('X-GitHub-Event')
        delivery_id = request.headers.get('X-GitHub-Delivery')
        signature = request.headers.get('X-Hub-Signature-256')
        user_agent = request.headers.get('User-Agent', '')
        
        logger.info(f"Received webhook - Event: {event_type}, Delivery ID: {delivery_id}, User-Agent: {user_agent}")
        
        if not event_type:
            logger.warning("No X-GitHub-Event header found")
            return jsonify({'error': 'Missing event type header'}), 400
        
        # Get raw payload for signature verification
        payload_body = request.get_data()
        
        # Verify signature if webhook secret is configured
        webhook_secret = current_app.config.get('GITHUB_WEBHOOK_SECRET')
        if webhook_secret and not verify_github_signature(payload_body, signature, webhook_secret):
            logger.error("Invalid webhook signature")
            return jsonify({'error': 'Invalid signature'}), 401
        
        # Handle ping event from GitHub
        if event_type == 'ping':
            logger.info("Received GitHub webhook ping - webhook is configured correctly")
            return jsonify({
                'message': 'Webhook ping received successfully',
                'delivery_id': delivery_id
            }), 200
        
        # Get JSON payload
        payload = request.get_json()
        if not payload:
            logger.warning("No JSON payload received")
            return jsonify({'error': 'No JSON payload'}), 400
        
        # Log the repository information
        repository = payload.get('repository', {})
        repo_name = repository.get('name', 'Unknown')
        repo_owner = repository.get('owner', {}).get('login', 'Unknown')
        repo_full_name = f"{repo_owner}/{repo_name}"
        
        logger.info(f"Processing {event_type} event for repository: {repo_full_name}")
        
        # Process different event types
        webhook_event = None
        
        if event_type == 'push':
            # Handle push events
            ref = payload.get('ref', '')
            # Skip tag pushes, only process branch pushes
            if not ref.startswith('refs/heads/'):
                logger.info(f"Ignoring push to {ref} (not a branch)")
                return jsonify({
                    'message': f'Ignored push to {ref} (not a branch)',
                    'repository': repo_full_name,
                    'delivery_id': delivery_id
                }), 200
            
            webhook_event = WebhookEvent.from_github_push(payload)
            logger.info(f"Push event: {webhook_event.author} -> {webhook_event.to_branch} in {webhook_event.repository_name}")
            
        elif event_type == 'pull_request':
            # Handle pull request events
            action = payload.get('action')
            logger.info(f"Pull request action: {action}")
            
            if action == 'opened':
                # Pull request opened
                webhook_event = WebhookEvent.from_github_pull_request(payload)
                logger.info(f"PR opened: {webhook_event.author} - {webhook_event.from_branch} -> {webhook_event.to_branch}")
                
            elif action == 'closed' and payload['pull_request'].get('merged'):
                # Pull request merged
                webhook_event = WebhookEvent.from_github_merge(payload)
                logger.info(f"PR merged: {webhook_event.author} - {webhook_event.from_branch} -> {webhook_event.to_branch}")
            
            else:
                logger.info(f"Ignoring pull request action: {action}")
                return jsonify({
                    'message': f'Ignored pull request action: {action}',
                    'repository': repo_full_name,
                    'delivery_id': delivery_id
                }), 200
        
        else:
            logger.info(f"Ignoring event type: {event_type}")
            return jsonify({
                'message': f'Event type {event_type} not handled',
                'repository': repo_full_name,
                'delivery_id': delivery_id,
                'supported_events': ['push', 'pull_request', 'ping']
            }), 200
        
        # Save the webhook event to MongoDB
        if webhook_event:
            event_id = webhook_event.save()
            logger.info(f"Event saved successfully with ID: {event_id}")
            
            # Log detailed event information
            logger.info(f"Event Details - ID: {event_id}, Action: {webhook_event.action}, "
                       f"Author: {webhook_event.author}, Repository: {webhook_event.repository_name}")
            
            return jsonify({
                'message': 'Webhook processed successfully',
                'event_id': str(event_id),
                'event_type': event_type,
                'action': webhook_event.action,
                'repository': repo_full_name,
                'author': webhook_event.author,
                'delivery_id': delivery_id,
                'timestamp': webhook_event.timestamp.isoformat()
            }), 200
        
        return jsonify({
            'message': 'No event processed',
            'repository': repo_full_name,
            'delivery_id': delivery_id
        }), 200
        
    except ValueError as e:
        logger.error(f"Validation error: {str(e)}")
        return jsonify({'error': f'Validation error: {str(e)}'}), 400
    
    except Exception as e:
        logger.error(f"Unexpected error processing webhook: {str(e)}")
        logger.exception("Full exception details:")
        return jsonify({
            'error': 'Internal server error',
            'delivery_id': delivery_id if 'delivery_id' in locals() else None
        }), 500

@webhook.route('/test', methods=['POST'])
def test_receiver():
    """
    Enhanced test endpoint for manual testing with realistic data
    """
    try:
        # Get test type from request or default
        test_data = request.get_json() or {}
        test_type = test_data.get('type', 'push')
        
        # Generate unique test data based on current time
        from datetime import datetime
        timestamp_str = datetime.now().strftime("%H%M%S")
        
        if test_type == 'push':
            test_event = WebhookEvent(
                request_id=f'test{timestamp_str}',
                author='TestDeveloper',
                action='PUSH',
                to_branch=f'feature/test-{timestamp_str}',
                repository_name='test-action-repo',
                repository_url='https://github.com/testuser/test-action-repo',
                commit_message=f'Test commit at {datetime.now().strftime("%H:%M:%S")}',
                timestamp=None  # Will use current time
            )
        elif test_type == 'pull_request':
            test_event = WebhookEvent(
                request_id=f'pr{timestamp_str}',
                author='TestDeveloper',
                action='PULL_REQUEST',
                from_branch=f'feature/test-{timestamp_str}',
                to_branch='main',
                repository_name='test-action-repo',
                repository_url='https://github.com/testuser/test-action-repo',
                pull_request_title=f'Test PR created at {datetime.now().strftime("%H:%M:%S")}',
                timestamp=None
            )
        elif test_type == 'merge':
            test_event = WebhookEvent(
                request_id=f'merge{timestamp_str}',
                author='TestMaintainer',
                action='MERGE',
                from_branch=f'feature/test-{timestamp_str}',
                to_branch='main',
                repository_name='test-action-repo',
                repository_url='https://github.com/testuser/test-action-repo',
                pull_request_title=f'Test merge at {datetime.now().strftime("%H:%M:%S")}',
                timestamp=None
            )
        else:
            return jsonify({'error': f'Unknown test type: {test_type}'}), 400
        
        event_id = test_event.save()
        logger.info(f"Test {test_type} event created with ID: {event_id}")
        
        return jsonify({
            'message': f'Test {test_type} event created successfully',
            'event_id': str(event_id),
            'action': test_event.action,
            'author': test_event.author,
            'repository': test_event.repository_name,
            'timestamp': test_event.timestamp.isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"Error creating test event: {str(e)}")
        return jsonify({'error': 'Failed to create test event'}), 500

@webhook.route('/debug', methods=['GET'])
def debug_events():
    """
    Debug endpoint to see recent events in JSON format
    """
    try:
        events = WebhookEvent.get_recent_events(limit=10)
        formatted_events = []
        
        for event in events:
            # Convert ObjectId to string for JSON serialization
            event['_id'] = str(event['_id'])
            # Convert datetime to string
            if 'timestamp' in event:
                event['timestamp'] = event['timestamp'].isoformat()
            formatted_events.append(event)
        
        return jsonify({
            'success': True,
            'events': formatted_events,
            'count': len(formatted_events),
            'webhook_configured': current_app.config.get('GITHUB_WEBHOOK_SECRET') is not None,
            'debug_info': {
                'total_events': len(formatted_events),
                'latest_event': formatted_events[0] if formatted_events else None,
                'unique_authors': list(set(event.get('author', 'Unknown') for event in formatted_events)),
                'event_types': list(set(event.get('action', 'Unknown') for event in formatted_events))
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Error in debug endpoint: {str(e)}")
        return jsonify({'error': 'Debug endpoint failed'}), 500

@webhook.route('/status', methods=['GET'])
def webhook_status():
    """
    Status endpoint to check webhook configuration and connectivity
    """
    try:
        from app.extensions import get_collection
        
        # Check MongoDB connectivity
        collection = get_collection(WebhookEvent.COLLECTION_NAME)
        event_count = collection.count_documents({})
        
        # Get latest event
        latest_events = WebhookEvent.get_recent_events(limit=1)
        latest_event = latest_events[0] if latest_events else None
        
        status_info = {
            'webhook_endpoint': f"{request.host_url}webhook/receiver",
            'database_connected': True,
            'total_events': event_count,
            'webhook_secret_configured': current_app.config.get('GITHUB_WEBHOOK_SECRET') is not None,
            'latest_event': {
                'id': str(latest_event['_id']) if latest_event else None,
                'action': latest_event.get('action') if latest_event else None,
                'author': latest_event.get('author') if latest_event else None,
                'timestamp': latest_event['timestamp'].isoformat() if latest_event else None
            } if latest_event else None,
            'supported_events': ['push', 'pull_request', 'ping'],
            'status': 'healthy'
        }
        
        return jsonify(status_info), 200
        
    except Exception as e:
        logger.error(f"Error in status endpoint: {str(e)}")
        return jsonify({
            'status': 'error',
            'error': str(e),
            'database_connected': False
        }), 500