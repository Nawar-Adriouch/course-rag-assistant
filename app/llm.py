import os
import time
from google import genai
from google.genai import errors

MODELS = ["gemini-3.8-flash", "gemini-flash-latest", "gemini-flash-lite-latest"]


def _generate(prompt):
    """Appelle Gemini avec réessais (503) et modèle de secours (429)."""
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    last_error = None

    for model in MODELS:
        for attempt in range(3):
            try:
                response = client.models.generate_content(
                    model=model, contents=prompt
                )
                return response.text
            except errors.ServerError as e:
                last_error = e
                time.sleep(2 ** attempt)
            except errors.ClientError as e:
                last_error = e
                if getattr(e, "code", None) == 429:
                    break
                raise

    raise last_error


def format_history(history, max_messages=6):
    lines = []
    for m in history[-max_messages:]:
        role = "Étudiant" if m["role"] == "user" else "Assistant"
        lines.append(f"{role} : {m['content']}")
    return "\n".join(lines)


def rewrite_question(question, history):
    if not history:
        return question

    prompt = f"""Voici une conversation entre un étudiant et un assistant de cours.

{format_history(history)}

NOUVELLE QUESTION : {question}

Réécris la nouvelle question pour qu'elle soit compréhensible seule, sans la conversation
(remplace "il", "elle", "le", "ça" par ce qu'ils désignent).
N'ajoute AUCUN mot qui ne vient pas de la conversation (ne précise pas de domaine comme "informatique").
Si la question est déjà claire, recopie-la exactement telle quelle.
Réponds uniquement avec la question réécrite, sans explication."""
    return _generate(prompt).strip()


def build_prompt(question, hits, history=None):
    context = "\n\n".join(
        f"[Cours : {h['source']} - Page {h['page']}]\n{h['text']}" for h in hits
    )
    history_block = ""
    if history:
        history_block = (
            "\nCONVERSATION PRÉCÉDENTE (sert uniquement à comprendre la question, "
            "ce n'est pas une source d'information) :\n"
            f"{format_history(history)}\n"
        )

    return f"""Tu es un assistant pour étudiants.
Réponds à la question en utilisant UNIQUEMENT les extraits de cours ci-dessous.
Si la réponse n'est pas dans les extraits, réponds exactement : "Je ne trouve pas la réponse dans le cours."
Fais une réponse complète, en reformulant avec tes mots.
Cite les sources utilisées sous la forme (nom du cours, page X).
{history_block}
EXTRAITS :
{context}

QUESTION : {question}

RÉPONSE :"""
def ask_llm(question, hits, history=None):
    return _generate(build_prompt(question, hits, history))