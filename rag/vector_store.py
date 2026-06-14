import os
import shutil
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings

def get_vector_store(persist_directory: str = "chroma_db"):
    """
    Returns the Chroma vector store instance.
    Uses HuggingFace embeddings (local) to avoid API rate limits.
    """
    # Use a standard, efficient model
    embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    
    vectorstore = Chroma(
        persist_directory=persist_directory,
        embedding_function=embeddings
    )
    return vectorstore

def add_documents_to_store(documents, persist_directory: str = "chroma_db"):
    """
    Adds documents to the vector store.
    """
    if not documents:
        print("No documents to add.")
        return

    print(f"Adding {len(documents)} documents to ChromaDB...")
    vectorstore = get_vector_store(persist_directory)
    vectorstore.add_documents(documents)
    print("Documents added.")

def clear_vector_store(persist_directory: str = "chroma_db"):
    """
    Deletes the entire vector store directory to start fresh.
    Use with caution!
    """
    if os.path.exists(persist_directory):
        print(f"⚠️  Deleting vector store at {persist_directory}...")
        shutil.rmtree(persist_directory)
        print("✅ Vector store cleared.")
    else:
        print(f"ℹ️  No vector store found at {persist_directory}")

def get_collection_stats(persist_directory: str = "chroma_db"):
    """
    Returns statistics about the current vector store.
    """
    try:
        vectorstore = get_vector_store(persist_directory)
        collection = vectorstore._collection
        count = collection.count()
        print(f"📊 Vector store contains {count} documents")
        return count
    except Exception as e:
        print(f"❌ Error getting stats: {e}")
        return 0

def delete_documents_by_source(ticker: str, persist_directory: str = "chroma_db"):
    """
    Deletes all documents for a specific ticker/company.
    Useful for re-ingesting a single company without clearing everything.
    """
    try:
        vectorstore = get_vector_store(persist_directory)
        collection = vectorstore._collection
        
        # Get all document IDs for this ticker
        results = collection.get(where={"source": ticker})
        
        if results and results['ids']:
            print(f"🗑️  Deleting {len(results['ids'])} documents for {ticker}...")
            collection.delete(ids=results['ids'])
            print(f"✅ Deleted all documents for {ticker}")
        else:
            print(f"ℹ️  No documents found for {ticker}")
            
    except Exception as e:
        print(f"❌ Error deleting documents: {e}")