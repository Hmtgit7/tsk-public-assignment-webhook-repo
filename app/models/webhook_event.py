# app/models/webhook_event.py
from datetime import datetime
from app.extensions import get_collection
from bson import ObjectId
import logging

logger = logging.getLogger(__name__)

class WebhookEvent:
    COLLECTION_NAME = 'webhook_events'
    
    def __init__(self, request_id, author, action, from_branch=None, to_branch=None, 
                 repository_name=None, repository_url=None, commit_message=None, 
                 pull_request_title=None, timestamp=None):
        self.request_id = request_id
        self.author = author
        self.action = action
        self.from_branch = from_branch
        self.to_branch = to_branch
        self.repository_name = repository_name
        self.repository_url = repository_url
        self.commit_message = commit_message
        self.pull_request_title = pull_request_title
        self.timestamp = timestamp or datetime.utcnow()
    
    def to_dict(self):
        """Convert to dictionary for MongoDB storage"""
        return {
            'request_id': self.request_id,
            'author': self.author,
            'action': self.action,
            'from_branch': self.from_branch,
            'to_branch': self.to_branch,
            'repository_name': self.repository_name,
            'repository_url': self.repository_url,
            'commit_message': self.commit_message,
            'pull_request_title': self.pull_request_title,
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
        """Format event message for display with enhanced details"""
        try:
            author = event['author']
            action = event['action']
            timestamp = event['timestamp']
            from_branch = event.get('from_branch')
            to_branch = event.get('to_branch')
            repository_name = event.get('repository_name', 'Unknown Repository')
            commit_message = event.get('commit_message')
            pull_request_title = event.get('pull_request_title')
            
            # Format timestamp
            if isinstance(timestamp, datetime):
                formatted_time = timestamp.strftime("%d %B %Y - %I:%M %p UTC")
            else:
                formatted_time = str(timestamp)
            
            # Format message based on action type with enhanced details
            if action == 'PUSH':
                base_message = f'"{author}" pushed to "{to_branch}" in "{repository_name}" on {formatted_time}'
                if commit_message:
                    base_message += f' - "{commit_message}"'
                return base_message
                
            elif action == 'PULL_REQUEST':
                base_message = f'"{author}" submitted a pull request from "{from_branch}" to "{to_branch}" in "{repository_name}" on {formatted_time}'
                if pull_request_title:
                    base_message += f' - "{pull_request_title}"'
                return base_message
                
            elif action == 'MERGE':
                base_message = f'"{author}" merged branch "{from_branch}" to "{to_branch}" in "{repository_name}" on {formatted_time}'
                if pull_request_title:
                    base_message += f' - "{pull_request_title}"'
                return base_message
            else:
                return f'"{author}" performed {action} in "{repository_name}" on {formatted_time}'
                
        except Exception as e:
            logger.error(f"Error formatting message: {str(e)}")
            return "Error formatting event message"
    
    @staticmethod
    def from_github_push(payload):
        """Create WebhookEvent from GitHub push payload with enhanced data extraction"""
        try:
            # Extract commit message from the latest commit
            commit_message = None
            if payload.get('commits') and len(payload['commits']) > 0:
                commit_message = payload['commits'][0].get('message', '')[:100]  # Limit to 100 chars
            
            # Extract repository information
            repository = payload.get('repository', {})
            repository_name = repository.get('name', 'Unknown')
            repository_url = repository.get('html_url', '')
            
            # Extract branch name properly
            ref = payload.get('ref', '')
            branch_name = ref.split('/')[-1] if ref.startswith('refs/heads/') else ref
            
            return WebhookEvent(
                request_id=payload.get('after', '')[:12],  # Short commit hash
                author=payload['pusher']['name'],
                action='PUSH',
                to_branch=branch_name,
                repository_name=repository_name,
                repository_url=repository_url,
                commit_message=commit_message,
                timestamp=datetime.utcnow()
            )
        except KeyError as e:
            logger.error(f"Missing key in push payload: {str(e)}")
            raise ValueError(f"Invalid push payload: missing {str(e)}")
    
    @staticmethod
    def from_github_pull_request(payload):
        """Create WebhookEvent from GitHub pull request payload with enhanced data"""
        try:
            pr = payload['pull_request']
            repository = payload.get('repository', {})
            
            return WebhookEvent(
                request_id=str(pr['id']),
                author=pr['user']['login'],
                action='PULL_REQUEST',
                from_branch=pr['head']['ref'],
                to_branch=pr['base']['ref'],
                repository_name=repository.get('name', 'Unknown'),
                repository_url=repository.get('html_url', ''),
                pull_request_title=pr.get('title', '')[:100],  # Limit to 100 chars
                timestamp=datetime.utcnow()
            )
        except KeyError as e:
            logger.error(f"Missing key in pull request payload: {str(e)}")
            raise ValueError(f"Invalid pull request payload: missing {str(e)}")
    
    @staticmethod
    def from_github_merge(payload):
        """Create WebhookEvent from GitHub merge payload with enhanced data"""
        try:
            pr = payload['pull_request']
            repository = payload.get('repository', {})
            
            return WebhookEvent(
                request_id=str(pr['id']),
                author=pr['merged_by']['login'] if pr['merged_by'] else pr['user']['login'],
                action='MERGE',
                from_branch=pr['head']['ref'],
                to_branch=pr['base']['ref'],
                repository_name=repository.get('name', 'Unknown'),
                repository_url=repository.get('html_url', ''),
                pull_request_title=pr.get('title', '')[:100],
                timestamp=datetime.utcnow()
            )
        except KeyError as e:
            logger.error(f"Missing key in merge payload: {str(e)}")
            raise ValueError(f"Invalid merge payload: missing {str(e)}")