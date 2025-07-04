import json
import sys
import os
from datetime import datetime

def handle(req):
    """Fonction simple de test pour OpenFaaS"""
    
    try:
        # Parser le JSON d'entrée si présent
        if req:
            try:
                data = json.loads(req)
                name = data.get('name', 'Monde')
            except json.JSONDecodeError:
                name = req.strip() if req.strip() else 'Monde'
        else:
            name = 'Monde'
        
        # Créer la réponse
        response = {
            "message": f"Bonjour {name} !",
            "timestamp": datetime.now().isoformat(),
            "function": "hello-world",
            "version": "1.0.0",
            "status": "success"
        }
        
        return json.dumps(response, ensure_ascii=False, indent=2)
        
    except Exception as e:
        error_response = {
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
            "function": "hello-world",
            "status": "error"
        }
        return json.dumps(error_response, ensure_ascii=False, indent=2) 