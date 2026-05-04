from io import BytesIO
from pathlib import Path

from django.core.files.base import ContentFile
from PIL import Image


def compress_uploaded_image(image_field, max_size=(500, 500), quality=70):
    if not image_field:
        return image_field

    try:
        image_field.seek(0)
        img = Image.open(image_field)

        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")

        img.thumbnail(max_size)

        buffer = BytesIO()
        img.save(buffer, format="JPEG", quality=quality, optimize=True)

        original_name = Path(image_field.name).stem
        new_name = f"{original_name}.jpg"

        return ContentFile(buffer.getvalue(), name=new_name)

    except Exception:
        return image_field