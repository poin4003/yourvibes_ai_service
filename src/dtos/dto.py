from dataclasses import dataclass
from typing import List

@dataclass
class ContentResult:
    label: str 
    censored_text: str

@dataclass
class MediaResult:
    label: str

# Json type to receivce from golang server
@dataclass
class PostModerationRequest:
    post_id: str
    content: str
    base_url: str 
    media: List[str]

# Json type to send to golang server
@dataclass
class PostModerationResponse:
    post_id: str
    content: ContentResult
    media: MediaResult

    def to_dict(self):
        return {
            "post_id": self.post_id,
            "content": {
                "label": self.content.label,
                "censored_text": self.content.censored_text
            },
            "media": {
                "label": self.media.label
            }
        }