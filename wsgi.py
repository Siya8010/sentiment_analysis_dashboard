"""
WSGI Entry Point
Production server entry point for Gunicorn
"""

import os
from app import app

if __name__ == "__main__":
    # Get configuration
    port = int(os.getenv('PORT', 5000))
    host = os.getenv('HOST', '0.0.0.0')
    
    app.run(host=host, port=port)