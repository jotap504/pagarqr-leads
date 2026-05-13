from openai import OpenAI
import os
import json

class AIHandler:
    def __init__(self):
        api_key = os.getenv("DEEPSEEK_API_KEY")
        self.client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com") if api_key else None

    def filter_lead(self, company_name, email, website, manual_params=""):
        if not self.client:
            return {"status": "error", "reason": "API Key no configurada"}

        prompt = f"""
        Analiza si este prospecto B2B es válido para una campaña de marketing.
        Empresa: {company_name}
        Email: {email}
        Website: {website}
        Parámetros extra del usuario: {manual_params}

        Criterios:
        1. El email no debe pertenecer a un portal de noticias, revista o directorio (ej: info@diario.com).
        2. Si el email contiene el nombre de la empresa, es de alta calidad.
        3. Descarta correos genéricos de servicios masivos si no tienen relación con la empresa.

        Responde ÚNICAMENTE en formato JSON:
        {{
            "status": "valid" o "discarded",
            "score": 0 a 100,
            "reason": "breve explicación de por qué"
        }}
        """

        try:
            response = self.client.chat.completions.create(
                model="deepseek-chat",
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )
            return json.loads(response.choices[0].message.content)
        except Exception as e:
            return {"status": "error", "reason": str(e)}

    def generate_email(self, company_name, campaign_goal, template_style="profesional"):
        if not self.client:
            return "API Key no configurada para generar correos."

        prompt = f"""
        Escribe un correo de ventas personalizado para la empresa '{company_name}'.
        Objetivo de la campaña: {campaign_goal}
        Estilo: {template_style}

        El correo debe ser breve, directo y generar curiosidad. No uses demasiados adjetivos.
        Incluye un asunto llamativo.
        """

        try:
            response = self.client.chat.completions.create(
                model="deepseek-chat",
                messages=[{"role": "user", "content": prompt}]
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"Error generando mail: {e}"
