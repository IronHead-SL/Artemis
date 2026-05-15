from __future__ import annotations

import io
import logging

import torch
from PIL import Image

from infrastructure.adapters.db import get_clip_model
from infrastructure.ports.image_embedder import ImageEmbedder


class ClipImageEmbedder(ImageEmbedder):
    def __init__(self, model_provider=get_clip_model):
        self._model_provider = model_provider
        self._device_logged = False

    def embed(self, image_bytes: bytes) -> list[float]:
        model, preprocess = self._model_provider()
        try:
            device = next(model.parameters()).device
        except StopIteration:
            device = "unknown"
        if not self._device_logged:
            logging.info("CLIP frontend device: %s", device)
            self._device_logged = True
        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        tensor = preprocess(img).unsqueeze(0)
        if device != "unknown":
            tensor = tensor.to(device)
        if getattr(device, "type", "") == "cuda":
            with torch.no_grad(), torch.amp.autocast(device_type="cuda"):
                vector = model.encode_image(tensor)
        else:
            with torch.no_grad():
                vector = model.encode_image(tensor)
        vector /= vector.norm(dim=-1, keepdim=True)
        return vector.cpu().numpy().tolist()[0]
