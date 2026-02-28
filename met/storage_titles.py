from typing import List
import os
import json
from met_fetch import OUTPUT_FILE
from artwork import Artwork

NAMES_FILE = "met_artworks.json"

def save_artworks(artworks: List[Artwork]):
    existing = []
    if os.path.exists(NAMES_FILE):
        with open(NAMES_FILE, "r") as f:
            existing = json.load(f)
    existing.extend([artwork.to_dict() for artwork in artworks])
    with open(NAMES_FILE, "w") as f:
        json.dump(existing, f, ensure_ascii=False, indent=2)

def grab_artworks():
    artworks = []
    seen = set()
    if os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE, "r") as f:
            for artwork in json.load(f):
                title = artwork["title"]
                primary_image = artwork["primaryImage"]
                object_id = artwork["objectID"]
                constituents = artwork["constituents"]
                artwork_obj = Artwork(object_id, title, constituents, primary_image)
                if title not in seen and not exist_title(title):
                    if primary_image != "":
                        artworks.append(artwork_obj)
                        seen.add(title)
    return artworks

def exist_title(title):
    if os.path.exists(NAMES_FILE):
        with open(NAMES_FILE, "r") as f:
            for artwork in json.load(f):
                if title == artwork["title"]:
                    return True
    return False

def main():
    save_artworks(grab_artworks())

if __name__ == "__main__":
    main()