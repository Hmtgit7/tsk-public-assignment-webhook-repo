# GitHub Webhook Monitor

A complete Flask-based webhook receiver that captures GitHub events (Push, Pull Request, Merge) and displays them in a real-time web interface. Built for the TechStaX Developer Assessment.

![GitHub Webhook Monitor](assets/image.png)

## 🚀 Live Demo

- **Live Application**: https://tsk-public-assignment-webhook-repo.onrender.com/
- **Repository**: https://github.com/Hmtgit7/tsk-public-assignment-webhook-repo
- **Webhook Endpoint**: `https://tsk-public-assignment-webhook-repo.onrender.com/webhook/receiver`

## ✨ Features

- 🔄 **Real-time webhook event processing** for GitHub Push, Pull Request, and Merge events
- 📊 **Live dashboard** with event monitoring and statistics
- 🎨 **Modern, responsive UI** with auto-refresh every 15 seconds
- 📱 **Mobile-friendly design** that works on all devices
- 💾 **MongoDB Atlas integration** for persistent event storage
- 🔐 **Secure webhook validation** with GitHub webhook secrets
- ☁️ **Production deployment** on Render with automatic scaling

## 🏗️ Architecture

```
GitHub Repository → Webhook → Flask App → MongoDB Atlas → Web Dashboard
```

## 📁 Project Structure

```
tsk-public-assignment-webhook-repo/
├── app/
│   ├── __init__.py              # Flask app factory
│   ├── extensions.py            # MongoDB setup
│   ├── webhook/
│   │   ├── __init__.py
│   │   └── routes.py           # Webhook receiver endpoints
│   ├── api/
│   │   ├── __init__.py
│   │   └── routes.py           # API endpoints for frontend
│   ├── models/
│   │   ├── __init__.py
│   │   └── webhook_event.py    # Data models and MongoDB operations
│   ├── static/
│   │   ├── css/
│   │   │   └── style.css       # Modern styling with gradients
│   │   └── js/
│   │       └── main.js         # Real-time frontend JavaScript
│   └── templates/
│       └── index.html          # Responsive web interface
├── requirements.txt             # Python dependencies
├── run.py                      # Development server entry point
├── wsgi.py                     # Production server entry point
├── config.py                   # Configuration management
├── .env.example               # Environment variables template
└── README.md                  # This file
```

## 🛠️ Installation & Setup

### Prerequisites

- Python 3.8+
- MongoDB Atlas account (free tier available)
- Git

### 1. Clone the Repository

```bash
git clone https://github.com/Hmtgit7/tsk-public-assignment-webhook-repo.git
cd tsk-public-assignment-webhook-repo
```

### 2. Set Up Virtual Environment

#### On Windows (PowerShell - Recommended):
```powershell
python -m venv venv
venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

#### On macOS/Linux:
```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Configure Environment Variables

Create a `.env` file in the project root:

```bash
# Flask Configuration
FLASK_CONFIG=development
FLASK_DEBUG=True
SECRET_KEY=a1b2c3d4e5f6789012345678901234567890abcdef1234567890abcdef123456

# MongoDB Configuration (MongoDB Atlas)
MONGO_URI=mongodb+srv://your-username:your-password@cluster0.mongodb.net/webhook_db?retryWrites=true&w=majority

# GitHub Webhook Configuration
GITHUB_WEBHOOK_SECRET=your-webhook-secret-here

# Server Configuration
HOST=127.0.0.1
PORT=5000

# CORS Configuration
CORS_ORIGINS=*
```

### 4. Set Up MongoDB Atlas

