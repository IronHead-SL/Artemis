import requests
import time
from pymongo import MongoClient
from artwork import Artwork

BASE_URL = "https://collectionapi.metmuseum.org/public/collection/v1"
MONGO_URI = "mongodb://localhost:27017/" # Cambia a 27018 si usas Docker

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0"
}

client = MongoClient(MONGO_URI)
db = client["artemis_db"]
artworks_collection = db["artworks"]


def get_all_object_ids():
    print("Obteniendo la lista de obras del museo...")
    response = requests.get(f"{BASE_URL}/search?hasImages=true&q=art", headers=HEADERS)
    response.raise_for_status()
    data = response.json()
    print(f"Encontradas {data['total']} obras posibles.")
    return data["objectIDs"]

def fetch_artwork(object_id, retries=3):
    """Descarga 1 cuadro (Lógica de tu amigo con freno de velocidad)"""
    time.sleep(1.2)
    
    for attempt in range(1, retries + 1):
        try:
            response = requests.get(f"{BASE_URL}/objects/{object_id}", headers=HEADERS, timeout=10)
            
            if response.status_code == 404:
                return None
                
            response.raise_for_status()
            data = response.json()

            if not data.get("primaryImage"):
                return None
                
            return data
            
        except Exception as e:
            print(f"Error en ID {object_id} (Intento {attempt}): {e}")
            if attempt < retries:
                time.sleep(2) # Si falla, esperamos un poco más antes de reintentar
    return None


# --- 3. BUCLE PRINCIPAL (Sin progress.json) ---
def main():
    all_ids = get_all_object_ids()
    
    # En lugar de leer 'progress.json', le preguntamos a Mongo qué IDs ya tenemos
    print("Consultando progreso en MongoDB...")
    existentes = set(artworks_collection.distinct("_id"))
    
    # Nos quedamos con los IDs que aún no hemos descargado
    ids_pendientes = [oid for oid in all_ids if str(oid) not in existentes]
    total_pendientes = len(ids_pendientes)
    
    print(f"Ya tienes {len(existentes)} guardados. Faltan por descargar: {total_pendientes}")
    if total_pendientes == 0:
        return

    print("\nIniciando descarga (1 a 1)...")
    
    batch = []
    guardados_hoy = 0

    for i, object_id in enumerate(ids_pendientes):
        raw_data = fetch_artwork(object_id)
        
        if raw_data:
            obra = Artwork(
                object_id=raw_data["objectID"],
                title=raw_data.get("title", "Unknown"),
                constituents=raw_data.get("constituents"),
                image_url=raw_data["primaryImage"]
            )
            batch.append(obra.to_dict())
            guardados_hoy += 1
            print(f" [+] ({i+1}/{total_pendientes}) Cuadro {object_id} listo.")
        else:
            print(f" [-] ({i+1}/{total_pendientes}) Cuadro {object_id} saltado (borrado/sin foto).")

        if len(batch) >= 50:
            try:
                artworks_collection.insert_many(batch, ordered=False)
                print(f" >>> Lote guardado en BD. Total hoy: {guardados_hoy}")
            except Exception as e:
                print(f"Error guardando lote en Mongo: {e}")

            batch = []

    if batch:
        artworks_collection.insert_many(batch, ordered=False)
        print(" >>> Lote final guardado en BD.")

if __name__ == "__main__":
    main()