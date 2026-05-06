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

    def get_embedding(self, image_id, image_url):
        try:
            response = requests.get(image_url, timeout=10)
            response.raise_for_status()

            content_type = response.headers.get('content-type', '')
            if not content_type.startswith('image/'):
                raise ValueError(f"URL no es imagen: {content_type}")
            
            image = Image.open(BytesIO(response.content)).convert("RGB")
            
        except Exception as e:
            print(f"Error cargando imagen {image_id} desde {image_url}: {e}")
            return None

        image_tensor = self.preprocess(image).unsqueeze(0).to(self.device)

        if self.device == "cuda":
            with torch.no_grad(), torch.amp.autocast(device_type='cuda'):
                vector = self.model.encode_image(image_tensor)
        else:
            with torch.no_grad():
                vector = self.model.encode_image(image_tensor)
        
        vector /= vector.norm(dim=-1, keepdim=True)
        vector_list = vector.cpu().numpy().tolist()[0]
            
        return EmbeddingResult(image_id=image_id, vector=vector_list, image_url=image_url, title= str(image_id),
                               processed_at=None)