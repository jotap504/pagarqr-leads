import streamlit as st
import pandas as pd
import re
import time
import requests
import os
from bs4 import BeautifulSoup
from ddgs import DDGS
from db_handler import Database
from email_sender import EmailSender

# Configuración de página
st.set_page_config(page_title="PagarQR - Lead Scraper", page_icon="🔍", layout="wide")

# Inicializar Base de Datos y Email
db = Database()
mailer = EmailSender()

st.title("🔍 PagarQR - B2B Lead Scraper & CRM")

# Tabs principales
tab1, tab2, tab3 = st.tabs(["🚀 Scraper", "📋 Depuración (CRM)", "✉️ Campañas Email"])

# --- TAB 1: SCRAPER ---
with tab1:
    st.header("Extracción de Leads")
    
    # --- PANEL LATERAL (PARÁMETROS) ---
    with st.expander("⚙️ Configurar Búsqueda", expanded=True):
        col_a, col_b = st.columns(2)
        with col_a:
            keywords = st.text_input("Palabras clave", value="fabricante dispenser agua caliente mate")
            zone = st.text_input("Zona o Ubicación", value="Argentina")
        with col_b:
            exclude_sites_raw = st.text_input("Sitios a excluir (ej: mercadolibre, facebook, instagram)", value="mercadolibre, facebook, instagram, youtube, pinterest")
            num_results = st.slider("Links a analizar", 10, 100, 20)

    # --- PROCESAR PARÁMETROS ---
    exclude_list = [s.strip().lower() for s in exclude_sites_raw.split(",") if s.strip()]
    excl_str = " ".join([f"-site:{site}" for site in exclude_list])
    final_query = f"{keywords} {zone} {excl_str}".strip()
    st.code(f"Query enviada: {final_query}")

    # Inicializar offset en session_state si no existe
    if 'search_offset' not in st.session_state:
        st.session_state.search_offset = 0

    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🚀 Nueva Búsqueda (Primeros 100)", use_container_width=True):
            st.session_state.search_offset = 0
            st.rerun()

    with col2:
        if st.button("➕ Cargar Siguientes 100", use_container_width=True):
            st.session_state.search_offset += 100
            st.rerun()

    # Si hay un offset activo, ejecutamos la búsqueda
    if 'last_query' not in st.session_state:
        st.session_state.last_query = ""

    # Lógica de ejecución automática tras pulsar botones
    trigger_search = False
    if final_query != st.session_state.last_query:
        # Si la query cambió, reseteamos todo
        st.session_state.search_offset = 0
        st.session_state.last_query = final_query
    
    # Usamos un flag para saber si acabamos de pulsar un botón de búsqueda
    # (En Streamlit esto se suele manejar con un botón que cambia el estado)
    
    # Para simplificar la UX, vamos a ejecutar la búsqueda si el offset es > 0 
    # o si es la primera vez que se pulsa el botón principal.
    
    # RE-DISEÑO DEL BOTÓN PARA EVITAR CONFUSIÓN:
    st.markdown(f"**Progreso actual:** Resultados del {st.session_state.search_offset + 1} al {st.session_state.search_offset + 100}")

    if st.button("🔍 Iniciar Proceso de Extracción", type="primary"):
        with st.status(f"Analizando bloque {st.session_state.search_offset + 1} - {st.session_state.search_offset + 100}...") as status:
            results = []
            try:
                # Obtenemos los leads existentes para evitar duplicados
                existing_urls = set(db.get_all_leads()['website'].str.lower().tolist())
                
                with DDGS() as ddgs:
                    # Pedimos hasta el final del bloque actual
                    total_to_fetch = st.session_state.search_offset + 100
                    all_results = list(ddgs.text(final_query, max_results=total_to_fetch))
                    
                    # Nos quedamos solo con los últimos 100 (o los que haya en el bloque)
                    current_batch = all_results[st.session_state.search_offset:]
                
                for idx, res in enumerate(current_batch):
                    url = res.get('href', '').lower()
                    title = res.get('title', 'Sin título')
                    
                    # FILTRO DE EXCLUSIÓN
                    should_exclude = any(site in url for site in exclude_list)
                    # FILTRO DE DUPLICADOS (ya en DB)
                    is_duplicate = url in existing_urls
                    
                    if url and not should_exclude and not is_duplicate:
                        st.write(f"✅ Analizando: {url}")


                        # Lógica de extracción (simplificada aquí, pero igual a la anterior)
                        try:
                            headers = {'User-Agent': 'Mozilla/5.0'}
                            resp = requests.get(url, headers=headers, timeout=5)
                            text = resp.text
                            
                            emails = re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', text)
                            wa = re.findall(r'(?:\+|00)?(?:54|54\s*9)?\s*(?:11|[23]\d{2})\s*\d{3,4}[\s-]*\d{4}', text)
                            
                            if emails or wa:
                                lead = {
                                    "company": title,
                                    "website": url,
                                    "email": ", ".join(set(emails)) if emails else "",
                                    "whatsapp": ", ".join(set(wa)) if wa else "",
                                    "niche": keywords,
                                    "source": "DuckDuckGo",
                                    "notes": "Scraper Web"
                                }
                                db.insert_lead(lead)
                                results.append(lead)
                        except:
                            pass
                status.update(label="¡Extracción completada!", state="complete")
                st.success(f"Se encontraron y guardaron {len(results)} leads nuevos.")
            except Exception as e:
                st.error(f"Error: {e}")

