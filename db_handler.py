import firebase_admin
from firebase_admin import credentials, firestore
import os
import json
from datetime import datetime

class Database:
    def __init__(self):
        self.db = self._initialize_db()

    def _initialize_db(self):
        # Intentar cargar credenciales desde variable de entorno (Streamlit Secrets)
        # o desde un archivo local
        key_dict = None
        
        # 1. Buscar en variable de entorno (formato string JSON)
        firebase_key_json = os.getenv("FIREBASE_SERVICE_ACCOUNT")
        if firebase_key_json:
            try:
                key_dict = json.loads(firebase_key_json)
            except Exception as e:
                print(f"Error parsing FIREBASE_SERVICE_ACCOUNT: {e}")

        # 2. Buscar en archivo local si no hay variable
        if not key_dict and os.path.exists("firebase-key.json"):
            with open("firebase-key.json") as f:
                key_dict = json.load(f)

        if key_dict:
            if not firebase_admin._apps:
                cred = credentials.Certificate(key_dict)
                firebase_admin.initialize_app(cred)
            # Especificamos el ID de la base de datos que usa tu proyecto
            return firestore.client(database='pagar-webonline')
        else:

            print("⚠️ No se encontró configuración de Firebase. Firestore no estará disponible.")
            return None

    # --- CAMPAÑAS ---
    def create_campaign(self, name, config=None):
        if not self.db: return None
        campaign_ref = self.db.collection('campaigns').document()
        campaign_data = {
            'name': name,
            'status': 'draft', # draft, active, finished
            'config': config or {},
            'created_at': datetime.now(),
            'scheduled_at': None,
            'recurrence': None
        }
        campaign_ref.set(campaign_data)
        return campaign_ref.id

    def get_campaigns(self):
        if not self.db: return []
        docs = self.db.collection('campaigns').order_by('created_at', direction=firestore.Query.DESCENDING).stream()
        return [{**doc.to_dict(), 'id': doc.id} for doc in docs]

    # --- LEADS ---
    def insert_lead(self, lead_data, campaign_id):
        if not self.db: return
        # El lead_data debe incluir 'email', 'website', etc.
        lead_ref = self.db.collection('leads').document()
        lead_data['campaign_id'] = campaign_id
        lead_data['created_at'] = datetime.now()
        lead_data['status'] = lead_data.get('status', 'new') # new, valid, invalid, discarded
        lead_data['ai_score'] = 0
        lead_data['ai_reason'] = ""
        lead_ref.set(lead_data)

    def get_leads_by_campaign(self, campaign_id):
        if not self.db: return []
        docs = self.db.collection('leads').where('campaign_id', '==', campaign_id).stream()
        return [{**doc.to_dict(), 'id': doc.id} for doc in docs]

    def update_lead_status(self, lead_id, status, ai_score=None, ai_reason=None):
        if not self.db: return
        update_data = {'status': status}
        if ai_score is not None: update_data['ai_score'] = ai_score
        if ai_reason is not None: update_data['ai_reason'] = ai_reason
        self.db.collection('leads').document(lead_id).update(update_data)
