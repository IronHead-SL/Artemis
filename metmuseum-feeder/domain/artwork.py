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
            "objectId":           self.object_id,
            "title":              self.title,
            "constituents":       self.constituents,
            "imageUrl":           self.image_url,
            "department":         self.department,
            "medium":             self.medium,
            "artistDisplayName":  self.artist_display_name,
            "objectWikidataUrl":  self.object_wikidata_url,
            "artistWikidataUrl":  self.artist_wikidata_url,
            "objectDate":         self.object_date,
        }


class ArtworkBuilder:
    def __init__(self):
        self._artwork = Artwork()

    def set_basic_info(self, object_id, title, image_url):
        self._artwork.object_id = object_id
        self._artwork.title = title or "Unknown"
        self._artwork.image_url = image_url or ""
        return self

    def set_metadata(self, department="", medium="", date=""):
        self._artwork.department = department or ""
        self._artwork.medium = medium or ""
        self._artwork.object_date = date or ""
        return self

    def set_artist_info(self, name="", artist_wiki="", object_wiki=""):
        self._artwork.artist_display_name = name or ""
        self._artwork.artist_wikidata_url = artist_wiki or ""
        self._artwork.object_wikidata_url = object_wiki or ""
        return self

    def set_constituents(self, constituents):
        self._artwork.constituents = constituents or []
        return self

    def build(self):
        artwork = self._artwork
        self._artwork = Artwork()  # reset para el siguiente
        return artwork