# --- TAB 2: DEPURACIÓN ---
with tab2:
    st.header("Gestión y Limpieza de Leads")
    leads_df = db.get_all_leads()
    
    if not leads_df.empty:
        # Filtros
        status_filter = st.multiselect("Filtrar por estado", options=["Pendiente", "Validado", "Descartado", "Enviado"], default=["Pendiente", "Validado"])
        filtered_df = leads_df[leads_df['status'].isin(status_filter)]
        
        st.dataframe(filtered_df, use_container_width=True)
        
        # Acciones masivas/individuales
        with st.expander("✏️ Editar Lead"):
            lead_id = st.number_input("ID del Lead a editar", min_value=1, step=1)
            new_status = st.selectbox("Nuevo Estado", ["Pendiente", "Validado", "Descartado"])
            new_notes = st.text_area("Notas")
            if st.button("Actualizar Lead"):
                db.update_lead_status(lead_id, new_status)
                db.update_lead_notes(lead_id, new_notes)
                st.success("Lead actualizado.")
                st.rerun()
    else:
        st.info("No hay leads en la base de datos.")

# --- TAB 3: CAMPAÑAS ---
with tab3:
    st.header("Enviar Campaña de Email")
    
    # Seleccionar destinatarios
    leads_df = db.get_all_leads()
    valid_leads = leads_df[leads_df['status'] == 'Validado']
    
    if valid_leads.empty:
        st.warning("No hay leads con estado 'Validado'. Primero depura los leads en la pestaña anterior.")
    else:
        st.write(f"Destinatarios listos: {len(valid_leads)}")
        
        subject = st.text_input("Asunto del correo", value="Propuesta PagarQR - Mejora tus ventas")
        template = st.text_area("Cuerpo del mensaje (HTML permitido)", height=300)
        
        if st.button("📧 Enviar a todos los validados"):
            sent_count = 0
            for _, row in valid_leads.iterrows():
                if row['email']:
                    # Tomar el primer email si hay varios
                    email = row['email'].split(",")[0].strip()
                    success, msg = mailer.send_email(email, subject, template)
                    if success:
                        db.update_lead_status(row['id'], 'Enviado')
                        sent_count += 1
                    else:
                        st.error(f"Error enviando a {email}: {msg}")
            
            st.success(f"Campaña finalizada. Se enviaron {sent_count} correos.")
            st.rerun()

st.divider()
st.caption("PagarQR CRM & Scraper - v2.0")
