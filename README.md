Assistant de cours (RAG)

Application web où un étudiant importe ses cours en PDF et pose des questions. L'IA répond à partir du contenu des cours (et non de ses connaissances générales), en indiquant le cours et la page utilisés.

Fonctionnalités

-Import et indexation de plusieurs cours PDF (réindexer un cours le remplace, sans doublon).
-Recherche par le sens (embeddings), dans tous les cours ou dans un seul.
-Réponses sourcées : nom du cours et numéro de page.
-Seuil de distance réglable : si aucun passage n'est assez proche, l'application répond « Je ne trouve pas la réponse dans le cours. » sans appeler le LLM.
-Historique de conversation : les questions de suivi (« et ses étapes ? ») sont reformulées avant la recherche.
-Affichage des passages examinés, pour vérifier les réponses.

Comment ça marche

-Extraction : le texte est lu page par page (pypdf).
-Découpage : chaque page est découpée en chunks d'environ 800 caractères, avec 150 caractères de chevauchement.
-Embeddings : chaque chunk devient un vecteur de 384 nombres (paraphrase-multilingual-MiniLM-L12-v2, local, sans clé API).
-Stockage : les vecteurs, le texte, la page et le nom du cours sont enregistrés dans ChromaDB.
-Recherche : la question est transformée en vecteur avec le même modèle, puis on récupère les 3 passages les plus proches.
-Filtrage : les passages au-dessus de la distance maximale sont écartés.
-Réponse : les passages retenus et la question sont envoyés à Gemini, qui répond uniquement à partir de ces extraits et cite ses sources.

Technologie utilisées :

Python : Logique de l'application
Streamlit : Interface web
pypdf : Extraction du texte des PDF
sentence-transformers :	Embeddings multilingues
ChromaDB  :	Base de données vectorielle
Google Gemini (API) :	Rédaction des réponses
Docker / Docker Compose	: Environnement reproductible

Installation
Récupère le projet :

bash
   git clone <https://github.com/Nawar-Adriouch/course-rag-assistant.git>
   cd rag-cours

Crée un fichier .env à la racine, avec ta clé (sans guillemets ni espaces autour du =) :
   GEMINI_API_KEY=ta_cle_ici


Lance l'application :
bash
   docker compose up --build

Le premier lancement est long : les bibliothèques sont installées, puis le modèle d'embeddings (environ 470 Mo) est téléchargé au premier clic sur « Indexer ce cours ». Ensuite, il est conservé dans un volume Docker.

Ouvre http://localhost:8501.

Utilisation : 

-Dépose un PDF de cours et clique sur Indexer ce cours.
-Répète l'opération pour d'autres cours si tu le souhaites. La liste des cours indexés est dans la barre latérale (où tu peux aussi les supprimer).
-Choisis de chercher dans « Tous les cours » ou dans un cours précis.
-Pose tes questions dans la zone de chat.
-Ouvre « Passages examinés » sous une réponse pour voir les extraits utilisés et leur distance.

Dans la barre latérale :

Distance maximum acceptée : plus elle est basse, plus l'application est stricte. Valeur par défaut : 1.3. Si de bonnes questions sont rejetées, augmente-la. Si des questions hors sujet reçoivent une réponse, baisse-la.
Nouvelle conversation : efface l'historique.