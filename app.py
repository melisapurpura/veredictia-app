import streamlit as st
from google.oauth2 import service_account
from google.cloud import discoveryengine_v1alpha as de

# — Config de página (mover arriba) —
st.set_page_config(page_title="Buscador Legal IA", page_icon="⚖️")

# 1. Secrets
creds_info     = st.secrets["gcp"]["credentials"]
PROJECT_NUMBER = st.secrets["gcp"]["project_number"]
ENGINE_ID      = st.secrets["gcp"]["engine_id"]
LOCATION       = "global"

# 2. Cliente (cache)
@st.cache_resource(show_spinner=False)
def get_client():
    credentials = service_account.Credentials.from_service_account_info(creds_info)
    return de.SearchServiceClient(credentials=credentials)

client = get_client()

SERVING_CONFIG = (
    f"projects/{PROJECT_NUMBER}"
    f"/locations/{LOCATION}"
    f"/collections/default_collection"
    f"/engines/{ENGINE_ID}"
    f"/servingConfigs/default_search"
)

# 3. Búsqueda con follow-ups
def search_cases(query: str):
    request = de.SearchRequest(
        serving_config = SERVING_CONFIG,
        query          = query,
        page_size      = 10,
        guided_search_spec = {"enable_guided_search": True},
        content_search_spec = {"summary_spec": {"summary_result_count": 3}},
    )
    return client.search(request)

# 4. UI
if "query" not in st.session_state:
    st.session_state["query"] = ""

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

            # Resumen
            summary = getattr(response.summary, "summary_text", "")
            if summary:
                st.subheader("Resumen")
                st.markdown(summary)

            # Resultados
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

            # Follow-ups
            followups = getattr(response.guided_search_result, "follow_up_questions", [])
            if followups:
                st.subheader("Preguntas sugeridas:")
                cols = st.columns(2)
                for i, fq in enumerate(followups):
                    if cols[i % 2].button(
                        fq.suggested_query,
                        key=f"fq_{i}_{hash(query)}"
                    ):
                        st.session_state["query"] = fq.suggested_query
                        st.experimental_rerun()

        except Exception as e:
            st.error(f"Ocurrió un error al consultar la API:\n\n{e}")

elif search_pressed:
    st.warning("Por favor, escribe una pregunta antes de buscar.")
