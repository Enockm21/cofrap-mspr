#!/usr/bin/env python3
"""
Serveur HTTP simple pour la fonction authenticate-user
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
            
            # Appeler la fonction handler
            response = handle(post_data.decode('utf-8'))
            
            # Envoyer la réponse
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
            self.send_header('Access-Control-Allow-Headers', 'Content-Type')
            self.end_headers()
            
            if isinstance(response, tuple):
                response_data, status_code = response
                self.send_response(status_code)
                self.wfile.write(response_data.encode('utf-8'))
            else:
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
            <title>Authenticate User Function</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 40px; }
                .container { max-width: 600px; margin: 0 auto; }
                .form-group { margin-bottom: 15px; }
                label { display: block; margin-bottom: 5px; }
                input, select { width: 100%; padding: 8px; margin-bottom: 10px; }
                button { background: #007bff; color: white; padding: 10px 20px; border: none; cursor: pointer; }
                .result { margin-top: 20px; padding: 15px; background: #f8f9fa; border-radius: 5px; }
                .success { background: #d4edda; border: 1px solid #c3e6cb; }
                .error { background: #f8d7da; border: 1px solid #f5c6cb; }
                .warning { background: #fff3cd; border: 1px solid #ffeaa7; }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🔐 Authentification Utilisateur</h1>
                <form id="authForm">
                    <div class="form-group">
                        <label>Nom d'utilisateur:</label>
                        <input type="text" id="username" value="admin" required>
                    </div>
                    <div class="form-group">
                        <label>Mot de passe:</label>
                        <input type="password" id="password" value="password" required>
                    </div>
                    <div class="form-group">
                        <label>Code 2FA (optionnel):</label>
                        <input type="text" id="twoFactorCode" placeholder="000000" maxlength="6">
                    </div>
                    <div class="form-group">
                        <label>Code de récupération (optionnel):</label>
                        <input type="text" id="recoveryCode" placeholder="ABCD1234" maxlength="8">
                    </div>
                    <button type="submit">Se connecter</button>
                </form>
                <div id="result" class="result" style="display: none;"></div>
            </div>
            
            <script>
                document.getElementById('authForm').addEventListener('submit', async function(e) {
                    e.preventDefault();
                    
                    const data = {
                        username: document.getElementById('username').value,
                        password: document.getElementById('password').value
                    };
                    
                    const twoFactorCode = document.getElementById('twoFactorCode').value;
                    const recoveryCode = document.getElementById('recoveryCode').value;
                    
                    if (twoFactorCode) {
                        data.two_factor_code = twoFactorCode;
                    }
                    if (recoveryCode) {
                        data.recovery_code = recoveryCode;
                    }
                    
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
                            document.getElementById('result').className = 'result success';
                            document.getElementById('result').innerHTML = `
                                <h3>✅ Authentification réussie !</h3>
                                <p><strong>Token JWT:</strong> <code>${result.token.substring(0, 50)}...</code></p>
                                <p><strong>Utilisateur:</strong> ${result.user.username} (${result.user.email})</p>
                                <p><strong>2FA activé:</strong> ${result.user.two_factor_enabled ? 'Oui' : 'Non'}</p>
                                <p><strong>Expire le:</strong> ${result.expires_at}</p>
                            `;
                        } else {
                            let className = 'result error';
                            if (result.requires_2fa) {
                                className = 'result warning';
                            }
                            
                            document.getElementById('result').className = className;
                            document.getElementById('result').innerHTML = `
                                <h3>❌ ${result.requires_2fa ? 'Code 2FA requis' : 'Erreur d\'authentification'}</h3>
                                <p>${result.error}</p>
                                ${result.requires_2fa ? '<p>Veuillez entrer votre code 2FA ou code de récupération.</p>' : ''}
                            `;
                        }
                        
                        document.getElementById('result').style.display = 'block';
                    } catch (error) {
                        document.getElementById('result').className = 'result error';
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
    print(f"🚀 Serveur authenticate-user démarré sur le port {port}")
    print(f"📝 Interface web: http://localhost:{port}")
    httpd.serve_forever()

if __name__ == '__main__':
    run_server() 