from flask import Blueprint, request, jsonify
from models.text_moderator import TextModerator
import asyncio
import concurrent.futures

bp = Blueprint("text_api", __name__)
moderator = TextModerator()
executor = concurrent.futures.ThreadPoolExecutor()

@bp.route("/moderate/text", methods=["POST"])
async def moderate_text():
    data = request.get_json()
    text = data.get("text", "")
    if not text:
        return jsonify({"error": "No text provided"}), 400

    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(executor, moderator.moderate, text)
    return jsonify(result)
