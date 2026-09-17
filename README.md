# ComfyUI-Advanced-Empty-Latent-Image

`Advanced Empty Latent Image` is an independent ComfyUI custom node for
high-resolution workflows.  Select the final resolution once and it calculates
the lower initial resolution for the first sampling pass.  It also outputs the
final dimensions as `INT` values for nodes such as Image Scale.

## Installation

Clone or copy this folder into ComfyUI's `custom_nodes` directory:

```text
ComfyUI/
└── custom_nodes/
    └── ComfyUI-Advanced-Empty-Latent-Image/
```

Restart ComfyUI, then search for **Advanced Empty Latent Image** in the node
menu. No additional Python packages are required.

## Inputs

| Input | Description |
| --- | --- |
| Preset | Built-in or saved final resolution. Select `Custom` to use the two Final fields. |
| Final Width / Final Height | Final resolution for `Custom`. These controls are disabled while a preset is selected. |
| Scale | Divisor used for the initial generation size. Default: `1.5`. |
| Multiple | Rounds each initial dimension to the nearest selected multiple: `8`, `16`, `32`, or `64`. Default: `8`. Exact halfway values round upward. |
| Batch Size | Number of empty latent images to create. Default: `1`. |

Built-in presets are:

- Smartphone — 1440 × 3200
- Smartphone 4K — 2160 × 4800
- 9:16 FHD — 1080 × 1920
- 9:16 4K — 2160 × 3840

## Calculation example

For a final size of **1440 × 3200**, Scale **1.5**, and Multiple **8**:

```text
1440 / 1.5 = 960       → 960
3200 / 1.5 = 2133.333… → 2136
```

The node creates a `960 × 2136` latent and outputs `1440` and `3200` for the
final resize stage.

## Outputs

1. `LATENT` — Standard ComfyUI empty latent, directly compatible with KSampler.
2. `Initial Width` — Calculated initial width (`INT`).
3. `Initial Height` — Calculated initial height (`INT`).
4. `Final Width` — Selected final width (`INT`).
5. `Final Height` — Selected final height (`INT`).

## Managing presets

Click **Manage Presets** on the node to add, duplicate, edit, or delete saved
presets. The dialog shows a simplified aspect ratio automatically. Built-in
presets cannot be edited or deleted, but they can be duplicated. User presets
are stored in `presets.json` and remain after ComfyUI restarts.

After saving preset changes, add a new node or reload the workflow if the
server-side dropdown needs to be rebuilt; already-open nodes refresh their
browser-side list immediately.

## Custom resolutions

Select `Custom`, enter Final Width and Final Height, then choose the Scale and
Multiple. The displayed Initial and Final values update before queueing. Values
must be positive and Scale must be greater than zero. Final Width and Height
use ComfyUI's current `16384` maximum resolution input limit.

## Typical workflow

```text
Advanced Empty Latent Image (LATENT) → KSampler → VAE Decode → upscale → Image Scale
Advanced Empty Latent Image (Final Width) ─────────────────────────────→ Image Scale width
Advanced Empty Latent Image (Final Height) ────────────────────────────→ Image Scale height
```
