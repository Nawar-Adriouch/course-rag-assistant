import chromadb
from sentence_transformers import SentenceTransformer

MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"

def load_model():
    return SentenceTransformer(MODEL_NAME)


def get_collection(reset=False):
    client = chromadb.PersistentClient(path="/code/chroma")
    if reset:
        try:
            client.delete_collection("cours")
        except Exception:
            pass
    return client.get_or_create_collection("cours")


def index_chunks(chunks, model, source_name):
    collection = get_collection()
    collection.delete(where={"source": source_name})

    texts = [c["text"] for c in chunks]
    embeddings = model.encode(texts, normalize_embeddings=True).tolist()

    collection.add(
        ids=[f"{source_name}-{i}" for i in range(len(chunks))],
        documents=texts,
        embeddings=embeddings,
        metadatas=[{"page": c["page"], "source": source_name} for c in chunks],
    )
    return collection.count(), len(embeddings[0])


def list_courses():
    collection = get_collection()
    metas = collection.get(include=["metadatas"])["metadatas"]
    courses = {}
    for meta in metas:
        courses[meta["source"]] = courses.get(meta["source"], 0) + 1
    return courses


def delete_course(source_name):
    get_collection().delete(where={"source": source_name})


def search(question, model, k=3, source=None):
    collection = get_collection()
    q_emb = model.encode([question], normalize_embeddings=True).tolist()

    params = {"query_embeddings": q_emb, "n_results": k}
    if source:
        params["where"] = {"source": source}
    results = collection.query(**params)

    hits = []
    for text, meta, dist in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
    ):
        hits.append(
            {"text": text, "page": meta["page"], "source": meta["source"], "distance": dist}
        )
    return hits