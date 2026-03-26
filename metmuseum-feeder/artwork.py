class Artwork:
    def __init__(self, object_id, title, constituents, image_url, department="", medium="", artist_display_name="", object_wikidata_url="", artist_wikidata_url="", object_date="", object_url=""):
        self.object_id = object_id
        self.title = title
        self.constituents = constituents
        self.image_url = image_url
        self.department = department
        self.medium = medium
        self.artist_display_name = artist_display_name
        self.object_wikidata_url = object_wikidata_url
        self.artist_wikidata_url = artist_wikidata_url
        self.object_date = object_date

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

    @classmethod
    def from_dict(cls, data):
        return cls(
            object_id=data.get("objectId") or data.get("objectID"),
            title=data.get("title", "Unknown"),
            constituents=data.get("constituents", []),
            image_url=data.get("imageUrl") or data.get("primaryImage", ""),
            department=data.get("department", ""),
            medium=data.get("medium", ""),
            artist_display_name=data.get("artistDisplayName", ""),
            object_wikidata_url=data.get("objectWikidataUrl") or data.get("objectWikidata_URL", ""),
            artist_wikidata_url=data.get("artistWikidataUrl") or data.get("artistWikidata_URL", ""),
            object_date=data.get("objectDate", ""),
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