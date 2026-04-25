"""
Pytest configuration: mock heavy dependencies so tests can run without
torch, flask, librosa, soundfile, or the demucs model being installed.
"""
import sys
import types
from unittest.mock import MagicMock

# ---------------------------------------------------------------------------
# Mock torch before anything imports it (config.py uses it for device check)
# ---------------------------------------------------------------------------
torch_mock = types.ModuleType("torch")
torch_mock.cuda = MagicMock()
torch_mock.cuda.is_available = MagicMock(return_value=False)
sys.modules.setdefault("torch", torch_mock)

# ---------------------------------------------------------------------------
# Mock other heavy deps that app.py or its imports pull in
# ---------------------------------------------------------------------------
for _mod in (
    "librosa",
    "soundfile",
    "numpy",
    "scipy",
    "demucs",
):
    sys.modules.setdefault(_mod, types.ModuleType(_mod))

# VocalRemovalModelHandler pulls in torch/demucs; mock the whole service so
# the Flask app can be imported without it.
_vr_mod = types.ModuleType("services.VocalRemovalModelHandler")
_vr_handler_cls = MagicMock()
_vr_handler_cls.return_value = MagicMock()
_vr_mod.vocalRemovalModelHandler = _vr_handler_cls
sys.modules["services.VocalRemovalModelHandler"] = _vr_mod