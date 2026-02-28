class Artwork:
    def __init__(self, object_id, title, constituents, image_url):
        self.object_id = object_id
        self.title = title
        self.constituents = constituents
        self.image_url = image_url

    def to_dict(self):
        return {
            "objectId": self.object_id,
            "title": self.title,
            "constituents": self.constituents,
            "imageUrl": self.image_url,
        }

    @classmethod
    def from_dict(cls, data):
        return cls(
            object_id=data["objectID"],
            title=data["title"],
            constituents=data["constituents"],
            image_url=data["primaryImage"],
        )

    @property
    def get_title(self):
        return self.title

    def get_object_id(self):
        return self.object_id

    def get_constituents(self):
        return self.constituents

    def get_image_url(self):
        return self.image_url