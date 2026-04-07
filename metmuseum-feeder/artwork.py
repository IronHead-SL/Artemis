class Artwork:
    def __init__(self):
        self.object_id = None
        self.title = "Unknown"
        self.constituents = []
        self.image_url = ""
        self.department = ""
        self.medium = ""
        self.artist_display_name = ""
        self.object_wikidata_url = ""
        self.artist_wikidata_url = ""
        self.object_date = ""

    def to_dict(self):
        return {
            "objectId": self.object_id,
            "title": self.title,
            "constituents": self.constituents,
            "imageUrl": self.image_url,
            "department": self.department,
            "medium": self.medium,
            "artistDisplayName": self.artist_display_name,
            "objectWikidataUrl": self.object_wikidata_url,
            "artistWikidataUrl": self.artist_wikidata_url,
            "objectDate": self.object_date,
        }

class ArtworkBuilder:
    def __init__(self):
        self.artwork = Artwork()

    def set_basic_info(self, object_id, title, image_url):
        self.artwork.object_id = object_id
        self.artwork.title = title or "Unknown"
        self.artwork.image_url = image_url
        return self

    def set_metadata(self, department="", medium="", date=""):
        self.artwork.department = department
        self.artwork.medium = medium
        self.artwork.object_date = date
        return self

    def set_artist_info(self, name="", artist_wiki="", object_wiki=""):
        self.artwork.artist_display_name = name
        self.artwork.artist_wikidata_url = artist_wiki
        self.artwork.object_wikidata_url = object_wiki
        return self

    def set_constituents(self, constituents):
        self.artwork.constituents = constituents or []
        return self

    def build(self):
        artwork = self.artwork
        self.artwork = Artwork()
        return artwork