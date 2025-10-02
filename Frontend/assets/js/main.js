/**
 * Application principale de la Plateforme WLC
 * Utilise toutes les APIs existantes du backend
 */

// Configuration globale
const API_BASE_URL = '';

// Variables globales pour les graphiques - éviter les redéclarations
window.currentChart = window.currentChart || null;
window.wlcComparisonChart = window.wlcComparisonChart || null;
window.discountRatesChart = window.discountRatesChart || null;

// État de l'application
const appState = {
    elements: [],
    isLoading: false,
    discountRates: [],
    stakeholders: [],
    uniformatCodes: new Set()
};

// Variables globales pour la comparaison
let comparisonState = {
    previousAnalysis: null,
    comparisonResults: null
};

/**
 * Initialisation de l'application
 */
document.addEventListener('DOMContentLoaded', function() {
    console.log('🏗️ Initialisation de la Plateforme WLC');
    
    // Vérification de l'état du système
    checkHealth();
    
    // Chargement initial des données
    loadElements();
    loadProjectLifespan();
    
    // Chargement du statut IFC
    updateIfcStatus();
    
    // Configuration des gestionnaires d'événements
    setupEventListeners();
    
    console.log('✅ Application initialisée');
});

/**
 * Configuration des gestionnaires d'événements
 */
function setupEventListeners() {
    // Gestionnaires pour l'upload de coûts
    document.querySelectorAll('.upload-area').forEach(area => {
        const phase = area.dataset.phase;
        const fileInput = area.querySelector('input[type="file"]');
        const uploadBtn = area.querySelector('button');
        
        fileInput.addEventListener('change', () => {
            uploadBtn.disabled = fileInput.files.length === 0;
        });
        
        uploadBtn.addEventListener('click', () => uploadCosts(phase, fileInput));
    });
    
    // Gestionnaire pour l'affichage du champ groupe personnalisé
    const customGroupCheckbox = document.getElementById('group-custom');
    const customGroupInput = document.getElementById('custom-group-input');
    
    if (customGroupCheckbox && customGroupInput) {
        customGroupCheckbox.addEventListener('change', function() {
            customGroupInput.style.display = this.checked ? 'block' : 'none';
            if (!this.checked) {
                document.getElementById('custom-group-guid').value = '';
            }
        });
    }
    
    // Gestionnaire pour les changements d'onglets
    document.querySelectorAll('button[data-bs-toggle="pill"]').forEach(tab => {
        tab.addEventListener('shown.bs.tab', function(event) {
            const targetId = event.target.getAttribute('data-bs-target');
            if (targetId === '#nav-summary') {
                refreshChart();
                loadDiscountRates(); // Charger les taux d'actualisation
                loadExistingWLC(); // Charger le WLC existant si disponible
            } else if (targetId === '#stakeholders') {
                // Recharger les données pour l'onglet parties prenantes
                console.log('🔄 Rechargement des données pour l\'onglet parties prenantes');
                loadStakeholders().then(() => {
                    populateStakeholderSelector(appState.stakeholders || []);
                });
                loadElements().then(() => {
                    populateElementSelector(appState.elements || []);
                    populateUniformatSelector(appState.elements || []);
                    console.log('✅ Sélecteurs mis à jour:', {
                        elements: appState.elements?.length || 0,
                        uniformatCodes: appState.uniformatCodes?.size || 0
                    });
                });
                loadExistingAttributions();
            }
        });
    });
}

/**
 * Vérification de l'état du système
 */
async function checkHealth() {
    try {
        const response = await fetch(`${API_BASE_URL}/ping`);
        const data = await response.json();
        
        const statusElement = document.getElementById('connection-status');
        if (response.ok && data.status === 'OK') {
            statusElement.className = 'badge bg-success';
            statusElement.textContent = 'Connecté';
        } else {
            statusElement.className = 'badge bg-danger';
            statusElement.textContent = 'Déconnecté';
        }
    } catch (error) {
        console.error('Erreur de connexion:', error);
        const statusElement = document.getElementById('connection-status');
        statusElement.className = 'badge bg-danger';
        statusElement.textContent = 'Erreur';
    }
}

/**
 * Chargement des éléments IFC
 */
async function loadElements() {
    setLoading(true);
    
    try {
        const response = await fetch(`${API_BASE_URL}/get-ifc-elements`);
        
        if (!response.ok) {
            throw new Error(`Erreur HTTP: ${response.status}`);
        }
        
        const elements = await response.json();
        appState.elements = elements;
        
        displayElements(elements);
        notifications.success(`${elements.length} éléments chargés`);
        
    } catch (error) {
        console.error('Erreur lors du chargement des éléments:', error);
        notifications.error('Erreur lors du chargement des éléments');
    } finally {
        setLoading(false);
    }
}

/**
 * Affichage des éléments dans le tableau
 */
function displayElements(elements) {
    // Stocker tous les éléments pour les fonctionnalités de filtrage
    allElements = elements;
    filteredElements = [...elements];
    
    const tbody = document.querySelector('#elements-table tbody');
    tbody.innerHTML = '';
    
    elements.forEach(element => {
        const row = createElementRow(element);
        tbody.appendChild(row);
    });
    
    // Initialiser les descriptions disponibles et les fonctionnalités
    updateDescriptionsList();
    updateSelectionCount();
    
    // Mettre à jour le compteur dans l'interface
    const elementsTab = document.querySelector('#nav-elements-tab');
    if (elementsTab) {
        elementsTab.textContent = `Éléments (${elements.length})`;
    }
}

/**
 * Création d'une ligne de tableau pour un élément
 */
function createElementRow(element) {
    const row = document.createElement('tr');
    row.dataset.guid = element.GlobalId;
    row.dataset.description = element.UniformatDesc || '';
    
    // Identifier si c'est un groupe par le code Uniformat
    const isGroup = element.Uniformat && element.Uniformat.startsWith('GRP_');
    
    // Ajouter une classe CSS pour les groupes
    if (isGroup) {
        row.classList.add('group-element');
    }
    
    row.innerHTML = `
        <td>
            <input type="checkbox" class="element-checkbox" data-guid="${element.UniformatDesc || element.GlobalId}" 
                   onchange="updateSelectionCount()">
        </td>
        <td class="text-truncate" style="max-width: 200px;" title="${element.GlobalId || ''}">${element.GlobalId || ''}</td>
        <td class="text-truncate" style="max-width: 120px;" title="${element.IfcClass || ''}">${isGroup ? '<i class="fas fa-layer-group text-primary me-1"></i>' : ''}${element.IfcClass || ''}</td>
        <td>${element.Uniformat || ''}</td>
        <td class="text-truncate" style="max-width: 200px;" title="${element.UniformatDesc || ''}">${element.UniformatDesc || ''}</td>
        <td>
            <input type="text" class="form-control form-control-sm material-input" 
                   value="${element.Material || ''}" 
                   data-guid="${element.UniformatDesc || element.GlobalId}"
                   placeholder="Matériau">
        </td>
        <td>
            <input type="number" class="form-control form-control-sm cost-input" 
                   value="${element.ConstructionCost || ''}" 
                   data-guid="${element.UniformatDesc || element.GlobalId}" 
                   data-phase="ConstructionCosts"
                   min="0" step="0.01">
        </td>
        <td>
            <input type="number" class="form-control form-control-sm cost-input" 
                   value="${element.OperationCost || ''}" 
                   data-guid="${element.UniformatDesc || element.GlobalId}" 
                   data-phase="OperationCosts"
                   min="0" step="0.01">
        </td>
        <td>
            <input type="number" class="form-control form-control-sm cost-input" 
                   value="${element.MaintenanceCost || ''}" 
                   data-guid="${element.UniformatDesc || element.GlobalId}" 
                   data-phase="MaintenanceCosts"
                   min="0" step="0.01">
        </td>
        <td>
            <input type="number" class="form-control form-control-sm cost-input" 
                   value="${element.EndOfLifeCost || ''}" 
                   data-guid="${element.UniformatDesc || element.GlobalId}" 
                   data-phase="EndOfLifeCosts"
                   min="0" step="0.01">
        </td>
        <td>
            <select class="form-control form-control-sm strategy-select" 
                    data-guid="${element.UniformatDesc || element.GlobalId}">
                <option value="">Choisir...</option>
                <!-- Options chargées dynamiquement -->
            </select>
        </td>
        <td>
            <input type="number" class="form-control form-control-sm lifespan-input" 
                   value="${element.Lifespan || ''}" 
                   data-guid="${element.UniformatDesc || element.GlobalId}"
                   min="1" max="200">
        </td>
    `;
    
    // Gestionnaires d'événements pour les inputs
    setupRowEventListeners(row);
    
    return row;
}

/**
 * Configuration des gestionnaires d'événements pour une ligne
 */
function setupRowEventListeners(row) {
    // Gestionnaires pour les coûts
    row.querySelectorAll('.cost-input').forEach(input => {
        input.addEventListener('change', handleCostChange);
    });
    
    // Gestionnaires pour les durées de vie
    row.querySelectorAll('.lifespan-input').forEach(input => {
        input.addEventListener('change', handleLifespanChange);
    });
    
    // Gestionnaires pour les matériaux
    row.querySelectorAll('.material-input').forEach(input => {
        input.addEventListener('change', handleMaterialChange);
    });
}

/**
 * Gestionnaire de changement de coût
 */
async function handleCostChange(event) {
    const input = event.target;
    const guid = input.dataset.guid;
    const phase = input.dataset.phase;
    const cost = input.value;
    
    if (!guid || !phase) return;
    
    // Feedback visuel - input loading
    input.disabled = true;
    input.classList.add('is-loading');
    
    try {
        const response = await fetch(`${API_BASE_URL}/update-costs`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify([{ guid, category: phase, cost: parseFloat(cost) || 0 }])
        });
        
        if (response.ok) {
            // Feedback visuel - succès
            input.classList.add('is-valid');
            setTimeout(() => input.classList.remove('is-valid'), 2000);
            notifications.success('Coût mis à jour');
        } else {
            const error = await response.json();
            input.classList.add('is-invalid');
            setTimeout(() => input.classList.remove('is-invalid'), 3000);
            notifications.error(error.error || 'Erreur lors de la mise à jour');
        }
    } catch (error) {
        console.error('Erreur:', error);
        input.classList.add('is-invalid');
        setTimeout(() => input.classList.remove('is-invalid'), 3000);
        notifications.error('Erreur réseau');
    } finally {
        input.disabled = false;
        input.classList.remove('is-loading');
    }
}

/**
 * Gestionnaire de changement de durée de vie
 */
async function handleLifespanChange(event) {
    const input = event.target;
    const guid = input.dataset.guid;
    const lifespan = input.value;
    
    if (!guid) return;
    
    // Feedback visuel - input loading
    input.disabled = true;
    input.classList.add('is-loading');
    
    try {
        const response = await fetch(`${API_BASE_URL}/update-lifespan`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify([{ guid, lifespan: parseInt(lifespan) || 0 }])
        });
        
        if (response.ok) {
            // Feedback visuel - succès
            input.classList.add('is-valid');
            setTimeout(() => input.classList.remove('is-valid'), 2000);
            notifications.success('Durée de vie mise à jour');
        } else {
            const error = await response.json();
            input.classList.add('is-invalid');
            setTimeout(() => input.classList.remove('is-invalid'), 3000);
            notifications.error(error.error || 'Erreur lors de la mise à jour');
        }
    } catch (error) {
        console.error('Erreur:', error);
        input.classList.add('is-invalid');
        setTimeout(() => input.classList.remove('is-invalid'), 3000);
        notifications.error('Erreur réseau');
    } finally {
        input.disabled = false;
        input.classList.remove('is-loading');
    }
}

/**
 * Gestionnaire de changement de matériau
 */
async function handleMaterialChange(event) {
    const input = event.target;
    const guid = input.dataset.guid;
    const material = input.value.trim();
    
    if (!guid) return;
    
    // Feedback visuel - input loading
    input.disabled = true;
    input.classList.add('is-loading');
    
    try {
        const response = await fetch(`${API_BASE_URL}/update-material`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify([{ guid, material }])
        });
        
        if (response.ok) {
            // Feedback visuel - succès
            input.classList.add('is-valid');
            setTimeout(() => input.classList.remove('is-valid'), 2000);
            notifications.success('Matériau mis à jour');
        } else {
            const error = await response.json();
            input.classList.add('is-invalid');
            setTimeout(() => input.classList.remove('is-invalid'), 3000);
            notifications.error(error.error || 'Erreur lors de la mise à jour');
        }
    } catch (error) {
        console.error('Erreur:', error);
        input.classList.add('is-invalid');
        setTimeout(() => input.classList.remove('is-invalid'), 3000);
        notifications.error('Erreur réseau');
    } finally {
        input.disabled = false;
        input.classList.remove('is-loading');
    }
}

/**
 * Import d'un fichier IFC
 */
async function importIfc() {
    const fileInput = document.getElementById('ifc-file');
    const file = fileInput.files[0];
    
    if (!file) {
        notifications.warning('Veuillez sélectionner un fichier IFC');
        return;
    }
    
    setLoading(true, 'Import du fichier IFC en cours...');
    
    try {
        const formData = new FormData();
        formData.append('file', file);
        
        const response = await fetch(`${API_BASE_URL}/parse-ifc`, {
            method: 'POST',
            body: formData
        });
        
        if (response.ok) {
            notifications.success('Fichier IFC importé avec succès');
            loadElements(); // Recharger les éléments
            fileInput.value = ''; // Réinitialiser l'input
        } else {
            const error = await response.json();
            notifications.error(error.error || 'Erreur lors de l\'import');
        }
    } catch (error) {
        console.error('Erreur:', error);
        notifications.error('Erreur lors de l\'import du fichier');
    } finally {
        setLoading(false);
    }
}

/**
 * Upload des coûts par phase
 */
async function uploadCosts(phase, fileInput) {
    const file = fileInput.files[0];
    
    if (!file) {
        notifications.warning('Veuillez sélectionner un fichier');
        return;
    }
    
    setLoading(true, `Import des coûts ${phase} en cours...`);
    
    try {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('phase', phase);
        
        const response = await fetch(`${API_BASE_URL}/upload-phase-costs`, {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        
        if (response.ok) {
            notifications.success(data.status || 'Coûts importés avec succès');
            loadElements(); // Recharger les éléments
            fileInput.value = ''; // Réinitialiser l'input
        } else {
            notifications.error(data.error || 'Erreur lors de l\'import');
        }
    } catch (error) {
        console.error('Erreur:', error);
        notifications.error('Erreur lors de l\'import');
    } finally {
        setLoading(false);
    }
}

/**
 * Réinitialisation du projet
 */
async function resetProject() {
    if (!confirm('Êtes-vous sûr de vouloir réinitialiser tout le projet ? Cette action est irréversible.')) {
        return;
    }
    
    setLoading(true, 'Réinitialisation en cours...');
    
    try {
        const response = await fetch(`${API_BASE_URL}/reset`, {
            method: 'POST'
        });
        
        if (response.ok) {
            notifications.success('Projet réinitialisé');
            loadElements(); // Recharger les éléments
        } else {
            notifications.error('Erreur lors de la réinitialisation');
        }
    } catch (error) {
        console.error('Erreur:', error);
        notifications.error('Erreur de connexion');
    } finally {
        setLoading(false);
    }
}

/**
 * Export Excel
 */
async function exportExcel() {
    setLoading(true, 'Préparation de l\'export...');
    
    try {
        const response = await fetch(`${API_BASE_URL}/export-costs-excel`);
        
        if (response.ok) {
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'couts_elements.xlsx';
            document.body.appendChild(a);
            a.click();
            a.remove();
            window.URL.revokeObjectURL(url);
            
            notifications.success('Fichier Excel téléchargé');
        } else {
            notifications.error('Erreur lors de l\'export');
        }
    } catch (error) {
        console.error('Erreur:', error);
        notifications.error('Erreur lors de l\'export');
    } finally {
        setLoading(false);
    }
}

/**
 * Chargement de la durée de vie du projet
 */
async function loadProjectLifespan() {
    try {
        const response = await fetch(`${API_BASE_URL}/get-project-lifespan`);
        const data = await response.json();
        
        if (response.ok && data.lifespan) {
            const input = document.getElementById('project-lifespan');
            input.value = data.lifespan;
            showStatusMessage('project-lifespan-status', 
                `Durée de vie actuelle : ${data.lifespan} années`, 'info');
        }
    } catch (error) {
        console.error('Erreur lors du chargement de la durée de vie:', error);
    }
}

/**
 * Définition de la durée de vie du projet
 */
async function setProjectLifespan() {
    const input = document.getElementById('project-lifespan');
    const lifespan = parseInt(input.value);
    
    if (!lifespan || lifespan <= 0) {
        notifications.warning('Veuillez entrer une durée de vie valide');
        return;
    }
    
    setLoading(true, 'Enregistrement de la durée de vie...');
    
    try {
        const response = await fetch(`${API_BASE_URL}/set-project-lifespan`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ lifespan })
        });
        
        if (response.ok) {
            notifications.success('Durée de vie du projet enregistrée');
            showStatusMessage('project-lifespan-status', 
                `Durée de vie définie : ${lifespan} années`, 'success');
        } else {
            const error = await response.json();
            notifications.error(error.error || 'Erreur lors de l\'enregistrement');
        }
    } catch (error) {
        console.error('Erreur:', error);
        notifications.error('Erreur de connexion');
    } finally {
        setLoading(false);
    }
}

/**
 * Chargement de la base de données matériaux
 */
async function loadMaterialsDB() {
    const fileInput = document.getElementById('bdd-file');
    const file = fileInput.files[0];
    
    if (!file) {
        notifications.warning('Veuillez sélectionner un fichier');
        return;
    }
    
    setLoading(true, 'Chargement de la base de données...');
    
    try {
        const formData = new FormData();
        formData.append('file', file);
        
        const response = await fetch(`${API_BASE_URL}/load-lifespan-bdd`, {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        
        if (response.ok && data.success) {
            notifications.success('Base de données matériaux chargée');
            showStatusMessage('bdd-status', 'Base de données chargée', 'success');
        } else {
            notifications.error(data.error || 'Erreur lors du chargement');
        }
    } catch (error) {
        console.error('Erreur:', error);
        notifications.error('Erreur lors du chargement');
    } finally {
        setLoading(false);
    }
}

/**
 * Auto-remplissage des durées de vie
 */
async function autofillLifespan() {
    setLoading(true, 'Auto-remplissage en cours...');
    
    try {
        const response = await fetch(`${API_BASE_URL}/autofill-lifespan`, {
            method: 'POST'
        });
        
        const data = await response.json();
        
        if (response.ok && data.success) {
            notifications.success(data.message || 'Durées de vie auto-remplies');
            loadElements(); // Recharger les éléments
        } else {
            notifications.error(data.error || 'Erreur lors de l\'auto-remplissage');
        }
    } catch (error) {
        console.error('Erreur:', error);
        notifications.error('Erreur de connexion');
    } finally {
        setLoading(false);
    }
}

/**
 * Import des durées de vie depuis Excel
 */
async function importLifespan() {
    const fileInput = document.getElementById('lifespan-file');
    const file = fileInput.files[0];
    
    if (!file) {
        notifications.warning('Veuillez sélectionner un fichier');
        return;
    }
    
    setLoading(true, 'Import des durées de vie...');
    
    try {
        const formData = new FormData();
        formData.append('file', file);
        
        const response = await fetch(`${API_BASE_URL}/upload-lifespan-excel`, {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        
        if (response.ok) {
            notifications.success(data.status || 'Durées de vie importées');
            loadElements(); // Recharger les éléments
            fileInput.value = ''; // Réinitialiser l'input
        } else {
            notifications.error(data.error || 'Erreur lors de l\'import');
        }
    } catch (error) {
        console.error('Erreur:', error);
        notifications.error('Erreur lors de l\'import');
    } finally {
        setLoading(false);
    }
}

/**
 * Actualisation du graphique de synthèse
 */
async function refreshChart() {
    try {
        const response = await fetch(`${API_BASE_URL}/costs-by-year`);
        const data = await response.json();
        
        if (response.ok) {
            displayChart(data);
        } else {
            console.error('Erreur lors du chargement des données du graphique');
        }
    } catch (error) {
        console.error('Erreur:', error);
    }
}

/**
 * Affichage du graphique
 */
function displayChart(data) {
    const ctx = document.getElementById('cost-chart').getContext('2d');
    
    // Détruire l'ancien graphique s'il existe
    if (window.currentChart) {
        window.currentChart.destroy();
    }
    
    // Données pour le graphique
    const labels = data.map(item => `Année ${item.year}`);
    const constructionData = data.map(item => item.ConstructionCosts || 0);
    const operationData = data.map(item => item.OperationCosts || 0);
    const maintenanceData = data.map(item => item.MaintenanceCosts || 0);
    const endOfLifeData = data.map(item => item.EndOfLifeCosts || 0);
    
    // Échantillonnage pour la lisibilité (afficher seulement certaines années)
    const sampleIndices = data.map((item, index) => {
        return index === 0 || // Première année
               index === data.length - 1 || // Dernière année
               item.year % 10 === 0 || // Années multiples de 10
               item.total > 0; // Années avec des coûts
    });
    
    window.currentChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'Construction ($)',
                    data: constructionData,
                    backgroundColor: 'rgba(40, 167, 69, 0.8)',
                    borderColor: 'rgba(40, 167, 69, 1)',
                    borderWidth: 1
                },
                {
                    label: 'Opération ($)',
                    data: operationData,
                    backgroundColor: 'rgba(13, 110, 253, 0.8)',
                    borderColor: 'rgba(13, 110, 253, 1)',
                    borderWidth: 1
                },
                {
                    label: 'Maintenance ($)',
                    data: maintenanceData,
                    backgroundColor: 'rgba(255, 193, 7, 0.8)',
                    borderColor: 'rgba(255, 193, 7, 1)',
                    borderWidth: 1
                },
                {
                    label: 'Fin de vie ($)',
                    data: endOfLifeData,
                    backgroundColor: 'rgba(220, 53, 69, 0.8)',
                    borderColor: 'rgba(220, 53, 69, 1)',
                    borderWidth: 1
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                x: {
                    stacked: true,
                    title: {
                        display: true,
                        text: 'Années'
                    },
                    ticks: {
                        maxRotation: 45,
                        minRotation: 0,
                        callback: function(value, index) {
                            const year = data[index]?.year;
                            // Afficher seulement les années multiples de 10 plus la première et dernière
                            if (year === 0 || year % 10 === 0 || year === data.length - 1) {
                                return `Année ${year}`;
                            }
                            return year % 5 === 0 ? year : '';
                        }
                    }
                },
                y: {
                    stacked: true,
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: 'Coût ($)'
                    },
                    ticks: {
                        callback: function(value) {
                            return new Intl.NumberFormat('en-US', {
                                style: 'currency',
                                currency: 'USD',
                                minimumFractionDigits: 0,
                                maximumFractionDigits: 0
                            }).format(value);
                        }
                    }
                }
            },
            plugins: {
                title: {
                    display: true,
                    text: 'Évolution des coûts par année et par catégorie'
                },
                legend: {
                    display: true,
                    position: 'top'
                },
                tooltip: {
                    mode: 'index',
                    intersect: false,
                    callbacks: {
                        title: function(tooltipItems) {
                            const index = tooltipItems[0].dataIndex;
                            const year = data[index]?.year;
                            return `Année ${year}`;
                        },
                        label: function(context) {
                            const label = context.dataset.label || '';
                            const value = new Intl.NumberFormat('en-US', {
                                style: 'currency',
                                currency: 'USD',
                                minimumFractionDigits: 0,
                                maximumFractionDigits: 0
                            }).format(context.parsed.y);
                            return `${label}: ${value}`;
                        },
                        footer: function(tooltipItems) {
                            const index = tooltipItems[0].dataIndex;
                            const yearData = data[index];
                            const total = (yearData.ConstructionCosts || 0) + 
                                         (yearData.OperationCosts || 0) + 
                                         (yearData.MaintenanceCosts || 0) + 
                                         (yearData.EndOfLifeCosts || 0);
                            const totalFormatted = new Intl.NumberFormat('en-US', {
                                style: 'currency',
                                currency: 'USD',
                                minimumFractionDigits: 0,
                                maximumFractionDigits: 0
                            }).format(total);
                            return `Total: ${totalFormatted}`;
                        }
                    }
                }
            },
            interaction: {
                mode: 'index',
                intersect: false
            }
        }
    });
}

/**
 * Gestion de l'état de chargement
 */
function setLoading(loading, message = 'Chargement...') {
    const overlay = document.getElementById('loading-overlay');
    const text = overlay.querySelector('.loading-text');
    
    if (loading) {
        text.textContent = message;
        overlay.classList.remove('d-none');
    } else {
        overlay.classList.add('d-none');
    }
}

/**
 * Affiche un message de statut dans un élément donné
 */
function showStatusMessage(elementId, message, type = 'info') {
    const element = document.getElementById(elementId);
    if (!element) return;
    
    const alertClass = {
        'success': 'alert-success',
        'error': 'alert-danger',
        'warning': 'alert-warning',
        'info': 'alert-info'
    }[type] || 'alert-info';
    
    element.innerHTML = `<div class="alert ${alertClass} alert-sm mb-0">${message}</div>`;
}

// ================================
// FONCTIONNALITÉS DE FILTRAGE ET MODIFICATION EN LOT
// ================================

let allElements = []; // Stockage de tous les éléments
let filteredElements = []; // Éléments filtrés
let selectedGuids = new Set(); // GUIDs sélectionnés

/**
 * Initialise les fonctionnalités de filtrage
 */
function initializeFilteringFeatures() {
    // Gestionnaire pour le filtre de description
    const descriptionFilter = document.getElementById('description-filter');
    if (descriptionFilter) {
        descriptionFilter.addEventListener('input', debounce(filterByDescription, 300));
    }

    // Gestionnaire pour le sélecteur de descriptions
    const descriptionSelector = document.getElementById('description-selector');
    if (descriptionSelector) {
        descriptionSelector.addEventListener('change', updateTableVisibility);
    }

    // Gestionnaire pour le checkbox "Sélectionner tout"
    const selectAllCheckbox = document.getElementById('select-all-checkbox');
    if (selectAllCheckbox) {
        selectAllCheckbox.addEventListener('change', toggleSelectAll);
    }

    // Gestionnaire pour l'input du matériau en lot
    const bulkMaterialInput = document.getElementById('bulk-material-input');
    if (bulkMaterialInput) {
        bulkMaterialInput.addEventListener('input', updateBulkApplyButton);
    }
}

/**
 * Met à jour la liste des descriptions disponibles
 */
function updateDescriptionsList() {
    const descriptions = [...new Set(allElements.map(el => el.UniformatDesc).filter(Boolean))].sort();
    const selector = document.getElementById('description-selector');
    
    if (selector) {
        selector.innerHTML = descriptions.map(desc => 
            `<option value="${desc}" title="${desc}">${desc.length > 50 ? desc.substring(0, 50) + '...' : desc}</option>`
        ).join('');
    }
}

/**
 * Filtre les éléments par description
 */
function filterByDescription() {
    const filterText = document.getElementById('description-filter').value.toLowerCase().trim();
    const selector = document.getElementById('description-selector');
    
    if (!filterText) {
        // Si pas de filtre, montrer toutes les descriptions
        updateDescriptionsList();
        filteredElements = [...allElements];
    } else {
        // Filtrer les descriptions
        const filteredDescriptions = [...new Set(allElements
            .map(el => el.UniformatDesc)
            .filter(desc => desc && desc.toLowerCase().includes(filterText))
        )].sort();
        
        selector.innerHTML = filteredDescriptions.map(desc => 
            `<option value="${desc}" title="${desc}">${desc.length > 50 ? desc.substring(0, 50) + '...' : desc}</option>`
        ).join('');
        
        // Filtrer les éléments
        filteredElements = allElements.filter(el => 
            el.UniformatDesc && el.UniformatDesc.toLowerCase().includes(filterText)
        );
    }
    
    updateTableVisibility();
}

