import os
import anyio
from PIL import Image as PILImage
from app.config import settings

# Import ML functions from app.ml
# Note: we import these inside functions or globally? Globally is fine because ui_module does it too.
from app.ml.recognition_module import color_classification, single_classification

async def get_dominant_color(image_path: str) -> str:
    """
    Calls the ML model to get the dominant clothing color of the image.
    Runs the blocking ML operation in a separate thread.
    """
    abs_path = os.path.abspath(image_path)
    def run_color():
        return color_classification(abs_path)
    return await anyio.to_thread.run_sync(run_color)

async def classify_clothing(image_path: str) -> dict:
    """
    Calls the ML model to classify the clothing item in the image.
    Runs the blocking ML operation in a separate thread.
    Returns a dictionary of classification results.
    """
    abs_path = os.path.abspath(image_path)
    def run_classify():
        sub_type, res_str, res = single_classification(abs_path)
        return {
            "category": sub_type,
            "predictions": res,
            "description": res_str
        }
    return await anyio.to_thread.run_sync(run_classify)

async def generate_thumbnail(image_path: str, dest_path: str) -> str:
    """
    Generates a thumbnail of the image at image_path and saves it to dest_path.
    Runs the blocking Pillow operations in a separate thread.
    """
    src = image_path
    dest = dest_path
    
    def run_resize():
        # Ensure destination directory exists
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        with PILImage.open(src) as img:
            # We want to preserve aspect ratio, maximum dimensions 150x150
            img.thumbnail((150, 150), PILImage.Resampling.LANCZOS)
            img.save(dest)
        return dest

    await anyio.to_thread.run_sync(run_resize)
    return dest_path

async def remove_background(image_path: str) -> str:
    """
    Placeholder method for future background removal implementation.
    Raises NotImplementedError.
    """
    raise NotImplementedError("Background removal is not implemented yet.")

async def generate_embedding(image_path: str) -> list[float]:
    """
    Placeholder method for future vector embedding generation implementation.
    Raises NotImplementedError.
    """
    raise NotImplementedError("Vector embedding generation is not implemented yet.")
