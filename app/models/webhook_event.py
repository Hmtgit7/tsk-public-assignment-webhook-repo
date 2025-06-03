from datetime import datetime
from app.extensions import get_collection
from bson import ObjectId
import logging

logger = logging.getLogger(__name__)

class WebhookEvent:
    COLLECTION_NAME = 'webhook_events'
    
    def __init__(self, request_id, author, action, from_branch=None, to_branch=None, timestamp=None):
        self.request_id = request_id
        self.author = author
        self.action = action
        self.from_branch = from_branch
        self.to_branch = to_branch
        self.timestamp = timestamp or datetime.utcnow()
    
    def to_dict(self):
        """Convert to dictionary for MongoDB storage"""
        return {
            'request_id': self.request_id,
            'author': self.author,
            'action': self.action,
            'from_branch': self.from_branch,
            'to_branch': self.to_branch,
            'timestamp': self.timestamp
        }
    
    def save(self):
        """Save event to MongoDB"""
        try:
            collection = get_collection(self.COLLECTION_NAME)
            result = collection.insert_one(self.to_dict())
            logger.info(f"Webhook event saved with ID: {result.inserted_id}")
            return result.inserted_id
        except Exception as e:
            logger.error(f"Error saving webhook event: {str(e)}")
            raise
    
    @staticmethod
    def get_recent_events(limit=50):
        """Get recent webhook events from MongoDB"""
        try:
            collection = get_collection(WebhookEvent.COLLECTION_NAME)
            events = collection.find().sort('timestamp', -1).limit(limit)
            return list(events)
        except Exception as e:
            logger.error(f"Error fetching webhook events: {str(e)}")
            return []
    
    @staticmethod
    def format_message(event):
        """Format event message for display"""
        try:
            author = event['author']
            action = event['action']
            timestamp = event['timestamp']
            from_branch = event.get('from_branch')
            to_branch = event.get('to_branch')
            
            # Format timestamp
            if isinstance(timestamp, datetime):
                formatted_time = timestamp.strftime("%d %B %Y - %I:%M %p UTC")
            else:
                formatted_time = str(timestamp)
            
            # Format message based on action type
            if action == 'PUSH':
                return f'"{author}" pushed to "{to_branch}" on {formatted_time}'
            elif action == 'PULL_REQUEST':
                return f'"{author}" submitted a pull request from "{from_branch}" to "{to_branch}" on {formatted_time}'
            elif action == 'MERGE':
                return f'"{author}" merged branch "{from_branch}" to "{to_branch}" on {formatted_time}'
            else:
                return f'"{author}" performed {action} on {formatted_time}'
                
        except Exception as e:
            logger.error(f"Error formatting message: {str(e)}")
            return "Error formatting event message"
    
    @staticmethod
    def from_github_push(payload):
        """Create WebhookEvent from GitHub push payload"""
        try:
            return WebhookEvent(
                request_id=payload.get('after', ''),  # commit hash
                author=payload['pusher']['name'],
                action='PUSH',
                to_branch=payload['ref'].split('/')[-1],  # Extract branch name from refs/heads/branch
                timestamp=datetime.utcnow()
            )
        except KeyError as e:
            logger.error(f"Missing key in push payload: {str(e)}")
            raise ValueError(f"Invalid push payload: missing {str(e)}")
    
    @staticmethod
    def from_github_pull_request(payload):
        """Create WebhookEvent from GitHub pull request payload"""
        try:
            pr = payload['pull_request']
            return WebhookEvent(
                request_id=str(pr['id']),
                author=pr['user']['login'],
                action='PULL_REQUEST',
                from_branch=pr['head']['ref'],
                to_branch=pr['base']['ref'],
                timestamp=datetime.utcnow()
            )
        except KeyError as e:
            logger.error(f"Missing key in pull request payload: {str(e)}")
            raise ValueError(f"Invalid pull request payload: missing {str(e)}")
    
    @staticmethod
    def from_github_merge(payload):
        """Create WebhookEvent from GitHub merge payload (pull request merged)"""
        try:
            pr = payload['pull_request']
            return WebhookEvent(
                request_id=str(pr['id']),
                author=pr['merged_by']['login'] if pr['merged_by'] else pr['user']['login'],
                action='MERGE',
                from_branch=pr['head']['ref'],
                to_branch=pr['base']['ref'],
                timestamp=datetime.utcnow()
            )
        except KeyError as e:
            logger.error(f"Missing key in merge payload: {str(e)}")
            raise ValueError(f"Invalid merge payload: missing {str(e)}")