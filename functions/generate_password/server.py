#!/usr/bin/env python3
"""
Serveur HTTP simple pour la fonction generate-password
"""

import json
import os
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse
import sys

# Ajouter le répertoire parent au path pour importer handler
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from handler import handle

class FunctionHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        """Gestion des requêtes POST"""
        try:
            # Lire le contenu de la requête
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            
            # Créer l'événement au format attendu par la fonction handle
            event = {
                'body': post_data.decode('utf-8'),
                'headers': dict(self.headers),
                'method': 'POST',
                'path': self.path
            }
            
            # Contexte vide pour compatibilité
            context = {}
            
            # Appeler la fonction handler
            response = handle(event, context)
            
            # Envoyer la réponse
            if isinstance(response, dict) and 'statusCode' in response:
                # Format OpenFaaS
                self.send_response(response['statusCode'])
                self.send_header('Content-type', response.get('headers', {}).get('Content-Type', 'application/json'))
                self.send_header('Access-Control-Allow-Origin', '*')
                self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
                self.send_header('Access-Control-Allow-Headers', 'Content-Type')
                self.end_headers()
                self.wfile.write(response['body'].encode('utf-8'))
            else:
                # Format simple
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
                self.send_header('Access-Control-Allow-Headers', 'Content-Type')
                self.end_headers()
                self.wfile.write(response.encode('utf-8'))
                
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            error_response = json.dumps({'error': str(e)})
            self.wfile.write(error_response.encode('utf-8'))
    
    def do_OPTIONS(self):
        """Gestion des requêtes OPTIONS pour CORS"""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
    
    def do_GET(self):
        """Page d'accueil simple"""
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        
        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Generate Password Function</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 40px; }
                .container { max-width: 600px; margin: 0 auto; }
                .form-group { margin-bottom: 15px; }
                label { display: block; margin-bottom: 5px; }
                input, select { width: 100%; padding: 8px; margin-bottom: 10px; }
                button { background: #007bff; color: white; padding: 10px 20px; border: none; cursor: pointer; }
                .result { margin-top: 20px; padding: 15px; background: #f8f9fa; border-radius: 5px; }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🔐 Génération de Mot de Passe Sécurisé</h1>
                <form id="passwordForm">
                    <div class="form-group">
                        <label>Longueur du mot de passe:</label>
                        <input type="number" id="length" value="16" min="8" max="128">
                    </div>
                    <div class="form-group">
                        <label><input type="checkbox" id="includeSymbols" checked> Inclure les symboles</label>
                    </div>
                    <div class="form-group">
                        <label><input type="checkbox" id="includeNumbers" checked> Inclure les chiffres</label>
                    </div>
                    <div class="form-group">
                        <label><input type="checkbox" id="includeUppercase" checked> Inclure les majuscules</label>
                    </div>
                    <div class="form-group">
                        <label><input type="checkbox" id="includeLowercase" checked> Inclure les minuscules</label>
                    </div>
                    <div class="form-group">
                        <label><input type="checkbox" id="enableRotation"> Activer la rotation automatique</label>
                    </div>
                    <button type="submit">Générer le mot de passe</button>
                </form>
                <div id="result" class="result" style="display: none;"></div>
            </div>
            
            <script>
                document.getElementById('passwordForm').addEventListener('submit', async function(e) {
                    e.preventDefault();
                    
                    const data = {
                        length: parseInt(document.getElementById('length').value),
                        include_symbols: document.getElementById('includeSymbols').checked,
                        include_numbers: document.getElementById('includeNumbers').checked,
                        include_uppercase: document.getElementById('includeUppercase').checked,
                        include_lowercase: document.getElementById('includeLowercase').checked,
                        enable_rotation: document.getElementById('enableRotation').checked
                    };
                    
                    try {
                        const response = await fetch('/', {
                            method: 'POST',
                            headers: {
                                'Content-Type': 'application/json'
                            },
                            body: JSON.stringify(data)
                        });
                        
                        const result = await response.json();
                        
                        if (response.ok) {
                            document.getElementById('result').innerHTML = `
                                <h3>✅ Mot de passe généré avec succès !</h3>
                                <p><strong>Mot de passe:</strong> <code>${result.password}</code></p>
                                <p><strong>Généré le:</strong> ${result.generated_at}</p>
                                ${result.expires_at ? `<p><strong>Expire le:</strong> ${result.expires_at}</p>` : ''}
                            `;
                        } else {
                            document.getElementById('result').innerHTML = `
                                <h3>❌ Erreur</h3>
                                <p>${result.error}</p>
                            `;
                        }
                        
                        document.getElementById('result').style.display = 'block';
                    } catch (error) {
                        document.getElementById('result').innerHTML = `
                            <h3>❌ Erreur de connexion</h3>
                            <p>${error.message}</p>
                        `;
                        document.getElementById('result').style.display = 'block';
                    }
                });
            </script>
        </body>
        </html>
        """
        self.wfile.write(html.encode('utf-8'))

def run_server(port=8080):
    """Démarrage du serveur"""
    server_address = ('', port)
    httpd = HTTPServer(server_address, FunctionHandler)
    print(f"🚀 Serveur generate-password démarré sur le port {port}")
    print(f"📝 Interface web: http://localhost:{port}")
    httpd.serve_forever()

if __name__ == '__main__':
    run_server() 