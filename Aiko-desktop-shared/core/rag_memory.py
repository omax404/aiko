"""
AIKO RAG MEMORY SYSTEM
Long-term semantic memory using ChromaDB + Ollama Embeddings.
"""

import os
import uuid
import time

# Configuration
CHROMA_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "chroma_db")
EMBEDDING_MODEL_NAME = "nomic-embed-text"
OLLAMA_BASE_URL = "http://127.0.0.1:11434"

class RAGMemorySystem:
    """Semantic long-term memory using ChromaDB and Ollama Embeddings."""
    
    def __init__(self):
        self.client = None
        self.collection = None
        self.ef = None # Embedding Function
        
        try:
            self._initialize()
        except Exception as e:
            print(f" [X] [RAG] Initialization failed: {e}")
            
    def _initialize(self):
        """Initialize ChromaDB and embedding function."""
        print(" [RAG] Initializing Memory System...")
        
        try:
            import chromadb
            from chromadb.utils import embedding_functions
        except ImportError as e:
            print(f" [!] [RAG] Missing dependencies: {e}")
            return
            
        # Setup ChromaDB
        os.makedirs(CHROMA_PATH, exist_ok=True)
        self.client = chromadb.PersistentClient(path=CHROMA_PATH)
        
        # Setup Ollama Embedding Function
        try:
            self.ef = embedding_functions.OllamaEmbeddingFunction(
                model_name=EMBEDDING_MODEL_NAME,
                url=f"{OLLAMA_BASE_URL}/api/embeddings"
            )
            print(f" [OK] [RAG] Using Ollama Embeddings: {EMBEDDING_MODEL_NAME}")
        except Exception as e:
            print(f" [X] [RAG] Embedding Init Error: {e}")
            return
            
        # Get/Create Collection
        # Note: If embedding model changed, we might need a new collection or migration.
        # For simplicity, we assume compatible or new db.
        self.collection = self.client.get_or_create_collection(
            name="aiko_memory_v2", 
            embedding_function=self.ef
        )
        print(f" [OK] [RAG] Connected to DB. Items: {self.collection.count()}")
        
    def is_available(self) -> bool:
        return self.collection is not None
        
    def add_memory(self, text: str, metadata: dict = None):
        """Add a text snippet to long-term memory."""
        if not self.is_available() or not text.strip(): return
            
        try:
            mem_id = str(uuid.uuid4())
            meta = metadata or {}
            meta["timestamp"] = time.time()
            
            # Chroma handles embedding automatically via EF
            self.collection.add(
                documents=[text],
                metadatas=[meta],
                ids=[mem_id]
            )
        except Exception as e:
            print(f"[RAG] Add Error: {e}")
            
    def search_memory(self, query: str, n_results: int = 3) -> list:
        """Find relevant memories for a query."""
        if not self.is_available(): return []
            
        try:
            # Chroma handles embedding automatically via EF
            results = self.collection.query(
                query_texts=[query],
                n_results=n_results
            )
            
            memories = []
            if results["documents"]:
                for i, doc in enumerate(results["documents"][0]):
                    meta = results["metadatas"][0][i] if results["metadatas"] else {}
                    memories.append({"text": doc, "meta": meta})
                    
            return memories
        except Exception as e:
            print(f"[RAG] Search Error: {e}")
            return []
            
    def ingest_document(self, file_path: str) -> bool:
        """Ingest a file into memory."""
        if not self.is_available() or not os.path.exists(file_path): return False
            
        try:
            ext = file_path.lower().split(".")[-1]
            text = ""
            if ext == "pdf":
                try:
                    import pypdf
                    reader = pypdf.PdfReader(file_path)
                    for page in reader.pages:
                        t = page.extract_text()
                        if t: text += t + "\n"
                except: pass
            else:
                try:
                    with open(file_path, 'r', encoding='utf-8') as f: text = f.read()
                except: pass
            
            if text:
                self.add_memory(text, metadata={"source": os.path.basename(file_path), "type": "document"})
                print(f" [RAG] Ingested {file_path}")
                return True
        except Exception as e:
            print(f" [RAG] Ingest Error: {e}")
            return False

    def get_memory_count(self) -> int:
        return self.collection.count() if self.collection else 0