/**
 * Met à jour la visibilité du tableau selon les sélections
 */
function updateTableVisibility() {
    const selector = document.getElementById('description-selector');
    const selectedDescriptions = Array.from(selector.selectedOptions).map(opt => opt.value);
    
    const table = document.getElementById('elements-table');
    const rows = table.querySelectorAll('tbody tr');
    
    rows.forEach(row => {
        const description = row.dataset.description;
        const shouldShow = selectedDescriptions.length === 0 || selectedDescriptions.includes(description);
        
        if (shouldShow) {
            row.style.display = '';
            row.classList.remove('d-none');
        } else {
            row.style.display = 'none';
            row.classList.add('d-none');
            
            // Décocher si caché
            const checkbox = row.querySelector('.element-checkbox');
            if (checkbox && checkbox.checked) {
                checkbox.checked = false;
                selectedGuids.delete(checkbox.dataset.guid);
            }
        }
    });
    
    updateSelectionCount();
}

/**
 * Efface le filtre de description
 */
function clearDescriptionFilter() {
    document.getElementById('description-filter').value = '';
    document.getElementById('description-selector').selectedIndex = -1;
    updateDescriptionsList();
    filteredElements = [...allElements];
    updateTableVisibility();
}

/**
 * Sélectionne tous les éléments filtrés visibles
 */
function selectAllFiltered() {
    const table = document.getElementById('elements-table');
    const visibleRows = table.querySelectorAll('tbody tr:not(.d-none)');
    
    visibleRows.forEach(row => {
        if (row.style.display !== 'none') {
            const checkbox = row.querySelector('.element-checkbox');
            if (checkbox) {
                checkbox.checked = true;
                selectedGuids.add(checkbox.dataset.guid);
            }
        }
    });
    
    updateSelectionCount();
    updateBulkApplyButton();
}

/**
 * Désélectionne tous les éléments
 */
function deselectAll() {
    const checkboxes = document.querySelectorAll('.element-checkbox');
    checkboxes.forEach(checkbox => {
        checkbox.checked = false;
    });
    
    const selectAllCheckbox = document.getElementById('select-all-checkbox');
    if (selectAllCheckbox) {
        selectAllCheckbox.checked = false;
    }
    
    selectedGuids.clear();
    updateSelectionCount();
    updateBulkApplyButton();
}

/**
 * Toggle sélection de tous les éléments visibles
 */
function toggleSelectAll() {
    const selectAllCheckbox = document.getElementById('select-all-checkbox');
    const shouldSelect = selectAllCheckbox.checked;
    
    if (shouldSelect) {
        selectAllFiltered();
    } else {
        deselectAll();
    }
}

/**
 * Met à jour le compteur de sélection
 */
function updateSelectionCount() {
    // Mettre à jour le Set avec les checkboxes actuellement cochées
    selectedGuids.clear();
    const checkedBoxes = document.querySelectorAll('.element-checkbox:checked');
    checkedBoxes.forEach(checkbox => {
        selectedGuids.add(checkbox.dataset.guid);
    });
    
    const count = selectedGuids.size;
    const counter = document.getElementById('selection-count');
    if (counter) {
        counter.textContent = `${count} sélectionné${count > 1 ? 's' : ''}`;
        counter.className = count > 0 ? 'badge bg-success' : 'badge bg-info';
    }
    
    updateBulkApplyButton();
}

/**
 * Met à jour l'état du bouton d'application en lot
 */
function updateBulkApplyButton() {
    const applyBtn = document.getElementById('apply-bulk-btn');
    const materialInput = document.getElementById('bulk-material-input');
    
    if (applyBtn && materialInput) {
        const hasSelection = selectedGuids.size > 0;
        const hasMaterial = materialInput.value.trim().length > 0;
        
        applyBtn.disabled = !(hasSelection && hasMaterial);
        
        if (hasSelection && hasMaterial) {
            applyBtn.classList.remove('btn-outline-warning');
            applyBtn.classList.add('btn-warning');
        } else {
            applyBtn.classList.remove('btn-warning');
            applyBtn.classList.add('btn-outline-warning');
        }
    }
}

/**
 * Affiche un aperçu des modifications
 */
function showPreview() {
    if (selectedGuids.size === 0) {
        notifications.warning('Aucun élément sélectionné');
        return;
    }
    
    const newMaterial = document.getElementById('bulk-material-input').value.trim();
    if (!newMaterial) {
        notifications.warning('Veuillez entrer un matériau');
        return;
    }
    
    const selectedElements = allElements.filter(el => selectedGuids.has(el.GlobalId));
    const message = `Vous allez modifier le matériau de ${selectedGuids.size} élément(s) :\n\n` +
                   selectedElements.slice(0, 5).map(el => 
                       `• ${el.GlobalId} - ${el.UniformatDesc || 'Sans description'}`
                   ).join('\n') +
                   (selectedElements.length > 5 ? `\n... et ${selectedElements.length - 5} autres` : '') +
                   `\n\nNouveau matériau : "${newMaterial}"`;
    
    if (confirm(message)) {
        applyBulkMaterial();
    }
}

/**
 * Applique le matériau en lot aux éléments sélectionnés
 */
async function applyBulkMaterial() {
    const newMaterial = document.getElementById('bulk-material-input').value.trim();
    const statusDiv = document.getElementById('bulk-status');
    
    if (selectedGuids.size === 0 || !newMaterial) {
        notifications.error('Sélection ou matériau manquant');
        return;
    }
    
    // Préparer les données pour l'API
    const updates = Array.from(selectedGuids).map(guid => ({
        guid: guid,
        material: newMaterial
    }));
    
    try {
        statusDiv.innerHTML = `<div class="alert alert-info alert-sm mb-0">
            <i class="fas fa-spinner fa-spin me-2"></i>Mise à jour en cours...
        </div>`;
        
        const response = await fetch(`${API_BASE_URL}/update-material`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(updates)
        });
        
        if (response.ok) {
            // Mettre à jour l'interface
            selectedGuids.forEach(guid => {
                const row = document.querySelector(`tr[data-guid="${guid}"]`);
                if (row) {
                    const materialInput = row.querySelector('.material-input');
                    if (materialInput) {
                        materialInput.value = newMaterial;
                        // Animation de succès
                        materialInput.classList.add('is-valid');
                        setTimeout(() => materialInput.classList.remove('is-valid'), 2000);
                    }
                }
            });
            
            statusDiv.innerHTML = `<div class="alert alert-success alert-sm mb-0">
                <i class="fas fa-check me-2"></i>${selectedGuids.size} matériau(x) mis à jour
            </div>`;
            
            notifications.success(`${selectedGuids.size} matériau(x) mis à jour avec succès`);
            
            // Réinitialiser
            document.getElementById('bulk-material-input').value = '';
            deselectAll();
            
        } else {
            const error = await response.json();
            throw new Error(error.error || 'Erreur lors de la mise à jour');
        }
        
    } catch (error) {
        console.error('Erreur:', error);
        statusDiv.innerHTML = `<div class="alert alert-danger alert-sm mb-0">
            <i class="fas fa-exclamation-triangle me-2"></i>Erreur: ${error.message}
        </div>`;
        notifications.error(error.message);
    }
}

/**
 * Utilitaire de debounce pour limiter les appels fréquents
 */
function debounce(func, wait) {
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

// Initialiser les fonctionnalités au chargement de la page
document.addEventListener('DOMContentLoaded', function() {
    setupEventListeners();
    checkHealth();
    loadElements();
    loadProjectLifespan();
    initializeFilteringFeatures(); // Nouvelle initialisation
});

/**
 * Calcul du Whole Life Cost (WLC)
 */
async function calculateWLC() {
    // Vérifier d'abord si des taux sont configurés
    if (!appState.discountRates || appState.discountRates.length === 0) {
        notifications.warning('Veuillez d\'abord charger les taux d\'actualisation');
        loadDiscountRates();
        return;
    }
    
    const missingRates = appState.discountRates.filter(r => r.discount_rate === null);
    if (missingRates.length > 0) {
        const message = `${missingRates.length} années n'ont pas de taux d'actualisation défini. Voulez-vous continuer ?`;
        if (!confirm(message)) {
            return;
        }
    }
    
    // Afficher le loading
    showWLCLoading(true);
    hideWLCResults();
    hideWLCError();
    hideWLCWarnings();
    
    try {
        const response = await fetch(`${API_BASE_URL}/calculate-wlc`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({}) // Plus besoin de passer le taux, il est dans l'ontologie
        });
        
        const data = await response.json();
        
        if (response.ok && data.success) {
            displayWLCResults(data);
            
            // Afficher les avertissements s'il y en a
            if (data.warnings && data.warnings.length > 0) {
                showWLCWarnings(data.warnings.join(', '));
            }
            
            notifications.success('WLC calculé avec succès');
        } else {
            showWLCError(data.error || 'Erreur lors du calcul WLC');
        }
    } catch (error) {
        console.error('Erreur calcul WLC:', error);
        showWLCError('Erreur de connexion');
    } finally {
        showWLCLoading(false);
    }
}

/**
 * Affiche les résultats du calcul WLC
 */
function displayWLCResults(data) {
    // Afficher le total WLC
    const totalElement = document.getElementById('wlc-total');
    totalElement.textContent = new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD',
        minimumFractionDigits: 0,
        maximumFractionDigits: 0
    }).format(data.total_wlc);
    
    // Afficher les détails
    document.getElementById('wlc-avg-rate').textContent = `${(data.average_discount_rate * 100).toFixed(1)}%`;
    document.getElementById('wlc-costs-count').textContent = data.costs_count;
    document.getElementById('wlc-years-count').textContent = data.years_analyzed;
    
    // Calculer les économies (différence entre coûts nominaux et actualisés)
    const totalNominal = data.costs_by_year.reduce((sum, year) => sum + year.nominal_cost, 0);
    const savings = totalNominal - data.total_wlc;
    document.getElementById('wlc-savings').textContent = new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD',
        minimumFractionDigits: 0,
        maximumFractionDigits: 0
    }).format(savings);
    
    // Afficher le graphique de comparaison avec gestion intelligente des échelles
    displayWLCComparisonChartAlternative(data.costs_by_year);
    
    // Montrer les résultats
    showWLCResults();
}

/**
 * Affiche le graphique de comparaison WLC
 */
function displayWLCComparisonChart(costsData) {
    const ctx = document.getElementById('wlc-comparison-chart').getContext('2d');
    
    // Destruction du graphique précédent
    if (window.wlcComparisonChart) {
        window.wlcComparisonChart.destroy();
    }
    
    // Préparer les données
    const labels = costsData.map(item => `Année ${item.year}`);
    const nominalData = costsData.map(item => item.nominal_cost);
    const discountedData = costsData.map(item => item.discounted_cost);
    
    // Création du graphique
    window.wlcComparisonChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'Coûts nominaux ($)',
                    data: nominalData,
                    borderColor: 'rgba(220, 53, 69, 1)',
                    backgroundColor: 'rgba(220, 53, 69, 0.1)',
                    borderWidth: 2,
                    fill: false,
                    tension: 0.1,
                    spanGaps: true,
                    pointRadius: 4,
                    pointHoverRadius: 6
                },
                {
                    label: 'Coûts actualisés ($)',
                    data: discountedData,
                    borderColor: 'rgba(40, 167, 69, 1)',
                    backgroundColor: 'rgba(40, 167, 69, 0.1)',
                    borderWidth: 2,
                    fill: false,
                    tension: 0.1,
                    spanGaps: true,
                    pointRadius: 4,
                    pointHoverRadius: 6
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                x: {
                    title: {
                        display: true,
                        text: 'Années'
                    },
                    ticks: {
                        maxRotation: 45,
                        callback: function(value, index) {
                            const year = costsData[index]?.year;
                            // Afficher seulement certaines années pour éviter l'encombrement
                            if (year === 0 || year % 20 === 0 || year === costsData.length - 1) {
                                return `Année ${year}`;
                            }
                            return year % 10 === 0 ? year : '';
                        }
                    }
                },
                y: {
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: 'Coût ($)'
                    },
                    ticks: {
                        callback: function(value) {
                            return new Intl.NumberFormat('en-US', {
                                style: 'currency',
                                currency: 'USD',
                                minimumFractionDigits: 0,
                                maximumFractionDigits: 0
                            }).format(value);
                        }
                    },
                    // Améliorer l'affichage pour les grandes différences d'échelle
                    grace: '5%'
                }
            },
            plugins: {
                title: {
                    display: true,
                    text: 'Impact de l\'actualisation sur les coûts annuels'
                },
                legend: {
                    display: true,
                    position: 'top'
                },
                tooltip: {
                    mode: 'index',
                    intersect: false,
                    callbacks: {
                        title: function(tooltipItems) {
                            const index = tooltipItems[0].dataIndex;
                            const year = costsData[index]?.year;
                            return `Année ${year}`;
                        },
                        label: function(context) {
                            const label = context.dataset.label || '';
                            const value = new Intl.NumberFormat('en-US', {
                                style: 'currency',
                                currency: 'USD',
                                minimumFractionDigits: 0,
                                maximumFractionDigits: 0
                            }).format(context.parsed.y);
                            return `${label}: ${value}`;
                        },
                        afterBody: function(tooltipItems) {
                            const index = tooltipItems[0].dataIndex;
                            const yearData = costsData[index];
                            const reduction = yearData.nominal_cost - yearData.discounted_cost;
                            const reductionPercent = ((reduction / yearData.nominal_cost) * 100).toFixed(1);
                            return `Réduction: ${new Intl.NumberFormat('en-US', {
                                style: 'currency',
                                currency: 'USD',
                                minimumFractionDigits: 0,
                                maximumFractionDigits: 0
                            }).format(reduction)} (${reductionPercent}%)`;
                        }
                    }
                }
            },
            interaction: {
                mode: 'index',
                intersect: false
            }
        }
    });
}

/**
 * Affiche un graphique WLC alternatif avec séparation construction/opération
 */
function displayWLCComparisonChartAlternative(costsData) {
    const ctx = document.getElementById('wlc-comparison-chart').getContext('2d');
    
    // Destruction du graphique précédent
    if (window.wlcComparisonChart) {
        window.wlcComparisonChart.destroy();
    }
    
    // Séparer les données de construction (année 0) des données opérationnelles
    const constructionData = costsData.filter(item => item.year === 0);
    const operationalData = costsData.filter(item => item.year > 0);
    
    // Si on a des données de construction très élevées, créer deux graphiques
    const hasHighConstructionCosts = constructionData.length > 0 && 
        constructionData[0].nominal_cost > 100000; // Plus de 100k
    
    if (hasHighConstructionCosts && operationalData.length > 0) {
        // Créer un graphique avec double axe Y
        const labels = costsData.map(item => `Année ${item.year}`);
        const nominalData = costsData.map(item => item.nominal_cost);
        const discountedData = costsData.map(item => item.discounted_cost);
        
        // Marquer les points de construction différemment
        const pointStyles = costsData.map(item => item.year === 0 ? 'rect' : 'circle');
        const pointSizes = costsData.map(item => item.year === 0 ? 8 : 4);
        
        window.wlcComparisonChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [
                    {
                        label: 'Coûts nominaux ($)',
                        data: nominalData,
                        borderColor: 'rgba(220, 53, 69, 1)',
                        backgroundColor: 'rgba(220, 53, 69, 0.1)',
                        borderWidth: 2,
                        fill: false,
                        tension: 0.1,
                        spanGaps: true,
                        pointStyle: pointStyles,
                        pointRadius: pointSizes,
                        pointHoverRadius: 8
                    },
                    {
                        label: 'Coûts actualisés ($)',
                        data: discountedData,
                        borderColor: 'rgba(40, 167, 69, 1)',
                        backgroundColor: 'rgba(40, 167, 69, 0.1)',
                        borderWidth: 2,
                        fill: false,
                        tension: 0.1,
                        spanGaps: true,
                        pointStyle: pointStyles,
                        pointRadius: pointSizes,
                        pointHoverRadius: 8
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    x: {
                        title: {
                            display: true,
                            text: 'Années'
                        },
                        ticks: {
                            maxRotation: 45,
                            callback: function(value, index) {
                                const year = costsData[index]?.year;
                                // Toujours afficher l'année 0 (construction)
                                if (year === 0) return `Année ${year} (Construction)`;
                                // Afficher certaines années pour éviter l'encombrement
                                if (year % 20 === 0 || year === costsData.length - 1) {
                                    return `Année ${year}`;
                                }
                                return year % 10 === 0 ? year : '';
                            }
                        }
                    },
                    y: {
                        type: 'logarithmic',
                        title: {
                            display: true,
                            text: 'Coût ($) - Échelle logarithmique'
                        },
                        ticks: {
                            callback: function(value) {
                                return new Intl.NumberFormat('en-US', {
                                    style: 'currency',
                                    currency: 'USD',
                                    minimumFractionDigits: 0,
                                    maximumFractionDigits: 0
                                }).format(value);
                            }
                        }
                    }
                },
                plugins: {
                    title: {
                        display: true,
                        text: 'Impact de l\'actualisation - Vue logarithmique'
                    },
                    legend: {
                        display: true,
                        position: 'top'
                    },
                    tooltip: {
                        mode: 'index',
                        intersect: false,
                        callbacks: {
                            title: function(tooltipItems) {
                                const index = tooltipItems[0].dataIndex;
                                const year = costsData[index]?.year;
                                const phase = year === 0 ? ' (Construction)' : year === costsData.length - 1 ? ' (Fin de vie)' : ' (Opération)';
                                return `Année ${year}${phase}`;
                            },
                            label: function(context) {
                                const label = context.dataset.label || '';
                                const value = new Intl.NumberFormat('en-US', {
                                    style: 'currency',
                                    currency: 'USD',
                                    minimumFractionDigits: 0,
                                    maximumFractionDigits: 0
                                }).format(context.parsed.y);
                                return `${label}: ${value}`;
                            },
                            afterBody: function(tooltipItems) {
                                const index = tooltipItems[0].dataIndex;
                                const yearData = costsData[index];
                                const reduction = yearData.nominal_cost - yearData.discounted_cost;
                                const reductionPercent = yearData.nominal_cost > 0 ? ((reduction / yearData.nominal_cost) * 100).toFixed(1) : '0';
                                return `Réduction: ${new Intl.NumberFormat('en-US', {
                                    style: 'currency',
                                    currency: 'USD',
                                    minimumFractionDigits: 0,
                                    maximumFractionDigits: 0
                                }).format(reduction)} (${reductionPercent}%)`;
                            }
                        }
                    }
                },
                interaction: {
                    mode: 'index',
                    intersect: false
                }
            }
        });
    } else {
        // Utiliser le graphique standard si pas de grandes différences
        displayWLCComparisonChart(costsData);
    }
}

/**
 * Fonctions utilitaires pour l'interface WLC
 */
function showWLCLoading(show) {
    const loadingElement = document.getElementById('wlc-loading');
    loadingElement.style.display = show ? 'block' : 'none';
}

function showWLCResults() {
    document.getElementById('wlc-results').classList.remove('d-none');
}

function hideWLCResults() {
    document.getElementById('wlc-results').classList.add('d-none');
}

function showWLCError(message) {
    const errorElement = document.getElementById('wlc-error');
    const messageElement = document.getElementById('wlc-error-message');
    messageElement.textContent = message;
    errorElement.classList.remove('d-none');
}

function hideWLCError() {
    document.getElementById('wlc-error').classList.add('d-none');
}

/**
 * Chargement automatique du WLC existant
 */
async function loadExistingWLC() {
    try {
        const response = await fetch(`${API_BASE_URL}/get-wlc`);
        const data = await response.json();
        
        if (response.ok && data.exists) {
            // Pré-remplir le taux d'actualisation
            const discountRateInput = document.getElementById('discount-rate');
            discountRateInput.value = (data.discount_rate * 100).toFixed(1);
            
            // Afficher les résultats existants
            displayWLCResults({
                total_wlc: data.total_value,
                discount_rate: data.discount_rate,
                costs_count: 0,
                years_analyzed: 0,
                costs_by_year: []
            });
            
            // Notification discrète
            console.log('WLC existant chargé:', data.total_value);
        }
    } catch (error) {
        console.log('Aucun WLC existant trouvé');
    }
}

/**
 * Gestion des taux d'actualisation
 */

/**
 * Définit un taux d'actualisation global pour toutes les années
 */
async function setGlobalDiscountRate() {
    const globalRateInput = document.getElementById('global-rate') || document.getElementById('global-rate-detailed');
    const ratePercent = parseFloat(globalRateInput.value);
    
    if (isNaN(ratePercent) || ratePercent < 0) {
        notifications.error('Veuillez entrer un taux valide');
        return;
    }
    
    console.log(`Application du taux global: ${ratePercent}%`);
    
    try {
        // Récupérer d'abord les données actuelles pour connaître le nombre d'années
        const currentData = await fetch('/get-discount-rates');
        const currentResult = await currentData.json();
        
        if (!currentResult.success || !currentResult.rates) {
            notifications.error('Impossible de récupérer les années existantes');
            return;
        }
        
        // Générer le tableau de taux pour toutes les années
        const rates = currentResult.rates.map(rateData => ({
            year: rateData.year,
            discount_rate: ratePercent / 100  // Convertir le pourcentage en décimal
        }));
        
        console.log(`Envoi de ${rates.length} taux à ${ratePercent}%`);
        
        const response = await fetch('/bulk-set-discount-rates', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ rates })
        });
        
        const result = await response.json();
        
        if (result.success) {
            notifications.success(`Taux global de ${ratePercent}% appliqué à ${rates.length} années`);
            
            // Recharger les données
            await loadDiscountRates();
        } else {
            notifications.error(result.error || 'Erreur lors de l\'application du taux global');
        }
    } catch (error) {
        console.error('Erreur:', error);
        notifications.error('Erreur de connexion');
    }
}

/**
 * Charge les taux d'actualisation depuis le serveur
 */
async function loadDiscountRates() {
    console.log('=== CHARGEMENT TAUX D\'ACTUALISATION ===');
    
    try {
        const response = await fetch(`${API_BASE_URL}/get-discount-rates`);
        const result = await response.json();
        
        console.log('Réponse API:', result);
        
        if (result.success) {
            // Stocker dans les deux variables pour compatibilité
            discountRatesData = result.rates;
            appState.discountRates = result.rates;
            
            console.log(`✅ ${result.total_years} taux chargés`);
            
            // Mettre à jour le résumé et le graphique
            displayDiscountRatesSummary(result.rates);
            displayDiscountRatesChart(result.rates);
            
            // Si le tableau détaillé est affiché, le mettre à jour
            const section = document.getElementById('detailed-discount-rates-section');
            if (section && section.style.display !== 'none') {
                displayDiscountRatesTable();
            }
            
            notifications.success(`${result.total_years} taux d'actualisation chargés`);
        } else {
            console.error('Erreur API:', result.error);
            notifications.error(result.error || 'Erreur lors du chargement des taux');
        }
    } catch (error) {
        console.error('Erreur réseau:', error);
        notifications.error('Erreur de connexion lors du chargement des taux');
    }
}

/**
 * Affiche le résumé des taux d'actualisation
 */
function displayDiscountRatesSummary(rates) {
    const configuredRates = rates.filter(r => r.discount_rate !== null);
    const missingRates = rates.filter(r => r.discount_rate === null);
    
    // Calculer le taux moyen
    const avgRate = configuredRates.length > 0 
        ? configuredRates.reduce((sum, r) => sum + r.discount_rate_percent, 0) / configuredRates.length 
        : 0;
    
    // Mettre à jour l'interface
    document.getElementById('configured-years').textContent = configuredRates.length;
    document.getElementById('average-rate').textContent = `${avgRate.toFixed(1)}%`;
    document.getElementById('missing-years').textContent = missingRates.length;
}

/**
 * Affiche le graphique des taux d'actualisation
 */
function displayDiscountRatesChart(rates) {
    const ctx = document.getElementById('discount-rates-chart').getContext('2d');
    
    // Destruction du graphique précédent
    if (window.discountRatesChart) {
        window.discountRatesChart.destroy();
    }
    
    // Filtrer les données (échantillonnage pour la lisibilité)
    const sampleRates = rates.filter((rate, index) => 
        index === 0 || // Première année
        index === rates.length - 1 || // Dernière année
        rate.year % 10 === 0 || // Années multiples de 10
        rate.discount_rate === null // Années sans taux
    );
    
    const labels = sampleRates.map(r => `Année ${r.year}`);
    const rateData = sampleRates.map(r => r.discount_rate_percent);
    
    window.discountRatesChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: 'Taux d\'actualisation (%)',
                data: rateData,
                borderColor: 'rgba(13, 110, 253, 1)',
                backgroundColor: 'rgba(13, 110, 253, 0.1)',
                borderWidth: 2,
                fill: true,
                tension: 0.1,
                pointBackgroundColor: sampleRates.map(r => 
                    r.discount_rate === null ? 'rgba(220, 53, 69, 1)' : 'rgba(13, 110, 253, 1)'
                ),
                pointBorderColor: sampleRates.map(r => 
                    r.discount_rate === null ? 'rgba(220, 53, 69, 1)' : 'rgba(13, 110, 253, 1)'
                ),
                pointRadius: sampleRates.map(r => r.discount_rate === null ? 6 : 4)
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                x: {
                    title: {
                        display: true,
                        text: 'Années (échantillon)'
                    }
                },
                y: {
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: 'Taux (%)'
                    },
                    ticks: {
                        callback: function(value) {
                            return `${value}%`;
                        }
                    }
                }
            },
            plugins: {
                title: {
                    display: true,
                    text: 'Évolution des taux d\'actualisation'
                },
                legend: {
                    display: false
                },
                tooltip: {
                    callbacks: {
                        title: function(tooltipItems) {
                            const index = tooltipItems[0].dataIndex;
                            return `Année ${sampleRates[index].year}`;
                        },
                        label: function(context) {
                            const rate = context.parsed.y;
                            return rate !== null ? `Taux: ${rate.toFixed(1)}%` : 'Taux non défini';
                        }
                    }
                }
            }
        }
    });
}

/**
 * Affiche le tableau détaillé des taux d'actualisation
 */
function displayDiscountRatesTable() {
    console.log('=== AFFICHAGE TABLEAU DÉTAILLÉ ===');
    const tableBody = document.getElementById('discount-rates-table');
    
    if (!tableBody) {
        console.error('Élément discount-rates-table non trouvé');
        notifications.error('Erreur: Élément tableau non trouvé');
        return;
    }
    
    if (!discountRatesData || discountRatesData.length === 0) {
        tableBody.innerHTML = '<tr><td colspan="4" class="text-center text-warning">Aucune donnée disponible. Cliquez sur "Charger les taux actuels".</td></tr>';
        console.warn('Pas de données de taux disponibles');
        return;
    }
    
    let html = '';
    discountRatesData.forEach(rate => {
        const year = rate.year;
        const discountRate = rate.discount_rate || 0;
        const ratePercent = (discountRate * 100).toFixed(1);
        const discountFactor = year === 0 ? 1.0 : (1 / Math.pow(1 + discountRate, year));
        
        html += `
            <tr>
                <td><strong>Année ${year}</strong></td>
                <td>
                    <div class="input-group input-group-sm">
                        <input type="number" class="form-control rate-input" 
                               value="${ratePercent}" step="0.1" min="0" max="20"
                               data-year="${year}" onchange="updateSingleRate(${year}, this.value)">
                        <span class="input-group-text">%</span>
                    </div>
                </td>
                <td>
                    <span class="badge bg-secondary">${discountFactor.toFixed(4)}</span>
                    <small class="text-muted d-block">1/(1+${ratePercent}%)^${year}</small>
                </td>
                <td>
                    <button class="btn btn-outline-primary btn-sm" onclick="setYearRate(${year}, ${ratePercent})" title="Confirmer le taux">
                        <i class="fas fa-check"></i>
                    </button>
                </td>
            </tr>
        `;
    });
    
    tableBody.innerHTML = html;
    console.log(`✅ Tableau généré avec ${discountRatesData.length} lignes`);
}

