from __future__ import annotations

import io

import torch
from PIL import Image

from infrastructure.adapters.db import get_clip_model
from infrastructure.ports.image_embedder import ImageEmbedder


class ClipImageEmbedder(ImageEmbedder):
    def __init__(self, model_provider=get_clip_model):
        self._model_provider = model_provider

    def embed(self, image_bytes: bytes) -> list[float]:
        model, preprocess = self._model_provider()
        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        tensor = preprocess(img).unsqueeze(0)
        with torch.no_grad():
            vector = model.encode_image(tensor)
        vector /= vector.norm(dim=-1, keepdim=True)
        return vector.cpu().numpy().tolist()[0]
