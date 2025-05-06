import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification
from langdetect import detect
from googletrans import Translator
import re


class TextModerator:
    def __init__(self, english_model="martin-ha/toxic-comment-model", threshold=0.5):
        self.toxic_threshold = threshold
        self.tokenizer = AutoTokenizer.from_pretrained(english_model)
        self.model = AutoModelForSequenceClassification.from_pretrained(english_model).to(self._device())
        self.translator = Translator()
        self.translation_cache = {}
        self.prediction_cache = {}

        predefined_toxic_words = [
            "vl", "vcl", "dm", "đm", "cc", "cl", "dmm",
            "đĩ", "địt", "lồn", "buồi"
        ]
        for word in predefined_toxic_words:
            self.translation_cache[word] = word
            self.prediction_cache[word] = 1.0

    def _device(self):
        return torch.device("cuda" if torch.cuda.is_available() else "cpu")

    def moderate(self, text):
        lang = detect(text)
        words = text.split()
        translated_words = []

        if lang == "vi":
            for word in words:
                cleaned = self._normalize_word(word)
                if cleaned in self.translation_cache:
                    translated_words.append(self.translation_cache[cleaned])
                else:
                    try:
                        translated = self.translator.translate(cleaned, src="vi", dest="en").text
                    except Exception:
                        translated = cleaned
                    self.translation_cache[cleaned] = translated
                    translated_words.append(translated)
        else:
            translated_words = [self._normalize_word(word) for word in words]

        uncached_indices = []
        uncached_translations = []
        toxic_scores = []

        for i, word in enumerate(translated_words):
            if word in self.prediction_cache:
                toxic_scores.append(self.prediction_cache[word])
            else:
                uncached_indices.append(i)
                uncached_translations.append(word)
                toxic_scores.append(None)

        if uncached_translations:
            encoded = self.tokenizer(uncached_translations, return_tensors="pt", padding=True, truncation=True).to(self._device())
            with torch.no_grad():
                outputs = self.model(**encoded)
                scores = torch.nn.functional.softmax(outputs.logits, dim=-1)
                new_scores = scores[:, 1].tolist()

            for i, score in zip(uncached_indices, new_scores):
                toxic_scores[i] = score
                self.prediction_cache[translated_words[i]] = score

        censored_words = []
        for orig_word, score in zip(words, toxic_scores):
            if score > self.toxic_threshold:
                censored_word = ''.join('*' if c.isalnum() else c for c in orig_word)
                censored_words.append(censored_word)
            else:
                censored_words.append(orig_word)

        censored_text = ' '.join(censored_words)
        return {
            "censored_text": censored_text,
        }

    def _normalize_word(self, word):
        return re.sub(r'\W+', '', word.lower())

