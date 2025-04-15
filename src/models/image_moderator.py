import requests
from transformers import AutoProcessor, AutoModelForImageClassification, CLIPProcessor, CLIPModel
from PIL import Image
import torch
import os
import uuid
from moviepy.editor import VideoFileClip
from statistics import mean

class ImageModerator:
    def __init__(self):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.nsfw_model = AutoModelForImageClassification.from_pretrained("Falconsai/nsfw_image_detection").to(self.device)
        self.nsfw_processor = AutoProcessor.from_pretrained("Falconsai/nsfw_image_detection")
        self.nsfw_labels = ["normal", "nsfw"]

        self.clip_model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32").to(self.device)
        self.clip_processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")
        self.violence_labels = ["normal", "violence"]
        self.political_labels = ["normal", "political"]
        self.violence_threshold = 0.7  
        self.political_threshold = 0.7

    def _fetch_media(self, base_url: str, media_filename: str) -> str:
        """Lấy dữ liệu media từ API HTTP và lưu vào file tạm trong src/temp."""
        try:
            media_url = f"{base_url}{media_filename}"
            print(f"Fetching media from: {media_url}", flush=True)

            headers = {"Range": "bytes=0-"}
            response = requests.get(media_url, headers=headers, stream=True, timeout=10)
            print(f"Response status: {response.status_code}", flush=True)
            print(f"Response headers: {response.headers}", flush=True)
            response.raise_for_status()

            content_length = int(response.headers.get("Content-Length", 0))
            print(f"Content-Length: {content_length}", flush=True)
            if content_length == 0:
                raise ValueError("Received empty data from API")

            temp_dir = os.path.join("src", "temp")
            os.makedirs(temp_dir, exist_ok=True)
            print(f"Using temporary directory: {temp_dir}", flush=True)

            suffix = os.path.splitext(media_filename)[1]
            temp_filename = f"temp_{uuid.uuid4().hex}{suffix}"
            tmp_path = os.path.join(temp_dir, temp_filename)

            total_size = 0
            with open(tmp_path, "wb") as tmp_file:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        tmp_file.write(chunk)
                        total_size += len(chunk)

            if total_size == 0:
                os.remove(tmp_path)
                raise ValueError("Failed to download media: empty file")

            print(f"Saved temporary file at: {tmp_path} (size: {total_size} bytes)", flush=True)
            return tmp_path

        except requests.exceptions.RequestException as e:
            print(f"Error fetching media {media_filename}: {e}", flush=True)
            raise
        except Exception as e:
            print(f"Error saving media {media_filename}: {e}", flush=True)
            raise

    def moderate_image(self, image_path: str) -> dict:
        """Kiểm tra hình ảnh (được gọi từ file tạm)."""
        try:
            print(f"Opening image: {image_path}", flush=True)
            image = Image.open(image_path).convert("RGB")
            print(f"Image opened successfully: {image_path}", flush=True)
        except Exception as e:
            print(f"Error opening image {image_path}: {e}", flush=True)
            raise

        print(f"Processing NSFW detection for: {image_path}", flush=True)
        inputs_nsfw = self.nsfw_processor(images=image, return_tensors="pt").to(self.device)
        outputs_nsfw = self.nsfw_model(**inputs_nsfw)
        probs_nsfw = outputs_nsfw.logits.softmax(dim=1).tolist()[0]
        nsfw_label = self.nsfw_labels[probs_nsfw.index(max(probs_nsfw))]
        nsfw_score = max(probs_nsfw)
        print(f"NSFW detection result: label={nsfw_label}, score={nsfw_score}", flush=True)

        if nsfw_label == "nsfw":
            return {"label": "nsfw", "score": round(nsfw_score, 4)}

        print(f"Processing violence detection for: {image_path}", flush=True)
        inputs_clip_violence = self.clip_processor(text=self.violence_labels, images=image, return_tensors="pt", padding=True).to(self.device)
        outputs_clip_violence = self.clip_model(**inputs_clip_violence)
        probs_clip_violence = outputs_clip_violence.logits_per_image.softmax(dim=1).tolist()[0]
        violence_label = self.violence_labels[probs_clip_violence.index(max(probs_clip_violence))]
        violence_score = max(probs_clip_violence)
        print(f"Violence detection result: label={violence_label}, score={violence_score}", flush=True)

        if violence_label == "violence" and violence_score > self.violence_threshold:
            return {"label": "violence", "score": round(violence_score, 4)}

        print(f"Processing political detection for: {image_path}", flush=True)
        inputs_clip_political = self.clip_processor(text=self.political_labels, images=image, return_tensors="pt", padding=True).to(self.device)
        outputs_clip_political = self.clip_model(**inputs_clip_political)
        probs_clip_political = outputs_clip_political.logits_per_image.softmax(dim=1).tolist()[0]
        political_label = self.political_labels[probs_clip_political.index(max(probs_clip_political))]
        political_score = max(probs_clip_political)
        print(f"Political detection result: label={political_label}, score={political_score}", flush=True)

        if political_label == "political" and political_score > self.political_threshold:
            return {"label": "political", "score": round(political_score, 4)}

        return {"label": "normal", "score": round(nsfw_score, 4)}

    def moderate(self, base_url: str, media_filename: str) -> dict:
        """Kiểm tra media (ảnh hoặc video) từ HTTP API."""
        try:
            temp_path = self._fetch_media(base_url, media_filename)
            try:
                if media_filename.lower().endswith((".mp4", ".m4v", ".mov", ".avi", ".mkv")):
                    return self._moderate_video(temp_path)
                else:
                    return self.moderate_image(temp_path)
            finally:
                if os.path.exists(temp_path):
                    print(f"Removing temporary file: {temp_path}", flush=True)
                    os.remove(temp_path)
        except Exception as e:
            print(f"Failed to moderate media {media_filename}: {e}", flush=True)
            return {"label": "error", "score": 0.0}

    def _moderate_video(self, video_path: str, num_frames: int = 3) -> dict:
        """Kiểm tra video."""
        try:
            clip = VideoFileClip(video_path)
        except Exception as e:
            print(f"Error opening video {video_path}: {e}", flush=True)
            raise

        duration = clip.duration
        timestamps = [duration * i / (num_frames + 1) for i in range(1, num_frames + 1)]

        temp_dir = os.path.join("src", "temp")
        os.makedirs(temp_dir, exist_ok=True)
        print(f"Using temporary directory for frames: {temp_dir}", flush=True)

        temp_files = []
        for t in timestamps:
            frame = clip.get_frame(t)
            temp_filename = f"frame_{uuid.uuid4().hex}.jpg"
            frame_path = os.path.join(temp_dir, temp_filename)
            Image.fromarray(frame).save(frame_path)
            print(f"Saved temporary frame at: {frame_path}", flush=True)
            temp_files.append(frame_path)

        results = []
        for path in temp_files:
            result = self.moderate_image(path)
            results.append(result)
            print(f"Removing temporary frame: {path}", flush=True)
            os.remove(path)

        clip.reader.close()
        if clip.audio:
            clip.audio.reader.close_proc()

        labels = [r["label"] for r in results]
        scores = [r["score"] for r in results]

        if "nsfw" in labels:
            final_label = "nsfw"
            final_score = mean([s for l, s in zip(labels, scores) if l == "nsfw"])
        elif "violence" in labels:
            final_label = "violence"
            final_score = mean([s for l, s in zip(labels, scores) if l == "violence"])
        elif "political" in labels:
            final_label = "political"
            final_score = mean([s for l, s in zip(labels, scores) if l == "political"])
        else:
            final_label = "normal"
            final_score = mean(scores)

        return {"label": final_label, "score": round(final_score, 4)}