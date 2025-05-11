import io
import os
from PIL import Image, ImageOps
from PIL.Image import Resampling

def reduce_image_weight(image_data: bytes, target_max_kb=500) -> bytes:
    target_max_bytes = target_max_kb * 1024
    image = Image.open(io.BytesIO(image_data))
    image = ImageOps.exif_transpose(image)
    if image.mode != "RGB":
        image = image.convert("RGB")
    max_dimension = 1024  
    if max(image.size) > max_dimension:
        image.thumbnail((max_dimension, max_dimension), Resampling.LANCZOS)
    quality = 90
    output = io.BytesIO()
    image.save(output, format="JPEG", quality=quality)
    while output.tell() > target_max_bytes and quality > 10:
        quality -= 5
        output = io.BytesIO()
        image.save(output, format="JPEG", quality=quality)
    compressed_data = output.getvalue()
    final_size_kb = len(compressed_data) / 1024
    if image_data == compressed_data:
        print("La imagen no ha cambiado de peso y sus dimensiones son las mismas.")
    else:
        print(f"Peso final: {final_size_kb:.2f} KB con calidad {quality}")
        print(f"Dimensiones finales: {image.size}")
    print("Imagen comprimida")
    return compressed_data