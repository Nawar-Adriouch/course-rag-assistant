def split_text(text, chunk_size=800 , overlap=300):

    chunks =[]
    start = 0
    while start<len(text):
        end =start + chunk_size
        chunks.append(text[start:end])
        start += chunk_size -overlap
        return chunks

def chunk_pages(pages, chunk_size=800, overlap=300):
    
    all_chunks = []
    for p in pages:
        for piece in split_text(p["text"], chunk_size, overlap):
            if piece.strip():
                all_chunks.append({"page": p["page"], "text": piece})
    return all_chunks