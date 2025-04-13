from transformers import AutoProcessor, AutoModelForImageClassification, CLIPProcessor, CLIPModel
from PIL import Image
import torch
import os
from moviepy.editor import VideoFileClip
import tempfile
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

    def moderate_image(self, image_path: str) -> dict:
        image = Image.open(image_path).convert("RGB")

        inputs_nsfw = self.nsfw_processor(images=image, return_tensors="pt").to(self.device)
        outputs_nsfw = self.nsfw_model(**inputs_nsfw)
        probs_nsfw = outputs_nsfw.logits.softmax(dim=1).tolist()[0]
        nsfw_label = self.nsfw_labels[probs_nsfw.index(max(probs_nsfw))]
        nsfw_score = max(probs_nsfw)

        if nsfw_label == "nsfw":
            return {"label": "nsfw", "score": round(nsfw_score, 4)}

        inputs_clip_violence = self.clip_processor(text=self.violence_labels, images=image, return_tensors="pt", padding=True).to(self.device)
        outputs_clip_violence = self.clip_model(**inputs_clip_violence)
        probs_clip_violence = outputs_clip_violence.logits_per_image.softmax(dim=1).tolist()[0]
        violence_label = self.violence_labels[probs_clip_violence.index(max(probs_clip_violence))]
        violence_score = max(probs_clip_violence)

        if violence_label == "violence" and violence_score > self.violence_threshold:
            return {"label": "violence", "score": round(violence_score, 4)}

        inputs_clip_political = self.clip_processor(text=self.political_labels, images=image, return_tensors="pt", padding=True).to(self.device)
        outputs_clip_political = self.clip_model(**inputs_clip_political)
        probs_clip_political = outputs_clip_political.logits_per_image.softmax(dim=1).tolist()[0]
        political_label = self.political_labels[probs_clip_political.index(max(probs_clip_political))]
        political_score = max(probs_clip_political)

        if political_label == "political" and political_score > self.political_threshold:
            return {"label": "political", "score": round(political_score, 4)}

        return {"label": "normal", "score": round(nsfw_score, 4)}

    def moderate(self, file_path: str) -> dict:
        if file_path.lower().endswith((".mp4", ".m4v", ".mov", ".avi", ".mkv")):
            return self._moderate_video(file_path)
        else:
            return self.moderate_image(file_path)

    def _moderate_video(self, video_path: str, num_frames: int = 3) -> dict:
        clip = VideoFileClip(video_path)
        duration = clip.duration
        timestamps = [duration * i / (num_frames + 1) for i in range(1, num_frames + 1)]

        temp_files = []
        for t in timestamps:
            frame = clip.get_frame(t)
            with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp:
                Image.fromarray(frame).save(tmp.name)
                temp_files.append(tmp.name)

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