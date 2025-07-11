# app.py
# ════════════════════════════════════════════════════════════════════
# Buscador Legal IA  ·  Streamlit + Vertex AI Search (engine global)
# ════════════════════════════════════════════════════════════════════

import streamlit as st
from google.oauth2 import service_account
from google.cloud import discoveryengine_v1alpha as de

# ────────────────────────────────────────────────────────────
# 1. Leer secretos
# ────────────────────────────────────────────────────────────
creds_info      = st.secrets["gcp"]["credentials"]
PROJECT_NUMBER  = st.secrets["gcp"]["project_number"]        # 107344050799
ENGINE_ID       = st.secrets["gcp"]["engine_id"]             # veredictia_global_…

LOCATION = "global"  # La app se creó como multirregión global

# ────────────────────────────────────────────────────────────
# 2. Crear cliente y SERVING_CONFIG (una sola vez gracias a cache)
# ────────────────────────────────────────────────────────────
@st.cache_resource(show_spinner=False)
def get_search_client():
    credentials = service_account.Credentials.from_service_account_info(creds_info)
    return de.SearchServiceClient(credentials=credentials)

client = get_search_client()

SERVING_CONFIG = (
    f"projects/{PROJECT_NUMBER}"
    f"/locations/{LOCATION}"
    f"/collections/default_collection"
    f"/engines/{ENGINE_ID}"
    f"/servingConfigs/default_search"      # Confirma en pestaña "Serving configs"
)

# ────────────────────────────────────────────────────────────
# 3. Función de búsqueda
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
st.set_page_config(page_title="Buscador Legal IA", page_icon="⚖️")
st.title("⚖️ Buscador Legal IA")

st.write(
    "Ingresa tu pregunta sobre jurisprudencia. "
    "El sistema generará un resumen y listará los documentos relevantes."
)

query = st.text_input(
    "Pregunta:",
    placeholder="¿Qué precedentes existen sobre arrendamiento financiero?"
)

search_pressed = st.button("Buscar", key="search_btn")

# ────────────────────────────────────────────────────────────
# 5. Lógica al presionar el botón
# ────────────────────────────────────────────────────────────
if search_pressed and query:
    with st.spinner("Consultando Vertex AI Search…"):
        try:
            response = search_cases(query)

            # ── Resumen ─────────────────────────────────────
            summary = getattr(response.summary, "summary_text", "")
            if summary:
                st.subheader("Resumen")
                st.markdown(summary)
            else:
                st.info("No se generó resumen para esta consulta.")

            # ── Resultados ─────────────────────────────────
            if response.results:
                st.subheader("Documentos relevantes")
                for r in response.results:
                    meta  = r.document.derived_struct_data
                    title = meta.get("title", "Título no disponible")
                    link  = meta.get("link", "#")

                    with st.expander(title):
                        for snip in meta.get("snippets", []):
                            st.markdown(f"> …{snip.get('snippet', '')}…")
                        if link != "#":
                            st.markdown(f"[Abrir documento]({link})")
            else:
                st.warning("No se encontraron documentos.")

        except Exception as e:
            st.error(f"Ocurrió un error al consultar la API:\n\n{e}")

elif search_pressed:
    st.warning("Por favor, escribe una pregunta antes de buscar.")
