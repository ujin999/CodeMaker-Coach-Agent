if __name__ == "__main__":
    import os
    # Temporarily force fallback for safety in smoke check execution
    os.environ["ENV"] = "test"
    os.environ["USE_FAKE_EMBEDDINGS"] = "true"

    from rag.bootstrap import get_vectorstore_status, bootstrap_rag_indexes

    status = get_vectorstore_status()
    print("=== Qdrant Vector Store Status (Smoke Test) ===")
    print(f"Qdrant URL: {status['qdrant_url']}")
    print(f"Using Fallback: {status['using_fallback']}")
    print("Collections:")
    for col, info in status['collections'].items():
        print(f"  - {col}: status={info['status']}, type={info['vectorstore_type']}, error={info['error']}")

    print("\n=== Bootstrapping RAG Indexes (Smoke Test) ===")
    summary = bootstrap_rag_indexes(knowledge_root="docs/knowledge", force_rebuild=True)
    print(f"Concept Index Built: {summary['concept_index_built']}")
    print(f"Collection: {summary['collection_name']}")
    print(f"Type: {summary['vectorstore_type']}")
    print(f"Fallback Used: {summary['fallback_used']}")
    print(f"Error: {summary['error']}")
