import base64
from io import BytesIO
from PIL import Image

def convert_image_to_base64(uploaded_file):
    """Encodes an uploaded file object into a Base64 string."""
    if uploaded_file is None: 
        return ""
    return base64.b64encode(uploaded_file.getvalue()).decode("utf-8")

def convert_base64_to_image(b64_string):
    """Decodes a Base64 string back into a viewable PIL Image."""
    if not b64_string: 
        return None
    try:
        return Image.open(BytesIO(base64.b64decode(b64_string)))
    except Exception:
        return None