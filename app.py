import streamlit as st
from google.oauth2 import service_account
from google.cloud import discoveryengine_v1alpha as discoveryengine

# ──────────────────────────────────────────────
# 1. Cargar secretos y credenciales de GCP
# ──────────────────────────────────────────────
try:
    gcp_creds_dict   = st.secrets["gcp"]["credentials"]
    PROJECT_NUMBER   = st.secrets["gcp"]["project_number"]   # 107344050799
    DATA_STORE_ID    = st.secrets["gcp"]["data_store_id"]    # casos-mvp_1752189050616
except KeyError as e:
    st.error(f"Falta la clave {e} en .streamlit/secrets.toml")
    st.stop()

credentials   = service_account.Credentials.from_service_account_info(gcp_creds_dict)
LOCATION      = "global"    # El endpoint de búsqueda siempre usa global

# ──────────────────────────────────────────────
# 2. Crear cliente y ruta SERVING_CONFIG (una vez)
# ──────────────────────────────────────────────
@st.cache_resource(show_spinner=False)
def get_client():
    return discoveryengine.SearchServiceClient(credentials=credentials)

client = get_client()

SERVING_CONFIG = client.serving_config_path(
    project        = PROJECT_NUMBER,
    location       = LOCATION,
    data_store     = DATA_STORE_ID,
    serving_config = "default_search",          # Ver pestaña “Serving configs” en consola
)

# ──────────────────────────────────────────────
# 3. Lógica de búsqueda
# ──────────────────────────────────────────────
def search_cases(query: str):
    request = discoveryengine.SearchRequest(
        serving_config = SERVING_CONFIG,
        query          = query,
        page_size      = 10,
        content_search_spec = {
            "summary_spec": {
                "summary_result_count": 3,
                "model_prompt_spec": {
                    "preamble": (
                        "Resume el siguiente texto en español, con detalle, "
                        "y tono de asistente legal."
                    )
                },
            }
        },
    )
    return client.search(request)

# ──────────────────────────────────────────────
# 4. Interfaz Streamlit
# ──────────────────────────────────────────────
st.title("⚖️ Buscador Legal IA")

st.write(
    "Haz una pregunta sobre los casos cargados. "
    "Obtendrás un resumen generado por IA y los documentos relevantes."
)

query = st.text_input(
    label      = "Escribe tu pregunta:",
    placeholder= "Ej: ¿Qué se resolvió en el caso de Equipos Médicos Peninsulares?"
)

if st.button("Buscar") and query:
    with st.spinner("Buscando…"):
        try:
            response = search_cases(query)

            # ── Resumen ─────────────────────
            summary_text = getattr(response.summary, "summary_text", "")
            if summary_text:
                st.subheader("Resumen:")
                st.markdown(summary_text)
            else:
                st.info("No se pudo generar un resumen para esta consulta.")

            # ── Resultados ──────────────────
            if response.results:
                st.subheader("Documentos relevantes:")
                for result in response.results:
                    meta  = result.document.derived_struct_data
                    title = meta.get("title", "Título no disponible")
                    link  = meta.get("link", "#")

                    with st.expander(title):
                        for snip in meta.get("snippets", []):
                            st.markdown(f"> …{snip.get('snippet', '')}…")
                        if link != "#":
                            st.markdown(f"_[Abrir documento completo]({link})_")
            else:
                st.warning("No se encontraron documentos para esa búsqueda.")

        except Exception as e:
            st.error(f"Ocurrió un error al contactar la API:\n\n{e}")
elif st.button("Buscar"):
    st.warning("Por favor, escribe una pregunta antes de buscar.")
