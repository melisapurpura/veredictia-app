import streamlit as st
from google.cloud import discoveryengine_v1alpha as discoveryengine
from google.oauth2 import service_account

# --- Configuración ---
# Usamos st.secrets para manejar las credenciales de forma segura al desplegar.
try:
    # Cargar credenciales desde los secrets de Streamlit
    gcp_creds_dict = st.secrets["gcp"]["credentials"]
    credentials = service_account.Credentials.from_service_account_info(gcp_creds_dict)
    
    PROJECT_ID = st.secrets["gcp"]["project_id"]
    LOCATION = st.secrets["gcp"]["location"]
    DATA_STORE_ID = st.secrets["gcp"]["data_store_id"]
    
    client = discoveryengine.SearchServiceClient(credentials=credentials)

except (KeyError, FileNotFoundError):
    st.error("Error: No se encontraron las credenciales de GCP en los secrets de Streamlit.")
    st.stop()


def search_cases(query: str):
    """
    Función que llama a la API de Vertex AI Search y devuelve los resultados.
    """
    serving_config = client.serving_config_path(
        project=PROJECT_ID,
        location=LOCATION,
        data_store=DATA_STORE_ID,
        serving_config="default_config",
    )

    request = discoveryengine.SearchRequest(
        serving_config=serving_config,
        query=query,
        page_size=5,
        content_search_spec={
            "summary_spec": {
                "summary_result_count": 3,
                "model_prompt_spec": { "preamble": "Resume el siguiente texto en español de forma concisa como si fueras un asistente legal, sé muy detallado." }
            }
        }
    )
    
    return client.search(request)


st.title("Buscador Legal IA ⚖️")

# --- Interfaz de Usuario con Streamlit ---

st.title("Buscador Legal IA ⚖️")
st.write("Realiza una pregunta sobre los documentos legales para obtener un resumen y las fuentes relevantes.")

# Crear el campo de texto para la búsqueda
query = st.text_input("Escribe tu pregunta:", placeholder="Ej: ¿Qué se resolvió en el caso de Equipos Médicos Peninsulares?")

# Crear el botón de búsqueda
if st.button("Buscar"):
    if query:
        with st.spinner("Buscando y generando resumen..."):
            try:
                response = search_cases(query)
                
                if response.summary and response.summary.summary_text:
                    st.info("**Resumen Generado por IA:**")
                    st.markdown(response.summary.summary_text)
                else:
                    st.warning("No se pudo generar un resumen.")

                if response.results:
                    st.success("**Documentos Relevantes Encontrados:**")
                    for result in response.results:
                        title = result.document.derived_struct_data.get('title', 'Título no disponible')
                        link = result.document.derived_struct_data.get('link', '#')
                        with st.expander(f"**Fuente:** {title}"):
                            for snippet in result.document.derived_struct_data.get("snippets", []):
                                st.markdown(f"> ...{snippet.get('snippet', '')}...")
                            st.markdown(f"_[Ver documento completo]({link})_")
                else:
                    st.warning("No se encontraron documentos para la consulta.")

            except Exception as e:
                st.error(f"Ocurrió un error al contactar la API: {e}")
    else:
        st.warning("Por favor, escribe una pregunta.")