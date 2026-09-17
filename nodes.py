"""The Advanced Empty Latent Image ComfyUI node."""

from __future__ import annotations

import math

import torch

from .presets import find_preset, preset_names


MULTIPLES = (8, 16, 32, 64)
# Kept in sync with the current ComfyUI Empty Latent Image input limit.
MAX_RESOLUTION = 16384


def round_to_multiple(value: float, multiple: int) -> int:
    """Round to the nearest multiple, with exact halves rounded upward."""
    if multiple <= 0:
        raise ValueError("multiple must be greater than zero")
    return int(math.floor((value / multiple) + 0.5) * multiple)


def calculate_resolution(
    final_width: int, final_height: int, scale: float, multiple: int
) -> tuple[int, int]:
    if final_width <= 0 or final_height <= 0:
        raise ValueError("final width and height must be greater than zero")
    if not math.isfinite(scale) or scale <= 0:
        raise ValueError("scale must be a finite number greater than zero")
    if multiple <= 0:
        raise ValueError("multiple must be greater than zero")
    initial_width = round_to_multiple(final_width / scale, multiple)
    initial_height = round_to_multiple(final_height / scale, multiple)
    if initial_width <= 0 or initial_height <= 0:
        raise ValueError("calculated initial width and height must be greater than zero")
    return initial_width, initial_height


class AdvancedEmptyLatentImage:
    """Generate a standard ComfyUI latent from an automatically scaled size."""

    @classmethod
    def INPUT_TYPES(cls):
        # Called at node-definition load time, so it also exposes newly saved
        # presets after a normal ComfyUI restart.
        return {
            "required": {
                "preset": (preset_names(), {"default": "Smartphone"}),
                "final_width": (
                    "INT",
                    {"default": 1440, "min": 1, "max": MAX_RESOLUTION, "step": 1},
                ),
                "final_height": (
                    "INT",
                    {"default": 3200, "min": 1, "max": MAX_RESOLUTION, "step": 1},
                ),
                "scale": ("FLOAT", {"default": 1.5, "min": 0.000001, "step": 0.01}),
                "multiple": ([str(value) for value in MULTIPLES], {"default": "8"}),
                "batch_size": ("INT", {"default": 1, "min": 1, "max": 4096}),
            }
        }

    RETURN_TYPES = ("LATENT", "INT", "INT", "INT", "INT")
    RETURN_NAMES = ("LATENT", "Initial Width", "Initial Height", "Final Width", "Final Height")
    OUTPUT_TOOLTIPS = (
        "A standard empty ComfyUI latent batch.",
        "Calculated initial width in pixels.",
        "Calculated initial height in pixels.",
        "Final output width in pixels.",
        "Final output height in pixels.",
    )
    FUNCTION = "generate"
    CATEGORY = "model/latent"
    DESCRIPTION = "Creates an empty latent using a scaled, rounded initial resolution."
    SEARCH_ALIASES = ["empty", "latent", "resolution", "upscale"]

    def generate(self, preset, final_width, final_height, scale, multiple, batch_size=1):
        selected = find_preset(preset)
        if preset != "Custom" and selected is None:
            raise ValueError(f"Unknown preset: {preset}. Select Custom or a listed preset.")
        if selected is not None:
            final_width, final_height = selected["width"], selected["height"]

        try:
            multiple_value = int(multiple)
        except (TypeError, ValueError) as exc:
            raise ValueError("multiple must be one of 8, 16, 32, or 64") from exc
        if multiple_value not in MULTIPLES:
            raise ValueError("multiple must be one of 8, 16, 32, or 64")
        if batch_size < 1:
            raise ValueError("batch size must be greater than zero")

        initial_width, initial_height = calculate_resolution(
            int(final_width), int(final_height), float(scale), multiple_value
        )

        # Mirrors ComfyUI's EmptyLatentImage format and device/dtype choices.
        import comfy.model_management

        latent = torch.zeros(
            [batch_size, 4, initial_height // 8, initial_width // 8],
            device=comfy.model_management.intermediate_device(),
            dtype=comfy.model_management.intermediate_dtype(),
        )
        return (
            {"samples": latent, "downscale_ratio_spacial": 8},
            initial_width,
            initial_height,
            int(final_width),
            int(final_height),
        )
