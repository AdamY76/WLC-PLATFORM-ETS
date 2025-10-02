/**
 * Composant pour améliorer les tableaux de données
 */
class DataTableComponent {
    constructor(tableElement, options = {}) {
        this.table = tableElement;
        this.options = {
            responsive: true,
            striped: true,
            hover: true,
            ...options
        };
        
        this.init();
    }
    
    init() {
        // Ajouter les classes Bootstrap
        if (this.options.striped) {
            this.table.classList.add('table-striped');
        }
        
        if (this.options.hover) {
            this.table.classList.add('table-hover');
        }
        
        // Ajouter un conteneur responsive s'il n'existe pas
        if (this.options.responsive && !this.table.parentElement.classList.contains('table-responsive')) {
            const wrapper = document.createElement('div');
            wrapper.className = 'table-responsive';
            this.table.parentNode.insertBefore(wrapper, this.table);
            wrapper.appendChild(this.table);
        }
        
        // Ajouter des tooltips pour les cellules tronquées
        this.addTooltips();
        
        // Observer les changements pour réappliquer les améliorations
        this.observeChanges();
    }
    
    addTooltips() {
        const cells = this.table.querySelectorAll('td, th');
        cells.forEach(cell => {
            // Vérifier si le contenu déborde
            if (cell.scrollWidth > cell.clientWidth) {
                const textContent = cell.textContent.trim();
                if (textContent) {
                    cell.setAttribute('title', textContent);
                }
            }
        });
    }
    
    observeChanges() {
        // Observer les changements dans le tableau pour réappliquer les améliorations
        const observer = new MutationObserver(() => {
            this.addTooltips();
        });
        
        observer.observe(this.table.querySelector('tbody'), {
            childList: true,
            subtree: true
        });
    }
    
    // Méthode pour ajouter un filtre simple
    addSimpleFilter(inputElement) {
        inputElement.addEventListener('input', (e) => {
            const filter = e.target.value.toLowerCase();
            const rows = this.table.querySelectorAll('tbody tr');
            
            rows.forEach(row => {
                const text = row.textContent.toLowerCase();
                row.style.display = text.includes(filter) ? '' : 'none';
            });
        });
    }
    
    // Méthode pour exporter en CSV
    exportToCsv(filename = 'export.csv') {
        const rows = Array.from(this.table.querySelectorAll('tr'));
        const csv = rows.map(row => {
            return Array.from(row.querySelectorAll('th, td'))
                .map(cell => {
                    // Pour les inputs, prendre la valeur
                    const input = cell.querySelector('input');
                    return input ? input.value : cell.textContent.trim();
                })
                .map(text => `"${text.replace(/"/g, '""')}"`)
                .join(',');
        }).join('\n');
        
        const blob = new Blob([csv], { type: 'text/csv' });
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        a.click();
        window.URL.revokeObjectURL(url);
    }
}

// Initialisation automatique
document.addEventListener('DOMContentLoaded', function() {
    const table = document.getElementById('elements-table');
    if (table) {
        window.dataTable = new DataTableComponent(table);
    }
}); 