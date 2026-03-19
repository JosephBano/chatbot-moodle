import os
import chromadb
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader, TextLoader

DOCS_PATH = "./knowledge/docs"
CHROMA_PATH = "./chroma_db"

def index_documents():
    client = chromadb.PersistentClient(path=CHROMA_PATH)
    collection = client.get_or_create_collection("moodle_docs")

    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    docs_added = 0

    # Asegurar que la carpeta de documentos existe
    if not os.path.exists(DOCS_PATH):
        os.makedirs(DOCS_PATH)
        print(f"Creada carpeta {DOCS_PATH}. Coloca tus documentos ahí.")

    for filename in os.listdir(DOCS_PATH):
        filepath = os.path.join(DOCS_PATH, filename)

        if filename.endswith(".pdf"):
            loader = PyPDFLoader(filepath)
        elif filename.endswith(".txt") or filename.endswith(".md"):
            loader = TextLoader(filepath, encoding="utf-8")
        else:
            continue

        documents = loader.load()
        chunks = splitter.split_documents(documents)

        for i, chunk in enumerate(chunks):
            doc_id = f"{filename}_{i}"
            collection.upsert(
                ids=[doc_id],
                documents=[chunk.page_content],
                metadatas=[{"source": filename}]
            )
            docs_added += 1

    print(f"Indexación completa. {docs_added} fragmentos añadidos.")

if __name__ == "__main__":
    index_documents()
