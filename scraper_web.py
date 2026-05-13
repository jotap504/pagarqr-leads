import streamlit as st
import pandas as pd
from googlesearch import search
import requests

from bs4 import BeautifulSoup
import re
import time
from db_handler import Database
from ai_handler import AIHandler
from encryptor import Encryptor
from email_sender import EmailSender
import os
import cloudscraper

# Inicializar scraper avanzado
scraper = cloudscraper.create_scraper()


# --- CONFIGURACIÓN ---
st.set_page_config(page_title="PagarQR Marketing Pro", page_icon="🚀", layout="wide")

# Inicializar clases
db = Database()
ai = AIHandler()
enc = Encryptor()

# --- ESTILOS ---
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stButton>button { border-radius: 8px; }
    .status-valid { color: #28a745; font-weight: bold; }
    .status-discarded { color: #dc3545; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

# --- BARRA LATERAL (GESTIÓN DE CAMPAÑAS) ---
# st.sidebar.image("/nav-logo.png", width=100)
st.sidebar.title("🎯 Control de Campañas")


all_campaigns = db.get_campaigns()
if all_campaigns:
    campaign_names = [c['name'] for c in all_campaigns]
    selected_campaign_name = st.sidebar.selectbox("Seleccionar Campaña Activa", campaign_names)
    active_campaign = next(c for c in all_campaigns if c['name'] == selected_campaign_name)
    st.sidebar.info(f"Estado: {active_campaign['status'].upper()}")
else:
    active_campaign = None
    st.sidebar.warning("No hay campañas creadas.")

# --- TABS PRINCIPALES ---
tab_camp, tab_scrap, tab_filter, tab_mail = st.tabs([
    "📂 Gestión de Campañas", 
    "🔍 Scraper de Leads", 
    "🤖 Filtrado IA", 
    "✉️ Envio & Mailing"
])

# --- TAB 1: GESTIÓN DE CAMPAÑAS ---
with tab_camp:
    st.header("📂 Tus Campañas de Marketing")
    
    col1, col2 = st.columns([1, 2])
    with col1:
        st.subheader("Crear Nueva Campaña")
        new_name = st.text_input("Nombre de la Campaña", placeholder="Ej: Dispenser GBA Norte Mayo")
        if st.button("Crear Campaña"):
            if new_name:
                cid = db.create_campaign(new_name)
                st.success(f"Campaña '{new_name}' creada!")
                st.rerun()
    
    with col2:
        st.subheader("Campañas Recientes")
        if all_campaigns:
            df_camp = pd.DataFrame(all_campaigns)[['name', 'status', 'created_at']]
            st.dataframe(df_camp, use_container_width=True)
        else:
            st.info("Crea tu primera campaña para empezar.")

# --- TAB 2: SCRAPER (VINCULADO A CAMPAÑA) ---
with tab_scrap:
    if not active_campaign:
        st.error("⚠️ Primero debes seleccionar o crear una campaña en la barra lateral.")
    else:
        st.header(f"🔍 Buscando Leads para: {active_campaign['name']}")
        
        with st.expander("⚙️ Configuración de Búsqueda", expanded=True):
            col_a, col_b = st.columns(2)
            with col_a:
                keywords = st.text_input("Palabras clave (sepáralas por coma)", value=active_campaign.get('config', {}).get('keywords', "fabricante, dispenser"))
                
                # Mapeo de regiones
                regions = {
                    "Argentina": "ar-es",
                    "España": "es-es",
                    "México": "mx-es",
                    "Chile": "cl-es",
                    "Global": "wt-wt"
                }
                zone_label = st.selectbox("País / Región", list(regions.keys()), index=0)
                city_filter = st.text_input("Ciudad (Opcional - Más rápido)", placeholder="Ej: Buenos Aires")
                region_code = regions[zone_label]

                
            with col_b:
                exclude_sites = st.text_input("Excluir sitios", value="mercadolibre, facebook, instagram, youtube")
                num_results = st.slider("Resultados por bloque", 10, 500, 50)


        # Lógica de Offset
        if 'scrap_offset' not in st.session_state: st.session_state.scrap_offset = 0
        
        c1, c2, c3 = st.columns([1, 1, 2])
        with c1:
            if st.button("🔄 Reiniciar Búsqueda"):
                st.session_state.scrap_offset = 0
                st.rerun()
        with c2:
            if st.button("➕ Siguientes 100"):
                st.session_state.scrap_offset += 100
                st.rerun()
        
        st.write(f"Rango actual: {st.session_state.scrap_offset + 1} - {st.session_state.scrap_offset + 100}")

        if st.button("🚀 Iniciar Extracción", type="primary"):
            with st.status("Procesando búsqueda...") as status:
                existing_leads = db.get_leads_by_campaign(active_campaign['id'])
                existing_urls = {l['website'].lower() for l in existing_leads}
                
                # --- PROCESAR PARÁMETROS ---
                keyword_list = [k.strip() for k in keywords.split(",") if k.strip()]
                exclude_list = [s.strip().lower() for s in exclude_sites.split(",") if s.strip()]
                urls_to_analyze = {} # Usamos dict para guardar URL -> Fuente

                # --- MODO 1: OPENSTREETMAP (MAPA) ---
                st.write(f"🗺️ Buscando empresas en el mapa...")
                try:
                    overpass_url = "https://overpass-api.de/api/interpreter"
                    area_name = city_filter if city_filter else zone_label
                    for k in keyword_list:
                        osm_query = f"""
                        [out:json][timeout:30];
                        area["name"="{area_name}"]->.searchArea;
                        (
                          nwr["name"~"{k}",i](area.searchArea);
                          nwr["shop"~"{k}",i](area.searchArea);
                          nwr["industrial"~"{k}",i](area.searchArea);
                        );
                        out body;
                        """
                        response = requests.post(overpass_url, data={'data': osm_query}, timeout=35)
                        if response.status_code == 200:
                            data = response.json()
                            elements = data.get('elements', [])
                            st.write(f"📍 Mapa: {len(elements)} resultados para '{k}' en {area_name}.")
                            for el in elements:
                                website = el.get('tags', {}).get('website')
                                if website:
                                    if not website.startswith('http'): website = 'http://' + website
                                    urls_to_analyze[website] = "🗺️ Mapa (OSM)"
                except Exception as e:
                    st.write(f"⚠️ El mapa no respondió.")

                # --- MODO 2: BRAVE (WEB) ---
                for k in keyword_list:
                    st.write(f"📡 Buscando en Brave: *{k}*...")
                    try:
                        search_url = f"https://search.brave.com/search?q={k}+{area_name}"
                        headers = {'User-Agent': 'Mozilla/5.0'}
                        b_resp = requests.get(search_url, headers=headers, timeout=10)
                        b_urls = re.findall(r'href="(https?://[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}[^"]*)"', b_resp.text)
                        for u in b_urls:
                            if u not in urls_to_analyze and not any(x in u for x in ['brave.com', 'google', 'facebook', 'instagram']):
                                urls_to_analyze[u] = "🦁 Brave Search"
                    except:
                        pass

                # --- MODO 3: GOOGLE (WEB) ---
                for k in keyword_list:
                    st.write(f"📡 Buscando en Google: *{k}*...")
                    try:
                        results = search(f"{k} {area_name}", num_results=10, lang="es")
                        for u in results:
                            if u not in urls_to_analyze:
                                urls_to_analyze[u] = "🔍 Google"
                    except:
                        pass

                st.write(f"🔎 Total de páginas únicas a analizar: {len(urls_to_analyze)}")
                
                leads_encontrados = 0
                for url, source in urls_to_analyze.items():
                    url = url.lower()
                    if any(s in url for s in exclude_list) or url in existing_urls:
                        continue
                    
                    st.write(f"🔍 Analizando [{source}]: {url}")
                    emails = []
                    title = url.split("//")[-1].split("/")[0] # Nombre base del sitio como título
                    
                    try:
                        # Intentar entrar a la web
                        resp = scraper.get(url, timeout=10)
                        if resp.status_code == 200:
                            # Sacar título real de la página si es posible
                            soup = BeautifulSoup(resp.text, 'html.parser')
                            if soup.title: title = soup.title.string.strip()
                            
                            emails = re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', resp.text)
                            
                            # Si no hay en portada, buscar contacto
                            if not emails:
                                for a in soup.find_all('a', href=True):
                                    if any(x in a.get_text().lower() for x in ['contact', 'nosotros', 'quienes']):
                                        c_url = a['href']
                                        if c_url.startswith('/'): c_url = url.rstrip('/') + c_url
                                        elif not c_url.startswith('http'): c_url = url.rstrip('/') + '/' + c_url
                                        c_resp = scraper.get(c_url, timeout=5)
                                        emails = re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', c_resp.text)
                                        if emails: break
                    except:
                        pass
                    
                    # Limpiar y guardar
                    emails = list(set([e for e in emails if not e.endswith(('.png', '.jpg', '.jpeg', '.gif', '.svg'))]))
                    
                    if emails:
                        db.insert_lead({
                            'company_name': title[:50],
                            'website': url,
                            'email': emails[0],
                            'source': source, # Guardamos la fuente
                            'whatsapp': "" 
                        }, active_campaign['id'])
                        st.write(f"✨ ¡Lead encontrado!: {emails[0]} ({source})")
                        leads_encontrados += 1
                        existing_urls.add(url)

                    else:
                        st.write(f"❌ No se detectaron emails públicos.")


                if leads_encontrados > 0:
                    st.success(f"¡Éxito! Se encontraron y guardaron {leads_encontrados} leads nuevos.")
                else:
                    st.warning("No se extrajeron emails. Prueba cambiando las palabras clave (ej: agrega la palabra 'contacto' o 'distribuidor').")


# --- TAB 3: FILTRADO IA (DEEPSEEK) ---
with tab_filter:
    if active_campaign:
        st.header(f"🤖 Filtrado Inteligente: {active_campaign['name']}")
        leads = db.get_leads_by_campaign(active_campaign['id'])
        
        if not leads:
            st.info("No hay leads para filtrar aún.")
        else:
            df_leads = pd.DataFrame(leads)
            
            st.subheader("Parámetros de Calidad (IA)")
            manual_rules = st.text_area("Instrucciones para la IA", "Descarta si el mail es de un diario, revista o si parece un directorio general.")
            
            if st.button("🧠 Ejecutar Filtro DeepSeek"):
                with st.spinner("DeepSeek está analizando los prospectos..."):
                    for l in leads:
                        if l['status'] == 'new':
                            res = ai.filter_lead(l['company_name'], l['email'], l['website'], manual_rules)
                            db.update_lead_status(l['id'], res['status'], res.get('score', 0), res.get('reason', ""))
                    st.success("Filtrado completado!")
                    st.rerun()

            # Mostrar tabla con estados
            st.dataframe(df_leads[['company_name', 'email', 'status', 'ai_score', 'ai_reason']], use_container_width=True)

# --- TAB 4: MAILING ---
with tab_mail:
    st.header("✉️ Configuración de Envío")
    
    col_l, col_r = st.columns(2)
    with col_l:
        st.subheader("Configuración SMTP (Segura)")
        host = st.text_input("Servidor SMTP", value="smtp.gmail.com")
        user_mail = st.text_input("Email", value="")
        pass_mail = st.text_input("Contraseña / App Token", type="password")
        if st.button("Guardar Credenciales"):
            # En un entorno real guardaríamos esto en Firestore encriptado
            st.session_state.smtp_config = {
                'host': host,
                'user': user_mail,
                'pass': enc.encrypt(pass_mail)
            }
            st.success("Configuración guardada temporalmente.")

    with col_r:
        st.subheader("Armar Correo")
        subject = st.text_input("Asunto")
        message = st.text_area("Cuerpo del Mensaje (HTML soportado)")
        attachment = st.file_uploader("Adjuntar Imagen para el mailing", type=['png', 'jpg', 'jpeg'])
        
        if st.button("✨ Generar Texto con IA"):
            if active_campaign:
                msg = ai.generate_email(active_campaign['name'], "Venta de dispensers de agua para empresas")
                st.write(msg)
            else:
                st.error("Selecciona una campaña primero.")

    st.divider()
    st.subheader("🗓️ Programación y Envío")
    send_date = st.date_input("Fecha de envío")
    send_time = st.time_input("Hora de envío")
    
    if st.button("🚀 ENVIAR CAMPAÑA AHORA"):
        st.warning("Esto enviará mails a todos los leads marcados como 'VALID' en la campaña actual.")
        # Lógica de envío masivo aquí usando EmailSender
