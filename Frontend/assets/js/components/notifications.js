/**
 * Système de notifications moderne pour la Plateforme WLC
 */
class NotificationSystem {
    constructor() {
        this.toastElement = document.getElementById('notification-toast');
        this.toastInstance = new bootstrap.Toast(this.toastElement);
    }

    /**
     * Affiche une notification
     * @param {string} message - Le message à afficher
     * @param {string} type - Type: 'success', 'error', 'warning', 'info'
     * @param {string} title - Titre personnalisé (optionnel)
     * @param {number} duration - Durée en ms (optionnel, 0 = permanent)
     */
    show(message, type = 'info', title = null, duration = 5000) {
        const toastHeader = this.toastElement.querySelector('.toast-header');
        const toastBody = this.toastElement.querySelector('.toast-body');
        const toastIcon = document.getElementById('toast-icon');
        const toastTitle = document.getElementById('toast-title');

        // Configuration des types
        const types = {
            success: {
                icon: 'fas fa-check-circle text-success',
                title: 'Succès',
                class: 'border-success'
            },
            error: {
                icon: 'fas fa-exclamation-triangle text-danger',
                title: 'Erreur',
                class: 'border-danger'
            },
            warning: {
                icon: 'fas fa-exclamation-circle text-warning',
                title: 'Attention',
                class: 'border-warning'
            },
            info: {
                icon: 'fas fa-info-circle text-primary',
                title: 'Information',
                class: 'border-primary'
            }
        };

        const config = types[type] || types.info;

        // Mise à jour du contenu
        toastIcon.className = config.icon;
        toastTitle.textContent = title || config.title;
        toastBody.textContent = message;

        // Mise à jour des classes
        this.toastElement.className = `toast ${config.class}`;

        // Configuration de la durée
        if (duration > 0) {
            this.toastElement.setAttribute('data-bs-delay', duration);
        } else {
            this.toastElement.removeAttribute('data-bs-delay');
        }

        // Affichage
        this.toastInstance.show();
    }

    /**
     * Raccourcis pour les différents types
     */
    success(message, title = null) {
        this.show(message, 'success', title);
    }

    error(message, title = null) {
        this.show(message, 'error', title);
    }

    warning(message, title = null) {
        this.show(message, 'warning', title);
    }

    info(message, title = null) {
        this.show(message, 'info', title);
    }

    /**
     * Masque la notification actuelle
     */
    hide() {
        this.toastInstance.hide();
    }
}

// Instance globale
window.notifications = new NotificationSystem();

/**
 * Fonction globale simplifiée pour l'affichage de notifications
 * @param {string} message - Le message à afficher
 * @param {string} type - Type: 'success', 'error', 'warning', 'info'
 * @param {string} title - Titre personnalisé (optionnel)
 */
function showNotification(message, type = 'info', title = null) {
    if (window.notifications) {
        window.notifications.show(message, type, title);
    } else {
        // Fallback si le système de notifications n'est pas disponible
        console.log(`[${type.toUpperCase()}] ${title || ''}: ${message}`);
        alert(`${title || type.toUpperCase()}: ${message}`);
    }
}

/**
 * Affiche un message de statut dans un élément spécifique
 * @param {string} elementId - ID de l'élément
 * @param {string} message - Message à afficher
 * @param {string} type - Type: 'success', 'error', 'warning', 'info'
 */
function showStatusMessage(elementId, message, type = 'info') {
    const element = document.getElementById(elementId);
    if (!element) return;

    element.className = `status-message status-${type}`;
    element.textContent = message;
    element.style.display = 'block';

    // Animation d'apparition
    element.classList.add('fade-in');
    
    // Auto-masquage après 5 secondes pour les succès
    if (type === 'success') {
        setTimeout(() => {
            element.style.display = 'none';
        }, 5000);
    }
}

/**
 * Efface un message de statut
 * @param {string} elementId - ID de l'élément
 */
function clearStatusMessage(elementId) {
    const element = document.getElementById(elementId);
    if (element) {
        element.style.display = 'none';
        element.textContent = '';
    }
} 