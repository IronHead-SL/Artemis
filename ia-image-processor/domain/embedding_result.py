class EmbeddingResult:
    def __init__(self, image_id, vector, image_url=None, title=None, processed_at=None):
        self.image_id = image_id
        self.vector = vector
        self.image_url = image_url
        self.title = title
        self.processed_at = processed_at