import streamlit as st
from pdf_utils import extract_pages
from chunking import chunk_pages
from vectorstore import load_model, index_chunks, search, list_courses, delete_course
from llm import ask_llm, rewrite_question


@st.cache_resource
def get_model():
    return load_model()


st.title("Assistant de cours")


uploaded = st.file_uploader("Dépose un cours en PDF", type="pdf")

if uploaded is not None:
    pages = extract_pages(uploaded)
    chunks = chunk_pages(pages)
    st.success(f"{len(pages)} pages, découpées en {len(chunks)} chunks")

    if st.button("Indexer ce cours"):
        with st.spinner("Calcul des embeddings..."):
            model = get_model()
            total, dim = index_chunks(chunks, model, uploaded.name)
        st.success(f"Cours ajouté. La base contient maintenant {total} passages.")

st.divider()


courses = list_courses()

st.sidebar.header("Cours indexés")
if not courses:
    st.sidebar.info("Aucun cours indexé pour l'instant.")
for name, count in courses.items():
    col1, col2 = st.sidebar.columns([4, 1])
    col1.write(f"{name} ({count} passages)")
    if col2.button("🗑", key=f"del_{name}", help=f"Supprimer {name}"):
        delete_course(name)
        st.rerun()

choice = st.sidebar.selectbox("Chercher dans", ["Tous les cours"] + list(courses))
source = None if choice == "Tous les cours" else choice

st.sidebar.header("Réglages")
max_distance = st.sidebar.slider(
    "Distance maximum acceptée", min_value=0.5, max_value=2.0, value=1.3, step=0.05
)
if st.sidebar.button("Nouvelle conversation"):
    st.session_state.messages = []

if "messages" not in st.session_state:
    st.session_state.messages = []


def show_assistant(content, note=None, sources=None):
    st.markdown(content)
    if note:
        st.caption(note)
    if sources:
        with st.expander("Passages examinés"):
            for s in sources:
                st.markdown(
                    f"**{s.get('source', '')} - page {s['page']}** "
                    f"(distance {s['distance']:.3f}) {s['statut']}"
                )
                st.text(s["text"])


for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        if m["role"] == "user":
            st.markdown(m["content"])
        else:
            show_assistant(m["content"], m.get("note"), m.get("sources"))

question = st.chat_input("Pose ta question sur tes cours")

if question and not courses:
    st.info("Indexe d'abord un cours avant de poser une question.")
elif question:
    history = [m for m in st.session_state.messages if not m.get("failed")]

    with st.chat_message("user"):
        st.markdown(question)

    try:
        with st.spinner("Recherche et réponse..."):
            standalone = rewrite_question(question, history)
            model = get_model()
            hits = search(standalone, model, k=3, source=source)

            if standalone != question:
                best = {(h["source"], h["page"], h["text"]): h for h in hits}
                for h in search(question, model, k=3, source=source):
                    key = (h["source"], h["page"], h["text"])
                    if key not in best or h["distance"] < best[key]["distance"]:
                        best[key] = h
                hits = sorted(best.values(), key=lambda h: h["distance"])[:3]

            relevant = [h for h in hits if h["distance"] <= max_distance]

            if relevant:
                answer = ask_llm(question, relevant, history)
            else:
                answer = "Je ne trouve pas la réponse dans le cours."
    except Exception as e:
        st.warning("Gemini est indisponible pour le moment. Réessaie dans un instant.")
        st.caption(f"Détail technique : {type(e).__name__}")
        st.stop()

    note = f"Question reformulée : {standalone}" if standalone != question else None
    sources = [
        {
            "source": h["source"],
            "page": h["page"],
            "distance": h["distance"],
            "text": h["text"],
            "statut": "retenu" if h["distance"] <= max_distance else "ignoré",
        }
        for h in hits
    ]

    with st.chat_message("assistant"):
        show_assistant(answer, note, sources)

    failed = not relevant
    st.session_state.messages.append(
        {"role": "user", "content": question, "failed": failed}
    )
    st.session_state.messages.append(
        {"role": "assistant", "content": answer, "note": note, "sources": sources, "failed": failed}
    )