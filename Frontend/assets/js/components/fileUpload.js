/**
 * Composant générique pour l'upload de fichiers avec drag & drop
 */
class FileUploadComponent {
    constructor(element, options = {}) {
        this.element = element;
        this.options = {
            acceptedTypes: options.acceptedTypes || [],
            maxSize: options.maxSize || 10 * 1024 * 1024, // 10MB par défaut
            onUpload: options.onUpload || (() => {}),
            ...options
        };
        
        this.init();
    }
    
    init() {
        // Gestion du drag & drop
        this.element.addEventListener('dragover', this.handleDragOver.bind(this));
        this.element.addEventListener('dragleave', this.handleDragLeave.bind(this));
        this.element.addEventListener('drop', this.handleDrop.bind(this));
        
        // Click pour ouvrir le sélecteur de fichier
        this.element.addEventListener('click', this.handleClick.bind(this));
    }
    
    handleDragOver(event) {
        event.preventDefault();
        this.element.classList.add('dragover');
    }
    
    handleDragLeave(event) {
        event.preventDefault();
        this.element.classList.remove('dragover');
    }
    
    handleDrop(event) {
        event.preventDefault();
        this.element.classList.remove('dragover');
        
        const files = Array.from(event.dataTransfer.files);
        this.handleFiles(files);
    }
    
    handleClick(event) {
        // Ne déclencher le sélecteur que si on clique sur la zone, pas sur les boutons
        if (event.target === this.element || event.target.classList.contains('upload-zone')) {
            const input = this.element.querySelector('input[type="file"]');
            if (input) {
                input.click();
            }
        }
    }
    
    handleFiles(files) {
        if (files.length === 0) return;
        
        const file = files[0]; // Premier fichier seulement
        
        // Validation du type
        if (this.options.acceptedTypes.length > 0) {
            const extension = '.' + file.name.split('.').pop().toLowerCase();
            if (!this.options.acceptedTypes.includes(extension)) {
                notifications.error(`Type de fichier non supporté. Types acceptés: ${this.options.acceptedTypes.join(', ')}`);
                return;
            }
        }
        
        // Validation de la taille
        if (file.size > this.options.maxSize) {
            notifications.error(`Fichier trop volumineux. Taille maximum: ${this.formatFileSize(this.options.maxSize)}`);
            return;
        }
        
        // Appeler le callback d'upload
        this.options.onUpload(file);
    }
    
    formatFileSize(bytes) {
        if (bytes === 0) return '0 B';
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }
}

// Initialisation automatique des zones d'upload
document.addEventListener('DOMContentLoaded', function() {
    // Zone d'upload IFC
    const ifcUploadZone = document.querySelector('.upload-zone');
    if (ifcUploadZone) {
        new FileUploadComponent(ifcUploadZone, {
            acceptedTypes: ['.ifc'],
            onUpload: (file) => {
                const input = document.getElementById('ifc-file');
                const dt = new DataTransfer();
                dt.items.add(file);
                input.files = dt.files;
                
                // Déclencher l'import
                importIfc();
            }
        });
    }
}); 