/**
 * Affiche la section du tableau détaillé des taux d'actualisation
 */
function showDiscountRatesTable() {
    console.log('=== DEBUT showDiscountRatesTable ===');
    const section = document.getElementById('detailed-discount-rates-section');
    
    if (!section) {
        console.error('Section detailed-discount-rates-section non trouvée');
        notifications.error('Erreur: Section tableau non trouvée');
        return;
    }
    
    // Forcer l'affichage de la section
    section.style.display = 'block';
    console.log('Section affichée');
    
    // Scroller vers la section
    section.scrollIntoView({ behavior: 'smooth' });
    
    // Charger et afficher les données
    if (!discountRatesData || discountRatesData.length === 0) {
        console.log('Pas de données, chargement depuis l\'API...');
        loadDiscountRates().then(() => {
            console.log('Données chargées, affichage du tableau...');
            displayDiscountRatesTable();
        });
    } else {
        console.log('Données déjà disponibles, affichage direct...');
        displayDiscountRatesTable();
    }
    
    notifications.info('Tableau détaillé des taux d\'actualisation affiché');
    console.log('=== FIN showDiscountRatesTable ===');
}

/**
 * Met à jour un taux pour une année spécifique
 */
async function updateSingleRate(year, ratePercent) {
    console.log(`Mise à jour du taux année ${year}: ${ratePercent}%`);
    
    try {
        const discountRate = parseFloat(ratePercent) / 100;
        
        // Utiliser l'endpoint bulk avec un seul taux
        const response = await fetch('/bulk-set-discount-rates', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                rates: [{ year: year, discount_rate: discountRate }]
            })
        });
        
        const result = await response.json();
        
        if (result.success) {
            // Mettre à jour localement
            const rateIndex = discountRatesData.findIndex(r => r.year === year);
            if (rateIndex !== -1) {
                discountRatesData[rateIndex].discount_rate = discountRate;
            }
            
            // Régénérer le tableau pour mettre à jour le facteur d'actualisation
            displayDiscountRatesTable();
            
            notifications.success(`Taux année ${year} mis à jour: ${ratePercent}%`);
        } else {
            notifications.error(result.error || 'Erreur lors de la mise à jour');
        }
    } catch (error) {
        console.error('Erreur:', error);
        notifications.error('Erreur de connexion');
    }
}

/**
 * Définit un taux pour une année spécifique (fonction helper)
 */
async function setYearRate(year, rate) {
    await updateSingleRate(year, rate);
}

/**
 * Fonctions utilitaires pour l'interface WLC - mises à jour
 */
function showWLCWarnings(message) {
    const warningsElement = document.getElementById('wlc-warnings');
    const messageElement = document.getElementById('wlc-warnings-message');
    messageElement.textContent = message;
    warningsElement.classList.remove('d-none');
}

function hideWLCWarnings() {
    document.getElementById('wlc-warnings').classList.add('d-none');
}

/**
 * Sauvegarde tous les taux modifiés
 */
async function saveAllDiscountRates() {
    console.log('Sauvegarde de tous les taux...');
    
    const inputs = document.querySelectorAll('.rate-input');
    const updates = [];
    
    inputs.forEach(input => {
        const year = parseInt(input.dataset.year);
        const rate = parseFloat(input.value) / 100;
        updates.push({ year, discount_rate: rate });
    });
    
    try {
        const response = await fetch('/bulk-set-discount-rates', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ rates: updates })
        });
        
        const result = await response.json();
        
        if (result.success) {
            notifications.success(`${updates.length} taux sauvegardés`);
            await loadDiscountRates();
        } else {
            notifications.error(result.error || 'Erreur lors de la sauvegarde');
        }
    } catch (error) {
        console.error('Erreur:', error);
        notifications.error('Erreur de connexion');
    }
}

/**
 * Exporte les taux en CSV
 */
function exportDiscountRates() {
    if (!discountRatesData || discountRatesData.length === 0) {
        notifications.warning('Aucune donnée à exporter. Chargez d\'abord les taux.');
        return;
    }
    
    try {
        let csvContent = 'Année,Taux (%),Facteur d\'actualisation\n';
        
        discountRatesData.forEach(rate => {
            const year = rate.year;
            const discountRate = rate.discount_rate || 0;
            const ratePercent = (discountRate * 100).toFixed(1);
            const discountFactor = year === 0 ? 1.0 : (1 / Math.pow(1 + discountRate, year));
            
            csvContent += `${year},${ratePercent},${discountFactor.toFixed(4)}\n`;
        });
        
        const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
        const link = document.createElement('a');
        const url = URL.createObjectURL(blob);
        
        link.setAttribute('href', url);
        link.setAttribute('download', 'taux_actualisation_WLC.csv');
        link.style.visibility = 'hidden';
        
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        
        notifications.success(`Export CSV réussi: ${discountRatesData.length} taux exportés`);
        
    } catch (error) {
        console.error('Erreur export CSV:', error);
        notifications.error('Erreur lors de l\'export CSV');
    }
}

/**
 * Fonction de diagnostic complète
 */
function diagnosticTableauTaux() {
    console.log('=== DIAGNOSTIC COMPLET ===');
    
    // 1. Vérifier la section principale
    const sectionPrincipale = document.getElementById('detailed-discount-rates-section');
    console.log('Section detailed-discount-rates-section:', {
        exists: !!sectionPrincipale,
        display: sectionPrincipale ? sectionPrincipale.style.display : 'N/A',
        visible: sectionPrincipale ? sectionPrincipale.offsetParent !== null : false
    });
    
    // 2. Vérifier l'élément tableau
    const tableBody = document.getElementById('discount-rates-table');
    console.log('Élément discount-rates-table:', {
        exists: !!tableBody,
        content: tableBody ? tableBody.innerHTML.substring(0, 100) + '...' : 'N/A'
    });
    
    // 3. Vérifier les données
    console.log('Variables globales:', {
        discountRatesData: discountRatesData ? discountRatesData.length : 'null/undefined',
        appState: appState.discountRates ? appState.discountRates.length : 'null/undefined'
    });
    
    // 4. Tester l'API
    fetch('/get-discount-rates')
        .then(response => response.json())
        .then(data => {
            console.log('Test API get-discount-rates:', {
                success: data.success,
                total: data.total_years,
                premierTaux: data.rates ? data.rates[0] : 'N/A'
            });
            
            notifications.info(`Diagnostic terminé - API: ${data.success ? 'OK' : 'ERREUR'}, Données: ${discountRatesData.length} taux`);
        })
        .catch(error => {
            console.error('Erreur API:', error);
            notifications.error('Erreur API lors du diagnostic');
        });
    
    console.log('=== FIN DIAGNOSTIC ===');
}

/**
 * Force le rechargement complet du tableau
 */
async function forceReloadDiscountTable() {
    console.log('=== DEBUG: Rechargement forcé du tableau ===');
    
    // Vider les données pour forcer un rechargement complet
    discountRatesData = [];
    appState.discountRates = [];
    
    // Vérifier que l'élément table existe
    const tableBody = document.getElementById('discount-rates-table');
    console.log('Élément table trouvé:', !!tableBody);
    
    if (tableBody) {
        tableBody.innerHTML = '<tr><td colspan="4" class="text-center"><div class="spinner-border spinner-border-sm me-2"></div>Rechargement en cours...</td></tr>';
    }
    
    // Recharger depuis l'API
    await loadDiscountRates();
    
    console.log('=== FIN DEBUG ===');
}

/**
 * Masque le tableau détaillé
 */
function hideDiscountRatesTable() {
    const section = document.getElementById('discount-rates-section');
    if (section) {
        section.style.display = 'none';
        console.log('✅ Section tableau taux cachée');
    }
}

/**
 * Fonctions IFC complètes - Workflow: Upload → Parse → Enrich → Download
 */

async function uploadIfc() {
    const fileInput = document.getElementById('ifc-file');
    const file = fileInput.files[0];
    
    if (!file) {
        notifications.warning('Veuillez sélectionner un fichier IFC');
        return;
    }
    
    setLoading(true, 'Upload du fichier IFC en stockage temporaire...');
    
    try {
        const formData = new FormData();
        formData.append('file', file);
        
        const response = await fetch(`${API_BASE_URL}/upload-ifc-temp`, {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        
        if (response.ok && data.success) {
            notifications.success(`Fichier ${data.filename} uploadé (${data.size_mb} MB)`);
            updateIfcStatus(); // Mettre à jour le statut
            enableIfcButtons(); // Activer les boutons suivants
        } else {
            notifications.error(data.error || 'Erreur lors de l\'upload');
        }
    } catch (error) {
        console.error('Erreur:', error);
        notifications.error('Erreur lors de l\'upload du fichier');
    } finally {
        setLoading(false);
    }
}

async function parseIfc() {
    try {
        setLoading(true, 'Parsing du fichier IFC vers l\'ontologie...');
        
        const response = await fetch(`${API_BASE_URL}/parse-ifc`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        
        const data = await response.json();
        
        if (response.ok && data.success) {
            notifications.success(`Fichier parsé: ${data.elements_count} éléments`);
            loadElements(); // Recharger les éléments
            updateIfcStatus(); // Mettre à jour le statut
        } else {
            notifications.error(data.error || 'Erreur lors du parsing');
        }
    } catch (error) {
        console.error('Erreur:', error);
        notifications.error('Erreur lors du parsing');
    } finally {
        setLoading(false);
    }
}

async function enrichIfc() {
    try {
        const response = await fetch(`${API_BASE_URL}/get-ifc-temp-status`);
        const data = await response.json();
        
        if (!data.has_file) {
            notifications.warning('Aucun fichier IFC en mémoire');
            return;
        }
        
        setLoading(true, 'Enrichissement du modèle IFC avec calculs WLC corrects...');
        
        // Appeler l'endpoint d'enrichissement réel
        const enrichResponse = await fetch(`${API_BASE_URL}/enrich-ifc`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        
        const enrichData = await enrichResponse.json();
        
        if (enrichResponse.ok && enrichData.success) {
            notifications.success(`🎉 ${enrichData.message}`);
            notifications.info(`✅ ${enrichData.elements_enriched} éléments enrichis avec PropertySets WLC_CostData`);
            notifications.info(`📁 Nouveau fichier: ${enrichData.new_size_mb} MB`);
            
            // Afficher les détails des calculs
            if (enrichData.project_lifespan) {
                notifications.info(`⏱️ Durée projet: ${enrichData.project_lifespan} ans - Taux actualisation: ${(enrichData.avg_discount_rate * 100).toFixed(1)}%`);
            }
            
            if (enrichData.total_nominal_project && enrichData.total_discounted_project) {
                const nominalFormatted = new Intl.NumberFormat('en-US', {style: 'currency', currency: 'USD', minimumFractionDigits: 0}).format(enrichData.total_nominal_project);
                const discountedFormatted = new Intl.NumberFormat('en-US', {style: 'currency', currency: 'USD', minimumFractionDigits: 0}).format(enrichData.total_discounted_project);
                const savingsFormatted = new Intl.NumberFormat('en-US', {style: 'currency', currency: 'USD', minimumFractionDigits: 0}).format(enrichData.total_savings);
                
                notifications.info(`💰 Total nominal: ${nominalFormatted} → Total actualisé: ${discountedFormatted}`);
                notifications.info(`💸 Économies d'actualisation: ${savingsFormatted}`);
            }
            
            // Afficher les méthodes de calcul
            if (enrichData.calculations) {
                notifications.info(`🧮 Calculs appliqués:`);
                notifications.info(`   • ${enrichData.calculations.operation_costs}`);
                notifications.info(`   • ${enrichData.calculations.maintenance_costs}`);
                notifications.info(`   • ${enrichData.calculations.discounting}`);
            }
            
            notifications.info(`🔬 PropertySets IFC standards: Construction_Cost, Operation_Cost, Maintenance_Cost, End_of_Life_Cost, Element_Lifespan, Total_Nominal_Cost, Total_Discounted_Cost`);
            
            // Mettre à jour le statut pour refléter l'enrichissement
            updateIfcStatus();
        } else {
            notifications.error(enrichData.error || 'Erreur lors de l\'enrichissement');
        }
        
    } catch (error) {
        console.error('Erreur:', error);
        notifications.error('Erreur lors de l\'enrichissement');
    } finally {
        setLoading(false);
    }
}

async function downloadEnrichedIfc() {
    try {
        const response = await fetch(`${API_BASE_URL}/get-ifc-temp-status`);
        const data = await response.json();
        
        if (!data.has_file) {
            notifications.warning('Aucun fichier IFC en mémoire');
            return;
        }
        
        setLoading(true, 'Préparation du téléchargement...');
        
        // Télécharger le fichier enrichi directement depuis le serveur
        const downloadResponse = await fetch(`${API_BASE_URL}/download-enriched-ifc`, {
            method: 'POST'
        });
        
        if (downloadResponse.ok) {
            const blob = await downloadResponse.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            
            // Nom du fichier enrichi
            const originalName = data.filename;
            const enrichedName = originalName.replace('.ifc', '_WLC_enriched.ifc');
            a.download = enrichedName;
            
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            window.URL.revokeObjectURL(url);
            
            notifications.success(`📥 Fichier enrichi téléchargé: ${enrichedName}`);
            notifications.info('🏗️ Le fichier contient maintenant les PropertySets WLC_CostData standard IFC');
            notifications.info('🔍 Testez dans votre viewer IFC préféré (Navisworks, Solibri, etc.)');
        } else {
            const errorData = await downloadResponse.json();
            notifications.error(errorData.error || 'Erreur lors du téléchargement');
        }
        
    } catch (error) {
        console.error('Erreur:', error);
        notifications.error('Erreur lors du téléchargement');
    } finally {
        setLoading(false);
    }
}

async function clearIfc() {
    if (!confirm('Êtes-vous sûr de vouloir vider le stockage temporaire IFC ?')) {
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE_URL}/clear-ifc-temp`, {
            method: 'POST'
        });
        
        const data = await response.json();
        
        if (response.ok && data.success) {
            notifications.success('Stockage temporaire IFC vidé');
            updateIfcStatus();
            disableIfcButtons();
        } else {
            notifications.error(data.error || 'Erreur lors du vidage');
        }
    } catch (error) {
        console.error('Erreur:', error);
        notifications.error('Erreur lors du vidage');
    }
}

async function updateIfcStatus() {
    try {
        const response = await fetch(`${API_BASE_URL}/get-ifc-temp-status`);
        const data = await response.json();
        
        const statusElement = document.getElementById('ifc-status');
        
        if (data.has_file) {
            const uploadDate = new Date(data.uploaded_at).toLocaleDateString('fr-FR');
            const parsedStatus = data.parsed ? 'Parsé' : 'Non parsé';
            const statusColor = data.parsed ? 'text-success' : 'text-warning';
            
            statusElement.innerHTML = `
                <div class="d-flex align-items-center">
                    <div class="me-3">
                        <i class="fas fa-file-alt fa-2x text-primary"></i>
                    </div>
                    <div>
                        <h6 class="mb-1">${data.filename}</h6>
                        <small class="text-muted d-block">Taille: ${data.size_mb} MB</small>
                        <small class="text-muted d-block">Uploadé: ${uploadDate}</small>
                        <span class="badge ${data.parsed ? 'bg-success' : 'bg-warning'}">${parsedStatus}</span>
                        ${data.elements_count > 0 ? `<span class="badge bg-info ms-1">${data.elements_count} éléments</span>` : ''}
                    </div>
                </div>
            `;
        } else {
            statusElement.innerHTML = `
                <div class="text-muted text-center py-3">
                    <i class="fas fa-file-alt fa-2x mb-2"></i>
                    <p>Aucun fichier IFC en mémoire</p>
                </div>
            `;
        }
    } catch (error) {
        console.error('Erreur lors de la mise à jour du statut:', error);
    }
}

async function enableIfcButtons() {
    // Activer les boutons selon le statut du fichier
    try {
        const response = await fetch(`${API_BASE_URL}/get-ifc-temp-status`);
        const data = await response.json();
        
        const parseBtn = document.getElementById('parse-btn');
        const enrichBtn = document.getElementById('enrich-btn');
        const downloadBtn = document.getElementById('download-btn');
        const clearBtn = document.getElementById('clear-btn');
        const extractGroupsBtn = document.getElementById('extract-groups-btn');
        
        if (data.has_file) {
            parseBtn.disabled = data.parsed; // Désactiver si déjà parsé
            enrichBtn.disabled = false; // Toujours activer si fichier présent - enrichissement basé sur GUIDs ontologie
            downloadBtn.disabled = false; // Toujours activer si fichier présent
            clearBtn.disabled = false; // Toujours disponible si fichier présent
            if (extractGroupsBtn) extractGroupsBtn.disabled = false; // Activer l'extraction des groupes
        } else {
            parseBtn.disabled = true;
            enrichBtn.disabled = true;
            downloadBtn.disabled = true;
            clearBtn.disabled = true;
            if (extractGroupsBtn) extractGroupsBtn.disabled = true; // Désactiver l'extraction des groupes
        }
    } catch (error) {
        console.error('Erreur lors de la mise à jour des boutons:', error);
    }
}

function disableIfcButtons() {
    document.getElementById('parse-btn').disabled = true;
    document.getElementById('enrich-btn').disabled = true;
    document.getElementById('download-btn').disabled = true;
    document.getElementById('clear-btn').disabled = true;
    const extractGroupsBtn = document.getElementById('extract-groups-btn');
    if (extractGroupsBtn) extractGroupsBtn.disabled = true;
}

async function downloadEnrichmentReport() {
    notifications.info('Rapport d\'enrichissement temporairement indisponible');
}

/**
 * Fonctions d'analyse manquantes - Placeholder pour éviter les erreurs
 */

async function analyzeCostImpact() {
    try {
        setLoading(true, 'Analyse d\'impact des coûts en cours...');
        
        const response = await fetch('/analyze-cost-impact');
        const data = await response.json();
        
        if (data.success) {
            displayAnalysisResults(data, 'Impact des Coûts');
            showNotification(`Analyse terminée: ${data.results.length} éléments analysés`, 'success');
        } else {
            showNotification('Erreur lors de l\'analyse d\'impact', 'error');
        }
    } catch (error) {
        console.error('Erreur:', error);
        showNotification('Erreur de connexion lors de l\'analyse', 'error');
    } finally {
        setLoading(false);
    }
}

async function analyzeFrequentReplacements() {
    try {
        setLoading(true, 'Analyse des remplacements fréquents en cours...');
        
        const response = await fetch('/analyze-frequent-replacements');
        const data = await response.json();
        
        if (data.success) {
            displayAnalysisResults(data, 'Remplacements Fréquents');
            showNotification(`Analyse terminée: ${data.results.length} éléments avec remplacements fréquents`, 'success');
        } else {
            showNotification('Erreur lors de l\'analyse des remplacements', 'error');
        }
    } catch (error) {
        console.error('Erreur:', error);
        showNotification('Erreur de connexion lors de l\'analyse', 'error');
    } finally {
        setLoading(false);
    }
}

async function analyzeHighMaintenance() {
    try {
        setLoading(true, 'Analyse de maintenance élevée en cours...');
        
        const response = await fetch('/analyze-high-maintenance');
        const data = await response.json();
        
        if (data.success) {
            displayAnalysisResults(data, 'Maintenance Élevée');
            showNotification(`Analyse terminée: ${data.results.length} éléments à maintenance élevée`, 'success');
        } else {
            showNotification('Erreur lors de l\'analyse de maintenance', 'error');
        }
    } catch (error) {
        console.error('Erreur:', error);
        showNotification('Erreur de connexion lors de l\'analyse', 'error');
    } finally {
        setLoading(false);
    }
}

async function analyzeHighOperation() {
    try {
        setLoading(true, 'Analyse d\'opération élevée en cours...');
        
        const response = await fetch('/analyze-high-operation');
        const data = await response.json();
        
        if (data.success) {
            displayAnalysisResults(data, 'Opération Élevée');
            showNotification(`Analyse terminée: ${data.results.length} éléments à opération élevée`, 'success');
        } else {
            showNotification('Erreur lors de l\'analyse d\'opération', 'error');
        }
    } catch (error) {
        console.error('Erreur:', error);
        showNotification('Erreur de connexion lors de l\'analyse', 'error');
    } finally {
        setLoading(false);
    }
}

async function analyzeCostByPhase(filterType = 'all') {
    try {
        setLoading(true, 'Analyse de la répartition des coûts par phases...');
        
        let url = '/analyze-cost-by-phase';
        let urlParams = new URLSearchParams();
        
        // Pour l'affichage initial, toujours afficher tous les éléments
        urlParams.append('filter_type', 'all');
        
        if (urlParams.toString()) {
            url += '?' + urlParams.toString();
        }
        
        const response = await fetch(url);
        const data = await response.json();
        
        if (data.success) {
            displayPhaseAnalysisResults(data);
            showNotification('Analyse par phases terminée', 'success');
        } else {
            showNotification('Erreur lors de l\'analyse : ' + (data.error || 'Erreur inconnue'), 'error');
        }
    } catch (error) {
        console.error('Erreur lors de l\'analyse par phases:', error);
        showNotification('Erreur lors de l\'analyse par phases', 'error');
    } finally {
        setLoading(false);
    }
}

function showPhaseFilterModal() {
    // Mettre à jour le compteur d'éléments sélectionnés
    const selectedCount = getSelectedElementGuids().length;
    document.getElementById('selectedElementsCount').textContent = selectedCount + ' sélectionnés';
    
    // Configurer les événements du modal
    setupPhaseFilterModalEvents();
    
    // Afficher le modal
    const modal = new bootstrap.Modal(document.getElementById('phaseFilterModal'));
    modal.show();
}

function setupPhaseFilterModalEvents() {
    // Gérer les changements de type de filtre
    const filterTypeRadios = document.querySelectorAll('input[name="phaseFilterType"]');
    filterTypeRadios.forEach(radio => {
        radio.addEventListener('change', handlePhaseFilterTypeChange);
    });
    
    // Gérer la recherche d'éléments personnalisés
    const searchInput = document.getElementById('elementSearchInput');
    if (searchInput) {
        searchInput.addEventListener('input', debounce(searchElementsForPhaseFilter, 300));
    }
    
    // Gérer les changements de filtre Uniformat
    const uniformatInput = document.getElementById('uniformatCodeFilter');
    if (uniformatInput) {
        uniformatInput.addEventListener('input', updatePhaseFilterPreview);
    }
    
    // Initialiser l'aperçu
    updatePhaseFilterPreview();
}

function handlePhaseFilterTypeChange(event) {
    const filterType = event.target.value;
    
    // Masquer toutes les options
    document.getElementById('uniformatFilterOptions').classList.add('d-none');
    document.getElementById('customFilterOptions').classList.add('d-none');
    document.getElementById('generalPreview').classList.remove('d-none');
    
    // Afficher les options correspondantes
    if (filterType === 'uniformat') {
        document.getElementById('uniformatFilterOptions').classList.remove('d-none');
        document.getElementById('generalPreview').classList.add('d-none');
    } else if (filterType === 'custom') {
        document.getElementById('customFilterOptions').classList.remove('d-none');
        document.getElementById('generalPreview').classList.add('d-none');
    }
    
    updatePhaseFilterPreview();
}

function updatePhaseFilterPreview() {
    const filterType = document.querySelector('input[name="phaseFilterType"]:checked').value;
    const previewElement = document.getElementById('filterPreviewText');
    
    if (filterType === 'all') {
        previewElement.textContent = 'Tous les éléments seront analysés';
    } else if (filterType === 'selected') {
        const selectedCount = getSelectedElementGuids().length;
        previewElement.textContent = `${selectedCount} éléments sélectionnés seront analysés`;
    } else if (filterType === 'uniformat') {
        const uniformatCode = document.getElementById('uniformatCodeFilter').value;
        previewElement.textContent = uniformatCode ? 
            `Éléments avec code Uniformat contenant "${uniformatCode}"` : 
            'Spécifiez un code Uniformat';
    } else if (filterType === 'custom') {
        const customCount = getCustomSelectedElementsCount();
        previewElement.textContent = `${customCount} éléments personnalisés sélectionnés`;
    }
}

async function searchElementsForPhaseFilter() {
    const searchTerm = document.getElementById('elementSearchInput').value.toLowerCase();
    const resultsContainer = document.getElementById('elementSearchResults');
    
    if (searchTerm.length < 2) {
        resultsContainer.innerHTML = '<p class="text-muted mb-0">Tapez au moins 2 caractères pour rechercher...</p>';
        return;
    }
    
    try {
        // Récupérer tous les éléments
        const response = await fetch('/get-ifc-elements');
        const elements = await response.json();
        
        // Filtrer les éléments qui correspondent au terme de recherche
        const filteredElements = elements.filter(element => 
            element.UniformatDesc.toLowerCase().includes(searchTerm) ||
            element.Material.toLowerCase().includes(searchTerm) ||
            element.GlobalId.toLowerCase().includes(searchTerm)
        ).slice(0, 20); // Limiter à 20 résultats
        
        // Afficher les résultats
        if (filteredElements.length === 0) {
            resultsContainer.innerHTML = '<p class="text-muted mb-0">Aucun élément trouvé</p>';
        } else {
            resultsContainer.innerHTML = filteredElements.map(element => `
                <div class="form-check">
                    <input class="form-check-input custom-element-check" type="checkbox" 
                           id="custom-${element.UniformatDesc || element.GlobalId}" value="${element.GlobalId}">
                    <label class="form-check-label" for="custom-${element.UniformatDesc || element.GlobalId}">
                        <strong>${element.UniformatDesc || element.UniformatDesc || element.GlobalId}</strong>
                        <small class="text-muted d-block">${element.Material} - ${element.UniformatDesc || element.GlobalId}</small>
                    </label>
                </div>
            `).join('');
            
            // Ajouter les événements de changement
            resultsContainer.querySelectorAll('.custom-element-check').forEach(checkbox => {
                checkbox.addEventListener('change', updateCustomSelectionCount);
            });
        }
    } catch (error) {
        console.error('Erreur lors de la recherche d\'éléments:', error);
        resultsContainer.innerHTML = '<p class="text-danger mb-0">Erreur lors de la recherche</p>';
    }
}

function updateCustomSelectionCount() {
    const count = getCustomSelectedElementsCount();
    document.getElementById('customSelectedCount').textContent = count;
    updatePhaseFilterPreview();
}

function getCustomSelectedElementsCount() {
    const checkboxes = document.querySelectorAll('#elementSearchResults input[type="checkbox"]:checked');
    return checkboxes.length;
}

/**
 * Importe une analyse précédente pour comparaison
 */
async function importPreviousAnalysis() {
    const fileInput = document.getElementById('previous-analysis-file');
    const file = fileInput.files[0];
    
    if (!file) {
        notifications.warning('Veuillez sélectionner un fichier d\'analyse');
        return;
    }
    
    try {
        setLoading(true, 'Import de l\'analyse précédente...');
        
        const formData = new FormData();
        formData.append('file', file);
        
        const response = await fetch(`${API_BASE_URL}/import-previous-analysis`, {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        
        if (data.success) {
            comparisonState.previousAnalysis = data.analysis_info;
            
            console.log('✅ Analyse importée:', data.analysis_info);
            
            // Mettre à jour l'interface avec les informations détaillées
            const statusDiv = document.getElementById('import-status');
            const analysisInfo = data.analysis_info;
            
            statusDiv.innerHTML = `
                <div class="alert alert-success alert-sm">
                    <i class="fas fa-check me-2"></i>
                    <strong>Analyse importée avec succès</strong>
                    <div class="mt-2">
                        <small class="d-block"><strong>Fichier :</strong> ${file.name}</small>
                        <small class="d-block"><strong>Date :</strong> ${analysisInfo.date || 'Non spécifiée'}</small>
                        <small class="d-block"><strong>Éléments :</strong> ${analysisInfo.elements_count || 0}</small>
                        <small class="d-block"><strong>Triplets RDF :</strong> ${analysisInfo.triplets_count || 0}</small>
                        ${analysisInfo.total_wlc ? `<small class="d-block"><strong>WLC Total :</strong> ${new Intl.NumberFormat('fr-FR', {style: 'currency', currency: 'USD'}).format(analysisInfo.total_wlc)}</small>` : ''}
                        ${analysisInfo.lifespan ? `<small class="d-block"><strong>Durée de vie :</strong> ${analysisInfo.lifespan} ans</small>` : ''}
                    </div>
                </div>
            `;
            
            // Mettre à jour l'affichage de l'info précédente
            const previousInfo = document.getElementById('previous-analysis-info');
            const infoText = `${file.name} - ${analysisInfo.elements_count || 0} éléments`;
            const dateText = analysisInfo.date ? ` (${new Date(analysisInfo.date).toLocaleDateString('fr-FR')})` : '';
            
            previousInfo.innerHTML = `
                <span class="text-success">
                    <i class="fas fa-file-check me-1"></i>
                    ${infoText}${dateText}
                </span>
            `;
            
            // Activer le bouton de comparaison
            const compareBtn = document.getElementById('compare-btn');
            if (compareBtn) {
                compareBtn.disabled = false;
                compareBtn.classList.remove('btn-outline-secondary');
                compareBtn.classList.add('btn-warning');
            }
            
            // Scroller vers la section de comparaison pour montrer que c'est prêt
            const comparisonSection = document.querySelector('.card.border-warning');
            if (comparisonSection) {
                comparisonSection.scrollIntoView({ behavior: 'smooth', block: 'center' });
            }
            
            notifications.success(`Analyse précédente importée avec succès - ${analysisInfo.elements_count || 0} éléments trouvés`);
        } else {
            throw new Error(data.error || 'Erreur lors de l\'import');
        }
    } catch (error) {
        console.error('❌ Erreur import:', error);
        
        // Afficher l'erreur dans l'interface
        const statusDiv = document.getElementById('import-status');
        statusDiv.innerHTML = `
            <div class="alert alert-danger alert-sm">
                <i class="fas fa-exclamation-triangle me-2"></i>
                <strong>Erreur lors de l'import</strong>
                <div class="mt-1">
                    <small>${error.message || 'Erreur inconnue'}</small>
                </div>
            </div>
        `;
        
        notifications.error('Erreur lors de l\'import de l\'analyse précédente');
    } finally {
        setLoading(false);
    }
}

/**
 * Lance la comparaison entre l'analyse actuelle et précédente
 */
async function compareAnalyses() {
    if (!comparisonState.previousAnalysis) {
        notifications.warning('Veuillez d\'abord importer une analyse précédente');
            return;
        }
        
    try {
        setLoading(true, 'Comparaison des analyses en cours...');
        
        const response = await fetch(`${API_BASE_URL}/compare-analyses`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        
        const data = await response.json();
        
        if (data.success) {
            comparisonState.comparisonResults = data.comparison;
            displayComparisonResults(data.comparison);
            
            // Afficher la section des résultats
            const resultsSection = document.getElementById('comparison-results-section');
            resultsSection.style.display = 'block';
            
            // Scroller vers les résultats
            resultsSection.scrollIntoView({ behavior: 'smooth' });
            
            notifications.success('Comparaison terminée avec succès');
        } else {
            throw new Error(data.error || 'Erreur lors de la comparaison');
        }
    } catch (error) {
        console.error('Erreur comparaison:', error);
        notifications.error('Erreur lors de la comparaison');
    } finally {
        setLoading(false);
    }
}

/**
 * Affiche les résultats de la comparaison
 */
function displayComparisonResults(comparison) {
    console.log('📊 Affichage des résultats de comparaison:', comparison);
    
    // Vérifier si les analyses sont identiques
    const isIdentical = comparison.is_identical || false;
    
    // Résumé exécutif
    const executiveSummary = document.getElementById('executive-summary');
    const discountedWlcEvolution = comparison.discounted_wlc_evolution || {};
    const wlcEvolution = comparison.wlc_evolution || {};
    const evolutionPercent = discountedWlcEvolution.percentage_change || 0;
    const evolutionAbsolute = discountedWlcEvolution.absolute_change || 0;
    
    // Formatage des montants
    const formatCurrency = (amount) => new Intl.NumberFormat('fr-FR', {
        style: 'currency',
        currency: 'USD'
    }).format(amount);
    
    const getEvolutionClass = (percent) => {
        if (Math.abs(percent) < 0.01) return 'stable';
        return percent > 0 ? 'increase' : 'decrease';
    };
    
    const getEvolutionIcon = (percent) => {
        if (Math.abs(percent) < 0.01) return '⚖️';
        return percent > 0 ? '📈' : '📉';
    };
    
    // Affichage du résumé exécutif
    if (isIdentical) {
        executiveSummary.innerHTML = `
            <div class="summary-card identical">
                <div class="summary-header">
                    <h3>✅ Analyses identiques</h3>
                    <span class="summary-badge identical">Aucun changement</span>
                </div>
                <div class="summary-content">
                    <p><strong>Les deux analyses sont parfaitement identiques.</strong></p>
                    <p>Aucune différence significative détectée dans :</p>
                    <ul>
                        <li>Le coût total du cycle de vie (WLC)</li>
                        <li>La répartition par phases</li>
                        <li>La répartition par parties prenantes</li>
                        <li>Le nombre d'éléments</li>
                    </ul>
                    <div class="wlc-summary">
                        <div class="wlc-item">
                            <span class="wlc-label">WLC Actualisé</span>
                            <span class="wlc-value">${formatCurrency(discountedWlcEvolution.current || 0)}</span>
                        </div>
                        <div class="wlc-item">
                            <span class="wlc-label">WLC Nominal</span>
                            <span class="wlc-value">${formatCurrency(wlcEvolution.current || 0)}</span>
                        </div>
                    </div>
                </div>
            </div>
        `;
    } else {
        const evolutionText = evolutionPercent > 0 ? 'augmentation' : 'diminution';
        const evolutionClass = getEvolutionClass(evolutionPercent);
        const evolutionIcon = getEvolutionIcon(evolutionPercent);
        
        executiveSummary.innerHTML = `
            <div class="summary-card ${evolutionClass}">
                <div class="summary-header">
                    <h3>${evolutionIcon} ${comparison.main_impact || 'Évolution détectée'}</h3>
                    <span class="summary-badge ${evolutionClass}">
                        ${Math.abs(evolutionPercent).toFixed(2)}% ${evolutionText}
                    </span>
                </div>
                <div class="summary-content">
                    <div class="evolution-details">
                        <div class="evolution-item">
                            <span class="evolution-label">WLC Actualisé</span>
                            <div class="evolution-values">
                                <span class="previous-value">${formatCurrency(discountedWlcEvolution.previous || 0)}</span>
                                <span class="arrow">→</span>
                                <span class="current-value">${formatCurrency(discountedWlcEvolution.current || 0)}</span>
                            </div>
                            <span class="evolution-change ${evolutionClass}">
                                ${evolutionAbsolute > 0 ? '+' : ''}${formatCurrency(evolutionAbsolute)}
                            </span>
                        </div>
                        <div class="evolution-item">
                            <span class="evolution-label">WLC Nominal</span>
                            <div class="evolution-values">
                                <span class="previous-value">${formatCurrency(wlcEvolution.previous || 0)}</span>
                                <span class="arrow">→</span>
                                <span class="current-value">${formatCurrency(wlcEvolution.current || 0)}</span>
                            </div>
                            <span class="evolution-change ${getEvolutionClass(wlcEvolution.percentage_change)}">
                                ${(wlcEvolution.absolute_change || 0) > 0 ? '+' : ''}${formatCurrency(wlcEvolution.absolute_change || 0)}
                            </span>
                        </div>
                    </div>
                    
                    <div class="comparison-stats">
                        <div class="stat-item">
                            <span class="stat-value">${comparison.elements_changed || 0}</span>
                            <span class="stat-label">Éléments modifiés</span>
                        </div>
                        <div class="stat-item">
                            <span class="stat-value">${comparison.phases_affected || 0}</span>
                            <span class="stat-label">Phases affectées</span>
                        </div>
                        <div class="stat-item">
                            <span class="stat-value">${comparison.stakeholders_affected || 0}</span>
                            <span class="stat-label">Parties prenantes modifiées</span>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }
    
    // Affichage des graphiques seulement s'il y a des changements significatifs
    const phasesData = comparison.phases_comparison || {};
    const stakeholdersData = comparison.stakeholders_comparison || {};
    
    if (!isIdentical && (phasesData.current || stakeholdersData.current)) {
        // Graphique des phases
        if (phasesData.current && Object.keys(phasesData.current).length > 0) {
            createPhasesComparisonChart(phasesData);
        }
        
        // Graphique des parties prenantes
        if (stakeholdersData.current && Object.keys(stakeholdersData.current).length > 0) {
            createStakeholdersComparisonChart(stakeholdersData);
        }
    } else if (isIdentical) {
        // Masquer les graphiques pour les analyses identiques
        const phasesChartContainer = document.getElementById('phases-comparison-chart');
        const stakeholdersChartContainer = document.getElementById('stakeholders-comparison-chart');
        
        if (phasesChartContainer) {
            phasesChartContainer.innerHTML = '<p class="no-changes">Aucun changement dans la répartition par phases</p>';
        }
        if (stakeholdersChartContainer) {
            stakeholdersChartContainer.innerHTML = '<p class="no-changes">Aucun changement dans la répartition par parties prenantes</p>';
        }
    }
    
    // Affichage des changements détaillés seulement s'il y en a
    const detailedChanges = comparison.detailed_changes || [];
    if (!isIdentical && detailedChanges.length > 0) {
        displayDetailedChangesTable(detailedChanges);
    } else {
        const detailedChangesContainer = document.getElementById('detailed-changes-table');
        if (detailedChangesContainer) {
            if (isIdentical) {
                detailedChangesContainer.innerHTML = '<p class="no-changes">Aucun changement détaillé à afficher</p>';
            } else {
                detailedChangesContainer.innerHTML = '<p class="no-changes">Aucun changement détaillé disponible</p>';
            }
        }
    }
    
    // Afficher la section des résultats
    const resultsSection = document.getElementById('comparison-results');
    if (resultsSection) {
        resultsSection.style.display = 'block';
        resultsSection.scrollIntoView({ behavior: 'smooth' });
    }
    
    // Activer le bouton d'export
    const exportBtn = document.getElementById('export-comparison-btn');
    if (exportBtn) {
        exportBtn.disabled = false;
    }
    
    console.log('✅ Résultats de comparaison affichés', { isIdentical, evolutionPercent });
}

/**
 * Crée le graphique de comparaison par phases
 */
function createPhasesComparisonChart(phasesData) {
    const ctx = document.getElementById('phases-comparison-chart');
    if (!ctx) return;
    
    // Détruire le graphique existant
    if (window.phasesComparisonChart) {
        window.phasesComparisonChart.destroy();
    }
    
    const phases = ['Construction', 'Opération', 'Maintenance', 'Fin de vie'];
    const previousData = phases.map(phase => phasesData.previous?.[phase] || 0);
    const currentData = phases.map(phase => phasesData.current?.[phase] || 0);
    
    window.phasesComparisonChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: phases,
            datasets: [
                {
                    label: 'Analyse Précédente ($)',
                    data: previousData,
                    backgroundColor: 'rgba(108, 117, 125, 0.8)',
                    borderColor: 'rgba(108, 117, 125, 1)',
                    borderWidth: 1
                },
                {
                    label: 'Analyse Actuelle ($)',
                    data: currentData,
                    backgroundColor: 'rgba(13, 110, 253, 0.8)',
                    borderColor: 'rgba(13, 110, 253, 1)',
                    borderWidth: 1
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        callback: function(value) {
                            return new Intl.NumberFormat('en-US', {
                                style: 'currency',
                                currency: 'USD',
                                minimumFractionDigits: 0
                            }).format(value);
                        }
                    }
                }
            },
            plugins: {
                title: {
                    display: true,
                    text: 'Comparaison des Coûts par Phase'
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const value = new Intl.NumberFormat('en-US', {
                                style: 'currency',
                                currency: 'USD',
                                minimumFractionDigits: 0
                            }).format(context.parsed.y);
                            return `${context.dataset.label}: ${value}`;
                        }
                    }
                }
            }
        }
    });
}

