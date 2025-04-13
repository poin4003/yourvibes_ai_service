from flask import Blueprint, request, jsonify
from models.image_moderator import ImageModerator
import asyncio
import concurrent.futures
import tempfile
import os

bp = Blueprint("image_api", __name__)
moderator = ImageModerator()
executor = concurrent.futures.ThreadPoolExecutor()

@bp.route("/moderate/image", methods=["POST"])
async def moderate_image():
    if 'image' not in request.files:
        return jsonify({"error": "No image file provided"}), 400

    file = request.files['image']
    suffix = os.path.splitext(file.filename)[1]
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        file.save(tmp.name)
        file_path = tmp.name

    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(executor, moderator.moderate, file_path)
    os.remove(file_path)

    return jsonify(result)