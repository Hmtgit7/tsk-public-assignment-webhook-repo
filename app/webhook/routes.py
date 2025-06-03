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
    Handles Push, Pull Request, and Merge events
    """
    try:
        # Get the GitHub event type from headers
        event_type = request.headers.get('X-GitHub-Event')
        delivery_id = request.headers.get('X-GitHub-Delivery')
        signature = request.headers.get('X-Hub-Signature-256')
        user_agent = request.headers.get('User-Agent', '')
        
        logger.info(f"Received webhook - Event: {event_type}, Delivery ID: {delivery_id}")
        
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
            logger.info(f"Push event processed: {webhook_event.author} -> {webhook_event.to_branch}")
            
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