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
            exclude_sites = st.text_input("Sitios a excluir (comma separated)", value="mercadolibre.com.ar, facebook.com, instagram.com")
            num_results = st.slider("Links a analizar", 10, 100, 20)

    # Construir Query
    excl_str = " ".join([f"-site:{site.strip()}" for site in exclude_sites.split(",") if site.strip()])
    final_query = f"{keywords} {zone} {excl_str}".strip()
    st.code(f"Query: {final_query}")

    if st.button("🚀 Iniciar Extracción"):
        with st.status("Buscando prospectos...") as status:
            results = []
            try:
                with DDGS() as ddgs:
                    search_results = list(ddgs.text(final_query, max_results=num_results))
                
                for idx, res in enumerate(search_results):
                    url = res.get('href', '')
                    title = res.get('title', 'Sin título')
                    if url:
                        st.write(f"Analizando: {url}")
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
