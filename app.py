# app.py
# ════════════════════════════════════════════════════════════════════
# Buscador Legal IA · Streamlit + Vertex AI Search (engine global)
# ════════════════════════════════════════════════════════════════════

import streamlit as st
from google.oauth2 import service_account
from google.cloud import discoveryengine_v1beta as de   # v1beta

# ────────────────────────────────────────────────────────────
# Config global de página (debe ir antes de cualquier widget)
# ────────────────────────────────────────────────────────────
st.set_page_config(page_title="Buscador Legal IA", page_icon="⚖️")

# ────────────────────────────────────────────────────────────
# 1. Leer secretos
# ────────────────────────────────────────────────────────────
creds_info     = st.secrets["gcp"]["credentials"]
PROJECT_NUMBER = st.secrets["gcp"]["project_number"]        # 107344050799
ENGINE_ID      = st.secrets["gcp"]["engine_id"]             # veredictia_ocr_…

LOCATION = "global"  # La app se creó como multirregión global

# ────────────────────────────────────────────────────────────
# 2. Cliente y SERVING_CONFIG (cacheados)
# ────────────────────────────────────────────────────────────
@st.cache_resource(show_spinner=False)
def get_client_and_config():
    credentials = service_account.Credentials.from_service_account_info(creds_info)
    client = de.SearchServiceClient(credentials=credentials)
    serving_config = (
        f"projects/{PROJECT_NUMBER}/locations/{LOCATION}"
        f"/collections/default_collection/engines/{ENGINE_ID}"
        f"/servingConfigs/default_search"     # o default_config si tu consola lo muestra así
    )
    return client, serving_config

client, SERVING_CONFIG = get_client_and_config()

# ────────────────────────────────────────────────────────────
# 3. Función de búsqueda (sin follow-ups: SDK ≤ 0.13.x)
# ────────────────────────────────────────────────────────────
def search_cases(query: str):
    request = de.SearchRequest(
        serving_config = SERVING_CONFIG,
        query          = query,
        page_size      = 10,
        content_search_spec = {
            "summary_spec": {"summary_result_count": 3}
        },
    )
    return client.search(request)

# ────────────────────────────────────────────────────────────
# 4. Interfaz Streamlit
# ────────────────────────────────────────────────────────────
if "query" not in st.session_state:
    st.session_state["query"] = ""

st.title("⚖️ Buscador Legal IA")

query = st.text_input(
    "Pregunta:",
    value=st.session_state["query"],
    placeholder="¿Qué precedentes existen sobre arrendamiento financiero?",
    key="query_input"
)

search_pressed = st.button("Buscar", key="search_btn")

if search_pressed and query:
    with st.spinner("Consultando Vertex AI Search…"):
        try:
            response = search_cases(query)

            # ── Resumen ───────────────────────────────────────
            summary = getattr(response.summary, "summary_text", "")
            if summary:
                st.subheader("Resumen")
                st.markdown(summary)

            # ── Resultados ───────────────────────────────────
            if response.results:
                st.subheader("Documentos relevantes")

                for r in response.results:
                    meta   = r.document.derived_struct_data
                    title  = meta.get("title", "Título no disponible")

                    # 1️⃣ Link al documento
                    link = meta.get("link") or getattr(r.document, "uri", "#")

                    # 2️⃣ Snippets y páginas
                    snippets = meta.get("snippets", [])
                    with st.expander(title):
                        for snip in snippets:
                            text = snip.get("snippet", "")
                            page = snip.get("documentPageNumber")
                            page_tag = f" _(pág. {page})_" if page is not None else ""
                            st.markdown(f"> …{text}…{page_tag}")

                        if link != "#":
                            # Añade ancla #page=n si es PDF
                            first_page = snippets[0].get("documentPageNumber") if snippets else None
                            display_link = (
                                f"{link}#page={first_page}"
                                if first_page and link.lower().endswith(".pdf")
                                else link
                            )
                            st.markdown(f"[Abrir documento completo]({display_link})")
            else:
                st.warning("No se encontraron documentos.")

            # (Opcional) follow-ups futuribles: el bloque se mantiene seguro
            followups = getattr(getattr(response, "guided_search_result", None), "follow_up_questions", [])
            if followups:
                st.subheader("Preguntas sugeridas:")
                cols = st.columns(2)
                for i, fq in enumerate(followups):
                    if cols[i % 2].button(
                        fq.suggested_query, key=f"fq_{i}_{hash(query)}"
                    ):
                        st.session_state["query"] = fq.suggested_query
                        st.experimental_rerun()

        except Exception as e:
            st.error(f"Ocurrió un error al consultar la API:\n\n{e}")

elif search_pressed:
    st.warning("Por favor, escribe una pregunta antes de buscar.")
