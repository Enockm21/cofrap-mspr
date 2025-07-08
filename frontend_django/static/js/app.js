// Configuration globale
const CONFIG = {
    API_BASE_URL: '/',
    PASSWORD_MIN_LENGTH: 8,
    PASSWORD_MAX_LENGTH: 128
};

// Classe principale de l'application
class AuthApp {
    constructor() {
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.setupPasswordStrength();
        this.setupFormValidation();
        this.setupPasswordGenerator();
        this.setup2FAGenerator();
        this.setupAnimations();
    }

    setupEventListeners() {
        // Navigation mobile
        const mobileMenuToggle = document.querySelector('.mobile-menu-toggle');
        const navbarNav = document.querySelector('.navbar-nav');
        
        if (mobileMenuToggle && navbarNav) {
            mobileMenuToggle.addEventListener('click', () => {
                navbarNav.classList.toggle('show');
            });
        }

        // Fermer les alertes
        document.querySelectorAll('.alert .close').forEach(closeBtn => {
            closeBtn.addEventListener('click', (e) => {
                e.target.closest('.alert').remove();
            });
        });

        // Auto-hide des alertes après 5 secondes
        setTimeout(() => {
            document.querySelectorAll('.alert').forEach(alert => {
                if (!alert.classList.contains('alert-persistent')) {
                    alert.style.opacity = '0';
                    setTimeout(() => alert.remove(), 300);
                }
            });
        }, 5000);
    }

    setupPasswordStrength() {
        const passwordInputs = document.querySelectorAll('input[type="password"]');
        
        passwordInputs.forEach(input => {
            input.addEventListener('input', (e) => {
                this.updatePasswordStrength(e.target);
            });
        });
    }

    updatePasswordStrength(input) {
        const password = input.value;
        const strengthContainer = input.parentNode.querySelector('.password-strength');
        
        if (!strengthContainer) return;

        const strengthBar = strengthContainer.querySelector('.strength-fill');
        const strengthText = strengthContainer.querySelector('.strength-text');
        
        if (!password) {
            strengthBar.style.width = '0%';
            strengthBar.className = 'strength-fill';
            if (strengthText) strengthText.textContent = '';
            return;
        }

        const strength = this.calculatePasswordStrength(password);
        const percentage = (strength.score / 4) * 100;
        
        strengthBar.style.width = percentage + '%';
        strengthBar.className = `strength-fill strength-${strength.level}`;
        
        if (strengthText) {
            strengthText.textContent = strength.message;
        }
    }