/**
 * Crée le graphique de comparaison des parties prenantes
 */
function createStakeholdersComparisonChart(stakeholdersData) {
    const ctx = document.getElementById('stakeholders-comparison-chart');
    if (!ctx) return;
    
    // Détruire le graphique existant
    if (window.stakeholdersComparisonChart) {
        window.stakeholdersComparisonChart.destroy();
    }
    
    const stakeholders = Object.keys(stakeholdersData.current || {});
    const previousData = stakeholders.map(stakeholder => stakeholdersData.previous?.[stakeholder] || 0);
    const currentData = stakeholders.map(stakeholder => stakeholdersData.current?.[stakeholder] || 0);
    
    window.stakeholdersComparisonChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: stakeholders,
            datasets: [
                {
                    label: 'Analyse Précédente ($)',
                    data: previousData,
                    backgroundColor: 'rgba(108, 117, 125, 0.8)',
                    borderColor: 'rgba(108, 117, 125, 1)',
                    borderWidth: 1
                },
                {
                    label: 'Analyse Actuelle ($)',
                    data: currentData,
                    backgroundColor: 'rgba(40, 167, 69, 0.8)',
                    borderColor: 'rgba(40, 167, 69, 1)',
                    borderWidth: 1
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        callback: function(value) {
                            return new Intl.NumberFormat('en-US', {
                                style: 'currency',
                                currency: 'USD',
                                minimumFractionDigits: 0
                            }).format(value);
                        }
                    }
                }
            },
            plugins: {
                title: {
                    display: true,
                    text: 'Impact par Partie Prenante'
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const value = new Intl.NumberFormat('en-US', {
                                style: 'currency',
                                currency: 'USD',
                                minimumFractionDigits: 0
                            }).format(context.parsed.y);
                            return `${context.dataset.label}: ${value}`;
                        }
                    }
                }
            }
        }
    });
}

/**
 * Affiche le tableau détaillé des changements
 */
function displayDetailedChangesTable(changes) {
    console.log('📊 [DEBUG] Début displayDetailedChangesTable', changes);
    
    // Fonction helper pour formater les montants
    const formatCurrency = (amount) => {
        try {
            return new Intl.NumberFormat('fr-FR', {
                style: 'currency',
                currency: 'USD',
                minimumFractionDigits: 0,
                maximumFractionDigits: 0
            }).format(amount || 0);
        } catch (e) {
            return `${amount || 0}$`;
        }
    };
    
    const tableContainer = document.getElementById('detailed-changes-table');
    if (!tableContainer) {
        console.error('❌ Container detailed-changes-table non trouvé');
        return;
    }
    
    if (!changes || changes.length === 0) {
        console.log('📊 [DEBUG] Aucun changement à afficher');
        tableContainer.innerHTML = '<p class="no-changes">Aucun changement détaillé disponible</p>';
        return;
    }
    
    try {
        console.log('📊 [DEBUG] Traitement de', changes.length, 'changements');
        
        let tableHTML = `
            <div class="alert alert-info mb-3">
                <h6 class="alert-heading">
                    <i class="fas fa-info-circle me-2"></i>
                    Résumé des Changements
                </h6>
                <p><strong>${changes.length}</strong> changements détectés</p>
            </div>
            <div class="table-responsive">
                <table class="table table-striped table-hover">
                    <thead class="table-dark">
                        <tr>
                            <th>Type</th>
                            <th>Élément / Uniformat</th>
                            <th>Coût Investissement</th>
                            <th>Coût Total Précédent</th>
                            <th>Coût Total Actuel</th>
                            <th>Évolution</th>
                        </tr>
                    </thead>
                    <tbody>
        `;
        
        changes.forEach((change, index) => {
            try {
                const changeType = change.change_type || 'Inconnu';
                const elementId = change.element_id || 'N/A';
                const previousValue = change.previous_value || 'N/A';
                const currentValue = change.current_value || 'N/A';
                const evolution = change.evolution || 0;
                
                // Badge couleur selon le type
                let badgeClass = 'bg-secondary';
                if (changeType.includes('ajouté')) badgeClass = 'bg-success';
                else if (changeType.includes('supprimé')) badgeClass = 'bg-danger';
                else if (changeType.includes('modifié')) badgeClass = 'bg-warning';
                else if (changeType.includes('global')) badgeClass = 'bg-primary';
                else if (changeType.includes('phase')) badgeClass = 'bg-info';
                
                // Évolution avec couleur
                const evolutionClass = evolution > 0 ? 'text-success' : evolution < 0 ? 'text-danger' : 'text-muted';
                const evolutionIcon = evolution > 0 ? '↗' : evolution < 0 ? '↘' : '→';
                const evolutionText = evolution === Infinity ? '+∞%' : 
                                    evolution === -100 ? '-100%' : 
                                    `${evolution > 0 ? '+' : ''}${evolution.toFixed(1)}%`;
                
                // Informations supplémentaires pour les éléments
                let elementDisplay = elementId;
                let investmentCostDisplay = 'N/A';
                
                if (changeType.includes('Élément')) {
                    // Affichage enrichi pour les éléments avec informations Uniformat
                    const uniformatCode = change.uniformat_code || 'N/A';
                    const uniformatDescription = change.uniformat_description || 'N/A';
                    const elementDescription = change.element_description || 'N/A';
                    const elementClass = change.element_class || 'N/A';
                    
                    elementDisplay = `
                        <div>
                            <strong>${elementId}</strong><br>
                            <small class="text-primary">
                                <i class="fas fa-tag me-1"></i>
                                ${uniformatCode} - ${uniformatDescription}
                            </small><br>
                            <small class="text-muted">
                                <i class="fas fa-cube me-1"></i>
                                ${elementClass}: ${elementDescription}
                            </small>
                        </div>
                    `;
                    
                    // Coût d'investissement (construction)
                    if (changeType.includes('modifié')) {
                        const currentInvestment = change.construction_cost || 0;
                        const previousInvestment = change.previous_construction_cost || 0;
                        
                        if (currentInvestment !== previousInvestment) {
                            investmentCostDisplay = `
                                <div>
                                    <span class="text-muted">${formatCurrency(previousInvestment)}</span><br>
                                    <i class="fas fa-arrow-down text-primary"></i><br>
                                    <strong class="text-primary">${formatCurrency(currentInvestment)}</strong>
                                </div>
                            `;
                        } else {
                            investmentCostDisplay = formatCurrency(currentInvestment);
                        }
                    } else if (changeType.includes('ajouté')) {
                        investmentCostDisplay = `<strong class="text-success">${formatCurrency(change.construction_cost || 0)}</strong>`;
                    } else if (changeType.includes('supprimé')) {
                        investmentCostDisplay = `<strong class="text-danger">${formatCurrency(change.construction_cost || 0)}</strong>`;
                    }
                } else {
                    // Pour les changements non-éléments (phases, stakeholders, etc.)
                    elementDisplay = `<strong>${elementId}</strong>`;
                    investmentCostDisplay = 'N/A';
                }
                
                tableHTML += `
                    <tr>
                        <td><span class="badge ${badgeClass}">${changeType}</span></td>
                        <td>${elementDisplay}</td>
                        <td class="text-center">${investmentCostDisplay}</td>
                        <td class="text-end">${previousValue}</td>
                        <td class="text-end">${currentValue}</td>
                        <td class="text-center ${evolutionClass}">
                            ${evolutionIcon} ${evolutionText}
                        </td>
                    </tr>
                `;
                
            } catch (rowError) {
                console.error('📊 [ERROR] Erreur ligne', index, rowError);
                tableHTML += `
                    <tr>
                        <td colspan="6" class="text-danger">
                            Erreur affichage changement ${index + 1}
                        </td>
                    </tr>
                `;
            }
        });
        
        tableHTML += `
                    </tbody>
                </table>
            </div>
        `;
        
        tableContainer.innerHTML = tableHTML;
        console.log('✅ [DEBUG] Tableau affiché avec succès');
        
    } catch (error) {
        console.error('❌ [ERROR] Erreur dans displayDetailedChangesTable:', error);
        tableContainer.innerHTML = `
            <div class="alert alert-danger">
                <h6>Erreur lors de l'affichage</h6>
                <p>Une erreur est survenue. Consultez la console pour plus de détails.</p>
                <small>Erreur: ${error.message}</small>
            </div>
        `;
    }
}

/**
 * Exporte le rapport de comparaison
 */
async function exportComparisonReport() {
    if (!comparisonState.comparisonResults) {
        notifications.warning('Aucune comparaison à exporter');
        return;
    }
    
    try {
        setLoading(true, 'Génération du rapport...');
        
        const response = await fetch(`${API_BASE_URL}/export-comparison-report`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        
        if (response.ok) {
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            
            const timestamp = new Date().toISOString().slice(0, 19).replace(/:/g, '-');
            a.download = `rapport_comparaison_wlc_${timestamp}.pdf`;
            
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            window.URL.revokeObjectURL(url);
            
            notifications.success('Rapport de comparaison exporté');
        } else {
            throw new Error('Erreur lors de l\'export du rapport');
        }
    } catch (error) {
        console.error('Erreur export rapport:', error);
        notifications.error('Erreur lors de l\'export du rapport');
    } finally {
        setLoading(false);
    }
}

/**
 * Efface la comparaison actuelle
 */
function clearComparison() {
    document.getElementById('comparison-results').innerHTML = '';
    document.getElementById('comparison-results').style.display = 'none';
}

/**
 * Export des éléments en Excel
 */
async function exportElementsExcel() {
    try {
        // Afficher un indicateur de chargement
        notifications.info('Préparation du fichier Excel...');
        
        const response = await fetch(`${API_BASE_URL}/export-elements-excel`);
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || 'Erreur lors de l\'export');
        }
        
        // Récupérer le blob du fichier Excel
        const blob = await response.blob();
        
        // Créer un lien de téléchargement
        const url = window.URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        
        // Générer un nom de fichier avec la date
        const now = new Date();
        const timestamp = now.toISOString().slice(0, 19).replace(/[:-]/g, '').replace('T', '_');
        link.download = `elements_ifc_${timestamp}.xlsx`;
        
        // Déclencher le téléchargement
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        
        // Nettoyer l'URL
        window.URL.revokeObjectURL(url);
        
        notifications.success('Fichier Excel téléchargé avec succès');
        
    } catch (error) {
        console.error('Erreur lors de l\'export Excel:', error);
        notifications.error(`Erreur lors de l'export Excel: ${error.message}`);
    }
}

/**
 * Extraction des groupes IFC spécifiés pour l'analyse coût/bénéfice
 */
async function extractGroups() {
    // Fonction legacy - redirige vers la nouvelle fonction
    await extractSelectedGroups();
}

/**
 * Extraction des groupes sélectionnés par l'utilisateur
 */
async function extractSelectedGroups() {
    setLoading(true, 'Extraction des groupes en cours...');
    
    try {
        // Récupérer les groupes sélectionnés
        const selectedGroups = [];
        
        // Vérifier tous les groupes disponibles
        const groupCheckboxes = [
            'group-heating', 'group-curtain', 'group-persiennes', 
            'group-climatisation', 'group-radiateurs', 'group-d3040', 
            'group-d3030', 'group-d3050', 'group-d3020'
        ];
        
        groupCheckboxes.forEach(checkboxId => {
            const checkbox = document.getElementById(checkboxId);
            if (checkbox && checkbox.checked) {
                selectedGroups.push(checkbox.value);
            }
        });
        
        // Validation
        if (selectedGroups.length === 0) {
            notifications.warning('Veuillez sélectionner au moins un groupe à extraire');
            return;
        }
        
        console.log('🎯 Groupes sélectionnés pour extraction:', selectedGroups);
        
        const response = await fetch(`${API_BASE_URL}/parse-ifc-groups`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                target_groups: selectedGroups
            })
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || 'Erreur lors de l\'extraction des groupes');
        }

        // Au lieu d'afficher les résultats dans la section groupes,
        // on intègre directement dans l'onglet éléments
        await integrateGroupsAsElements(data.groups);
        
        notifications.success(`${data.groups_found} groupe(s) intégré(s) comme éléments`);

        if (data.warning) {
            notifications.warning(data.warning);
        }
        
        // Recharger les éléments pour inclure les nouveaux groupes
        await loadElements();

    } catch (error) {
        console.error('Erreur lors de l\'extraction des groupes:', error);
        notifications.error('Erreur lors de l\'extraction des groupes: ' + error.message);
        clearGroupsStatus();
    } finally {
        setLoading(false);
    }
}

/**
 * Intégrer les groupes extraits comme éléments dans l'onglet Éléments
 */
async function integrateGroupsAsElements(groups) {
    console.log('🔄 Intégration des groupes comme éléments...', groups);
    
    // Mettre à jour le statut de la section groupes
    const statusDiv = document.getElementById('groups-status');
    if (statusDiv) {
        statusDiv.innerHTML = `
            <div class="text-success text-center">
                <i class="fas fa-check-circle fa-2x mb-2"></i>
                <p class="mb-0">${groups.length} groupe(s) intégré(s) comme éléments</p>
                <small class="text-muted">Consultez l'onglet "Éléments" pour les voir</small>
            </div>
        `;
    }
    
    // Stocker les groupes pour référence
    window.extractedGroups = groups;
    
    // Basculer automatiquement vers l'onglet Éléments
    const elementsTab = document.getElementById('nav-elements-tab');
    if (elementsTab) {
        elementsTab.click();
    }
}

/**
 * Affichage des résultats d'extraction des groupes (conservé pour compatibilité)
 */
function displayGroupsResults(data) {
    const statusDiv = document.getElementById('groups-status');
    
    if (data.groups.length === 0) {
        statusDiv.innerHTML = `
            <div class="text-warning text-center">
                <i class="fas fa-exclamation-triangle fa-2x mb-2"></i>
                <p class="mb-0">Aucun groupe trouvé</p>
            </div>
        `;
        return;
    }

    let html = `
        <div class="groups-results">
            <div class="mb-3">
                <strong>Groupes extraits (${data.groups_found}/${data.groups_requested})</strong>
            </div>
    `;

    data.groups.forEach(group => {
        html += `
            <div class="group-item border rounded p-3 mb-3">
                <div class="row">
                    <div class="col-md-8">
                        <h6 class="text-primary mb-1">
                            <i class="fas fa-layer-group me-2"></i>
                            ${group.Name || 'Groupe sans nom'}
                        </h6>
                        <div class="text-muted small">
                            <strong>GUID:</strong> <code>${group.GlobalId}</code><br>
                            <strong>Type:</strong> ${group.Type}<br>
                            <strong>Éléments inclus:</strong> ${group.ElementsCount}
                        </div>
                        ${group.Description ? `<div class="text-muted small mt-1"><strong>Description:</strong> ${group.Description}</div>` : ''}
                    </div>
                    <div class="col-md-4 text-end">
                        <button class="btn btn-sm btn-outline-primary mb-1" onclick="viewGroupElements('${group.GlobalId}')">
                            <i class="fas fa-eye me-1"></i>Voir éléments
                        </button>
                        <br>
                        <button class="btn btn-sm btn-outline-success" onclick="prepareGroupCosting('${group.GlobalId}', '${group.Name}')">
                            <i class="fas fa-euro-sign me-1"></i>Coûter
                        </button>
                    </div>
                </div>
            </div>
        `;
    });

    html += `
            <div class="mt-3">
                <button class="btn btn-primary btn-sm me-2" onclick="exportGroupsExcel()">
                    <i class="fas fa-file-excel me-1"></i>Exporter Excel
                </button>
                <button class="btn btn-outline-secondary btn-sm" onclick="clearGroupsStatus()">
                    <i class="fas fa-times me-1"></i>Effacer
                </button>
            </div>
        </div>
    `;

    statusDiv.innerHTML = html;
    
    // Stocker les données des groupes pour les fonctions suivantes
    window.extractedGroups = data.groups;
}

