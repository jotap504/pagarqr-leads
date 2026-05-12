import re
import csv
import time
import requests
from bs4 import BeautifulSoup
from ddgs import DDGS

def extract_emails_from_url(url):
    """Accede a una URL y busca patrones de correo electrónico en su código HTML."""
    try:
        # Usamos un User-Agent común para que los sitios web no bloqueen la petición
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        response = requests.get(url, headers=headers, timeout=10)
        
        # Expresión regular para buscar correos electrónicos
        email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        emails = set(re.findall(email_pattern, response.text))
        
        # Filtrar correos basura o imágenes que coinciden por error
        invalid_endings = ('.png', '.jpg', '.jpeg', '.gif', 'sentry.io', 'wixpress.com')
        valid_emails = [e for e in emails if not e.endswith(invalid_endings)]
        return valid_emails
    except Exception as e:
        print(f"  [X] Error al acceder a la web: {e}")
        return []

def main():
    print("==================================================")
    print("   SCRAPER DE LEADS B2B - PAGAR QR (BETA) ")
    print("==================================================")
    
    query = input("Ingresa tu búsqueda (ej. 'club de padel buenos aires contacto'): ")
    
    try:
        num_results = int(input("¿Cuántos resultados quieres analizar? (ej. 20): "))
    except ValueError:
        num_results = 20
    
    print(f"\nBuscando en DuckDuckGo: '{query}'...")
    
    results = []
    
    try:
        with DDGS() as ddgs:
            # max_results controla cuántos links de Google/DuckDuckGo va a visitar
            search_results = list(ddgs.text(query, max_results=num_results))
    except Exception as e:
        print(f"Error al usar el buscador: {e}")
        return
        
    print(f"Se encontraron {len(search_results)} sitios web. Analizando...\n")
        
    for res in search_results:
        title = res.get('title', 'Sin título')
        url = res.get('href', '')
        
        if not url:
            continue
            
        print(f"Analizando: {title[:50]}... ({url})")
        emails = extract_emails_from_url(url)
        
        if emails:
            print(f"  -> ¡Éxito! Correos encontrados: {', '.join(emails)}")
            for email in emails:
                results.append({
                    "Empresa": title,
                    "Rubro": query,
                    "Sitio Web": url,
                    "Email": email,
                    "Estado": "Pendiente",
                    "Notas": "Scrapeado"
                })
        else:
            print("  -> No se encontraron correos visibles en esta página.")
            
        # Pequeña pausa para no saturar servidores y evitar bloqueos
        time.sleep(1)
        
    # Guardar o agregar al CSV
    if results:
        filename = "leads_tracker.csv" # Mismo archivo que ya tienes
        try:
            # Usamos 'a' (append) para agregar al final sin borrar lo que ya tenemos
            with open(filename, 'a', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=["Empresa", "Rubro", "Sitio Web", "Email", "Estado", "Notas"])
                # No escribimos el header porque el archivo ya lo tiene
                writer.writerows(results)
            print(f"\n✅ ¡Éxito! Se agregaron {len(results)} nuevos correos a tu archivo {filename}")
        except Exception as e:
            print(f"Error al guardar el archivo: {e}")
    else:
        print("\nNo se encontraron correos en esta búsqueda. Intenta con palabras clave como 'contacto', 'email', etc.")

if __name__ == "__main__":
    main()
