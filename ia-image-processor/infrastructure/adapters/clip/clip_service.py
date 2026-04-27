import torch
import open_clip
import requests
from PIL import Image
from io import BytesIO
from domain.embedding_result import EmbeddingResult
from infrastructure.ports.model_service import ModelService

class CLIPService(ModelService):
    def __init__(self):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"Cargando CLIP en: {self.device}")
        
        self.model, _, self.preprocess = open_clip.create_model_and_transforms(
            'ViT-B-32', pretrained='laion2b_s34b_b79k', device=self.device
        )
        self.model.eval()

    def get_embedding(self, image_id, image_url):
        response = requests.get(image_url, timeout=10)
        image = Image.open(BytesIO(response.content)).convert("RGB")
        
        image_tensor = self.preprocess(image).unsqueeze(0).to(self.device)
        
        with torch.no_grad(), torch.cuda.amp.autocast('cuda'):
            vector = self.model.encode_image(image_tensor)
            vector /= vector.norm(dim=-1, keepdim=True)
            
        vector_list = vector.cpu().numpy().tolist()[0]
            
        return EmbeddingResult(image_id=image_id, vector=vector_list)