/**
 * Voir les éléments d'un groupe spécifique
 */
function viewGroupElements(groupGuid) {
    const group = window.extractedGroups?.find(g => g.GlobalId === groupGuid);
    if (!group) {
        notifications.error('Groupe non trouvé');
        return;
    }

    // Créer une modal pour afficher les éléments
    const modalHtml = `
        <div class="modal fade" id="groupElementsModal" tabindex="-1">
            <div class="modal-dialog modal-lg">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">
                            <i class="fas fa-layer-group me-2"></i>
                            Éléments du groupe : ${group.Name}
                        </h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        <div class="mb-3">
                            <strong>GUID du groupe:</strong> <code>${group.GlobalId}</code><br>
                            <strong>Nombre d'éléments:</strong> ${group.ElementsCount}
                        </div>
                        <div class="table-responsive">
                            <table class="table table-sm">
                                <thead>
                                    <tr>
                                        <th>GUID</th>
                                        <th>Nom</th>
                                        <th>Type</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    ${group.Elements.map(element => `
                                        <tr>
                                            <td><code class="small">${element.UniformatDesc || element.GlobalId}</code></td>
                                            <td>${element.Name || '-'}</td>
                                            <td>${element.Type}</td>
                                        </tr>
                                    `).join('')}
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `;

    // Supprimer la modal existante si elle existe
    const existingModal = document.getElementById('groupElementsModal');
    if (existingModal) {
        existingModal.remove();
    }

    // Ajouter la nouvelle modal au body
    document.body.insertAdjacentHTML('beforeend', modalHtml);

    // Afficher la modal
    const modal = new bootstrap.Modal(document.getElementById('groupElementsModal'));
    modal.show();
}

/**
 * Préparer le coûtage d'un groupe
 */
function prepareGroupCosting(groupGuid, groupName) {
    const group = window.extractedGroups?.find(g => g.GlobalId === groupGuid);
    if (!group) {
        notifications.error('Groupe non trouvé');
        return;
    }

    // Créer une modal pour saisir les coûts
    const modalHtml = `
        <div class="modal fade" id="groupCostingModal" tabindex="-1">
            <div class="modal-dialog">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">
                            <i class="fas fa-euro-sign me-2"></i>
                            Coûtage du groupe : ${groupName}
                        </h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        <div class="mb-3">
                            <strong>GUID:</strong> <code>${groupGuid}</code><br>
                            <strong>Éléments inclus:</strong> ${group.ElementsCount}
                        </div>
                        <form id="groupCostingForm">
                            <div class="mb-3">
                                <label class="form-label">Coût de construction ($)</label>
                                <input type="number" class="form-control" id="groupConstructionCost" step="0.01" min="0" placeholder="0.00">
                            </div>
                            <div class="mb-3">
                                <label class="form-label">Coût d'exploitation ($/an)</label>
                                <input type="number" class="form-control" id="groupOperationCost" step="0.01" min="0" placeholder="0.00">
                            </div>
                            <div class="mb-3">
                                <label class="form-label">Coût de maintenance ($/an)</label>
                                <input type="number" class="form-control" id="groupMaintenanceCost" step="0.01" min="0" placeholder="0.00">
                            </div>
                            <div class="mb-3">
                                <label class="form-label">Durée de vie (années)</label>
                                <input type="number" class="form-control" id="groupLifespan" min="1" max="100" value="50" placeholder="50">
                            </div>
                            <div class="mb-3">
                                <label class="form-label">Notes</label>
                                <textarea class="form-control" id="costingNotes" rows="3" placeholder="Notes sur l'estimation des coûts..."></textarea>
                            </div>
                        </form>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Annuler</button>
                        <button type="button" class="btn btn-primary" onclick="saveGroupCosting('${groupGuid}', '${groupName}')">
                            <i class="fas fa-save me-1"></i>Sauvegarder
                        </button>
                    </div>
                </div>
            </div>
        </div>
    `;

    // Supprimer la modal existante si elle existe
    const existingModal = document.getElementById('groupCostingModal');
    if (existingModal) {
        existingModal.remove();
    }

    // Ajouter la nouvelle modal au body
    document.body.insertAdjacentHTML('beforeend', modalHtml);

    // Afficher la modal
    const modal = new bootstrap.Modal(document.getElementById('groupCostingModal'));
    modal.show();
}

/**
 * Sauvegarder les coûts d'un groupe
 */
async function saveGroupCosting(groupGuid, groupName) {
    const form = document.getElementById('groupCostingForm');
    const formData = new FormData(form);
    
    const costingData = {
        groupGuid: groupGuid,
        groupName: groupName,
        constructionCost: parseFloat(document.getElementById('groupConstructionCost').value) || 0,
        operationCost: parseFloat(document.getElementById('groupOperationCost').value) || 0,
        maintenanceCost: parseFloat(document.getElementById('groupMaintenanceCost').value) || 0,
        lifespan: parseInt(document.getElementById('groupLifespan').value) || 50,
        notes: document.getElementById('costingNotes').value || ''
    };

    try {
        // Ici, vous pourriez sauvegarder dans l'ontologie ou un fichier local
        // Pour l'instant, on stocke en localStorage comme exemple
        let groupCostings = JSON.parse(localStorage.getItem('groupCostings') || '[]');
        
        // Supprimer l'ancienne version si elle existe
        groupCostings = groupCostings.filter(item => item.groupGuid !== groupGuid);
        
        // Ajouter la nouvelle
        groupCostings.push({
            ...costingData,
            timestamp: new Date().toISOString()
        });
        
        localStorage.setItem('groupCostings', JSON.stringify(groupCostings));
        
        notifications.success(`Coûts sauvegardés pour le groupe ${groupName}`);
        
        // Fermer la modal
        const modal = bootstrap.Modal.getInstance(document.getElementById('groupCostingModal'));
        modal.hide();
        
        // Mettre à jour l'affichage
        updateGroupsDisplayWithCosts();
        
    } catch (error) {
        console.error('Erreur lors de la sauvegarde:', error);
        notifications.error('Erreur lors de la sauvegarde des coûts');
    }
}

/**
 * Mettre à jour l'affichage des groupes avec les coûts
 */
function updateGroupsDisplayWithCosts() {
    const groupCostings = JSON.parse(localStorage.getItem('groupCostings') || '[]');
    
    // Ici vous pourriez mettre à jour l'affichage pour montrer les coûts associés
    console.log('Coûts des groupes:', groupCostings);
}

/**
 * Exporter les groupes et leurs coûts vers Excel
 */
async function exportGroupsExcel() {
    if (!window.extractedGroups || window.extractedGroups.length === 0) {
        notifications.warning('Aucun groupe à exporter');
        return;
    }

    const groupCostings = JSON.parse(localStorage.getItem('groupCostings') || '[]');
    
    // Préparer les données pour l'export
    const exportData = window.extractedGroups.map(group => {
        const costing = groupCostings.find(c => c.groupGuid === group.GlobalId);
        
        return {
            'GUID': group.GlobalId,
            'Nom': group.Name || '',
            'Description': group.Description || '',
            'Type': group.Type,
            'Nb_Elements': group.ElementsCount,
            'Cout_Construction': costing?.constructionCost || '',
            'Cout_Exploitation': costing?.operationCost || '',
            'Cout_Maintenance': costing?.maintenanceCost || '',
            'Duree_Vie': costing?.lifespan || '',
            'Notes': costing?.notes || ''
        };
    });

    try {
        // Convertir en CSV pour le moment (vous pourriez améliorer avec une vraie export Excel)
        const csvContent = convertToCSV(exportData);
        const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
        const link = document.createElement('a');
        
        if (link.download !== undefined) {
            const url = URL.createObjectURL(blob);
            link.setAttribute('href', url);
            link.setAttribute('download', `groupes_analyse_${new Date().toISOString().split('T')[0]}.csv`);
            link.style.visibility = 'hidden';
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
        }
        
        notifications.success('Export Excel des groupes terminé');
        
    } catch (error) {
        console.error('Erreur lors de l\'export:', error);
        notifications.error('Erreur lors de l\'export Excel');
    }
}

/**
 * Convertir les données en CSV
 */
function convertToCSV(data) {
    if (data.length === 0) return '';
    
    const headers = Object.keys(data[0]);
    const csvRows = [];
    
    // Ajouter les en-têtes
    csvRows.push(headers.join(','));
    
    // Ajouter les données
    for (const row of data) {
        const values = headers.map(header => {
            const value = row[header];
            // Échapper les guillemets et entourer de guillemets si nécessaire
            return typeof value === 'string' && value.includes(',') ? `"${value}"` : value;
        });
        csvRows.push(values.join(','));
    }
    
    return csvRows.join('\n');
}

/**
 * Effacer le statut des groupes
 */
function clearGroupsStatus() {
    const statusDiv = document.getElementById('groups-status');
    statusDiv.innerHTML = `
        <div class="text-muted text-center">
            <i class="fas fa-layer-group fa-2x mb-2"></i>
            <p class="mb-0">Aucun groupe extrait</p>
        </div>
    `;
    
    // Nettoyer les données stockées
    delete window.extractedGroups;
}

/**
 * Activer le bouton d'extraction des groupes quand un fichier IFC est chargé
 */
function enableGroupsExtraction() {
    const extractBtn = document.getElementById('extract-groups-btn');
    if (extractBtn) {
        extractBtn.disabled = false;
    }
}

/**
 * Désactiver le bouton d'extraction des groupes
 */
function disableGroupsExtraction() {
    const extractBtn = document.getElementById('extract-groups-btn');
    if (extractBtn) {
        extractBtn.disabled = true;
    }
}

/**
 * Met à jour l'état du bouton d'extraction selon les groupes sélectionnés
 */
function updateExtractButton() {
    const groupCheckboxes = [
        'group-heating', 'group-curtain', 'group-persiennes', 
        'group-climatisation', 'group-radiateurs', 'group-d3040', 
        'group-d3030', 'group-d3050', 'group-d3020'
    ];
    
    const hasSelection = groupCheckboxes.some(checkboxId => {
        const checkbox = document.getElementById(checkboxId);
        return checkbox && checkbox.checked;
    });
    
    const btn = document.getElementById('extract-groups-btn');
    if (btn) {
        btn.disabled = !hasSelection;
    }
}

// Ajouter les gestionnaires d'événements pour les checkboxes
document.addEventListener('DOMContentLoaded', function() {
    const groupCheckboxes = [
        'group-heating', 'group-curtain', 'group-persiennes', 
        'group-climatisation', 'group-radiateurs', 'group-d3040', 
        'group-d3030', 'group-d3050', 'group-d3020'
    ];
    
    groupCheckboxes.forEach(checkboxId => {
        const checkbox = document.getElementById(checkboxId);
        if (checkbox) {
            checkbox.addEventListener('change', updateExtractButton);
        }
    });
    
    // Mise à jour initiale
    updateExtractButton();
});

// Fonctions pour le filtrage d'analyse par phase
function getCustomSelectedElementGuids() {
    return Array.from(document.querySelectorAll('.custom-element-check:checked'))
        .map(checkbox => checkbox.value);
}

function getSelectedElementGuids() {
    // Récupérer les éléments sélectionnés dans le tableau principal
    const selectedCheckboxes = document.querySelectorAll('#elements-table tbody input[type="checkbox"]:checked');
    return Array.from(selectedCheckboxes).map(checkbox => {
        const row = checkbox.closest('tr');
        return row.querySelector('td:first-child').textContent.trim();
    });
}

async function executePhaseAnalysisWithFilter() {
    const filterType = document.querySelector('input[name="phaseFilterType"]:checked').value;
    
    try {
        setLoading(true, 'Analyse de la répartition des coûts par phases...');
        
        let url = '/analyze-cost-by-phase';
        let urlParams = new URLSearchParams();
        
        // Construire les paramètres selon le type de filtre
        urlParams.append('filter_type', filterType);
        
        if (filterType === 'selected') {
            const selectedGuids = getSelectedElementGuids();
            if (selectedGuids.length === 0) {
                showNotification('Aucun élément sélectionné dans le tableau', 'warning');
                setLoading(false);
                return;
            }
            urlParams.append('selected_guids', selectedGuids.join(','));
        } else if (filterType === 'uniformat') {
            const uniformatFilter = document.getElementById('uniformatCodeFilter').value.trim();
            if (!uniformatFilter) {
                showNotification('Veuillez spécifier un code Uniformat', 'warning');
                setLoading(false);
                return;
            }
            urlParams.append('uniformat_filter', uniformatFilter);
        } else if (filterType === 'custom') {
            const customGuids = getCustomSelectedElementGuids();
            if (customGuids.length === 0) {
                showNotification('Aucun élément sélectionné dans la recherche personnalisée', 'warning');
                setLoading(false);
                return;
            }
            urlParams.append('filter_type', 'selected');
            urlParams.append('selected_guids', customGuids.join(','));
        }
        
        url += '?' + urlParams.toString();
        
        const response = await fetch(url);
        const data = await response.json();
        
        if (data.success) {
            displayPhaseAnalysisResults(data);
            showNotification('Analyse par phases terminée', 'success');
            
            // Fermer le modal
            const modal = bootstrap.Modal.getInstance(document.getElementById('phaseFilterModal'));
            if (modal) modal.hide();
        } else {
            showNotification('Erreur lors de l\'analyse : ' + (data.error || 'Erreur inconnue'), 'error');
        }
    } catch (error) {
        console.error('Erreur lors de l\'analyse par phases:', error);
        showNotification('Erreur lors de l\'analyse par phases', 'error');
    } finally {
        setLoading(false);
    }
}

function displayPhaseAnalysisResults(data) {
    if (!data || !data.success) {
        showNotification('Aucune donnée à afficher', 'warning');
        return;
    }

    const resultsSection = document.getElementById('analysis-results-section');
    const analysisResults = document.getElementById('analysis-results');
    const analysisSummary = document.getElementById('analysis-summary');
    const analysisCount = document.getElementById('analysis-count');
    const titleElement = document.getElementById('analysis-title');
    
    if (!resultsSection || !analysisResults) return;
    
    // Afficher la section
    resultsSection.classList.remove('d-none');
    
    // Mettre à jour le titre et le compteur
    if (titleElement) titleElement.textContent = 'Répartition des Coûts par Phases';
    
    const summary = data.summary || {};
    const distribution = data.phase_distribution || [];
    
    if (analysisCount) {
        analysisCount.textContent = `${summary.elements_analyzed || 0} éléments analysés`;
    }
    
    // Afficher le résumé avec option de filtrage
    if (analysisSummary) {
        // Calculer l'information sur les coûts d'opération, maintenance et fin de vie
        const operationPhase = distribution.find(phase => phase.phase === 'Opération');
        const maintenancePhase = distribution.find(phase => phase.phase === 'Maintenance');
        const endOfLifePhase = distribution.find(phase => phase.phase === 'Fin de vie');
        
        const operationInfo = operationPhase ? 
            `<small class="text-info d-block mt-1">
                <i class="fas fa-calculator me-1"></i>
                Opération: ${operationPhase.annual_cost ? operationPhase.annual_cost.toLocaleString('en-US', {style: 'currency', currency: 'USD'}) : 'N/A'}/an × ${summary.operation_years || 0} ans = ${operationPhase.total_cost.toLocaleString('en-US', {style: 'currency', currency: 'USD'})}
            </small>` : '';
            
        const maintenanceInfo = maintenancePhase ? 
            `<small class="text-warning d-block mt-1">
                <i class="fas fa-tools me-1"></i>
                Maintenance: ${maintenancePhase.classic_maintenance_cost ? maintenancePhase.classic_maintenance_cost.toLocaleString('en-US', {style: 'currency', currency: 'USD'}) : '$0'} (classique) + ${maintenancePhase.replacement_cost ? maintenancePhase.replacement_cost.toLocaleString('en-US', {style: 'currency', currency: 'USD'}) : '$0'} (${maintenancePhase.total_replacements || 0} remplacements)
            </small>` : '';
            
        const endOfLifeInfo = endOfLifePhase ? 
            `<small class="text-danger d-block mt-1">
                <i class="fas fa-recycle me-1"></i>
                Fin de vie: ${endOfLifePhase.total_cost.toLocaleString('en-US', {style: 'currency', currency: 'USD'})} (tous les éléments à la fin du projet)
            </small>` : '';
        
        analysisSummary.innerHTML = `
            <div class="row mb-4">
                <div class="col-md-8">
                    <div class="card bg-light">
                        <div class="card-body">
                            <h6 class="card-title text-primary">Analyse de Répartition par Phases</h6>
                            <div class="row text-center">
                                <div class="col-3">
                                    <h5 class="text-success">${(summary.total_project_cost || 0).toLocaleString('en-US', {style: 'currency', currency: 'USD'})}</h5>
                                    <small class="text-muted">Coût Total</small>
                                    ${operationInfo}
                                    ${maintenanceInfo}
                                    ${endOfLifeInfo}
                                </div>
                                <div class="col-3">
                                    <h5 class="text-info">${summary.phases_analyzed || 0}</h5>
                                    <small class="text-muted">Phases</small>
                                    <small class="text-muted d-block mt-1">Projet: ${summary.project_lifespan || 0} ans</small>
                                </div>
                                <div class="col-3">
                                    <h5 class="text-warning">${summary.elements_analyzed || 0}</h5>
                                    <small class="text-muted">Éléments</small>
                                </div>
                                <div class="col-3">
                                    <h5 class="text-primary">${summary.dominant_phase || 'N/A'}</h5>
                                    <small class="text-muted">Phase dominante</small>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
                <div class="col-md-4">
                    <div class="card border-info">
                        <div class="card-header bg-info text-white">
                            <h6 class="mb-0"><i class="fas fa-filter me-2"></i>Options de Filtrage</h6>
                        </div>
                        <div class="card-body">
                            <p class="text-muted small mb-3">Refiltrer cette analyse</p>
                            <div class="d-grid gap-2">
                                <button class="btn btn-outline-primary btn-sm" onclick="showPhaseFilterModal()">
                                    <i class="fas fa-filter me-2"></i>Filtre Avancé
                                </button>
                                <button class="btn btn-outline-success btn-sm" onclick="analyzeSelectedElementsPhase()">
                                    <i class="fas fa-check-square me-2"></i>Éléments Sélectionnés
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }
    
    // Créer le tableau des phases avec plus de détails
    const phaseTable = distribution.map(phase => {
        let additionalInfo = '';
        if (phase.phase === 'Opération' && phase.annual_cost && phase.operation_years) {
            additionalInfo = `<br><small class="text-muted">
                ${phase.annual_cost.toLocaleString('en-US', {style: 'currency', currency: 'USD'})}/an × ${phase.operation_years} ans
            </small>`;
        } else if (phase.phase === 'Maintenance') {
            const classicCost = phase.classic_maintenance_cost || 0;
            const replacementCost = phase.replacement_cost || 0;
            const totalReplacements = phase.total_replacements || 0;
            
            additionalInfo = `<br><small class="text-muted">
                Classique: ${classicCost.toLocaleString('en-US', {style: 'currency', currency: 'USD'})} | Remplacements: ${replacementCost.toLocaleString('en-US', {style: 'currency', currency: 'USD'})} (${totalReplacements})
            </small>`;
        } else if (phase.phase === 'Fin de vie') {
            additionalInfo = `<br><small class="text-muted">
                Tous les éléments à la fin du projet
            </small>`;
        }
        
        return `
        <tr>
            <td><strong>${phase.phase}</strong>${additionalInfo}</td>
            <td class="text-end">${(phase.total_cost || 0).toLocaleString('en-US', {style: 'currency', currency: 'USD'})}</td>
            <td class="text-end">${(phase.percentage || 0).toFixed(1)}%</td>
            <td class="text-end">${phase.cost_count || 0}</td>
        </tr>
        `;
    }).join('');
    
    // Afficher les résultats détaillés
    if (analysisResults) {
        analysisResults.innerHTML = `
            <div class="row mb-4">
                <div class="col-md-6">
                    <div class="card">
                        <div class="card-header">
                            <h6>Répartition par Phase (%)</h6>
                        </div>
                        <div class="card-body">
                            <canvas id="phase-distribution-chart" width="400" height="300"></canvas>
                        </div>
                    </div>
                </div>
                <div class="col-md-6">
                    <div class="card">
                        <div class="card-header">
                            <h6>Détail par Phase</h6>
                        </div>
                        <div class="card-body">
                            <div class="table-responsive">
                                <table class="table table-sm">
                                    <thead>
                                        <tr>
                                            <th>Phase</th>
                                            <th class="text-end">Coût Total</th>
                                            <th class="text-end">Pourcentage</th>
                                            <th class="text-end">Nb. Coûts</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        ${phaseTable}
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            
            <div class="row">
                <div class="col-12">
                    <div class="alert alert-info">
                        <h6><i class="fas fa-info-circle me-2"></i>Information sur le calcul</h6>
                        <p class="mb-2">${data.description || 'Analyse de répartition des coûts par phases du cycle de vie'}</p>
                        ${summary.filter_description ? `<p class="mb-2"><strong>Filtre appliqué :</strong> ${summary.filter_description}</p>` : ''}
                        ${data.calculation_note ? `<p class="mb-0"><strong>📊 Calcul :</strong> ${data.calculation_note}</p>` : ''}
                        <p class="mb-0 mt-2"><strong>💡 Note :</strong> Les coûts d'opération sont calculés sur ${summary.operation_years || 0} années (durée projet - 1). Les coûts de maintenance incluent la maintenance classique sur ${summary.project_lifespan || 0} années + les coûts de fin de vie des éléments remplacés pendant le projet. Les coûts de fin de vie représentent le coût de fin de vie de TOUS les éléments à la fin du projet (année ${summary.project_lifespan || 0}).</p>
                    </div>
                </div>
            </div>
        `;
        
        // Créer le graphique après avoir ajouté le HTML
        setTimeout(() => createPhaseDistributionChart(distribution), 100);
    }
}

// Fonction pour analyser seulement les éléments sélectionnés
async function analyzeSelectedElementsPhase() {
    const selectedGuids = getSelectedElementGuids();
    if (selectedGuids.length === 0) {
        showNotification('Veuillez sélectionner des éléments dans le tableau principal (onglet Éléments)', 'warning');
        return;
    }
    
    try {
        setLoading(true, `Analyse par phases de ${selectedGuids.length} éléments sélectionnés...`);
        
        const url = `/analyze-cost-by-phase?filter_type=selected&selected_guids=${selectedGuids.join(',')}`;
        const response = await fetch(url);
        const data = await response.json();
        
        if (data.success) {
            displayPhaseAnalysisResults(data);
            showNotification(`Analyse terminée pour ${selectedGuids.length} éléments`, 'success');
        } else {
            showNotification('Erreur lors de l\'analyse : ' + (data.error || 'Erreur inconnue'), 'error');
        }
    } catch (error) {
        console.error('Erreur lors de l\'analyse:', error);
        showNotification('Erreur lors de l\'analyse des éléments sélectionnés', 'error');
    } finally {
        setLoading(false);
    }
}

// Fonction pour créer le graphique de distribution des phases
function createPhaseDistributionChart(distribution) {
    const ctx = document.getElementById('phase-distribution-chart');
    if (!ctx) return;
    
    // Détruire le graphique existant s'il existe
    if (window.phaseDistributionChart) {
        window.phaseDistributionChart.destroy();
    }
    
    const labels = distribution.map(phase => phase.phase);
    const data = distribution.map(phase => phase.total_cost || 0);
    const percentages = distribution.map(phase => phase.percentage || 0);
    
    // Couleurs pour chaque phase
    const colors = [
        'rgba(40, 167, 69, 0.8)',   // Construction - Vert
        'rgba(255, 193, 7, 0.8)',   // Opération - Jaune
        'rgba(23, 162, 184, 0.8)',  // Maintenance - Bleu
        'rgba(220, 53, 69, 0.8)'    // Fin de vie - Rouge
    ];
    
    const borderColors = [
        'rgba(40, 167, 69, 1)',
        'rgba(255, 193, 7, 1)',
        'rgba(23, 162, 184, 1)',
        'rgba(220, 53, 69, 1)'
    ];
    
    window.phaseDistributionChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: labels,
            datasets: [{
                data: data,
                backgroundColor: colors.slice(0, labels.length),
                borderColor: borderColors.slice(0, labels.length),
                borderWidth: 2
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                title: {
                    display: true,
                    text: 'Répartition des Coûts par Phase'
                },
                legend: {
                    position: 'bottom',
                    labels: {
                        generateLabels: function(chart) {
                            const data = chart.data;
                            if (data.labels.length && data.datasets.length) {
                                return data.labels.map((label, i) => {
                                    const percentage = percentages[i] || 0;
                                    const value = data.datasets[0].data[i] || 0;
                                    return {
                                        text: `${label}: ${percentage.toFixed(1)}% (${value.toLocaleString('en-US', {style: 'currency', currency: 'USD'})})`,
                                        fillStyle: data.datasets[0].backgroundColor[i],
                                        strokeStyle: data.datasets[0].borderColor[i],
                                        lineWidth: data.datasets[0].borderWidth,
                                        hidden: false,
                                        index: i
                                    };
                                });
                            }
                            return [];
                        }
                    }
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const label = context.label || '';
                            const value = context.parsed || 0;
                            const percentage = percentages[context.dataIndex] || 0;
                            return `${label}: ${value.toLocaleString('en-US', {style: 'currency', currency: 'USD'})}) (${percentage.toFixed(1)}%)`;
                        }
                    }
                }
            }
        }
    });
}

// Fonction pour afficher les notifications
function showNotification(message, type = 'info') {
    // Utiliser l'existant toast si possible
    const toastElement = document.getElementById('notification-toast');
    if (toastElement) {
        const titleElement = document.getElementById('toast-title');
        const bodyElement = document.getElementById('toast-body');
        const iconElement = document.getElementById('toast-icon');
        
        if (titleElement && bodyElement && iconElement) {
            // Définir le titre et l'icône selon le type
            switch(type) {
                case 'success':
                    titleElement.textContent = 'Succès';
                    iconElement.className = 'fas fa-check-circle me-2 text-success';
                    break;
                case 'error':
                    titleElement.textContent = 'Erreur';
                    iconElement.className = 'fas fa-exclamation-triangle me-2 text-danger';
                    break;
                case 'warning':
                    titleElement.textContent = 'Attention';
                    iconElement.className = 'fas fa-exclamation-circle me-2 text-warning';
                    break;
                default:
                    titleElement.textContent = 'Information';
                    iconElement.className = 'fas fa-info-circle me-2 text-info';
            }
            
            bodyElement.textContent = message;
            
            // Afficher le toast
            const toast = new bootstrap.Toast(toastElement, {
                delay: type === 'error' ? 8000 : 4000
            });
            toast.show();
            
            return;
        }
    }
    
    // Fallback : utiliser console et alert
    console.log(`[${type.toUpperCase()}] ${message}`);
    if (type === 'error') {
        alert(`Erreur: ${message}`);
    }
}

/**
 * Exporte l'analyse complète au format Turtle
 */
async function exportCompleteAnalysis() {
    try {
        setLoading(true, 'Export de l\'analyse complète...');
        
        const response = await fetch('/export-complete-analysis');
        
        if (!response.ok) {
            throw new Error(`Erreur HTTP: ${response.status}`);
        }
        
        // La réponse est du contenu Turtle, pas du JSON
        const turtleContent = await response.text();
        
        // Créer le lien de téléchargement
        const blob = new Blob([turtleContent], { type: 'text/turtle' });
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.style.display = 'none';
        a.href = url;
        a.download = `wlc_analysis_${new Date().toISOString().split('T')[0]}.ttl`;
        
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
        
        // Mettre à jour le statut
        const statusDiv = document.getElementById('export-status');
        if (statusDiv) {
            statusDiv.innerHTML = `
                <div class="alert alert-success alert-sm">
                    <i class="fas fa-check me-2"></i>
                    Analyse exportée avec succès (fichier Turtle)
                </div>
            `;
        }
        
        showNotification('Analyse exportée avec succès', 'success');
        
    } catch (error) {
        console.error('Erreur export:', error);
        
        const statusDiv = document.getElementById('export-status');
        if (statusDiv) {
            statusDiv.innerHTML = `
                <div class="alert alert-danger alert-sm">
                    <i class="fas fa-exclamation-triangle me-2"></i>
                    Erreur : ${error.message}
                </div>
            `;
        }
        
        showNotification('Erreur lors de l\'export', 'error');
    } finally {
        setLoading(false);
    }
}

/**
 * Affiche les résultats génériques d'analyse (impact, remplacements, maintenance, opération)
 */
function displayAnalysisResults(data, analysisTitle) {
    if (!data || !data.success) {
        showNotification('Aucune donnée à afficher', 'warning');
        return;
    }

    const resultsSection = document.getElementById('analysis-results-section');
    const analysisResults = document.getElementById('analysis-results');
    const analysisSummary = document.getElementById('analysis-summary');
    const analysisCount = document.getElementById('analysis-count');
    const titleElement = document.getElementById('analysis-title');
    
    if (!resultsSection || !analysisResults) return;
    
    // Afficher la section
    resultsSection.classList.remove('d-none');
    
    // Mettre à jour le titre et le compteur
    if (titleElement) titleElement.textContent = analysisTitle || 'Résultats d\'Analyse';
    if (analysisCount) {
        const count = data.results ? data.results.length : 0;
        analysisCount.textContent = `${count} éléments trouvés`;
    }
    
    // Afficher le résumé
    if (analysisSummary) {
        const summary = data.summary || {};
        const resultsCount = data.results ? data.results.length : 0;
        
        analysisSummary.innerHTML = `
            <div class="row mb-4">
                <div class="col-md-8">
                    <div class="card bg-light">
                        <div class="card-body">
                            <h6 class="card-title text-primary">${analysisTitle}</h6>
                            <div class="row text-center">
                                <div class="col-3">
                                    <h5 class="text-success">${resultsCount}</h5>
                                    <small class="text-muted">Éléments identifiés</small>
                                </div>
                                <div class="col-3">
                                    <h5 class="text-info">${(summary.total_cost || 0).toLocaleString('en-US', {style: 'currency', currency: 'USD'})}</h5>
                                    <small class="text-muted">Coût Total</small>
                                </div>
                                <div class="col-3">
                                    <h5 class="text-warning">${(summary.average_cost || 0).toLocaleString('en-US', {style: 'currency', currency: 'USD'})}</h5>
                                    <small class="text-muted">Coût Moyen</small>
                                </div>
                                <div class="col-3">
                                    <h5 class="text-primary">${(summary.max_cost || 0).toLocaleString('en-US', {style: 'currency', currency: 'USD'})}</h5>
                                    <small class="text-muted">Coût Maximum</small>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
                <div class="col-md-4">
                    <div class="card border-info">
                        <div class="card-header bg-info text-white">
                            <h6 class="mb-0"><i class="fas fa-info-circle me-2"></i>Information</h6>
                        </div>
                        <div class="card-body">
                            <p class="text-muted small mb-2">${data.description || 'Analyse des éléments critiques'}</p>
                            <p class="mb-0">
                                <strong>Critère :</strong> ${summary.criteria || 'Selon seuils définis'}
                            </p>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }
    
    // Créer le tableau des résultats
    if (analysisResults && data.results) {
        const resultsCount = data.results.length;
        const tableRows = data.results.map(element => `
            <tr>
                <td><code>${element.guid || element.global_id || 'N/A'}</code></td>
                <td>${element.ifc_class || 'N/A'}</td>
                <td>${element.uniformat_code || 'N/A'}</td>
                <td>${element.description || 'Non spécifié'}</td>
                <td>${element.material || 'Non spécifié'}</td>
                <td class="text-end">${(element.construction_cost || 0).toLocaleString('en-US', {style: 'currency', currency: 'USD'})}</td>
                <td class="text-end">${(element.operation_cost || 0).toLocaleString('en-US', {style: 'currency', currency: 'USD'})}</td>
                <td class="text-end">${(element.maintenance_cost || 0).toLocaleString('en-US', {style: 'currency', currency: 'USD'})}</td>
                <td class="text-end">${(element.end_of_life_cost || 0).toLocaleString('en-US', {style: 'currency', currency: 'USD'})}</td>
                <td class="text-center">${element.lifespan || 'N/A'}</td>
                <td class="text-end"><strong>${(element.total_cost || 0).toLocaleString('en-US', {style: 'currency', currency: 'USD'})}</strong></td>
            </tr>
        `).join('');
        
        analysisResults.innerHTML = `
            <div class="row">
                <div class="col-12">
                    <div class="card">
                        <div class="card-header d-flex justify-content-between align-items-center">
                            <h6 class="mb-0">Détail des Éléments</h6>
                            <button class="btn btn-outline-success btn-sm" onclick="exportAnalysisResults()">
                                <i class="fas fa-file-excel me-2"></i>Exporter Excel
                            </button>
                        </div>
                        <div class="card-body">
                            <div class="table-responsive">
                                <table class="table table-sm table-hover">
                                    <thead class="table-dark">
                                        <tr>
                                            <th>GUID</th>
                                            <th>Classe IFC</th>
                                            <th>Uniformat</th>
                                            <th>Description</th>
                                            <th>Matériau</th>
                                            <th class="text-end">Construction</th>
                                            <th class="text-end">Opération</th>
                                            <th class="text-end">Maintenance</th>
                                            <th class="text-end">Fin de vie</th>
                                            <th class="text-center">Durée (ans)</th>
                                            <th class="text-end">Total</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        ${tableRows}
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            
            ${resultsCount > 0 ? `
            <div class="row mt-4">
                <div class="col-12">
                    <div class="alert alert-info">
                        <h6><i class="fas fa-lightbulb me-2"></i>Recommandations</h6>
                        <p class="mb-0">${getAnalysisRecommendations(analysisTitle, data.results)}</p>
                    </div>
                </div>
            </div>
            ` : ''}
        `;
    }
}

