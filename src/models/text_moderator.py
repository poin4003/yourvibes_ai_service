import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification
from langdetect import detect
from googletrans import Translator

class TextModerator:
    def __init__(self, model_name="martin-ha/toxic-comment-model", threshold=0.5):
        self.toxic_threshold = threshold
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModelForSequenceClassification.from_pretrained(model_name)
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model.to(self.device)
        self.cache = {}
        self.translator = Translator()

    def moderate(self, text):
        try:
            lang = detect(text)
        except:
            lang = "en"  

        if lang != "en":
            translated = self.translator.translate(text, src=lang, dest="en").text
        else:
            translated = text

        encoded = self.tokenizer(translated, return_tensors="pt", truncation=True, padding=True).to(self.device)
        with torch.no_grad():
            output = self.model(**encoded)
            scores = torch.nn.functional.softmax(output.logits, dim=-1)
            toxic_score = scores[0][1].item()

        label = "toxic" if toxic_score > self.toxic_threshold else "not toxic"

        censored_text = self.censor_text_with_model(text, translated)

        return {
            "censored_text": censored_text,
            "label": label,
            "score": round(toxic_score, 4),
        }

    def censor_text_with_model(self, original_text, translated_text):
        original_words = original_text.split()
        translated_words = translated_text.split()
        censored_words = []

        min_len = min(len(original_words), len(translated_words))

        for i in range(min_len):
            orig_word = original_words[i]
            trans_word = translated_words[i]

            stripped_word = trans_word.strip(",.!?;:\"'()[]{}").lower()
            prefix_len = orig_word.find(orig_word.strip(",.!?;:\"'()[]{}")) if orig_word.strip(",.!?;:\"'()[]{}") in orig_word else 0
            suffix_len = len(orig_word) - prefix_len - len(orig_word.strip(",.!?;:\"'()[]{}"))

            prefix = orig_word[:prefix_len]
            suffix = orig_word[-suffix_len:] if suffix_len > 0 else ""

            if len(stripped_word) <= 1:
                censored_words.append(orig_word)
                continue

            if stripped_word in self.cache:
                word_score = self.cache[stripped_word]
            else:
                encoded = self.tokenizer(stripped_word, return_tensors="pt", truncation=True, padding=True).to(self.device)
                with torch.no_grad():
                    output = self.model(**encoded)
                    scores = torch.nn.functional.softmax(output.logits, dim=-1)
                    word_score = scores[0][1].item()
                self.cache[stripped_word] = word_score

            if word_score > self.toxic_threshold:
                stripped_orig = orig_word.strip(",.!?;:\"'()[]{}")
                censored = "*" * len(stripped_orig)
                censored_words.append(prefix + censored + suffix)
            else:
                censored_words.append(orig_word)

        if len(original_words) > min_len:
            censored_words.extend(original_words[min_len:])

        return " ".join(censored_words)