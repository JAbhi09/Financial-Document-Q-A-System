import os
import sys
import time
import shutil
sys.path.append(os.path.dirname(__file__))

from rag.ingestion import process_filing
from rag.vector_store import add_documents_to_store, get_collection_stats

# Set your API key
if "GOOGLE_API_KEY" not in os.environ:
    os.environ["GOOGLE_API_KEY"] = "your-api-key-here"

print("="*60)
print("Re-ingesting WMT with improved deduplication")
print("="*60)

persist_dir = "chroma_db_WMT"
backup_dir = f"{persist_dir}_old"

# ✅ Step 1: Move old database FIRST (before opening it!)
print("\n📦 Checking for existing database...")
if os.path.exists(persist_dir):
    # Delete old backup if exists
    if os.path.exists(backup_dir):
        try:
            shutil.rmtree(backup_dir)
            print(f"  🗑️  Deleted old backup")
        except Exception as e:
            print(f"  ⚠️  Could not delete old backup: {e}")
            backup_dir = f"{persist_dir}_old_{int(time.time())}"
    
    # Rename current to backup
    try:
        os.rename(persist_dir, backup_dir)
        print(f"  ✅ Moved existing database to {backup_dir}")
    except Exception as e:
        print(f"  ❌ Failed to move: {e}")
        print("     Trying to delete instead...")
        try:
            shutil.rmtree(persist_dir)
            print("  ✅ Deleted instead")
        except Exception as e2:
            print(f"  ❌ Could not delete either: {e2}")
            print("     Please manually delete 'chroma_db_WMT' folder and try again")
            sys.exit(1)
else:
    print("  ℹ️  No existing database found")

# ✅ Step 2: Process with new chunking
print("\n📥 Processing WMT 10-K with improved deduplication...")
docs = process_filing("WMT")

# ✅ Step 3: Add to vector store
print("\n💾 Adding to new vector store...")
add_documents_to_store(docs, persist_directory=persist_dir)

# ✅ Step 4: Verify
print("\n📊 New vector store state:")
get_collection_stats(persist_dir)

print("\n✅ Re-ingestion complete!")
print(f"Processed {len(docs)} unique chunks")
if os.path.exists(backup_dir):
    print(f"\n💡 Tip: You can now delete the backup folder: {backup_dir}")