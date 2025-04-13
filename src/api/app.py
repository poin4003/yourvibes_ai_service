from flask import Flask
from flask_cors import CORS
from api.image import bp as image_bp
from api.text import bp as text_bp

def create_app():
    app = Flask(__name__)
    CORS(app)

    app.register_blueprint(image_bp) 
    app.register_blueprint(text_bp)

    return app