    calculatePasswordStrength(password) {
        let score = 0;
        let feedback = [];

        // Longueur
        if (password.length >= 8) score++;
        else feedback.push('Au moins 8 caractères');

        // Lettres minuscules
        if (/[a-z]/.test(password)) score++;
        else feedback.push('Lettres minuscules');

        // Lettres majuscules
        if (/[A-Z]/.test(password)) score++;
        else feedback.push('Lettres majuscules');

        // Chiffres
        if (/\d/.test(password)) score++;
        else feedback.push('Chiffres');

        // Caractères spéciaux
        if (/[!@#$%^&*(),.?":{}|<>]/.test(password)) score++;
        else feedback.push('Caractères spéciaux');

        let level, message;
        if (score <= 1) {
            level = 'weak';
            message = 'Faible';
        } else if (score <= 3) {
            level = 'medium';
            message = 'Moyen';
        } else {
            level = 'strong';
            message = 'Fort';
        }

        return { score, level, message, feedback };
    }

    setupFormValidation() {
        const forms = document.querySelectorAll('form[data-validate]');
        
        forms.forEach(form => {
            form.addEventListener('submit', (e) => {
                if (!this.validateForm(form)) {
                    e.preventDefault();
                }
            });
        });
    }

    validateForm(form) {
        let isValid = true;
        const inputs = form.querySelectorAll('input[required], select[required], textarea[required]');
        
        inputs.forEach(input => {
            if (!this.validateField(input)) {
                isValid = false;
            }
        });

        return isValid;
    }

    validateField(field) {
        const value = field.value.trim();
        const type = field.type;
        let isValid = true;
        let message = '';

        // Supprimer les messages d'erreur précédents
        this.removeFieldError(field);

        // Validation selon le type
        switch (type) {
            case 'email':
                if (value && !this.isValidEmail(value)) {
                    isValid = false;
                    message = 'Adresse email invalide';
                }
                break;
            case 'password':
                if (value && value.length < CONFIG.PASSWORD_MIN_LENGTH) {
                    isValid = false;
                    message = `Le mot de passe doit contenir au moins ${CONFIG.PASSWORD_MIN_LENGTH} caractères`;
                }
                break;
            default:
                if (field.hasAttribute('required') && !value) {
                    isValid = false;
                    message = 'Ce champ est requis';
                }
        }

        if (!isValid) {
            this.showFieldError(field, message);
        }

        return isValid;
    }

    isValidEmail(email) {
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        return emailRegex.test(email);
    }

    showFieldError(field, message) {
        field.classList.add('is-invalid');
        
        const errorDiv = document.createElement('div');
        errorDiv.className = 'invalid-feedback';
        errorDiv.textContent = message;
        errorDiv.id = `${field.id || field.name}-error`;
        
        field.parentNode.appendChild(errorDiv);
    }

    removeFieldError(field) {
        field.classList.remove('is-invalid');
        const errorDiv = field.parentNode.querySelector('.invalid-feedback');
        if (errorDiv) {
            errorDiv.remove();
        }
    }

    setupPasswordGenerator() {
        const generateBtn = document.querySelector('#generate-password');
        const passwordInput = document.querySelector('#password');
        
        if (generateBtn && passwordInput) {
            generateBtn.addEventListener('click', async (e) => {
                e.preventDefault();
                await this.generatePassword();
            });
        }
    }

    async generatePassword() {
        const generateBtn = document.querySelector('#generate-password');
        const passwordInput = document.querySelector('#password');
        
        if (!generateBtn || !passwordInput) return;

        // Afficher le spinner
        const originalText = generateBtn.innerHTML;
        generateBtn.innerHTML = '<span class="spinner"></span> Génération...';
        generateBtn.disabled = true;

        try {
            const response = await fetch('/generate-password/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify({
                    length: 16,
                    include_uppercase: true,
                    include_lowercase: true,
                    include_numbers: true,
                    include_symbols: true
                })
            });

            if (response.ok) {
                const data = await response.json();
                passwordInput.value = data.password;
                this.updatePasswordStrength(passwordInput);
                this.showNotification('Mot de passe généré avec succès !', 'success');
            } else {
                throw new Error('Erreur lors de la génération');
            }
        } catch (error) {
            console.error('Erreur:', error);
            this.showNotification('Erreur lors de la génération du mot de passe', 'error');
        } finally {
            // Restaurer le bouton
            generateBtn.innerHTML = originalText;
            generateBtn.disabled = false;
        }
    }

    setup2FAGenerator() {
        const generate2FABtn = document.querySelector('#generate-2fa');
        
        if (generate2FABtn) {
            generate2FABtn.addEventListener('click', async (e) => {
                e.preventDefault();
                await this.generate2FA();
            });
        }
    }

    async generate2FA() {
        const generateBtn = document.querySelector('#generate-2fa');
        
        if (!generateBtn) return;

        // Afficher le spinner
        const originalText = generateBtn.innerHTML;
        generateBtn.innerHTML = '<span class="spinner"></span> Génération...';
        generateBtn.disabled = true;

        try {
            const response = await fetch('/generate-2fa/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify({})
            });

            if (response.ok) {
                const data = await response.json();
                this.show2FASetup(data);
                this.showNotification('Code 2FA généré avec succès !', 'success');
            } else {
                throw new Error('Erreur lors de la génération 2FA');
            }
        } catch (error) {
            console.error('Erreur:', error);
            this.showNotification('Erreur lors de la génération du code 2FA', 'error');
        } finally {
            // Restaurer le bouton
            generateBtn.innerHTML = originalText;
            generateBtn.disabled = false;
        }
    }

    show2FASetup(data) {
        // Créer une modal pour afficher le QR code et les codes de récupération
        const modal = document.createElement('div');
        modal.className = 'modal fade-in';
        modal.innerHTML = `
            <div class="modal-overlay">
                <div class="modal-content">
                    <div class="modal-header">
                        <h3>Configuration 2FA</h3>
                        <button class="modal-close">&times;</button>
                    </div>
                    <div class="modal-body">
                        <div class="qr-container">
                            <h4>Scannez ce QR code avec votre application d'authentification</h4>
                            <div class="qr-code">
                                <img src="${data.qr_code_url}" alt="QR Code 2FA" />
                            </div>
                            <p><strong>Code secret:</strong> ${data.secret}</p>
                        </div>
                        <div class="recovery-codes">
                            <h4>Codes de récupération</h4>
                            <p>Conservez ces codes en lieu sûr. Ils vous permettront de récupérer l'accès à votre compte.</p>
                            <div class="codes-list">
                                ${data.recovery_codes.map(code => `<code>${code}</code>`).join('')}
                            </div>
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button class="btn btn-primary" onclick="this.closest('.modal').remove()">Fermer</button>
                    </div>
                </div>
            </div>
        `;

        document.body.appendChild(modal);

        // Fermer la modal
        modal.querySelector('.modal-close').addEventListener('click', () => {
            modal.remove();
        });

        modal.querySelector('.modal-overlay').addEventListener('click', (e) => {
            if (e.target === modal.querySelector('.modal-overlay')) {
                modal.remove();
            }
        });
    }

    setupAnimations() {
        // Animation d'apparition des éléments
        const observerOptions = {
            threshold: 0.1,
            rootMargin: '0px 0px -50px 0px'
        };

        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.classList.add('fade-in');
                }
            });
        }, observerOptions);

        // Observer les cartes et sections
        document.querySelectorAll('.card, .stat-card, .hero, .section').forEach(el => {
            observer.observe(el);
        });
    }

    getCSRFToken() {
        return document.querySelector('[name=csrfmiddlewaretoken]')?.value || 
               document.querySelector('meta[name=csrf-token]')?.getAttribute('content');
    }

    showNotification(message, type = 'info') {
        const notification = document.createElement('div');
        notification.className = `alert alert-${type} notification`;
        notification.innerHTML = `
            ${message}
            <button type="button" class="close" onclick="this.parentElement.remove()">&times;</button>
        `;

        // Positionner la notification
        notification.style.position = 'fixed';
        notification.style.top = '20px';
        notification.style.right = '20px';
        notification.style.zIndex = '9999';
        notification.style.minWidth = '300px';

        document.body.appendChild(notification);

        // Auto-remove après 5 secondes
        setTimeout(() => {
            if (notification.parentElement) {
                notification.style.opacity = '0';
                setTimeout(() => notification.remove(), 300);
            }
        }, 5000);
    }

    // Méthodes utilitaires
    formatDate(dateString) {
        const date = new Date(dateString);
        return date.toLocaleDateString('fr-FR', {
            year: 'numeric',
            month: 'long',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
    }

    formatNumber(number) {
        return new Intl.NumberFormat('fr-FR').format(number);
    }

    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }
}

// Initialisation de l'application
document.addEventListener('DOMContentLoaded', () => {
    window.authApp = new AuthApp();
});

// Export pour utilisation dans d'autres modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = AuthApp;
} 