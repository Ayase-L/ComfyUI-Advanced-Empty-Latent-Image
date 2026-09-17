"""ComfyUI registration for Advanced Empty Latent Image."""

from .nodes import AdvancedEmptyLatentImage
# Importing this module registers its optional PromptServer routes.
from . import routes as _routes


NODE_CLASS_MAPPINGS = {
    "AdvancedEmptyLatentImage": AdvancedEmptyLatentImage,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "AdvancedEmptyLatentImage": "Advanced Empty Latent Image",
}

# ComfyUI serves this directory at /extensions/<custom-node-name>/.
WEB_DIRECTORY = "./web"

__all__ = [
    "NODE_CLASS_MAPPINGS",
    "NODE_DISPLAY_NAME_MAPPINGS",
    "WEB_DIRECTORY",
]
