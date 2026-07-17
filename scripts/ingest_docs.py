import os
import glob
import logging
import pymupdf4llm
import chromadb
from chromadb.utils import embedding_functions
from langchain.text_splitter import RecursiveCharacterTextSplitter

# Configuración de logs
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Rutas configuradas para coincidir con los volúmenes de Docker
PDF_DIR = "/app/documentos_proteccion_civil"
CHROMA_DB_DIR = "/app/chroma_db"
COLLECTION_NAME = "proteccion_civil"

def init_chroma():
    """Inicializa la conexión persistente con ChromaDB."""
    logger.info(f"Inicializando ChromaDB en {CHROMA_DB_DIR}...")
    client = chromadb.PersistentClient(path=CHROMA_DB_DIR)
    
    # Función de embedding por defecto de Chroma (all-MiniLM-L6-v2)
    # Es muy rápida y funciona bien en CPU
    ef = embedding_functions.DefaultEmbeddingFunction()
    
    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        embedding_function=ef,
        metadata={"description": "Manuales y protocolos de Protección Civil"}
    )
    return collection

def process_pdfs_to_chroma(collection):
    """Lee PDFs, convierte a Markdown, los divide y los guarda en Chroma."""
    pdf_files = glob.glob(os.path.join(PDF_DIR, "*.pdf"))
    
    if not pdf_files:
        logger.warning(f"No se encontraron archivos PDF en {PDF_DIR}.")
        return

    # Usaremos un divisor especializado para mantener el contexto
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        length_function=len,
        separators=["\n\n", "\n", " ", ""]
    )

    for pdf_path in pdf_files:
        filename = os.path.basename(pdf_path)
        logger.info(f"Procesando: {filename}")
        
        try:
            # Magia pura: Convierte el PDF entero a un string de Markdown estructurado
            md_text = pymupdf4llm.to_markdown(pdf_path)
            
            # Dividir en fragmentos lógicos (chunks)
            chunks = text_splitter.split_text(md_text)
            logger.info(f"  -> Se generaron {len(chunks)} fragmentos.")
            
            # Preparar datos para Chroma
            documents = []
            metadatas = []
            ids = []
            
            for i, chunk in enumerate(chunks):
                documents.append(chunk)
                metadatas.append({"source": filename, "chunk_index": i})
                ids.append(f"{filename}_chunk_{i}")
            
            # Inyectar (upsert) en la base de datos vectorial
            collection.upsert(
                documents=documents,
                metadatas=metadatas,
                ids=ids
            )
            logger.info(f"  -> {filename} indexado exitosamente en ChromaDB.")
            
        except Exception as e:
            logger.error(f"Error procesando {filename}: {str(e)}")

if __name__ == "__main__":
    logger.info("=== Iniciando Pipeline de Ingesta RAG ===")
    collection = init_chroma()
    process_pdfs_to_chroma(collection)
    logger.info("=== Pipeline Finalizado ===")
    
    # Comprobación rápida
    count = collection.count()
    logger.info(f"Total de fragmentos en la base de datos: {count}")