/**
 * Génère des recommandations selon le type d'analyse
 */
function getAnalysisRecommendations(analysisTitle, results) {
    const count = results.length;
    
    switch(analysisTitle) {
        case 'Impact des Coûts':
            return `Les ${count} éléments identifiés représentent les coûts les plus importants du projet. Considérez des alternatives ou une optimisation de ces éléments.`;
        case 'Remplacements Fréquents':
            return `Ces ${count} éléments nécessitent des remplacements fréquents. Évaluez des matériaux plus durables ou une maintenance préventive renforcée.`;
        case 'Maintenance Élevée':
            return `Les ${count} éléments identifiés ont des coûts de maintenance élevés. Une stratégie de maintenance optimisée pourrait réduire les coûts.`;
        case 'Opération Élevée':
            return `Ces ${count} éléments génèrent des coûts d'exploitation importants sur la durée de vie. Considérez des solutions plus économes en énergie.`;
        default:
            return 'Analyse terminée. Consultez les résultats détaillés ci-dessus.';
    }
}

/**
 * Efface les résultats d'analyse affichés
 */
function clearAnalysisResults() {
    const resultsSection = document.getElementById('analysis-results-section');
    if (resultsSection) {
        resultsSection.classList.add('d-none');
    }
    
    // Nettoyer le contenu
    const analysisResults = document.getElementById('analysis-results');
    const analysisSummary = document.getElementById('analysis-summary');
    
    if (analysisResults) analysisResults.innerHTML = '';
    if (analysisSummary) analysisSummary.innerHTML = '';
    
    showNotification('Résultats d\'analyse effacés', 'info');
}

/**
 * Exporte les résultats d'analyse actuels vers Excel
 */
async function exportAnalysisResults() {
    try {
        setLoading(true, 'Export des résultats d\'analyse...');
        
        const response = await fetch('/export-analysis-results');
        const data = await response.json();
        
        if (data.success && data.download_url) {
            // Déclencher le téléchargement
            const link = document.createElement('a');
            link.href = data.download_url;
            link.download = data.filename || 'analyse_results.xlsx';
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            
            showNotification('Export terminé avec succès', 'success');
        } else {
            throw new Error(data.error || 'Erreur lors de l\'export');
        }
    } catch (error) {
        console.error('Erreur export:', error);
        showNotification('Erreur lors de l\'export', 'error');
    } finally {
        setLoading(false);
    }
}

/**
 * Charge la liste des parties prenantes depuis le backend
 */
async function loadStakeholders() {
    try {
        setLoading(true, 'Chargement des parties prenantes...');
        
        const response = await fetch('/api/stakeholders');
        const data = await response.json();
        
        if (data.success) {
            appState.stakeholders = data.stakeholders || [];
            displayStakeholders(appState.stakeholders);
            populateStakeholderSelector(appState.stakeholders);
            showNotification(`${data.count} parties prenantes chargées`, 'success');
        } else {
            throw new Error(data.error || 'Erreur lors du chargement');
        }
    } catch (error) {
        console.error('Erreur loadStakeholders:', error);
        showNotification('Erreur lors du chargement des parties prenantes', 'error');
        
        // Afficher un message d'erreur dans la liste
        const stakeholdersList = document.getElementById('stakeholders-list');
        if (stakeholdersList) {
            stakeholdersList.innerHTML = `
                <div class="alert alert-warning">
                    <i class="fas fa-exclamation-triangle me-2"></i>
                    Erreur lors du chargement des parties prenantes
                </div>
            `;
        }
    } finally {
        setLoading(false);
    }
}

/**
 * Affiche la liste des parties prenantes
 */
function displayStakeholders(stakeholders) {
    const stakeholdersList = document.getElementById('stakeholders-list');
    
    if (!stakeholders || stakeholders.length === 0) {
        stakeholdersList.innerHTML = '<p class="text-muted">Aucune partie prenante créée</p>';
        return;
    }
    
    let html = '<div class="list-group">';
    
    stakeholders.forEach(stakeholder => {
        const typeLabel = getStakeholderTypeLabel(stakeholder.type);
        
        html += `
            <div class="list-group-item">
                <div class="d-flex w-100 justify-content-between align-items-center">
                        <div>
                        <h6 class="mb-1">${stakeholder.name}</h6>
                        <small class="text-muted">${typeLabel}</small>
                    </div>
                    <button class="btn btn-sm btn-outline-danger" onclick="deleteStakeholder('${stakeholder.uri}')">
                        Supprimer
                    </button>
                </div>
            </div>
        `;
    });
    
    html += '</div>';
    stakeholdersList.innerHTML = html;
}

/**
 * Peuple le sélecteur de parties prenantes
 */
function populateStakeholderSelector(stakeholders) {
    const selector = document.getElementById('attribution-stakeholder');
    if (!selector) return;
    
    // Vider les options existantes (sauf la première)
    selector.innerHTML = '<option value="">Sélectionner une partie prenante...</option>';
    
    if (stakeholders && stakeholders.length > 0) {
        stakeholders.forEach(stakeholder => {
            const option = document.createElement('option');
            option.value = stakeholder.uri;
            option.textContent = `${stakeholder.name} (${getStakeholderTypeLabel(stakeholder.type)})`;
            selector.appendChild(option);
        });
    }
}

/**
 * Supprime toutes les parties prenantes
 */
async function deleteAllStakeholders() {
    if (!confirm('Êtes-vous sûr de vouloir supprimer TOUTES les parties prenantes ? Cette action est irréversible.')) {
        return;
    }
    
    try {
        setLoading(true, 'Suppression des parties prenantes...');
        
        const response = await fetch('/api/stakeholders', {
            method: 'DELETE'
        });
        
        const data = await response.json();
        
        if (data.success) {
            appState.stakeholders = [];
            displayStakeholders([]);
            populateStakeholderSelector([]);
            showNotification('Toutes les parties prenantes ont été supprimées', 'success');
        } else {
            throw new Error(data.error || 'Erreur lors de la suppression');
        }
    } catch (error) {
        console.error('Erreur deleteAllStakeholders:', error);
        showNotification('Erreur lors de la suppression', 'error');
    } finally {
        setLoading(false);
    }
}

/**
 * Supprime une partie prenante spécifique
 */
async function deleteStakeholder(stakeholderUri) {
    if (!confirm('Êtes-vous sûr de vouloir supprimer cette partie prenante ?')) {
        return;
    }
    
    try {
        setLoading(true, 'Suppression en cours...');
        
        // Pour l'instant, on supprime juste de l'interface
        // Dans la version complète, on appellerait une route DELETE spécifique
        appState.stakeholders = appState.stakeholders.filter(s => s.uri !== stakeholderUri);
        displayStakeholders(appState.stakeholders);
        populateStakeholderSelector(appState.stakeholders);
        
        showNotification('Partie prenante supprimée', 'success');
    } catch (error) {
        console.error('Erreur deleteStakeholder:', error);
        showNotification('Erreur lors de la suppression', 'error');
    } finally {
        setLoading(false);
    }
}

/**
 * Charge les attributions existantes
 */
async function loadExistingAttributions() {
    try {
        setLoading(true, 'Chargement des attributions...');
        
        const response = await fetch('/api/stakeholder-attributions');
        const data = await response.json();
        
        if (data.success) {
            displayAttributions(data.attributions || []);
            showNotification(`${data.count} attributions chargées`, 'success');
        } else {
            throw new Error(data.error || 'Erreur lors du chargement');
        }
    } catch (error) {
        console.error('Erreur loadExistingAttributions:', error);
        showNotification('Erreur lors du chargement des attributions', 'error');
    } finally {
        setLoading(false);
    }
}

/**
 * Affiche les attributions existantes
 */
function displayAttributions(attributions) {
    const attributionsContainer = document.getElementById('attributions-table');
    if (!attributionsContainer) return;
    
    if (!attributions || attributions.length === 0) {
        attributionsContainer.innerHTML = `
            <div class="alert alert-info">
                <i class="fas fa-info-circle me-2"></i>
                Aucune attribution existante. Créez des parties prenantes puis utilisez l'attribution manuelle ou automatique.
            </div>
        `;
        return;
    }
    
    // Créer le tableau des attributions
    let html = `
        <div class="table-responsive">
            <table class="table table-sm table-hover">
                <thead class="table-dark">
                    <tr>
                        <th>Partie Prenante</th>
                        <th>Élément</th>
                        <th>Types de Coûts</th>
                        <th>Responsabilité</th>
                        <th>Type</th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody>
    `;
    
    attributions.forEach(attr => {
        const costTypesDisplay = attr.cost_types.join(', ');
        const typeDisplay = attr.is_auto ? 
            '<span class="badge bg-info">Auto</span>' : 
            '<span class="badge bg-success">Manuel</span>';
        
        html += `
            <tr>
                <td>
                    <strong>${attr.stakeholder_name}</strong>
                </td>
                <td>
                    <code class="small">${attr.element_description}</code>
                </td>
                <td>
                    <span class="text-primary">${costTypesDisplay}</span>
                </td>
                <td>
                    <span class="badge bg-secondary">${attr.percentage}%</span>
                </td>
                <td>${typeDisplay}</td>
                <td>
                    <button class="btn btn-outline-danger btn-sm" onclick="deleteAttribution('${attr.id}')" title="Supprimer cette attribution">
                        <i class="fas fa-trash"></i>
                    </button>
                </td>
            </tr>
        `;
    });
    
    html += `
                </tbody>
            </table>
        </div>
        
        <div class="mt-3 p-3 bg-light rounded">
            <div class="row text-center">
                <div class="col-md-4">
                    <h6 class="text-primary">${attributions.length}</h6>
                    <small class="text-muted">Attributions groupées</small>
                </div>
                <div class="col-md-4">
                    <h6 class="text-info">${attributions.filter(a => a.is_auto).length}</h6>
                    <small class="text-muted">Automatiques</small>
                </div>
                <div class="col-md-4">
                    <h6 class="text-success">${attributions.filter(a => !a.is_auto).length}</h6>
                    <small class="text-muted">Manuelles</small>
                </div>
            </div>
        </div>
    `;
    
    attributionsContainer.innerHTML = html;
}

/**
 * Supprime une attribution spécifique
 */
async function deleteAttribution(attributionId) {
    if (!confirm('Êtes-vous sûr de vouloir supprimer cette attribution ?')) {
        return;
    }
    
    try {
        setLoading(true, 'Suppression en cours...');
        
        const response = await fetch(`/api/stakeholder-attributions/${attributionId}`, {
            method: 'DELETE'
        });
        
        const data = await response.json();
        
        if (data.success) {
            showNotification('Attribution supprimée', 'success');
            await loadExistingAttributions();
        } else {
            throw new Error(data.error || 'Erreur lors de la suppression');
        }
    } catch (error) {
        console.error('Erreur deleteAttribution:', error);
        showNotification('Erreur lors de la suppression: ' + error.message, 'error');
    } finally {
        setLoading(false);
    }
}

/**
 * Fonctions utilitaires pour les parties prenantes
 */
function getStakeholderTypeLabel(type) {
    const labels = {
        'PropertyOwner': 'Propriétaire',
        'EndUser': 'Utilisateur Final',
        'MaintenanceProvider': 'Prestataire Maintenance',
        'EnergyProvider': 'Fournisseur Énergie'
    };
    return labels[type] || type;
}

function getPriorityLabel(priority) {
    const labels = {
        1: 'Haute',
        2: 'Moyenne', 
        3: 'Basse'
    };
    return labels[priority] || 'Inconnue';
}

function getPriorityBadgeClass(priority) {
    const classes = {
        1: 'bg-danger',
        2: 'bg-warning',
        3: 'bg-secondary'
    };
    return classes[priority] || 'bg-secondary';
}

function getInfluenceProgressClass(influence) {
    if (influence >= 0.7) return 'bg-success';
    if (influence >= 0.4) return 'bg-warning';
    return 'bg-danger';
}

// Configuration des événements pour le formulaire de création de parties prenantes
document.addEventListener('DOMContentLoaded', function() {
    const createStakeholderForm = document.getElementById('create-stakeholder-form');
    if (createStakeholderForm) {
        let isSubmitting = false; // Protection contre les doubles soumissions
        
        createStakeholderForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            // Éviter les doubles soumissions
            if (isSubmitting) {
                console.log('🚫 Soumission en cours, ignorer la nouvelle tentative');
                return;
            }
            
            const formData = {
                type: document.getElementById('stakeholder-type').value,
                name: document.getElementById('stakeholder-name').value.trim()
            };
            
            if (!formData.type || !formData.name) {
                showNotification('Type et nom requis', 'error');
                return;
            }
            
            try {
                isSubmitting = true;
                setLoading(true, 'Création de la partie prenante...');
                
                // Désactiver le bouton de soumission
                const submitBtn = createStakeholderForm.querySelector('button[type="submit"]');
                if (submitBtn) {
                    submitBtn.disabled = true;
                }
                
                const response = await fetch('/api/stakeholders', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(formData)
                });
                
                const data = await response.json();
                
                if (data.success) {
                    showNotification(data.message, 'success');
                    createStakeholderForm.reset();
                    // Recharger la liste
                    await loadStakeholders();
                } else {
                    throw new Error(data.error || 'Erreur lors de la création');
                }
            } catch (error) {
                console.error('Erreur création stakeholder:', error);
                showNotification('Erreur lors de la création: ' + error.message, 'error');
            } finally {
                isSubmitting = false;
                setLoading(false);
                
                // Réactiver le bouton de soumission
                const submitBtn = createStakeholderForm.querySelector('button[type="submit"]');
                if (submitBtn) {
                    submitBtn.disabled = false;
                }
            }
        });
    }
    
    // Gestionnaire pour le formulaire d'attribution des coûts
    const costAttributionForm = document.getElementById('cost-attribution-form');
    if (costAttributionForm) {
        let isAttributing = false;
        
        costAttributionForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            if (isAttributing) {
                console.log('🚫 Attribution en cours, ignorer la nouvelle tentative');
                return;
            }
            
            try {
                isAttributing = true;
                setLoading(true, 'Attribution des coûts en cours...');
                
                // Récupérer les données du formulaire
                const formData = {
                    stakeholder_uri: document.getElementById('attribution-stakeholder').value,
                    percentage: parseFloat(document.getElementById('attribution-percentage').value),
                    selection_mode: document.querySelector('input[name="selection-mode"]:checked').value,
                    cost_types: []
                };
                
                // Récupérer les types de coûts sélectionnés
                if (document.getElementById('attr-construction').checked) formData.cost_types.push('ConstructionCosts');
                if (document.getElementById('attr-operation').checked) formData.cost_types.push('OperationCosts');
                if (document.getElementById('attr-maintenance').checked) formData.cost_types.push('MaintenanceCosts');
                if (document.getElementById('attr-endoflife').checked) formData.cost_types.push('EndOfLifeCosts');
                
                // Validation
                if (!formData.stakeholder_uri) {
                    throw new Error('Veuillez sélectionner une partie prenante');
                }
                
                if (formData.cost_types.length === 0) {
                    throw new Error('Veuillez sélectionner au moins un type de coût');
                }
                
                if (formData.percentage <= 0 || formData.percentage > 100) {
                    throw new Error('Le pourcentage doit être entre 1 et 100');
                }
                
                // Récupérer les éléments selon le mode de sélection
                if (formData.selection_mode === 'selected') {
                    formData.element_guids = getSelectedElementGuids();
                    if (formData.element_guids.length === 0) {
                        throw new Error('Aucun élément sélectionné dans le tableau');
                    }
                } else if (formData.selection_mode === 'uniformat') {
                    formData.uniformat_filter = document.getElementById('attribution-uniformat').value;
                    if (!formData.uniformat_filter) {
                        throw new Error('Veuillez sélectionner un code Uniformat');
                    }
                }
                
                // Envoyer au backend
                const response = await fetch('/api/stakeholder-attributions', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(formData)
                });
                
                const data = await response.json();
                
                if (data.success) {
                    showNotification(data.message, 'success');
                    costAttributionForm.reset();
                    // Recharger les attributions existantes
                    await loadExistingAttributions();
                } else {
                    throw new Error(data.error || 'Erreur lors de l\'attribution');
                }
                
            } catch (error) {
                console.error('Erreur attribution:', error);
                showNotification('Erreur: ' + error.message, 'error');
            } finally {
                isAttributing = false;
                setLoading(false);
            }
        });
    }
});

/**
 * Attribution automatique des coûts selon les règles métier standard
 */
