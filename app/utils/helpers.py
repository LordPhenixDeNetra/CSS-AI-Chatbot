import base64
from io import BytesIO
from PIL import Image


def image_to_base64(image: Image.Image, format: str = "PNG") -> str:
    """Convertit une image PIL en string base64"""
    buffer = BytesIO()
    image.save(buffer, format=format)
    img_str = base64.b64encode(buffer.getvalue()).decode()
    return f"data:image/{format.lower()};base64,{img_str}"
