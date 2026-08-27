import chromadb

CHROMA_PATH = "./chroma_db"
COLLECTION_NAME = "book"

client = chromadb.PersistentClient(
    path=CHROMA_PATH
)

collection = client.get_collection(
    name=COLLECTION_NAME
)

print("=" * 80)
print("CHROMA DATABASE")
print("=" * 80)

print(f"Collection: {collection.name}")
print(f"Total chunks: {collection.count()}")

result = collection.get(
    include=[
        "documents",
        "metadatas",
    ]
)

for i, (
    chunk_id,
    document,
    metadata,
) in enumerate(
    zip(
        result["ids"][:10],
        result["documents"][:10],
        result["metadatas"][:10],
    ),
    start=1,
):

    print()
    print("-" * 80)
    print(f"CHUNK {i}")
    print(f"ID: {chunk_id}")
    print(f"METADATA: {metadata}")
    print("-" * 80)
    print(document)