async function autoAssignCosts() {
    if (!confirm('Voulez-vous appliquer l\'attribution automatique selon les règles métier standard ?')) {
        return;
    }
    
    try {
        setLoading(true, 'Attribution automatique en cours...');
        
        const response = await fetch('/api/stakeholder-attributions/auto-assign', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        const data = await response.json();
        
        if (data.success) {
            showNotification(data.message, 'success');
            await loadExistingAttributions();
        } else {
            throw new Error(data.error || 'Erreur lors de l\'attribution automatique');
        }
    } catch (error) {
        console.error('Erreur attribution automatique:', error);
        showNotification('Erreur: ' + error.message, 'error');
    } finally {
        setLoading(false);
    }
}

/**
 * Supprime toutes les attributions
 */
async function deleteAllAttributions() {
    if (!confirm('Êtes-vous sûr de vouloir supprimer toutes les attributions ?')) {
        return;
    }
    
    try {
        setLoading(true, 'Suppression des attributions...');
        
        const response = await fetch('/api/stakeholder-attributions', {
            method: 'DELETE'
        });
        
        const data = await response.json();
        
        if (data.success) {
            showNotification(data.message, 'success');
            await loadExistingAttributions();
        } else {
            throw new Error(data.error || 'Erreur lors de la suppression');
        }
    } catch (error) {
        console.error('Erreur suppression attributions:', error);
        showNotification('Erreur: ' + error.message, 'error');
    } finally {
        setLoading(false);
    }
}

/**
 * Synchronise les valeurs de coûts
 */
async function syncCostValues() {
    try {
        setLoading(true, 'Synchronisation en cours...');
        
        const response = await fetch('/api/stakeholder-attributions/sync', {
            method: 'POST'
        });
        
        const data = await response.json();
        
        if (data.success) {
            showNotification(data.message, 'success');
            await loadExistingAttributions();
        } else {
            throw new Error(data.error || 'Erreur lors de la synchronisation');
        }
    } catch (error) {
        console.error('Erreur synchronisation:', error);
        showNotification('Erreur: ' + error.message, 'error');
    } finally {
        setLoading(false);
    }
}

/**
 * Charge la vue multi-parties prenantes
 */
async function loadMultiStakeholderView() {
    try {
        setLoading(true, 'Chargement de l\'analyse...');
        
        const response = await fetch('/api/stakeholder-analysis/multi-view');
        const data = await response.json();
        
        if (data.success) {
            displayMultiStakeholderView(data);
            showNotification('Analyse chargée', 'success');
        } else {
            throw new Error(data.error || 'Erreur lors du chargement');
        }
    } catch (error) {
        console.error('Erreur loadMultiStakeholderView:', error);
        showNotification('Erreur: ' + error.message, 'error');
        
        // Afficher un message par défaut
        const container = document.getElementById('multi-stakeholder-content');
        if (container) {
            container.innerHTML = `
                <div class="alert alert-warning">
                    <h6>Fonctionnalité en développement</h6>
                    <p>L'analyse multi-parties prenantes sera disponible une fois que des attributions auront été créées.</p>
                </div>
            `;
        }
    } finally {
        setLoading(false);
    }
}

/**
 * Affiche la vue multi-parties prenantes
 */
function displayMultiStakeholderView(data) {
    const container = document.getElementById('multi-stakeholder-content');
    if (!container) return;
    
    if (!data.stakeholders_analysis || Object.keys(data.stakeholders_analysis).length === 0) {
        container.innerHTML = `
            <div class="alert alert-warning">
                <h6>Aucune Attribution Trouvée</h6>
                <p>Créez d'abord des parties prenantes et des attributions pour voir l'analyse d'impact.</p>
                <div class="mt-3">
                    <button class="btn btn-primary btn-sm me-2" onclick="document.getElementById('nav-stakeholders-tab').click()">
                        Gérer les Parties Prenantes
                    </button>
                    <button class="btn btn-success btn-sm" onclick="autoAssignCosts()">
                        Attribution Automatique
                    </button>
                </div>
            </div>
        `;
        return;
    }
    
    // Préparer les données pour l'affichage
    const stakeholders = Object.entries(data.stakeholders_analysis);
    const dominantStakeholder = data.dominant_stakeholder;
    
    // Créer l'interface d'analyse
    container.innerHTML = `
        <!-- Résumé de l'analyse -->
        <div class="row mb-4">
            <div class="col-12">
                <div class="alert alert-info">
                    <div class="row text-center">
                        <div class="col-md-3">
                            <h5 class="text-primary">${data.stakeholders_count}</h5>
                            <small>Parties Prenantes</small>
                        </div>
                        <div class="col-md-3">
                            <h5 class="text-success">${data.attributions_count}</h5>
                            <small>Attributions</small>
                        </div>
                        <div class="col-md-3">
                            <h5 class="text-warning">${data.total_attributed_costs.toLocaleString('en-US', {style: 'currency', currency: 'USD'})}</h5>
                            <small>Coût Total Attribué</small>
                        </div>
                        <div class="col-md-3">
                            <h5 class="text-info">${dominantStakeholder ? dominantStakeholder.name : 'N/A'}</h5>
                            <small>Partie Prenante Dominante</small>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        
        <!-- Graphique de répartition -->
        <div class="row mb-4">
            <div class="col-md-6">
                <div class="card">
                    <div class="card-header">
                        <h6>Répartition des Responsabilités</h6>
                    </div>
                    <div class="card-body">
                        <canvas id="stakeholder-responsibility-chart" width="400" height="300"></canvas>
                    </div>
                </div>
            </div>
            <div class="col-md-6">
                <div class="card">
                    <div class="card-header">
                        <h6>Répartition par Type de Coût</h6>
                    </div>
                    <div class="card-body">
                        <canvas id="cost-type-breakdown-chart" width="400" height="300"></canvas>
                    </div>
                </div>
            </div>
        </div>
        
        <!-- Tableau détaillé des parties prenantes -->
        <div class="row">
            <div class="col-12">
                <div class="card">
                    <div class="card-header">
                        <h6>Détail par Partie Prenante</h6>
                    </div>
                    <div class="card-body">
                        <div class="table-responsive">
                            <table class="table table-hover">
                                <thead class="table-dark">
                                    <tr>
                                        <th>Partie Prenante</th>
                                        <th>Coût Total</th>
                                        <th>Responsabilité</th>
                                        <th>Construction</th>
                                        <th>Opération</th>
                                        <th>Maintenance</th>
                                        <th>Fin de vie</th>
                                        <th>Éléments</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    ${stakeholders.map(([name, data]) => `
                                        <tr onclick="showStakeholderDetails('${name}')" style="cursor: pointer;">
                                            <td><strong>${name}</strong></td>
                                            <td>${data.total_cost.toLocaleString('en-US', {style: 'currency', currency: 'USD'})}</td>
                                            <td>
                                                <div class="d-flex align-items-center">
                                                    <div class="progress flex-grow-1 me-2" style="height: 20px;">
                                                        <div class="progress-bar" style="width: ${data.responsibility_percentage}%">
                                                            ${data.responsibility_percentage.toFixed(1)}%
                                                        </div>
                                                    </div>
                                                </div>
                                            </td>
                                            <td>${data.cost_types.ConstructionCosts.toLocaleString('en-US', {style: 'currency', currency: 'USD'})}</td>
                                            <td>${data.cost_types.OperationCosts.toLocaleString('en-US', {style: 'currency', currency: 'USD'})}</td>
                                            <td>${data.cost_types.MaintenanceCosts.toLocaleString('en-US', {style: 'currency', currency: 'USD'})}</td>
                                            <td>${data.cost_types.EndOfLifeCosts.toLocaleString('en-US', {style: 'currency', currency: 'USD'})}</td>
                                            <td><span class="badge bg-secondary">${data.elements_count}</span></td>
                                        </tr>
                                    `).join('')}
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    // Créer les graphiques après avoir ajouté le HTML
    setTimeout(() => {
        createStakeholderResponsibilityChart(data.stakeholders_analysis);
        createCostTypeBreakdownChart(data.cost_breakdown);
        createStakeholderBreakdownChart(data.stakeholders_analysis);
    }, 100);
}

/**
 * Crée le graphique de répartition des responsabilités
 */
function createStakeholderResponsibilityChart(stakeholdersAnalysis) {
    const ctx = document.getElementById('stakeholder-responsibility-chart');
    if (!ctx) return;
    
    // Détruire le graphique existant
    if (window.stakeholderResponsibilityChart) {
        window.stakeholderResponsibilityChart.destroy();
    }
    
    const stakeholders = Object.entries(stakeholdersAnalysis);
    const labels = stakeholders.map(([name, data]) => name);
    const costs = stakeholders.map(([name, data]) => data.total_cost);
    const percentages = stakeholders.map(([name, data]) => data.responsibility_percentage);
    
    // Couleurs pour chaque partie prenante
    const colors = [
        'rgba(255, 99, 132, 0.8)',
        'rgba(54, 162, 235, 0.8)', 
        'rgba(255, 205, 86, 0.8)',
        'rgba(75, 192, 192, 0.8)',
        'rgba(153, 102, 255, 0.8)',
        'rgba(255, 159, 64, 0.8)'
    ];
    
    window.stakeholderResponsibilityChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: labels,
            datasets: [{
                data: costs,
                backgroundColor: colors.slice(0, labels.length),
                borderColor: colors.slice(0, labels.length).map(color => color.replace('0.8', '1')),
                borderWidth: 2
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                title: {
                    display: true,
                    text: 'Répartition des Coûts par Partie Prenante'
                },
                legend: {
                    position: 'bottom',
                    labels: {
                        generateLabels: function(chart) {
                            const data = chart.data;
                            return data.labels.map((label, i) => {
                                const percentage = percentages[i];
                                const value = data.datasets[0].data[i];
                                return {
                                    text: `${label}: ${percentage.toFixed(1)}% (${value.toLocaleString('en-US', {style: 'currency', currency: 'USD'})})`,
                                    fillStyle: data.datasets[0].backgroundColor[i],
                                    strokeStyle: data.datasets[0].borderColor[i],
                                    lineWidth: data.datasets[0].borderWidth,
                                    hidden: false,
                                    index: i
                                };
                            });
                        }
                    }
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const label = context.label || '';
                            const value = context.parsed || 0;
                            const percentage = percentages[context.dataIndex];
                            return `${label}: ${value.toLocaleString('en-US', {style: 'currency', currency: 'USD'})} (${percentage.toFixed(1)}%)`;
                        }
                    }
                }
            }
        }
    });
}

/**
 * Crée le graphique de répartition par type de coût
 */
function createCostTypeBreakdownChart(costBreakdown) {
    const ctx = document.getElementById('cost-type-breakdown-chart');
    if (!ctx) return;
    
    // Détruire le graphique existant
    if (window.costTypeBreakdownChart) {
        window.costTypeBreakdownChart.destroy();
    }
    
    // Préparer les données
    const costTypes = ['ConstructionCosts', 'OperationCosts', 'MaintenanceCosts', 'EndOfLifeCosts'];
    const costTypeLabels = {
        'ConstructionCosts': 'Construction',
        'OperationCosts': 'Opération',
        'MaintenanceCosts': 'Maintenance',
        'EndOfLifeCosts': 'Fin de vie'
    };
    
    // Récupérer toutes les parties prenantes
    const allStakeholders = new Set();
    Object.values(costBreakdown).forEach(typeData => {
        Object.keys(typeData).forEach(stakeholder => allStakeholders.add(stakeholder));
    });
    
    const stakeholders = Array.from(allStakeholders);
    const datasets = costTypes.map((costType, index) => {
        const data = stakeholders.map(stakeholder => 
            costBreakdown[costType][stakeholder] || 0
        );
        
        const colors = [
            'rgba(40, 167, 69, 0.8)',   // Construction - Vert
            'rgba(13, 110, 253, 0.8)',  // Opération - Bleu
            'rgba(255, 193, 7, 0.8)',   // Maintenance - Jaune
            'rgba(220, 53, 69, 0.8)'    // Fin de vie - Rouge
        ];
        
        return {
            label: costTypeLabels[costType],
            data: data,
            backgroundColor: colors[index],
            borderColor: colors[index].replace('0.8', '1'),
            borderWidth: 1
        };
    });
    
    window.costTypeBreakdownChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: stakeholders,
            datasets: datasets
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                x: {
                    stacked: true,
                    title: {
                        display: true,
                        text: 'Parties Prenantes'
                    }
                },
                y: {
                    stacked: true,
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: 'Coût ($)'
                    },
                    ticks: {
                        callback: function(value) {
                            return new Intl.NumberFormat('en-US', {
                                style: 'currency',
                                currency: 'USD',
                                minimumFractionDigits: 0
                            }).format(value);
                        }
                    }
                }
            },
            plugins: {
                title: {
                    display: true,
                    text: 'Répartition par Type de Coût et Partie Prenante'
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const value = new Intl.NumberFormat('en-US', {
                                style: 'currency',
                                currency: 'USD',
                                minimumFractionDigits: 0
                            }).format(context.parsed.y);
                            return `${context.dataset.label}: ${value}`;
                        }
                    }
                }
            }
        }
    });
}

/**
 * Affiche les détails d'une partie prenante spécifique
 */
function showStakeholderDetails(stakeholderName) {
    const detailsContainer = document.getElementById('stakeholder-analysis-details');
    if (!detailsContainer) return;
    
    detailsContainer.innerHTML = `
        <div class="card border-primary">
            <div class="card-header bg-primary text-white">
                <h6 class="mb-0">${stakeholderName}</h6>
            </div>
            <div class="card-body">
                <p class="text-muted">Analyse détaillée sélectionnée</p>
                <div class="mt-3">
                    <button class="btn btn-outline-primary btn-sm w-100" onclick="loadDetailedStakeholderAnalysis('${stakeholderName}')">
                        Charger l'Analyse Détaillée
                    </button>
                </div>
            </div>
        </div>
    `;
}

/**
 * Charge l'analyse détaillée d'une partie prenante
 */
async function loadDetailedStakeholderAnalysis(stakeholderName) {
    try {
        setLoading(true, `Chargement de l'analyse détaillée pour ${stakeholderName}...`);
        
        // Pour l'instant, afficher un message informatif
        const detailsContainer = document.getElementById('stakeholder-analysis-details');
        if (detailsContainer) {
            detailsContainer.innerHTML = `
                <div class="alert alert-info">
                    <h6>Analyse Détaillée : ${stakeholderName}</h6>
                    <p>Cette fonctionnalité affichera :</p>
                    <ul class="mb-0">
                        <li>Éléments attribués</li>
                        <li>Évolution des coûts</li>
                        <li>Recommandations</li>
                        <li>Comparaisons</li>
                    </ul>
                </div>
            `;
        }
        
        showNotification(`Analyse détaillée pour ${stakeholderName} (en développement)`, 'info');
    } catch (error) {
        console.error('Erreur analyse détaillée:', error);
        showNotification('Erreur lors du chargement de l\'analyse détaillée', 'error');
    } finally {
        setLoading(false);
    }
}

/**
 * Crée le graphique de répartition des impacts pour l'onglet analyse (graphique du bas)
 */
function createStakeholderBreakdownChart(stakeholdersAnalysis) {
    const ctx = document.getElementById('stakeholder-breakdown-chart');
    if (!ctx) return;
    
    // Détruire le graphique existant
    if (window.stakeholderBreakdownChart) {
        window.stakeholderBreakdownChart.destroy();
    }
    
    if (!stakeholdersAnalysis || Object.keys(stakeholdersAnalysis).length === 0) {
        // Afficher un message si pas de données
        ctx.getContext('2d').clearRect(0, 0, ctx.width, ctx.height);
        const context = ctx.getContext('2d');
        context.font = '16px Arial';
        context.fillStyle = '#6c757d';
        context.textAlign = 'center';
        context.fillText('Aucune donnée d\'attribution disponible', ctx.width / 2, ctx.height / 2);
        return;
    }
    
    const stakeholders = Object.entries(stakeholdersAnalysis);
    const costTypes = ['ConstructionCosts', 'OperationCosts', 'MaintenanceCosts', 'EndOfLifeCosts'];
    const costTypeLabels = {
        'ConstructionCosts': 'Construction',
        'OperationCosts': 'Opération', 
        'MaintenanceCosts': 'Maintenance',
        'EndOfLifeCosts': 'Fin de vie'
    };
    
    const colors = [
        'rgba(40, 167, 69, 0.8)',   // Construction - Vert
        'rgba(13, 110, 253, 0.8)',  // Opération - Bleu
        'rgba(255, 193, 7, 0.8)',   // Maintenance - Jaune
        'rgba(220, 53, 69, 0.8)'    // Fin de vie - Rouge
    ];
    
    const datasets = costTypes.map((costType, index) => {
        const data = stakeholders.map(([name, stakeholderData]) => 
            stakeholderData.cost_types[costType] || 0
        );
        
        return {
            label: costTypeLabels[costType],
            data: data,
            backgroundColor: colors[index],
            borderColor: colors[index].replace('0.8', '1'),
            borderWidth: 1
        };
    });
    
    window.stakeholderBreakdownChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: stakeholders.map(([name, data]) => name),
            datasets: datasets
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                x: {
                    stacked: true,
                    title: {
                        display: true,
                        text: 'Parties Prenantes'
                    }
                },
                y: {
                    stacked: true,
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: 'Coût ($)'
                    },
                    ticks: {
                        callback: function(value) {
                            return new Intl.NumberFormat('en-US', {
                                style: 'currency',
                                currency: 'USD',
                                minimumFractionDigits: 0
                            }).format(value);
                        }
                    }
                }
            },
            plugins: {
                title: {
                    display: true,
                    text: 'Répartition des Impacts par Type de Coût'
                },
                legend: {
                    position: 'top'
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const value = new Intl.NumberFormat('en-US', {
                                style: 'currency',
                                currency: 'USD',
                                minimumFractionDigits: 0
                            }).format(context.parsed.y);
                            return `${context.dataset.label}: ${value}`;
                        }
                    }
                }
            }
        }
    });
}

/**
 * Affiche le modal de création d'élément
 */
function showAddElementModal() {
    // Réinitialiser le formulaire
    document.getElementById('addElementForm').reset();
    
    // Générer un GUID automatique si le champ est vide
    const guidInput = document.getElementById('newElementGuid');
    if (!guidInput.value.trim()) {
        guidInput.value = generateGUID();
    }
    
    // Afficher le modal
    const modal = new bootstrap.Modal(document.getElementById('addElementModal'));
    modal.show();
}

/**
 * Génère un GUID au format IFC
 */
function generateGUID() {
    // Générer un UUID et le convertir au format IFC (22 caractères)
    return 'xxxxxxxxxxxxxxxxxxxxxxxx'.replace(/[x]/g, function() {
        return (Math.random() * 36 | 0).toString(36);
    });
}

/**
 * Crée un nouvel élément
 */
async function createElement() {
    console.log('🔧 [DEBUG] Début de createElement()');
    
    try {
        // Récupérer les données du formulaire
        const formData = {
            guid: document.getElementById('newElementGuid').value.trim(),
            ifcClass: document.getElementById('newElementIfcClass').value,
            material: document.getElementById('newElementMaterial').value.trim(),
            uniformatCode: document.getElementById('newElementUniformat').value.trim(),
            description: document.getElementById('newElementDescription').value.trim(),
            lifespan: parseInt(document.getElementById('newElementLifespan').value) || 0,
            constructionCost: parseFloat(document.getElementById('newElementConstructionCost').value) || 0,
            operationCost: parseFloat(document.getElementById('newElementOperationCost').value) || 0,
            maintenanceCost: parseFloat(document.getElementById('newElementMaintenanceCost').value) || 0,
            endOfLifeCost: parseFloat(document.getElementById('newElementEndOfLifeCost').value) || 0
        };
        
        console.log('🔧 [DEBUG] Données du formulaire:', formData);
        
        // Validation côté client
        if (!formData.ifcClass) {
            const message = 'Veuillez sélectionner une classe IFC';
            console.log('❌ [VALIDATION]', message);
            if (window.notifications) {
                notifications.error(message);
            } else {
                alert(message);
            }
            return;
        }
        
        if (!formData.material) {
            const message = 'Veuillez saisir un matériau';
            console.log('❌ [VALIDATION]', message);
            if (window.notifications) {
                notifications.error(message);
            } else {
                alert(message);
            }
            return;
        }
        
        if (!formData.description) {
            const message = 'Veuillez saisir une description';
            console.log('❌ [VALIDATION]', message);
            if (window.notifications) {
                notifications.error(message);
            } else {
                alert(message);
            }
            return;
        }
        
        console.log('✅ [VALIDATION] Toutes les validations passées');
        
        // Afficher le loading
        setLoading(true, 'Création de l\'élément en cours...');
        
        // Construire l'URL (gérer le cas où API_BASE_URL est vide)
        const baseUrl = API_BASE_URL || '';
        const fullUrl = `${baseUrl}/create-element`;
        console.log('🌐 [API] URL de la requête:', fullUrl);
        
        // Envoyer la requête au backend
        const response = await fetch(fullUrl, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(formData)
        });
        
        console.log('🌐 [API] Réponse reçue, status:', response.status);
        
        const result = await response.json();
        console.log('🌐 [API] Données de la réponse:', result);
        
        if (response.ok && result.success) {
            // Succès
            const message = result.message || 'Élément créé avec succès';
            console.log('✅ [SUCCESS]', message);
            
            if (window.notifications) {
                notifications.success(message);
            } else {
                alert(`Succès: ${message}`);
            }
            
            // Fermer le modal
            const modal = bootstrap.Modal.getInstance(document.getElementById('addElementModal'));
            if (modal) {
                modal.hide();
            }
            
            // Recharger la liste des éléments pour afficher le nouvel élément
            console.log('🔄 [RELOAD] Rechargement de la liste des éléments...');
            await loadElements();
            
            // Faire défiler vers le nouvel élément si possible
            if (result.element && result.element.GlobalId) {
                setTimeout(() => {
                    const newRow = document.querySelector(`tr[data-guid="${result.element.UniformatDesc || element.GlobalId}"]`);
                    if (newRow) {
                        newRow.scrollIntoView({ behavior: 'smooth', block: 'center' });
                        newRow.classList.add('table-success');
                        setTimeout(() => newRow.classList.remove('table-success'), 3000);
                        console.log('📍 [UI] Élément mis en évidence dans le tableau');
                    }
                }, 1000);
            }
            
        } else {
            // Erreur
            const message = result.error || 'Erreur lors de la création de l\'élément';
            console.log('❌ [ERROR]', message);
            
            if (window.notifications) {
                notifications.error(message);
            } else {
                alert(`Erreur: ${message}`);
            }
        }
        
    } catch (error) {
        console.error('💥 [EXCEPTION] Erreur lors de la création de l\'élément:', error);
        const message = 'Erreur réseau lors de la création de l\'élément';
        
        if (window.notifications) {
            notifications.error(message);
        } else {
            alert(`Erreur: ${message}`);
        }
    } finally {
        setLoading(false);
        console.log('🔧 [DEBUG] Fin de createElement()');
    }
}

/**
 * Ajoute une nouvelle ligne éditable directement dans le tableau des éléments
 */
function addNewElementRow() {
    console.log('🔧 [DEBUG] Ajout d\'une nouvelle ligne dans le tableau');
    
    const tableBody = document.querySelector('#elements-table tbody');
    if (!tableBody) {
        console.error('❌ Tableau des éléments non trouvé');
        if (window.notifications) {
            notifications.error('Erreur : tableau des éléments non trouvé');
        }
        return;
    }
    
    // Générer un GUID temporaire
    const tempGuid = 'NEW_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
    
    // Créer une nouvelle ligne avec des champs éditables
    const newRow = document.createElement('tr');
    newRow.setAttribute('data-guid', tempGuid);
    newRow.classList.add('table-warning'); // Mettre en évidence la nouvelle ligne
    newRow.innerHTML = `
        <td>
            <input type="checkbox" class="element-checkbox">
        </td>
        <td>
            <input type="text" class="form-control form-control-sm" value="${tempGuid}" 
                   title="GUID temporaire - sera remplacé lors de la sauvegarde" readonly>
        </td>
        <td>
            <select class="form-control form-control-sm ifc-class-select" required>
                <option value="">Sélectionner...</option>
                <option value="IfcWall">IfcWall</option>
                <option value="IfcSlab">IfcSlab</option>
                <option value="IfcBeam">IfcBeam</option>
                <option value="IfcColumn">IfcColumn</option>
                <option value="IfcDoor">IfcDoor</option>
                <option value="IfcWindow">IfcWindow</option>
                <option value="IfcRoof">IfcRoof</option>
                <option value="IfcStair">IfcStair</option>
                <option value="IfcRailing">IfcRailing</option>
                <option value="IfcCovering">IfcCovering</option>
                <option value="IfcFurnishingElement">IfcFurnishingElement</option>
                <option value="IfcBuildingElementProxy">IfcBuildingElementProxy</option>
                <option value="IfcFlowTerminal">IfcFlowTerminal</option>
                <option value="IfcFlowSegment">IfcFlowSegment</option>
                <option value="IfcFlowFitting">IfcFlowFitting</option>
                <option value="IfcEnergyConversionDevice">IfcEnergyConversionDevice</option>
                <option value="IfcFlowMovingDevice">IfcFlowMovingDevice</option>
                <option value="IfcFlowStorageDevice">IfcFlowStorageDevice</option>
                <option value="IfcFlowTreatmentDevice">IfcFlowTreatmentDevice</option>
                <option value="IfcDistributionControlElement">IfcDistributionControlElement</option>
                <option value="IfcElectricalElement">IfcElectricalElement</option>
            </select>
        </td>
        <td>
            <input type="text" class="form-control form-control-sm uniformat-input" 
                   placeholder="Ex: B1010, D3020...">
        </td>
        <td>
            <input type="text" class="form-control form-control-sm description-input" 
                   placeholder="Description de l'élément" required>
        </td>
        <td>
            <input type="text" class="form-control form-control-sm material-input" 
                   placeholder="Matériau" required>
        </td>
        <td>
            <input type="number" class="form-control form-control-sm cost-input" 
                   data-cost-type="construction" min="0" step="0.01" placeholder="0.00">
        </td>
        <td>
            <input type="number" class="form-control form-control-sm cost-input" 
                   data-cost-type="operation" min="0" step="0.01" placeholder="0.00">
        </td>
        <td>
            <input type="number" class="form-control form-control-sm cost-input" 
                   data-cost-type="maintenance" min="0" step="0.01" placeholder="0.00">
        </td>
        <td>
            <input type="number" class="form-control form-control-sm cost-input" 
                   data-cost-type="endoflife" min="0" step="0.01" placeholder="0.00">
        </td>
        <td>
            <select class="form-control form-control-sm strategy-select" 
                    data-guid="${element.UniformatDesc || element.GlobalId}">
                <option value="">Choisir...</option>
                <!-- Options chargées dynamiquement -->
            </select>
        </td>
        <td>
            <input type="number" class="form-control form-control-sm lifespan-input" 
                   value="${element.Lifespan || ''}" 
                   data-guid="${element.UniformatDesc || element.GlobalId}"
                   min="1" max="200">
        </td>
        <td>
            <div class="input-group">
                <input type="number" class="form-control form-control-sm lifespan-input" 
                       min="1" max="200" placeholder="50">
                <div class="input-group-append">
                    <button class="btn btn-success btn-sm save-new-element" type="button" 
                            onclick="saveNewElement('${tempGuid}')" title="Sauvegarder l'élément">
                        <i class="fas fa-save"></i>
                    </button>
                    <button class="btn btn-danger btn-sm cancel-new-element" type="button" 
                            onclick="cancelNewElement('${tempGuid}')" title="Annuler">
                        <i class="fas fa-times"></i>
                    </button>
                </div>
            </div>
        </td>
    `;
    
    // Ajouter la ligne au début du tableau
    tableBody.insertBefore(newRow, tableBody.firstChild);
    
    // Faire défiler vers la nouvelle ligne
    newRow.scrollIntoView({ behavior: 'smooth', block: 'center' });
    
    // Mettre le focus sur le premier champ éditable
    const firstInput = newRow.querySelector('.ifc-class-select');
    if (firstInput) {
        firstInput.focus();
    }
    
    console.log('✅ Nouvelle ligne ajoutée avec GUID temporaire:', tempGuid);
    
    if (window.notifications) {
        notifications.info('Nouvelle ligne ajoutée. Remplissez les champs et cliquez sur le bouton sauvegarder.');
    }
}

/**
 * Sauvegarde un nouvel élément depuis une ligne du tableau
 */
async function saveNewElement(tempGuid) {
    console.log('🔧 [DEBUG] Sauvegarde du nouvel élément:', tempGuid);
    
    const row = document.querySelector(`tr[data-guid="${tempGuid}"]`);
    if (!row) {
        console.error('❌ Ligne non trouvée:', tempGuid);
        return;
    }
    
    try {
        // Récupérer les données de la ligne
        const ifcClass = row.querySelector('.ifc-class-select').value;
        const uniformatCode = row.querySelector('.uniformat-input').value.trim();
        const description = row.querySelector('.description-input').value.trim();
        const material = row.querySelector('.material-input').value.trim();
        const lifespan = parseInt(row.querySelector('.lifespan-input').value) || 0;
        
        const constructionCost = parseFloat(row.querySelector('.cost-input[data-cost-type="construction"]').value) || 0;
        const operationCost = parseFloat(row.querySelector('.cost-input[data-cost-type="operation"]').value) || 0;
        const maintenanceCost = parseFloat(row.querySelector('.cost-input[data-cost-type="maintenance"]').value) || 0;
        const endOfLifeCost = parseFloat(row.querySelector('.cost-input[data-cost-type="endoflife"]').value) || 0;
        
        // Validation
        if (!ifcClass) {
            if (window.notifications) {
                notifications.error('Veuillez sélectionner une classe IFC');
            }
            row.querySelector('.ifc-class-select').focus();
            return;
        }
        
        if (!description) {
            if (window.notifications) {
                notifications.error('Veuillez saisir une description');
            }
            row.querySelector('.description-input').focus();
            return;
        }
        
        if (!material) {
            if (window.notifications) {
                notifications.error('Veuillez saisir un matériau');
            }
            row.querySelector('.material-input').focus();
            return;
        }
        
        // Préparer les données pour l'API
        const formData = {
            guid: '', // Sera généré par le backend
            ifcClass: ifcClass,
            material: material,
            uniformatCode: uniformatCode,
            description: description,
            lifespan: lifespan,
            constructionCost: constructionCost,
            operationCost: operationCost,
            maintenanceCost: maintenanceCost,
            endOfLifeCost: endOfLifeCost
        };
        
        console.log('🔧 [DEBUG] Données à envoyer:', formData);
        
        // Désactiver les boutons pendant la sauvegarde
        const saveBtn = row.querySelector('.save-new-element');
        const cancelBtn = row.querySelector('.cancel-new-element');
        saveBtn.disabled = true;
        cancelBtn.disabled = true;
        saveBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
        
        // Construire l'URL
        const baseUrl = API_BASE_URL || '';
        const fullUrl = `${baseUrl}/create-element`;
        
        // Envoyer la requête
        const response = await fetch(fullUrl, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(formData)
        });
        
        const result = await response.json();
        console.log('🌐 [API] Réponse:', result);
        
        if (response.ok && result.success) {
            // Succès - remplacer la ligne temporaire par une ligne normale
            const newGuid = result.element.GlobalId;
            console.log('✅ Élément créé avec succès, nouveau GUID:', newGuid);
            
            // Supprimer la ligne temporaire
            row.remove();
            
            // Recharger la liste des éléments pour afficher le nouvel élément correctement
            await loadElements();
            
            // Mettre en évidence le nouvel élément
            setTimeout(() => {
                const newRow = document.querySelector(`tr[data-guid="${newGuid}"]`);
                if (newRow) {
                    newRow.scrollIntoView({ behavior: 'smooth', block: 'center' });
                    newRow.classList.add('table-success');
                    setTimeout(() => newRow.classList.remove('table-success'), 3000);
                }
            }, 500);
            
            if (window.notifications) {
                notifications.success(`Élément créé avec succès (${newGuid})`);
            }
            
        } else {
            // Erreur
            console.error('❌ Erreur lors de la création:', result.error);
            if (window.notifications) {
                notifications.error(result.error || 'Erreur lors de la création de l\'élément');
            }
            
            // Réactiver les boutons
            saveBtn.disabled = false;
            cancelBtn.disabled = false;
            saveBtn.innerHTML = '<i class="fas fa-save"></i>';
        }
        
    } catch (error) {
        console.error('💥 [EXCEPTION] Erreur lors de la sauvegarde:', error);
        
        if (window.notifications) {
            notifications.error('Erreur réseau lors de la sauvegarde');
        }
        
        // Réactiver les boutons
        const saveBtn = row.querySelector('.save-new-element');
        const cancelBtn = row.querySelector('.cancel-new-element');
        if (saveBtn && cancelBtn) {
            saveBtn.disabled = false;
            cancelBtn.disabled = false;
            saveBtn.innerHTML = '<i class="fas fa-save"></i>';
        }
    }
}

