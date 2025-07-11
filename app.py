import streamlit as st
from google.oauth2 import service_account
from google.cloud import discoveryengine_v1alpha as discoveryengine

# ── 1. Secrets ──────────────────────────────────────────────────────
creds_info = st.secrets["gcp"]["credentials"]
PROJECT_NUMBER = st.secrets["gcp"]["project_number"]           # 107344050799
COLLECTION_ID  = st.secrets["gcp"]["collection_id"]           # casos-mvp_1752189050616
DATA_STORE_ID  = st.secrets["gcp"]["data_store_id"]           # casos-mvp_1752189050616_gcs_store
LOCATION       = "us"                                         # EXACTO como en consola

# ── 2. Cliente y serving_config (construido a mano) ────────────────
credentials = service_account.Credentials.from_service_account_info(creds_info)
client      = discoveryengine.SearchServiceClient(credentials=credentials)

SERVING_CONFIG = (
    f"projects/{PROJECT_NUMBER}"
    f"/locations/{LOCATION}"
    f"/collections/{COLLECTION_ID}"
    f"/dataStores/{DATA_STORE_ID}"
    f"/servingConfigs/default_search"       # o default_config, según tu consola
)

@st.cache_resource(show_spinner=False)
def get_client():
    return client

# ── 3. Función de búsqueda ─────────────────────────────────────────
def search_cases(query: str):
    request = discoveryengine.SearchRequest(
        serving_config = SERVING_CONFIG,
        query          = query,
        page_size      = 10,
        content_search_spec = {
            "summary_spec": {"summary_result_count": 3}
        },
    )
    return client.search(request)

# ── 4. UI -----------------------------------------------------------
st.title("⚖️ Buscador Legal IA")
st.write("Haz una pregunta y obtén jurisprudencia relevante.")

query = st.text_input(
    "Tu pregunta:",
    placeholder="¿Qué precedentes existen sobre arrendamiento financiero?",
)
search_pressed = st.button("Buscar", key="search_btn")

if search_pressed and query:
    with st.spinner("Consultando Vertex AI Search…"):
        try:
            response = search_cases(query)
            summary  = getattr(response.summary, "summary_text", "")
            if summary:
                st.subheader("Resumen")
                st.markdown(summary)
            else:
                st.info("No se generó resumen.")
            if response.results:
                st.subheader("Documentos")
                for r in response.results:
                    meta  = r.document.derived_struct_data
                    title = meta.get("title", "Sin título")
                    link  = meta.get("link", "#")
                    with st.expander(title):
                        for snip in meta.get("snippets", []):
                            st.markdown(f"> …{snip.get('snippet', '')}…")
                        if link != "#":
                            st.markdown(f"[Abrir documento]({link})")
            else:
                st.warning("Sin resultados.")
        except Exception as e:
            st.error(f"Ocurrió un error:\n\n{e}")
elif search_pressed:
    st.warning("Escribe primero tu pregunta.")