1. **Create Account**: Go to [MongoDB Atlas](https://www.mongodb.com/atlas)
2. **Create Cluster**: Choose the free M0 Sandbox tier
3. **Create Database User**: Set username and password
4. **Network Access**: Add `0.0.0.0/0` to allow access from anywhere
5. **Get Connection String**: Copy and update your `MONGO_URI` in `.env`

### 5. Run the Application

```bash
python run.py
```

The application will start at `http://127.0.0.1:5000`

## 🔗 GitHub Webhook Configuration

### Set Up Action Repository

Create a separate repository for testing webhook events:

```bash
# Create a new repository on GitHub called 'action-repo'
git clone https://github.com/yourusername/action-repo.git
cd action-repo
echo "# Test Repository" > README.md
git add .
git commit -m "Initial commit"
git push origin main
```

### Configure Webhook in GitHub

1. Go to your action repository on GitHub
2. Navigate to **Settings** → **Webhooks** → **Add webhook**
3. Configure:
   - **Payload URL**: `https://tsk-public-assignment-webhook-repo.onrender.com/webhook/receiver`
   - **Content type**: `application/json`
   - **Secret**: Use the same value as `GITHUB_WEBHOOK_SECRET` in your environment
   - **Events**: Select "Pushes" and "Pull requests"
4. Click **Add webhook**

## 📊 Event Formats

The application displays events in the following formats:

- **Push Event**: `"John Doe" pushed to "main" on 3rd June 2025 - 10:30 AM UTC`
- **Pull Request**: `"Jane Smith" submitted a pull request from "feature" to "main" on 3rd June 2025 - 9:15 AM UTC`
- **Merge Event**: `"John Doe" merged branch "feature" to "main" on 3rd June 2025 - 11:45 AM UTC`

## 🗄️ MongoDB Schema

```javascript
{
  _id: ObjectId,
  request_id: String,        // Git commit hash or PR ID
  author: String,            // GitHub username
  action: String,            // "PUSH", "PULL_REQUEST", "MERGE"
  from_branch: String,       // Source branch (for PR/Merge)
  to_branch: String,         // Target branch
  timestamp: DateTime        // Event timestamp
}
```

## 🌐 API Endpoints

### Webhook Endpoints
- `POST /webhook/receiver` - Main GitHub webhook receiver
- `POST /webhook/test` - Test endpoint for manual testing

### API Endpoints
- `GET /api/events` - Get all recent events
- `GET /api/events/count` - Get total event count
- `GET /api/events/latest` - Get latest event

### Web Interface
- `GET /` - Main dashboard
- `GET /health` - Health check endpoint

## 🧪 Testing

### Manual Testing

1. **Test webhook endpoint:**
```bash
curl -X POST https://tsk-public-assignment-webhook-repo.onrender.com/webhook/test
```

2. **Check events API:**
```bash
curl https://tsk-public-assignment-webhook-repo.onrender.com/api/events
```

### GitHub Events Testing

1. **Push Event:**
```bash
cd action-repo
echo "Test push" >> test.txt
git add test.txt
git commit -m "Test push event"
git push origin main
```

2. **Pull Request Event:**
```bash
git checkout -b feature-branch
echo "Feature change" >> feature.txt
git add feature.txt
git commit -m "Add feature"
git push origin feature-branch
# Create PR via GitHub UI
```

3. **Merge Event:**
```bash
# Merge the PR via GitHub UI
```

## 🚀 Deployment

### Production (Render)

The application is deployed on Render with the following configuration:

1. **Build Command**: `pip install -r requirements.txt`
2. **Start Command**: `gunicorn wsgi:app`
3. **Environment Variables**:
   ```
   SECRET_KEY=production-secret-key
   FLASK_CONFIG=production
   FLASK_DEBUG=False
   MONGO_URI=mongodb+srv://...
   GITHUB_WEBHOOK_SECRET=webhook-secret
   ```

### Local Development

```bash
# Development server
python run.py

# Production-like server (using gunicorn)
gunicorn wsgi:app
```

## 🔧 Configuration

### Environment Variables

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `FLASK_CONFIG` | Configuration mode (`development`/`production`) | No | `development` |
| `FLASK_DEBUG` | Enable debug mode | No | `True` |
| `SECRET_KEY` | Flask secret key for sessions | Yes | - |
| `MONGO_URI` | MongoDB connection string | Yes | - |
| `GITHUB_WEBHOOK_SECRET` | Webhook signature verification | No | - |
| `HOST` | Server host address | No | `127.0.0.1` |
| `PORT` | Server port | No | `5000` |
| `CORS_ORIGINS` | Allowed CORS origins | No | `*` |

### File Structure Details

- **`wsgi.py`**: Production WSGI entry point for Render deployment
- **`run.py`**: Development server with detailed configuration
- **`config.py`**: Environment-based configuration management
- **`app/__init__.py`**: Flask application factory pattern
- **`app/models/webhook_event.py`**: MongoDB data models and operations
- **`app/webhook/routes.py`**: Webhook receiver logic
- **`app/api/routes.py`**: REST API endpoints
- **`app/static/`**: Frontend assets (CSS/JS)
- **`app/templates/`**: HTML templates

## ⚡ Performance Features

- **Real-time Updates**: 15-second polling with visual feedback
- **Responsive Design**: Mobile-first approach with modern CSS
- **Error Handling**: Comprehensive error handling and logging
- **MongoDB Indexing**: Optimized queries for better performance
- **Production Ready**: Gunicorn WSGI server configuration

## 🔐 Security

- **Webhook Signature Verification**: Optional GitHub webhook secret validation
- **Environment Variables**: Sensitive data stored in environment variables
- **CORS Configuration**: Configurable cross-origin resource sharing
- **Input Validation**: Robust payload validation and error handling

## 📱 Frontend Features

- **Modern UI**: Gradient backgrounds and smooth animations
- **Real-time Updates**: Auto-refresh every 15 seconds
- **Status Indicators**: Connection status and last update time
- **Event Statistics**: Total events and refresh rate display
- **Copy Webhook URL**: Easy webhook URL copying functionality
- **Responsive Design**: Works on desktop, tablet, and mobile

## 🛠️ Technology Stack

- **Backend**: Flask, Python 3.8+
- **Database**: MongoDB Atlas (Cloud)
- **Frontend**: HTML5, CSS3, Vanilla JavaScript
- **Deployment**: Render (Cloud Platform)
- **Process Manager**: Gunicorn WSGI Server

## 📋 Requirements Met

This implementation satisfies all TechStaX assessment requirements:

- ✅ **GitHub Webhook Integration**: Receives Push, Pull Request, and Merge events
- ✅ **MongoDB Storage**: Persistent event storage with proper schema
- ✅ **Real-time UI**: 15-second polling with formatted event display
- ✅ **Clean Design**: Modern, responsive interface
- ✅ **Production Deployment**: Live on Render with proper configuration
- ✅ **Two Repositories**: Webhook receiver and action repository setup

## 🤝 Contributing

1. Fork the repository
2. Create feature branch: `git checkout -b feature-name`
3. Commit changes: `git commit -am 'Add feature'`
4. Push to branch: `git push origin feature-name`
5. Submit pull request

## 📄 License

This project is licensed under the MIT License.

## 🙏 Acknowledgments

- **TechStaX** for the development assessment opportunity
- **Flask** framework and ecosystem
- **MongoDB Atlas** for cloud database services
- **Render** for reliable deployment platform
- **GitHub** for webhook infrastructure

---

**Live Demo**: https://tsk-public-assignment-webhook-repo.onrender.com/

**Webhook URL**: https://tsk-public-assignment-webhook-repo.onrender.com/webhook/receiver