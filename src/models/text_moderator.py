import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification
from langdetect import detect
from googletrans import Translator

class TextModerator:
    def __init__(self, vietnamese_model="vinai/phobert-base", english_model="martin-ha/toxic-comment-model", threshold=0.5):
        self.toxic_threshold = threshold

        self.vi_tokenizer = AutoTokenizer.from_pretrained(vietnamese_model)
        self.vi_model = AutoModelForSequenceClassification.from_pretrained(vietnamese_model).to(self._device())

        self.en_tokenizer = AutoTokenizer.from_pretrained(english_model)
        self.en_model = AutoModelForSequenceClassification.from_pretrained(english_model).to(self._device())

        self.cache = {}
        self.translator = Translator()

    def _device(self):
        return torch.device("cuda" if torch.cuda.is_available() else "cpu")

    def moderate(self, text):
        toxic_score, label = self._classify_text(text)
        censored = self._censor_words(text)
        return {
            "censored_text": censored,
            "label": label,
            "score": round(toxic_score, 4),
        }

    def _classify_text(self, text):
        lang = detect(text)
        if lang == "vi":
            tokenizer, model = self.vi_tokenizer, self.vi_model
        else:
            tokenizer, model = self.en_tokenizer, self.en_model

        encoded = tokenizer(text, return_tensors="pt", truncation=True, padding=True).to(self._device())
        with torch.no_grad():
            output = model(**encoded)
            scores = torch.nn.functional.softmax(output.logits, dim=-1)
            toxic_score = scores[0][1].item()

        return toxic_score, "toxic" if toxic_score > self.toxic_threshold else "not toxic"

    def _censor_words(self, text):
        words = text.split()
        censored_words = []

        for word in words:
            stripped = word.strip(",.!?;:\"'()[]{}").lower()

            if len(stripped) <= 1:
                censored_words.append(word)
                continue

            if stripped in self.cache:
                score = self.cache[stripped]
            else:
                lang = detect(stripped)
                tokenizer = self.vi_tokenizer if lang == "vi" else self.en_tokenizer
                model = self.vi_model if lang == "vi" else self.en_model

                try:
                    encoded = tokenizer(stripped, return_tensors="pt", truncation=True, padding=True).to(self._device())
                    with torch.no_grad():
                        output = model(**encoded)
                        scores = torch.nn.functional.softmax(output.logits, dim=-1)
                        score = scores[0][1].item()
                except Exception:
                    score = 0.0 

                self.cache[stripped] = score

            if score > self.toxic_threshold:
                censored = "*" * len(stripped)
                prefix_len = word.find(stripped)
                suffix_len = len(word) - prefix_len - len(stripped)
                prefix = word[:prefix_len]
                suffix = word[-suffix_len:] if suffix_len > 0 else ""
                censored_words.append(prefix + censored + suffix)
            else:
                censored_words.append(word)

        return " ".join(censored_words)
