import importlib.util
import pathlib
import sys
import types
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
PACKAGE = "advanced_empty_latent_test"


def load_module(name):
    spec = importlib.util.spec_from_file_location(
        f"{PACKAGE}.{name}", ROOT / f"{name}.py", submodule_search_locations=[]
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


package = types.ModuleType(PACKAGE)
package.__path__ = [str(ROOT)]
sys.modules[PACKAGE] = package
sys.modules.setdefault("torch", types.SimpleNamespace(zeros=lambda *args, **kwargs: None))
presets = load_module("presets")
nodes = load_module("nodes")


class ResolutionCalculationTests(unittest.TestCase):
    def test_specification_smartphone_example(self):
        self.assertEqual(nodes.calculate_resolution(1440, 3200, 1.5, 8), (960, 2136))

    def test_fhd_example(self):
        self.assertEqual(nodes.calculate_resolution(1080, 1920, 1.5, 8), (720, 1280))

    def test_4k_example(self):
        self.assertEqual(nodes.calculate_resolution(2160, 3840, 2.0, 8), (1080, 1920))

    def test_halfway_rounds_up(self):
        self.assertEqual(nodes.round_to_multiple(12, 8), 16)

    def test_rejects_invalid_scale(self):
        with self.assertRaises(ValueError):
            nodes.calculate_resolution(1440, 3200, 0, 8)

    def test_user_preset_validation(self):
        preset = presets.normalize_preset(
            {"name": "My Portrait", "width": 1440, "height": 1920}
        )
        self.assertEqual(preset["name"], "My Portrait")
        self.assertFalse(preset["builtin"])


if __name__ == "__main__":
    unittest.main()
