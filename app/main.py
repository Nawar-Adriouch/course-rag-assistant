import streamlit as st
from pdf_utils import extract_pages, save_pdf, delete_pdf, render_page
from chunking import chunk_pages
from vectorstore import load_model, index_chunks, search, list_courses, delete_course
from llm import ask_llm, rewrite_question

st.set_page_config(page_title="Assistant de cours", layout="wide")


@st.cache_resource
def get_model():
    return load_model()


if "messages" not in st.session_state:
    st.session_state.messages = []
if "selected" not in st.session_state:
    st.session_state.selected = None  

st.title("Assistant de cours")


uploaded = st.file_uploader("Dépose un cours en PDF", type="pdf")

if uploaded is not None:
    pages = extract_pages(uploaded)
    chunks = chunk_pages(pages)
    st.success(f"{len(pages)} pages, découpées en {len(chunks)} chunks")

    if st.button("Indexer ce cours"):
        with st.spinner("Calcul des embeddings..."):
            model = get_model()
            save_pdf(uploaded)  
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
        delete_pdf(name)
        st.session_state.selected = None
        st.rerun()

choice = st.sidebar.selectbox("Chercher dans", ["Tous les cours"] + list(courses))
source = None if choice == "Tous les cours" else choice

st.sidebar.header("Réglages")
max_distance = st.sidebar.slider(
    "Distance maximum acceptée", min_value=0.5, max_value=2.0, value=1.3, step=0.05
)
if st.sidebar.button("Nouvelle conversation"):
    st.session_state.messages = []
    st.session_state.selected = None


def render_message(i, m):
    """Affiche un message, avec les boutons de citation pour l'assistant."""
    with st.chat_message(m["role"]):
        st.markdown(m["content"])
        if m["role"] != "assistant":
            return
        if m.get("note"):
            st.caption(m["note"])
        seen = set()
        for j, s in enumerate(m.get("sources", [])):
            key = (s["source"], s["page"])
            if not s.get("retenu") or key in seen:
                continue
            seen.add(key)
            if st.button(f"{s['source']} · page {s['page']}", key=f"cite_{i}_{j}"):
                st.session_state.selected = {
                    "msg": i, "source": s["source"], "page": s["page"]
                }



col_chat, col_panel = st.columns([3, 2], gap="large")
question = st.chat_input("Pose ta question sur tes cours")

with col_chat:
    for i, m in enumerate(st.session_state.messages):
        render_message(i, m)

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
            ok = True
        except Exception as e:
            ok = False
            st.warning("Gemini est indisponible pour le moment. Réessaie dans un instant.")
            st.caption(f"Détail technique : {type(e).__name__}")

        if ok:
            note = f"Question reformulée : {standalone}" if standalone != question else None
            sources = [
                {
                    "source": h["source"],
                    "page": h["page"],
                    "distance": h["distance"],
                    "text": h["text"],
                    "retenu": h["distance"] <= max_distance,
                }
                for h in hits
            ]
            failed = not relevant

            st.session_state.messages.append(
                {"role": "user", "content": question, "failed": failed}
            )
            st.session_state.messages.append(
                {"role": "assistant", "content": answer, "note": note,
                 "sources": sources, "failed": failed}
            )
            idx = len(st.session_state.messages) - 1

            cited = [s for s in sources if s["retenu"]]
            st.session_state.selected = {
                "msg": idx,
                "source": cited[0]["source"] if cited else None,
                "page": cited[0]["page"] if cited else None,
            }
            render_message(idx, st.session_state.messages[idx])

with col_panel:
    sel = st.session_state.selected
    if not sel:
        st.info("Pose une question : la page du cours citée s'affichera ici.")
    else:
        tab_cite, tab_pass = st.tabs(["Citation", "Passages examinés"])

        with tab_cite:
            if sel["source"]:
                st.caption(f"{sel['source']} - page {sel['page']}")
                img = render_page(sel["source"], sel["page"])
                if img:
                    st.image(img)
                else:
                    st.warning(
                        "PDF introuvable. Réindexe ce cours (bouton « Indexer ce cours ») "
                        "pour pouvoir afficher ses pages."
                    )
            else:
                st.info("Aucun passage assez proche : pas de citation.")

        with tab_pass:
            msgs = st.session_state.messages
            if sel["msg"] < len(msgs):
                for s in msgs[sel["msg"]].get("sources", []):
                    statut = "retenu" if s.get("retenu") else " ignoré"
                    st.markdown(
                        f"**{s['source']} - page {s['page']}** "
                        f"(distance {s['distance']:.3f}) {statut}"
                    )
                    st.text(s["text"])