/**
 * Annule la création d'un nouvel élément
 */
function cancelNewElement(tempGuid) {
    console.log('🔧 [DEBUG] Annulation de la création:', tempGuid);
    
    const row = document.querySelector(`tr[data-guid="${tempGuid}"]`);
    if (row) {
        row.remove();
        console.log('✅ Ligne temporaire supprimée');
        
        if (window.notifications) {
            notifications.info('Création d\'élément annulée');
        }
    }
}

/**
 * Génère un GUID au format IFC
 */
function generateGUID() {
    // Générer un UUID et le convertir au format IFC (22 caractères)
    return 'xxxxxxxxxxxxxxxxxxxxxxxx'.replace(/[x]/g, function() {
        return (Math.random() * 36 | 0).toString(36);
    });
}

// ================================
// GESTION DES STRATÉGIES DE FIN DE VIE
// ================================

/**
 * Variable globale pour stocker les stratégies disponibles
 */
let availableStrategies = [];

/**
 * Charge les stratégies de fin de vie disponibles
 */
async function loadEndOfLifeStrategies() {
    try {
        const response = await fetch(`${API_BASE_URL}/get-end-of-life-strategies`);
        const data = await response.json();
        
        if (data.strategies) {
            availableStrategies = data.strategies;
            populateStrategySelects();
            populateBulkStrategySelect();
        }
    } catch (error) {
        console.error('Erreur lors du chargement des stratégies:', error);
    }
}

/**
 * Remplit tous les selects de stratégie avec les options disponibles
 */
function populateStrategySelects() {
    const strategySelects = document.querySelectorAll('.strategy-select');
    
    strategySelects.forEach(select => {
        const currentValue = select.value;
        const currentElement = allElements.find(el => el.GlobalId === select.dataset.guid);
        
        // Vider le select
        select.innerHTML = '<option value="">Choisir...</option>';
        
        // Ajouter les options
        availableStrategies.forEach(strategy => {
            const option = document.createElement('option');
            option.value = strategy.value;
            option.textContent = strategy.label;
            select.appendChild(option);
        });
        
        // Restaurer la valeur actuelle ou celle de l'élément
        if (currentElement && currentElement.EndOfLifeStrategy) {
            select.value = currentElement.EndOfLifeStrategy;
        } else if (currentValue) {
            select.value = currentValue;
        }
        
        // Ajouter l'event listener s'il n'existe pas déjà
        if (!select.hasAttribute('data-listener-added')) {
            select.addEventListener('change', handleStrategyChange);
            select.setAttribute('data-listener-added', 'true');
        }
    });
}

/**
 * Remplit le select de gestion en lot
 */
function populateBulkStrategySelect() {
    const bulkSelect = document.getElementById('bulk-strategy-select');
    if (bulkSelect) {
        bulkSelect.innerHTML = '<option value="">Choisir une stratégie...</option>';
        
        availableStrategies.forEach(strategy => {
            const option = document.createElement('option');
            option.value = strategy.value;
            option.textContent = strategy.label;
            bulkSelect.appendChild(option);
        });
        
        // Event listener pour activer/désactiver le bouton
        bulkSelect.addEventListener('change', function() {
            const applyBtn = document.getElementById('apply-bulk-strategy-btn');
            if (applyBtn) {
                applyBtn.disabled = !this.value || selectedGuids.size === 0;
            }
        });
    }
}

/**
 * Gère le changement de stratégie d'un élément
 */
async function handleStrategyChange(event) {
    const select = event.target;
    const guid = select.dataset.guid;
    const strategy = select.value;
    
    if (!guid) return;
    
    try {
        // Afficher un indicateur de chargement
        const originalBg = select.style.backgroundColor;
        select.style.backgroundColor = '#fff3cd';
        select.disabled = true;
        
        const response = await fetch(`${API_BASE_URL}/update-end-of-life-strategy`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                guid: guid,
                strategy: strategy
            })
        });
        
        const result = await response.json();
        
        if (result.success) {
            // Mettre à jour l'élément dans allElements
            const elementIndex = allElements.findIndex(el => el.GlobalId === guid);
            if (elementIndex !== -1) {
                allElements[elementIndex].EndOfLifeStrategy = strategy;
            }
            
            // Succès visual feedback
            select.style.backgroundColor = '#d1edff';
            setTimeout(() => {
                select.style.backgroundColor = originalBg;
            }, 1000);
            
            // Mettre à jour les statistiques
            await updateEndOfLifeStatistics();
            
        } else {
            notifications.error(`Erreur: ${result.error}`);
            // Remettre l'ancienne valeur
            const element = allElements.find(el => el.GlobalId === guid);
            select.value = element ? element.EndOfLifeStrategy || '' : '';
        }
        
    } catch (error) {
        console.error('Erreur lors de la mise à jour de la stratégie:', error);
        notifications.error('Erreur lors de la mise à jour de la stratégie');
        
        // Remettre l'ancienne valeur
        const element = allElements.find(el => el.GlobalId === guid);
        select.value = element ? element.EndOfLifeStrategy || '' : '';
        
    } finally {
        select.style.backgroundColor = originalBg;
        select.disabled = false;
    }
}

/**
 * Applique une stratégie en lot aux éléments sélectionnés
 */
async function applyBulkStrategy() {
    const strategy = document.getElementById('bulk-strategy-select').value;
    
    if (!strategy) {
        notifications.warning('Veuillez sélectionner une stratégie');
        return;
    }
    
    if (selectedGuids.size === 0) {
        notifications.warning('Veuillez sélectionner des éléments');
        return;
    }
    
    const guids = Array.from(selectedGuids);
    const strategyLabel = availableStrategies.find(s => s.value === strategy)?.label || strategy;
    
    if (!confirm(`Appliquer la stratégie "${strategyLabel}" à ${guids.length} éléments sélectionnés ?`)) {
        return;
    }
    
    try {
        // Désactiver le bouton
        const applyBtn = document.getElementById('apply-bulk-strategy-btn');
        const originalText = applyBtn.textContent;
        applyBtn.disabled = true;
        applyBtn.textContent = 'Application...';
        
        const response = await fetch(`${API_BASE_URL}/update-group-end-of-life-strategy`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                guids: guids,
                strategy: strategy
            })
        });
        
        const result = await response.json();
        
        if (result.success) {
            // Mettre à jour les éléments dans allElements
            guids.forEach(guid => {
                const elementIndex = allElements.findIndex(el => el.GlobalId === guid);
                if (elementIndex !== -1) {
                    allElements[elementIndex].EndOfLifeStrategy = strategy;
                }
                
                // Mettre à jour le select dans l'interface
                const select = document.querySelector(`.strategy-select[data-guid="${guid}"]`);
                if (select) {
                    select.value = strategy;
                }
            });
            
            notifications.success(`Stratégie "${strategyLabel}" appliquée à ${guids.length} éléments`);
            
            // Mettre à jour les statistiques
            await updateEndOfLifeStatistics();
            
        } else {
            notifications.error(`Erreur: ${result.error}`);
        }
        
    } catch (error) {
        console.error('Erreur lors de l\'application en lot:', error);
        notifications.error('Erreur lors de l\'application en lot');
        
    } finally {
        // Réactiver le bouton
        const applyBtn = document.getElementById('apply-bulk-strategy-btn');
        applyBtn.disabled = false;
        applyBtn.textContent = originalText;
    }
}

/**
 * Met à jour les statistiques de fin de vie
 */
async function updateEndOfLifeStatistics() {
    try {
        const response = await fetch(`${API_BASE_URL}/get-end-of-life-statistics`);
        const data = await response.json();
        
        if (data.error) {
            console.error('Erreur statistiques:', data.error);
            return;
        }
        
        // Mettre à jour les indicateurs principaux
        document.getElementById('recyclability-percent').textContent = `${data.recyclability_percent}%`;
        document.getElementById('total-with-strategy').textContent = `${data.total_with_strategy}/${data.total_elements}`;
        
        // Mettre à jour la répartition des stratégies
        const breakdownDiv = document.getElementById('strategy-breakdown');
        if (breakdownDiv) {
            breakdownDiv.innerHTML = '';
            
            if (data.statistics && data.statistics.length > 0) {
                data.statistics.forEach(stat => {
                    const col = document.createElement('div');
                    col.className = 'col-md-2 col-sm-4 col-6 mb-2';
                    col.innerHTML = `
                        <div class="text-center">
                            <span class="badge bg-light text-dark">${stat.strategy}</span>
                            <div class="small">${stat.count} (${stat.percentage.toFixed(1)}%)</div>
                        </div>
                    `;
                    breakdownDiv.appendChild(col);
                });
            } else {
                breakdownDiv.innerHTML = '<div class="col-12 text-center text-muted">Aucune stratégie assignée</div>';
            }
        }
        
        // Activer/désactiver le bouton de gestion en lot
        const applyBtn = document.getElementById('apply-bulk-strategy-btn');
        const bulkSelect = document.getElementById('bulk-strategy-select');
        if (applyBtn && bulkSelect) {
            applyBtn.disabled = !bulkSelect.value || selectedGuids.size === 0;
        }
        
    } catch (error) {
        console.error('Erreur lors de la mise à jour des statistiques:', error);
    }
}

/**
 * Initialise les fonctionnalités de fin de vie
 */
async function initializeEndOfLifeFeatures() {
    console.log('🔄 Initialisation des fonctionnalités de fin de vie...');
    
    // Charger les stratégies
    await loadEndOfLifeStrategies();
    
    // Mettre à jour les statistiques
    await updateEndOfLifeStatistics();
    
    console.log('✅ Fonctionnalités de fin de vie initialisées');
}

// Initialiser les fonctionnalités au chargement de la page
document.addEventListener('DOMContentLoaded', function() {
    // Attendre un peu que les autres éléments soient chargés
    setTimeout(initializeEndOfLifeFeatures, 1000);
});

// Mettre à jour les statistiques quand la sélection change
function updateSelectionCount() {
    const checkboxes = document.querySelectorAll('.element-checkbox:checked');
    selectedGuids.clear();
    
    checkboxes.forEach(checkbox => {
        if (checkbox.dataset.guid) {
            selectedGuids.add(checkbox.dataset.guid);
        }
    });
    
    document.getElementById('selection-count').textContent = `${selectedGuids.size} sélectionné(s)`;
    
    // Mettre à jour les boutons qui dépendent de la sélection
    const applyBtn = document.getElementById('apply-bulk-strategy-btn');
    const bulkSelect = document.getElementById('bulk-strategy-select');
    if (applyBtn && bulkSelect) {
        applyBtn.disabled = !bulkSelect.value || selectedGuids.size === 0;
    }
    
    updateBulkApplyButton();
}

// ================================
// ONGLET GESTION FIN DE VIE
// ================================

/**
 * Variables globales pour l'onglet EOL
 */
let eolElements = [];
let selectedEOLGuids = new Set();
let availableResponsibles = [];

/**
 * Charge les données pour l'onglet Gestion Fin de Vie
 */
async function loadEOLManagementData() {
    try {
        console.log('🔄 Chargement des données EOL...');
        
        // Charger les données des éléments
        const response = await fetch(`${API_BASE_URL}/get-eol-management-data`);
        const data = await response.json();
        
        if (data.error) {
            console.error('Erreur lors du chargement EOL:', data.error);
            return;
        }
        
        eolElements = data.elements || [];
        console.log(`✅ ${eolElements.length} éléments EOL chargés`);
        
        // Afficher les données
        displayEOLTable(eolElements);
        updateEOLStatistics();
        
    } catch (error) {
        console.error('Erreur lors du chargement EOL:', error);
        notifications.error('Erreur lors du chargement des données EOL');
    }
}

/**
 * Affiche le tableau des données EOL
 */
function displayEOLTable(elements) {
    const tableBody = document.querySelector('#eol-table tbody');
    if (!tableBody) return;
    
    tableBody.innerHTML = '';
    
    elements.forEach(element => {
        const row = document.createElement('tr');
        row.dataset.guid = element.GlobalId;
        
        row.innerHTML = `
            <td>
                <input type="checkbox" class="eol-checkbox" data-guid="${element.UniformatDesc || element.GlobalId}" 
                       onchange="updateEOLSelectionCount()">
            </td>
            <td>
                <div class="fw-bold">${element.UniformatDesc || element.GlobalId}</div>
                <small class="text-muted">${element.GlobalId}</small>
            </td>
            <td>
                <select class="form-select form-select-sm eol-strategy-select" 
                        data-guid="${element.UniformatDesc || element.GlobalId}">
                    <option value="">Choisir...</option>
                    <!-- Options chargées dynamiquement -->
                </select>
            </td>
            <td>
                <input type="text" class="form-control form-control-sm eol-destination-input" 
                       value="${element.Destination || ''}" 
                       data-guid="${element.UniformatDesc || element.GlobalId}"
                       placeholder="Centre de traitement">
            </td>
            <td>
                <select class="form-select form-select-sm eol-responsible-select" 
                        data-guid="${element.UniformatDesc || element.GlobalId}">
                    <option value="">Choisir...</option>
                    <!-- Options chargées dynamiquement -->
                </select>
            </td>
            <td>
                <div class="input-group input-group-sm">
                    <input type="number" class="form-control eol-cost-input" 
                           value="${element.Cost || ''}" 
                           data-guid="${element.UniformatDesc || element.GlobalId}"
                           min="0" step="0.01" placeholder="0.00">
                    <span class="input-group-text">€</span>
                </div>
            </td>
        `;
        
        tableBody.appendChild(row);
    });
    
    // Ajouter les event listeners
    setupEOLEventListeners();
    
    // Peupler les selects
    populateEOLStrategies();
    loadEOLResponsibles();
}

/**
 * Configure les event listeners pour l'onglet EOL
 */
function setupEOLEventListeners() {
    // Strategy selects
    document.querySelectorAll('.eol-strategy-select').forEach(select => {
        select.addEventListener('change', handleEOLStrategyChange);
    });
    
    // Destination inputs
    document.querySelectorAll('.eol-destination-input').forEach(input => {
        input.addEventListener('blur', handleEOLDestinationChange);
    });
    
    // Responsible selects
    document.querySelectorAll('.eol-responsible-select').forEach(select => {
        select.addEventListener('change', handleEOLResponsibleChange);
    });
    
    // Cost inputs
    document.querySelectorAll('.eol-cost-input').forEach(input => {
        input.addEventListener('blur', handleEOLCostChange);
    });
    
    // Select all checkbox
    const selectAllCheckbox = document.getElementById('select-all-eol-checkbox');
    if (selectAllCheckbox) {
        selectAllCheckbox.addEventListener('change', function() {
            const checkboxes = document.querySelectorAll('.eol-checkbox');
            checkboxes.forEach(cb => {
                cb.checked = this.checked;
            });
            updateEOLSelectionCount();
        });
    }
}

/**
 * Gère le changement de stratégie EOL
 */
async function handleEOLStrategyChange(event) {
    const select = event.target;
    const guid = select.dataset.guid;
    const strategy = select.value;
    
    try {
        const response = await fetch(`${API_BASE_URL}/update-end-of-life-strategy`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ guid, strategy })
        });
        
        const result = await response.json();
        if (result.success) {
            // Mettre à jour l'élément local
            const elementIndex = eolElements.findIndex(el => el.GlobalId === guid);
            if (elementIndex !== -1) {
                eolElements[elementIndex].Strategy = strategy;
            }
            
            select.style.backgroundColor = '#d1edff';
            setTimeout(() => {
                select.style.backgroundColor = '';
            }, 1000);
            
            updateEOLStatistics();
        } else {
            notifications.error(`Erreur: ${result.error}`);
        }
    } catch (error) {
        console.error('Erreur stratégie EOL:', error);
        notifications.error('Erreur lors de la mise à jour de la stratégie');
    }
}

/**
 * Gère le changement de destination EOL
 */
async function handleEOLDestinationChange(event) {
    const input = event.target;
    const guid = input.dataset.guid;
    const destination = input.value.trim();
    
    try {
        const response = await fetch(`${API_BASE_URL}/update-eol-destination`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ guid, destination })
        });
        
        const result = await response.json();
        if (result.success) {
            // Mettre à jour l'élément local
            const elementIndex = eolElements.findIndex(el => el.GlobalId === guid);
            if (elementIndex !== -1) {
                eolElements[elementIndex].Destination = destination;
            }
            
            input.style.backgroundColor = '#d1edff';
            setTimeout(() => {
                input.style.backgroundColor = '';
            }, 1000);
            
            updateEOLStatistics();
        } else {
            notifications.error(`Erreur: ${result.error}`);
        }
    } catch (error) {
        console.error('Erreur destination EOL:', error);
        notifications.error('Erreur lors de la mise à jour de la destination');
    }
}

/**
 * Gère le changement de responsable EOL
 */
async function handleEOLResponsibleChange(event) {
    const select = event.target;
    const guid = select.dataset.guid;
    const responsible = select.value;
    
    try {
        const response = await fetch(`${API_BASE_URL}/update-eol-responsible`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ guid, responsible })
        });
        
        const result = await response.json();
        if (result.success) {
            // Mettre à jour l'élément local
            const elementIndex = eolElements.findIndex(el => el.GlobalId === guid);
            if (elementIndex !== -1) {
                eolElements[elementIndex].Responsible = responsible;
            }
            
            select.style.backgroundColor = '#d1edff';
            setTimeout(() => {
                select.style.backgroundColor = '';
            }, 1000);
            
            updateEOLStatistics();
        } else {
            notifications.error(`Erreur: ${result.error}`);
        }
    } catch (error) {
        console.error('Erreur responsable EOL:', error);
        notifications.error('Erreur lors de la mise à jour du responsable');
    }
}

/**
 * Gère le changement de coût EOL
 */
async function handleEOLCostChange(event) {
    const input = event.target;
    const guid = input.dataset.guid;
    const cost = parseFloat(input.value) || 0;
    
    try {
        // Utiliser la route existante de mise à jour des coûts
        const response = await fetch(`${API_BASE_URL}/update-costs`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                guid,
                phase: 'EndOfLifeCosts',
                cost: cost
            })
        });
        
        const result = await response.json();
        if (result.success) {
            // Mettre à jour l'élément local
            const elementIndex = eolElements.findIndex(el => el.GlobalId === guid);
            if (elementIndex !== -1) {
                eolElements[elementIndex].Cost = cost;
            }
            
            input.style.backgroundColor = '#d1edff';
            setTimeout(() => {
                input.style.backgroundColor = '';
            }, 1000);
            
            updateEOLStatistics();
        } else {
            notifications.error(`Erreur: ${result.error}`);
        }
    } catch (error) {
        console.error('Erreur coût EOL:', error);
        notifications.error('Erreur lors de la mise à jour du coût');
    }
}

/**
 * Peuple les selects de stratégies EOL
 */
function populateEOLStrategies() {
    const strategySelects = document.querySelectorAll('.eol-strategy-select, #bulk-eol-strategy');
    
    strategySelects.forEach(select => {
        const currentValue = select.value;
        const currentGuid = select.dataset.guid;
        
        // Vider et repeupler
        select.innerHTML = '<option value="">Choisir...</option>';
        
        availableStrategies.forEach(strategy => {
            const option = document.createElement('option');
            option.value = strategy.value;
            option.textContent = strategy.label;
            select.appendChild(option);
        });
        
        // Restaurer la valeur si c'est un select d'élément
        if (currentGuid) {
            const element = eolElements.find(el => el.GlobalId === currentGuid);
            if (element && element.Strategy) {
                select.value = element.Strategy;
            }
        } else if (currentValue) {
            select.value = currentValue;
        }
    });
}

/**
 * Charge la liste des responsables disponibles
 */
async function loadEOLResponsibles() {
    try {
        const response = await fetch(`${API_BASE_URL}/get-eol-responsibles`);
        const data = await response.json();
        
        if (data.responsibles) {
            availableResponsibles = data.responsibles;
            populateEOLResponsibles();
        }
    } catch (error) {
        console.error('Erreur lors du chargement des responsables:', error);
    }
}

/**
 * Peuple les selects de responsables
 */
function populateEOLResponsibles() {
    const responsibleSelects = document.querySelectorAll('.eol-responsible-select, #bulk-eol-responsible');
    
    responsibleSelects.forEach(select => {
        const currentValue = select.value;
        const currentGuid = select.dataset.guid;
        
        // Vider et repeupler
        select.innerHTML = '<option value="">Choisir...</option>';
        
        availableResponsibles.forEach(responsible => {
            const option = document.createElement('option');
            option.value = responsible;
            option.textContent = responsible;
            select.appendChild(option);
        });
        
        // Restaurer la valeur si c'est un select d'élément
        if (currentGuid) {
            const element = eolElements.find(el => el.GlobalId === currentGuid);
            if (element && element.Responsible) {
                select.value = element.Responsible;
            }
        } else if (currentValue) {
            select.value = currentValue;
        }
    });
}

/**
 * Met à jour le compteur de sélection EOL
 */
function updateEOLSelectionCount() {
    const checkboxes = document.querySelectorAll('.eol-checkbox:checked');
    selectedEOLGuids.clear();
    
    checkboxes.forEach(checkbox => {
        if (checkbox.dataset.guid) {
            selectedEOLGuids.add(checkbox.dataset.guid);
        }
    });
    
    const countElement = document.getElementById('eol-selection-count');
    if (countElement) {
        countElement.textContent = `${selectedEOLGuids.size} sélectionné(s)`;
    }
    
    // Activer/désactiver le bouton d'application en lot
    const applyBtn = document.getElementById('apply-bulk-eol-btn');
    if (applyBtn) {
        applyBtn.disabled = selectedEOLGuids.size === 0;
    }
}

/**
 * Applique les données EOL en lot
 */
async function applyBulkEOL() {
    const strategy = document.getElementById('bulk-eol-strategy').value;
    const destination = document.getElementById('bulk-eol-destination').value.trim();
    const responsible = document.getElementById('bulk-eol-responsible').value;
    
    if (!strategy && !destination && !responsible) {
        notifications.warning('Veuillez renseigner au moins un champ');
        return;
    }
    
    if (selectedEOLGuids.size === 0) {
        notifications.warning('Veuillez sélectionner des éléments');
        return;
    }
    
    const guids = Array.from(selectedEOLGuids);
    
    if (!confirm(`Appliquer ces modifications à ${guids.length} éléments sélectionnés ?`)) {
        return;
    }
    
    try {
        const applyBtn = document.getElementById('apply-bulk-eol-btn');
        const originalText = applyBtn.textContent;
        applyBtn.disabled = true;
        applyBtn.textContent = 'Application...';
        
        const response = await fetch(`${API_BASE_URL}/update-bulk-eol-data`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                guids,
                strategy,
                destination,
                responsible
            })
        });
        
        const result = await response.json();
        
        if (result.success) {
            notifications.success(`Données appliquées à ${guids.length} éléments`);
            
            // Actualiser les données
            await loadEOLManagementData();
            
            // Réinitialiser les champs
            document.getElementById('bulk-eol-strategy').value = '';
            document.getElementById('bulk-eol-destination').value = '';
            document.getElementById('bulk-eol-responsible').value = '';
            
        } else {
            notifications.error(`Erreur: ${result.error}`);
        }
        
    } catch (error) {
        console.error('Erreur application en lot EOL:', error);
        notifications.error('Erreur lors de l\'application en lot');
        
    } finally {
        const applyBtn = document.getElementById('apply-bulk-eol-btn');
        applyBtn.disabled = false;
        applyBtn.textContent = originalText;
    }
}

/**
 * Met à jour les statistiques EOL
 */
function updateEOLStatistics() {
    if (!eolElements.length) return;
    
    // Calculer les statistiques
    const totalElements = eolElements.length;
    const elementsWithStrategy = eolElements.filter(el => el.Strategy).length;
    const totalCost = eolElements.reduce((sum, el) => sum + (el.Cost || 0), 0);
    const uniqueDestinations = new Set(eolElements.filter(el => el.Destination).map(el => el.Destination)).size;
    
    // Recyclabilité (stratégies circulaires)
    const recyclableStrategies = ['Recycle', 'Reuse', 'Repurpose'];
    const recyclableElements = eolElements.filter(el => recyclableStrategies.includes(el.Strategy)).length;
    const recyclabilityPercent = totalElements > 0 ? (recyclableElements / totalElements * 100) : 0;
    
    // Mettre à jour l'affichage
    const recyclabilityEl = document.getElementById('eol-recyclability-percent');
    const totalElementsEl = document.getElementById('eol-total-elements');
    const totalCostEl = document.getElementById('eol-total-cost');
    const destinationsEl = document.getElementById('eol-destinations-count');
    
    if (recyclabilityEl) recyclabilityEl.textContent = `${recyclabilityPercent.toFixed(1)}%`;
    if (totalElementsEl) totalElementsEl.textContent = `${elementsWithStrategy}/${totalElements}`;
    if (totalCostEl) totalCostEl.textContent = `${new Intl.NumberFormat('fr-FR').format(totalCost)} €`;
    if (destinationsEl) destinationsEl.textContent = uniqueDestinations;
}

/**
 * Actualise les données EOL
 */
async function refreshEOLData() {
    await loadEOLManagementData();
    notifications.success('Données EOL actualisées');
}

/**
 * Exporte les données EOL en Excel
 */
async function exportEOLExcel() {
    try {
        // Préparer les données pour l'export
        const exportData = eolElements.map(element => ({
            'GUID': element.GlobalId,
            'Élément': element.UniformatDesc || element.GlobalId,
            'Stratégie': element.Strategy || '',
            'Destination': element.Destination || '',
            'Responsable': element.Responsible || '',
            'Coût (€)': element.Cost || 0
        }));
        
        if (exportData.length === 0) {
            notifications.warning('Aucune donnée à exporter');
            return;
        }
        
        // Convertir en CSV et télécharger
        const csv = convertToCSV(exportData);
        const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
        const link = document.createElement('a');
        link.href = URL.createObjectURL(blob);
        link.download = `gestion_fin_de_vie_${new Date().toISOString().split('T')[0]}.csv`;
        link.click();
        
        notifications.success('Export Excel généré');
        
    } catch (error) {
        console.error('Erreur export EOL:', error);
        notifications.error('Erreur lors de l\'export');
    }
}

/**
 * Efface toutes les données EOL
 */
async function clearAllEOLData() {
    if (!confirm('Êtes-vous sûr de vouloir effacer toutes les données de gestion fin de vie ?')) {
        return;
    }
    
    notifications.warning('Fonctionnalité à implémenter');
}

/**
 * Initialise l'onglet EOL quand il est sélectionné
 */
function initializeEOLTab() {
    console.log('🔄 Initialisation de l\'onglet Gestion Fin de Vie...');
    
    if (eolElements.length === 0) {
        loadEOLManagementData();
    }
    
    if (availableStrategies.length === 0) {
        loadEndOfLifeStrategies().then(() => {
            populateEOLStrategies();
        });
    } else {
        populateEOLStrategies();
    }
    
    console.log('✅ Onglet Gestion Fin de Vie initialisé');
}

// Event listener pour l'activation de l'onglet EOL
document.addEventListener('DOMContentLoaded', function() {
    const eolTab = document.getElementById('nav-eol-tab');
    if (eolTab) {
        eolTab.addEventListener('shown.bs.tab', initializeEOLTab);
    }
});
