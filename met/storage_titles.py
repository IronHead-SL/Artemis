from typing import List
import os
import json
from met_fetch import OUTPUT_FILE

NAMES_FILE = "met_artworks_titles.txt"

def save_artworks_name(names: List):
    exiting = []
    if os.path.exists(NAMES_FILE):
        with open(NAMES_FILE, "w") as f:
            exiting = json.load(f)
    exiting.extend(names)

def grab_name():
    artwork_titles = []
    if os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE, "r") as f:
            for artwork in json.load(f):
                if exist_title(artwork["title"]):
                    artwork_titles.append(artwork["title"])
                else:
                    pass
        return artwork_titles

def exist_title(title):
    if os.path.exists(NAMES_FILE):
        with open(NAMES_FILE, "r") as f:
            for line in f:
                if title in line:
                    return True
                else:
                    return False

def main():
    save_artworks_name(grab_name())


if __name__ == "__main__":
    main()