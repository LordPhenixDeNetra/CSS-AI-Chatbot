from enum import Enum


class Provider(str, Enum):
    MISTRAL = "mistral"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    DEEPSEEK = "deepseek"
    GROQ = "groq"


class ModalityType(str, Enum):
    TEXT = "text"
    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"


class ContentType(str, Enum):
    DOCUMENT = "document"
    IMAGE = "image"
    OCR_TEXT = "ocr_text"
    IMAGE_CAPTION = "image_caption"
    MIXED = "mixed"
