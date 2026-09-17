"""Small HTTP API used by the browser-side preset manager."""

from __future__ import annotations

from aiohttp import web

from .presets import all_presets, save_user_presets


try:
    from server import PromptServer

    routes = PromptServer.instance.routes

    @routes.get("/advanced-empty-latent/presets")
    async def get_presets(_request):
        return web.json_response({"presets": all_presets()})


    @routes.put("/advanced-empty-latent/presets")
    async def put_presets(request):
        try:
            data = await request.json()
            if not isinstance(data, dict) or not isinstance(data.get("presets"), list):
                raise ValueError("presets must be an array")
            presets = save_user_presets(data["presets"])
            return web.json_response({"presets": presets})
        except ValueError as exc:
            return web.json_response({"error": str(exc)}, status=400)
        except Exception:
            # Avoid sending internal paths or implementation details to the UI.
            return web.json_response({"error": "Unable to save presets"}, status=500)

except (AttributeError, ImportError):
    # Allows module-level tooling/tests to import this package without ComfyUI.
    pass
