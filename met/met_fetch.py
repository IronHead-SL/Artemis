import requests
import time
import json
import os

BASE_URL = "https://collectionapi.metmuseum.org/public/collection/v1"
OUTPUT_FILE = "met_artworks.json"
PROGRESS_FILE = "progress.json"


def get_all_object_ids():
    print("Fetching all object IDs...")
    response = requests.get(f"{BASE_URL}/objects")
    response.raise_for_status()
    data = response.json()
    total = data["total"]
    object_ids = data["objectIDs"]
    print(f"Retrieved {total} object IDs.")
    return object_ids


def fetch_artwork(object_id, retries=3, delay=0.5):
    for attempt in range(1, retries + 1):
        try:
            response = requests.get(f"{BASE_URL}/objects/{object_id}", timeout=10)
            if response.status_code == 404:
                return None
            response.raise_for_status()
            return response.json()
        except (requests.RequestException, Exception) as e:
            print(f"Attempt {attempt}/{retries} failed for ID {object_id}: {e}")
            if attempt < retries:
                time.sleep(delay * attempt)
    return None


def load_progress():
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE, "r") as f:
            data = json.load(f)
            print(f"Resuming from index {data['last_index']} / {data['total']}")
            return data["last_index"]
    return 0


def save_progress(index, total):
    with open(PROGRESS_FILE, "w") as f:
        json.dump({"last_index": index, "total": total}, f)

def save_artworks(artworks):
    if os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE, "r") as f:
            existing = json.load(f)
    else:
        existing = []
    existing.extend(artworks)
    with open(OUTPUT_FILE, "w") as f:
        json.dump(existing, f, indent=2)


def fetch_all_artworks(object_ids, batch_size=100, request_delay=0.05):
    total = len(object_ids)
    start_index = load_progress()
    batch = []
    fetched = 0
    skipped = 0

    print(f"\nStarting fetch of {total} artworks (from index {start_index})...\n")

    for i in range(start_index, total):
        object_id = object_ids[i]
        artwork = fetch_artwork(object_id)
        if artwork:
            batch.append(artwork)
            fetched += 1
        else:
            skipped += 1
        if len(batch) >= batch_size:
            save_artworks(batch)
            save_progress(i + 1, total)
            batch = []
            print(f"Saved batch | Progress: {i + 1}/{total} | Fetched: {fetched} | Skipped: {skipped}")
        time.sleep(request_delay)
    if batch:
        save_artworks(batch)
        save_progress(total, total)
        print(f"Saved final batch | Fetched: {fetched} | Skipped: {skipped}")

    print(f"\nDone! Total fetched: {fetched} | Total skipped: {skipped}")
    print(f"Results saved to: {OUTPUT_FILE}")


def main():
    object_ids = get_all_object_ids()
    fetch_all_artworks(
        object_ids,
        batch_size=100,
        request_delay=0.05
    )


if __name__ == "__main__":
    main()