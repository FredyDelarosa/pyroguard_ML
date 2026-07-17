import os
import urllib.request
import sys

# URL directa al archivo GGUF de Llama-3 (Versión cuantizada Q4_K_M de 4.9 GB)
# Cuantización Q4_K_M ofrece el mejor balance entre consumo de RAM (aprox 6-7 GB) y precisión.
MODEL_URL = "https://huggingface.co/QuantFactory/Meta-Llama-3-8B-Instruct-GGUF/resolve/main/Meta-Llama-3-8B-Instruct.Q4_K_M.gguf?download=true"
DEST_DIR = "/app/modelos_locales"
MODEL_FILENAME = "Llama-3-8B-Instruct.Q4_K_M.gguf"

def progress_hook(count, block_size, total_size):
    """Muestra una barra de progreso nativa en la consola."""
    downloaded = count * block_size
    if total_size > 0:
        percent = min(int(downloaded * 100 / total_size), 100)
        mb_downloaded = downloaded / (1024 * 1024)
        mb_total = total_size / (1024 * 1024)
        sys.stdout.write(f"\rDescargando modelo: {percent}%  [{mb_downloaded:.2f} MB / {mb_total:.2f} MB]")
        sys.stdout.flush()

def download_model():
    # Asegurar que la carpeta existe
    os.makedirs(DEST_DIR, exist_ok=True)
    dest_path = os.path.join(DEST_DIR, MODEL_FILENAME)
    
    if os.path.exists(dest_path):
        print(f"\n¡El modelo ya existe en {dest_path}! No es necesario descargarlo.")
        return

    print(f"Iniciando descarga del modelo (Esto puede tomar varios minutos dependiendo del internet)...")
    try:
        urllib.request.urlretrieve(MODEL_URL, dest_path, reporthook=progress_hook)
        print(f"\n\n¡Descarga completada con éxito! Modelo guardado en {dest_path}")
    except Exception as e:
        print(f"\nError durante la descarga: {e}")
        # Limpiar archivo corrupto si falló a la mitad
        if os.path.exists(dest_path):
            os.remove(dest_path)

if __name__ == "__main__":
    download_model()
