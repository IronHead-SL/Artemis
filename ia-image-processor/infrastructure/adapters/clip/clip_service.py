from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
import torch
from huggingface_hub import login
import open_clip
import requests
from PIL import Image
from io import BytesIO
from domain.embedding_result import EmbeddingResult
from infrastructure.ports.model_service import ModelService
import os

class CLIPService(ModelService):
    def __init__(self):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"Cargando CLIP en: {self.device}")
        
        hf_token = os.getenv("HF_TOKEN")
        if hf_token:
            login(token=hf_token)
        
        self.model, _, self.preprocess = open_clip.create_model_and_transforms(
            'ViT-B-32', pretrained='laion2b_s34b_b79k', device=self.device)
        self.model.eval()
        self.download_workers = max(1, int(os.getenv("IA_IMAGE_DOWNLOAD_WORKERS", "8")))
        self.embed_batch_size = max(1, int(os.getenv("IA_IMAGE_EMBED_BATCH", "16")))
        self.request_timeout = float(os.getenv("IA_IMAGE_REQUEST_TIMEOUT", "10"))
        self._thread_local = threading.local()

    def _get_session(self):
        session = getattr(self._thread_local, "session", None)
        if session is None:
            session = requests.Session()
            self._thread_local.session = session
        return session

    def _fetch_image(self, image_id, image_url):
        try:
            session = self._get_session()
            response = session.get(image_url, timeout=self.request_timeout)
            response.raise_for_status()

            content_type = response.headers.get('content-type', '')
            if not content_type.startswith('image/'):
                raise ValueError(f"URL no es imagen: {content_type}")

            image = Image.open(BytesIO(response.content)).convert("RGB")
            return image_id, image
        except Exception as e:
            print(f"Error cargando imagen {image_id} desde {image_url}: {e}")
            return image_id, None

    def _encode_batch(self, batch_tensors, batch_ids, id_to_url, results):
        if not batch_tensors:
            return
        image_tensor = torch.stack(batch_tensors).to(self.device)
        if self.device == "cuda":
            with torch.no_grad(), torch.amp.autocast(device_type='cuda'):
                vector = self.model.encode_image(image_tensor)
        else:
            with torch.no_grad():
                vector = self.model.encode_image(image_tensor)

        vector /= vector.norm(dim=-1, keepdim=True)
        vectors_list = vector.cpu().numpy().tolist()

        for image_id, vec in zip(batch_ids, vectors_list):
            results[image_id] = EmbeddingResult(
                image_id=image_id,
                vector=vec,
                image_url=id_to_url.get(image_id),
                title=str(image_id),
                processed_at=None,
            )

    def get_embedding(self, image_id, image_url):
        _, image = self._fetch_image(image_id, image_url)
        if image is None:
            return None

        batch_tensors = [self.preprocess(image)]
        results = {}
        self._encode_batch(batch_tensors, [image_id], {image_id: image_url}, results)
        return results.get(image_id)

    def get_embeddings(self, images):
        if not images:
            return {}

        images = list(images)
        id_to_url = {img.id: img.url for img in images}

        downloaded = {}
        with ThreadPoolExecutor(max_workers=self.download_workers) as executor:
            futures = [executor.submit(self._fetch_image, img.id, img.url) for img in images]
            for future in as_completed(futures):
                image_id, image = future.result()
                downloaded[image_id] = image

        results = {img.id: None for img in images}
        batch_tensors = []
        batch_ids = []

        for img in images:
            image = downloaded.get(img.id)
            if image is None:
                continue
            batch_tensors.append(self.preprocess(image))
            batch_ids.append(img.id)

            if len(batch_tensors) >= self.embed_batch_size:
                self._encode_batch(batch_tensors, batch_ids, id_to_url, results)
                batch_tensors = []
                batch_ids = []

        if batch_tensors:
            self._encode_batch(batch_tensors, batch_ids, id_to_url, results)

        return results