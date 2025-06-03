# app/models/webhook_event.py
from datetime import datetime, timezone
from app.extensions import get_collection
from bson import ObjectId
import logging
import dateutil.parser

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
        # Use provided timestamp or current UTC time
        self.timestamp = timestamp if timestamp else datetime.now(timezone.utc)
    
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
        """Format event message for display with proper current time calculation"""
        try:
            author = event['author']
            action = event['action']
            timestamp = event['timestamp']
            from_branch = event.get('from_branch')
            to_branch = event.get('to_branch')
            repository_name = event.get('repository_name', 'Unknown Repository')
            commit_message = event.get('commit_message')
            pull_request_title = event.get('pull_request_title')
            
            # Calculate time difference from now
            now = datetime.now(timezone.utc)
            if isinstance(timestamp, datetime):
                # Ensure timezone awareness
                if timestamp.tzinfo is None:
                    timestamp = timestamp.replace(tzinfo=timezone.utc)
                time_diff = now - timestamp
                formatted_time = WebhookEvent._format_time_ago(time_diff)
            else:
                # Try to parse string timestamp
                try:
                    parsed_time = dateutil.parser.parse(timestamp)
                    if parsed_time.tzinfo is None:
                        parsed_time = parsed_time.replace(tzinfo=timezone.utc)
                    time_diff = now - parsed_time
                    formatted_time = WebhookEvent._format_time_ago(time_diff)
                except:
                    formatted_time = str(timestamp)
            
            # Format message based on action type
            if action == 'PUSH':
                base_message = f'"{author}" pushed to "{to_branch}" in "{repository_name}" {formatted_time}'
                if commit_message:
                    base_message += f' - "{commit_message}"'
                return base_message
                
            elif action == 'PULL_REQUEST':
                base_message = f'"{author}" submitted a pull request from "{from_branch}" to "{to_branch}" in "{repository_name}" {formatted_time}'
                if pull_request_title:
                    base_message += f' - "{pull_request_title}"'
                return base_message
                
            elif action == 'MERGE':
                base_message = f'"{author}" merged branch "{from_branch}" to "{to_branch}" in "{repository_name}" {formatted_time}'
                if pull_request_title:
                    base_message += f' - "{pull_request_title}"'
                return base_message
            else:
                return f'"{author}" performed {action} in "{repository_name}" {formatted_time}'
                
        except Exception as e:
            logger.error(f"Error formatting message: {str(e)}")
            return "Error formatting event message"
    
    @staticmethod
    def _format_time_ago(time_diff):
        """Format time difference as human-readable string"""
        total_seconds = int(time_diff.total_seconds())
        
        if total_seconds < 60:
            return "just now"
        elif total_seconds < 3600:  # Less than 1 hour
            minutes = total_seconds // 60
            return f"{minutes} minute{'s' if minutes > 1 else ''} ago"
        elif total_seconds < 86400:  # Less than 1 day
            hours = total_seconds // 3600
            return f"{hours} hour{'s' if hours > 1 else ''} ago"
        elif total_seconds < 604800:  # Less than 1 week
            days = total_seconds // 86400
            return f"{days} day{'s' if days > 1 else ''} ago"
        else:
            weeks = total_seconds // 604800
            return f"{weeks} week{'s' if weeks > 1 else ''} ago"
    
    @staticmethod
    def from_github_push(payload):
        """Create WebhookEvent from GitHub push payload using actual commit timestamp"""
        try:
            # Extract commit information from the latest commit
            commit_message = None
            commit_timestamp = None
            
            if payload.get('commits') and len(payload['commits']) > 0:
                latest_commit = payload['commits'][0]
                commit_message = latest_commit.get('message', '')[:100]
                
                # Use the actual commit timestamp from GitHub
                commit_timestamp_str = latest_commit.get('timestamp')
                if commit_timestamp_str:
                    try:
                        commit_timestamp = dateutil.parser.parse(commit_timestamp_str)
                        logger.info(f"Using GitHub commit timestamp: {commit_timestamp}")
                    except Exception as e:
                        logger.warning(f"Could not parse commit timestamp {commit_timestamp_str}: {e}")
                        commit_timestamp = datetime.now(timezone.utc)
                else:
                    # Fallback to webhook received time
                    commit_timestamp = datetime.now(timezone.utc)
            else:
                commit_timestamp = datetime.now(timezone.utc)
            
            # Extract repository information
            repository = payload.get('repository', {})
            repository_name = repository.get('name', 'Unknown')
            repository_url = repository.get('html_url', '')
            
            # Extract branch name properly
            ref = payload.get('ref', '')
            branch_name = ref.split('/')[-1] if ref.startswith('refs/heads/') else ref
            
            return WebhookEvent(
                request_id=payload.get('after', '')[:12],
                author=payload['pusher']['name'],
                action='PUSH',
                to_branch=branch_name,
                repository_name=repository_name,
                repository_url=repository_url,
                commit_message=commit_message,
                timestamp=commit_timestamp
            )
        except KeyError as e:
            logger.error(f"Missing key in push payload: {str(e)}")
            raise ValueError(f"Invalid push payload: missing {str(e)}")
    
    @staticmethod
    def from_github_pull_request(payload):
        """Create WebhookEvent from GitHub pull request payload"""
        try:
            pr = payload['pull_request']
            repository = payload.get('repository', {})
            
            # Use PR creation timestamp from GitHub
            pr_timestamp = datetime.now(timezone.utc)
            created_at = pr.get('created_at')
            if created_at:
                try:
                    pr_timestamp = dateutil.parser.parse(created_at)
                    logger.info(f"Using GitHub PR timestamp: {pr_timestamp}")
                except Exception as e:
                    logger.warning(f"Could not parse PR timestamp {created_at}: {e}")
            
            return WebhookEvent(
                request_id=str(pr['id']),
                author=pr['user']['login'],
                action='PULL_REQUEST',
                from_branch=pr['head']['ref'],
                to_branch=pr['base']['ref'],
                repository_name=repository.get('name', 'Unknown'),
                repository_url=repository.get('html_url', ''),
                pull_request_title=pr.get('title', '')[:100],
                timestamp=pr_timestamp
            )
        except KeyError as e:
            logger.error(f"Missing key in pull request payload: {str(e)}")
            raise ValueError(f"Invalid pull request payload: missing {str(e)}")
    
    @staticmethod
    def from_github_merge(payload):
        """Create WebhookEvent from GitHub merge payload"""
        try:
            pr = payload['pull_request']
            repository = payload.get('repository', {})
            
            # Use merge timestamp from GitHub
            merge_timestamp = datetime.now(timezone.utc)
            merged_at = pr.get('merged_at')
            if merged_at:
                try:
                    merge_timestamp = dateutil.parser.parse(merged_at)
                    logger.info(f"Using GitHub merge timestamp: {merge_timestamp}")
                except Exception as e:
                    logger.warning(f"Could not parse merge timestamp {merged_at}: {e}")
            
            return WebhookEvent(
                request_id=str(pr['id']),
                author=pr['merged_by']['login'] if pr['merged_by'] else pr['user']['login'],
                action='MERGE',
                from_branch=pr['head']['ref'],
                to_branch=pr['base']['ref'],
                repository_name=repository.get('name', 'Unknown'),
                repository_url=repository.get('html_url', ''),
                pull_request_title=pr.get('title', '')[:100],
                timestamp=merge_timestamp
            )
        except KeyError as e:
            logger.error(f"Missing key in merge payload: {str(e)}")
            raise ValueError(f"Invalid merge payload: missing {str(e)}")