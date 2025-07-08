#!/usr/bin/env python3
"""
Fonction generate-2fa pour OpenFaaS avec template python3-http-debian
"""

import json
import sys
import os
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse

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
            <title>Generate 2FA Function</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 40px; }
                .container { max-width: 600px; margin: 0 auto; }
                .form-group { margin-bottom: 15px; }
                label { display: block; margin-bottom: 5px; }
                input, select { width: 100%; padding: 8px; margin-bottom: 10px; }
                button { background: #007bff; color: white; padding: 10px 20px; border: none; cursor: pointer; }
                .result { margin-top: 20px; padding: 15px; background: #f8f9fa; border-radius: 5px; }
                .qr-code { text-align: center; margin: 20px 0; }
                .qr-code img { max-width: 200px; border: 1px solid #ddd; }
                .recovery-codes { background: #fff3cd; padding: 15px; border-radius: 5px; margin: 15px 0; }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🔐 Génération d'Authentification à Deux Facteurs (2FA)</h1>
                <form id="twofaForm">
                    <div class="form-group">
                        <label>ID Utilisateur:</label>
                        <input type="text" id="userId" value="1" required>
                    </div>
                    <div class="form-group">
                        <label>Email Utilisateur:</label>
                        <input type="email" id="userEmail" value="user@example.com" required>
                    </div>
                    <div class="form-group">
                        <label>Émetteur (optionnel):</label>
                        <input type="text" id="issuer" value="MSPR2-Cofrap">
                    </div>
                    <button type="submit">Générer la configuration 2FA</button>
                </form>
                <div id="result" class="result" style="display: none;"></div>
            </div>
            
            <script>
                document.getElementById('twofaForm').addEventListener('submit', async function(e) {
                    e.preventDefault();
                    
                    const data = {
                        user_id: document.getElementById('userId').value,
                        user_email: document.getElementById('userEmail').value,
                        issuer: document.getElementById('issuer').value
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
                            let resultHtml = `
                                <h3>✅ Configuration 2FA générée avec succès !</h3>
                                <p><strong>Clé secrète:</strong> <code>${result.secret_key}</code></p>
                                <p><strong>Généré le:</strong> ${result.generated_at}</p>
                            `;
                            
                            if (result.qr_code) {
                                resultHtml += `
                                    <div class="qr-code">
                                        <h4>📱 Code QR pour votre application d'authentification</h4>
                                        <img src="data:image/png;base64,${result.qr_code}" alt="QR Code">
                                    </div>
                                `;
                            }
                            
                            if (result.recovery_codes && result.recovery_codes.length > 0) {
                                resultHtml += `
                                    <div class="recovery-codes">
                                        <h4>🔑 Codes de récupération (à conserver en lieu sûr)</h4>
                                        <p>Utilisez ces codes si vous perdez votre appareil d'authentification :</p>
                                        <ul>
                                            ${result.recovery_codes.map(code => `<li><code>${code}</code></li>`).join('')}
                                        </ul>
                                    </div>
                                `;
                            }
                            
                            document.getElementById('result').innerHTML = resultHtml;
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
    print(f"🚀 Serveur generate-2fa démarré sur le port {port}")
    print(f"📝 Interface web: http://localhost:{port}")
    httpd.serve_forever()

if __name__ == '__main__':
    run_server() 