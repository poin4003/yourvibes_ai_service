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
        self.abuse_labels = ["normal", "nude child", "child abuse", "child in swimsuit", "child in bikini", "child without clothes", "child shirtless", "child naked"]

        self.violence_threshold = 0.7
        self.political_threshold = 0.7
        self.abuse_threshold = 0.4

    def _fetch_media(self, base_url: str, media_filename: str) -> str:
        try:
            media_url = f"{base_url}{media_filename}"
            print(f"Fetching media from: {media_url}", flush=True)

            response = requests.get(media_url, stream=True, timeout=10)
            response.raise_for_status()

            first_chunk = next(response.iter_content(chunk_size=8192), None)
            if not first_chunk:
                raise ValueError("No data received")

            content_length = int(response.headers.get("Content-Length", 0))
            print(f"Content-Length: {content_length}", flush=True)

            temp_dir = os.path.join("src", "temp")
            os.makedirs(temp_dir, exist_ok=True)

            suffix = os.path.splitext(media_filename)[1]
            temp_filename = f"temp_{uuid.uuid4().hex}{suffix}"
            tmp_path = os.path.join(temp_dir, temp_filename)
            print(f"Saving to: {tmp_path}", flush=True)

            total_size = 0
            with open(tmp_path, "wb") as tmp_file:
                tmp_file.write(first_chunk)
                total_size += len(first_chunk)
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        tmp_file.write(chunk)
                        total_size += len(chunk)
                print(f"Total bytes written: {total_size}", flush=True)

            if os.path.getsize(tmp_path) == 0:
                raise ValueError("Downloaded file is empty")

            return tmp_path

        except Exception as e:
            print(f"Error fetching or saving media: {e}", flush=True)
            raise 

    def moderate_image(self, image_path: str) -> dict:
        try:
            image = Image.open(image_path).convert("RGB")
        except Exception as e:
            print(f"Error opening image {image_path}: {e}", flush=True)
            return {"label": "error", "score": 0.0, "error": str(e)}

        inputs_nsfw = self.nsfw_processor(images=image, return_tensors="pt").to(self.device)
        outputs_nsfw = self.nsfw_model(**inputs_nsfw)
        probs_nsfw = outputs_nsfw.logits.softmax(dim=1).tolist()[0]
        nsfw_label = self.nsfw_labels[probs_nsfw.index(max(probs_nsfw))]
        nsfw_score = max(probs_nsfw)
        print(f"NSFW detection: {nsfw_label} ({nsfw_score:.4f})", flush=True)

        if nsfw_label == "nsfw":
            result = {"label": "nsfw", "score": round(nsfw_score, 4)}
            print(f"Returning: {result}", flush=True)
            return result

        inputs_clip_violence = self.clip_processor(text=self.violence_labels, images=image, return_tensors="pt", padding=True).to(self.device)
        outputs_clip_violence = self.clip_model(**inputs_clip_violence)
        probs_violence = outputs_clip_violence.logits_per_image.softmax(dim=1).tolist()[0]
        violence_label = self.violence_labels[probs_violence.index(max(probs_violence))]
        violence_score = max(probs_violence)
        print(f"Violence detection: {violence_label} ({violence_score:.4f})", flush=True)

        if violence_label == "violence" and violence_score > self.violence_threshold:
            result = {"label": "violence", "score": round(violence_score, 4)}
            print(f"Returning: {result}", flush=True)
            return result

        inputs_clip_political = self.clip_processor(text=self.political_labels, images=image, return_tensors="pt", padding=True).to(self.device)
        outputs_clip_political = self.clip_model(**inputs_clip_political)
        probs_political = outputs_clip_political.logits_per_image.softmax(dim=1).tolist()[0]
        political_label = self.political_labels[probs_political.index(max(probs_political))]
        political_score = max(probs_political)
        print(f"Political detection: {political_label} ({political_score:.4f})", flush=True)

        if political_label == "political" and political_score > self.political_threshold:
            result = {"label": "political", "score": round(political_score, 4)}
            print(f"Returning: {result}", flush=True)
            return result

        inputs_clip_abuse = self.clip_processor(text=self.abuse_labels, images=image, return_tensors="pt", padding=True).to(self.device)
        outputs_clip_abuse = self.clip_model(**inputs_clip_abuse)
        probs_abuse = outputs_clip_abuse.logits_per_image.softmax(dim=1).tolist()[0]
        for label, score in zip(self.abuse_labels, probs_abuse):
            print(f"Abuse label '{label}': {score:.4f}", flush=True)
        abuse_label = self.abuse_labels[probs_abuse.index(max(probs_abuse))]
        abuse_score = max(probs_abuse)
        print(f"Final abuse detection: {abuse_label} ({abuse_score:.4f})", flush=True)

        if abuse_label != "abuse" and abuse_score > self.abuse_threshold:
            result = {"label": "abuse", "score": round(abuse_score, 4)}
            print(f"Returning abuse result: {result}", flush=True)
            return result

        result = {"label": "normal", "score": round(nsfw_score, 4)}
        print(f"Returning normal result: {result}", flush=True)
        return result

    def moderate(self, base_url: str, media_filename: str) -> dict:
        try:
            temp_path = self._fetch_media(base_url, media_filename)
            try:
                if media_filename.lower().endswith((".mp4", ".m4v", ".mov", ".avi", ".mkv")):
                    return self._moderate_video(temp_path)
                else:
                    return self.moderate_image(temp_path)
            finally:
                if os.path.exists(temp_path):
                    os.remove(temp_path)
        except Exception as e:
            print(f"Moderation error: {e}", flush=True)
            return {"label": "error", "score": 0.0}

    def _moderate_video(self, video_path: str, num_frames: int = 3) -> dict:
        try:
            clip = VideoFileClip(video_path)
        except Exception as e:
            print(f"Error opening video: {e}", flush=True)
            raise

        duration = clip.duration
        timestamps = [duration * i / (num_frames + 1) for i in range(1, num_frames + 1)]

        temp_dir = os.path.join("src", "temp")
        os.makedirs(temp_dir, exist_ok=True)

        temp_files = []
        for t in timestamps:
            frame = clip.get_frame(t)
            frame_path = os.path.join(temp_dir, f"frame_{uuid.uuid4().hex}.jpg")
            Image.fromarray(frame).save(frame_path)
            temp_files.append(frame_path)

        results = []
        for path in temp_files:
            result = self.moderate_image(path)
            results.append(result)
            os.remove(path)

        clip.reader.close()
        if clip.audio:
            clip.audio.reader.close_proc()

        labels = [r["label"] for r in results]
        scores = [r["score"] for r in results]

        for priority_label in ["nsfw", "abuse", "violence", "political"]:
            if priority_label in labels:
                final_score = mean([s for l, s in zip(labels, scores) if l == priority_label])
                detail = next((r.get("detail", "") for r in results if r["label"] == priority_label), "")
                return {"label": priority_label, "score": round(final_score, 4), "detail": detail}

        return {"label": "normal", "score": round(mean(scores), 4)}