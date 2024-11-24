// DOM Elements
const searchInput = document.getElementById('searchInput');
const difficultyFilter = document.getElementById('difficultyFilter');
const conceptGrid = document.getElementById('conceptGrid');
const conceptModal = document.getElementById('conceptModal');
const modalTitle = document.getElementById('modalTitle');
const modalContent = document.getElementById('modalContent');

// State
let concepts = [];
let filteredConcepts = [];

// Initialize the page
async function initializeConcepts() {
    await loadConcepts();
    setupEventListeners();
}

// Load concepts from the API
async function loadConcepts() {
    try {
        const response = await fetch('/api/concepts');
        if (!response.ok) throw new Error('Failed to fetch concepts');
        
        concepts = await response.json();
        filteredConcepts = [...concepts];
        displayConcepts(filteredConcepts);
    } catch (error) {
        showError('Failed to load concepts: ' + error.message);
    }
}

// Display concepts in the grid
function displayConcepts(conceptsToDisplay) {
    conceptGrid.innerHTML = '';
    
    conceptsToDisplay.forEach(concept => {
        const card = document.createElement('div');
        card.className = 'concept-card bg-white p-6 rounded-lg shadow-lg';
        card.innerHTML = `
            <h3 class="text-xl font-semibold text-indigo-600 mb-4">${concept.name}</h3>
            <ul class="space-y-2 text-gray-600">
                ${concept.topics.map(topic => `<li>${topic}</li>`).join('')}
            </ul>
            <div class="mt-4">
                <button onclick="startPractice('${concept.id}')" 
                        class="px-4 py-2 bg-indigo-600 text-white rounded hover:bg-indigo-700 transition-colors">
                    Practice This Concept
                </button>
                <button onclick="showConceptDetails('${concept.id}')"
                        class="ml-2 px-4 py-2 bg-gray-100 text-gray-700 rounded hover:bg-gray-200 transition-colors">
                    Details
                </button>
            </div>
        `;
        conceptGrid.appendChild(card);
    });
}

// Filter concepts based on search and difficulty
function filterConcepts() {
    const searchTerm = searchInput.value.toLowerCase();
    const difficulty = difficultyFilter.value;
    
    filteredConcepts = concepts.filter(concept => {
        const matchesSearch = concept.name.toLowerCase().includes(searchTerm) ||
                            concept.topics.some(topic => topic.toLowerCase().includes(searchTerm));
        const matchesDifficulty = !difficulty || concept.difficulty === difficulty;
        return matchesSearch && matchesDifficulty;
    });
    
    displayConcepts(filteredConcepts);
}

// Show concept details in modal
async function showConceptDetails(conceptId) {
    try {
        const response = await fetch(`/api/concepts/${conceptId}`);
        if (!response.ok) throw new Error('Failed to fetch concept details');
        
        const concept = await response.json();
        modalTitle.textContent = concept.name;
        modalContent.innerHTML = `
            <div class="space-y-4">
                <div>
                    <h4 class="font-semibold text-gray-700">Description</h4>
                    <p class="text-gray-600">${concept.description}</p>
                </div>
                <div>
                    <h4 class="font-semibold text-gray-700">Topics Covered</h4>
                    <ul class="list-disc list-inside text-gray-600">
                        ${concept.topics.map(topic => `<li>${topic}</li>`).join('')}
                    </ul>
                </div>
                <div>
                    <h4 class="font-semibold text-gray-700">Difficulty</h4>
                    <p class="text-gray-600 capitalize">${concept.difficulty}</p>
                </div>
                <div>
                    <h4 class="font-semibold text-gray-700">Prerequisites</h4>
                    <ul class="list-disc list-inside text-gray-600">
                        ${concept.prerequisites.map(prereq => `<li>${prereq}</li>`).join('')}
                    </ul>
                </div>
            </div>
        `;
        conceptModal.classList.remove('hidden');
    } catch (error) {
        showError('Failed to load concept details: ' + error.message);
    }
}

// Start practicing a concept
function startPractice(conceptId) {
    window.location.href = `/practice?concept=${conceptId}`;
}

// Close the concept details modal
function closeConceptModal() {
    conceptModal.classList.add('hidden');
}

// Setup event listeners
function setupEventListeners() {
    searchInput.addEventListener('input', filterConcepts);
    difficultyFilter.addEventListener('change', filterConcepts);
    
    // Close modal when clicking outside
    conceptModal.addEventListener('click', event => {
        if (event.target === conceptModal) {
            closeConceptModal();
        }
    });
    
    // Close modal on escape key
    document.addEventListener('keydown', event => {
        if (event.key === 'Escape') {
            closeConceptModal();
        }
    });
}

// Initialize when the page loads
document.addEventListener('DOMContentLoaded', initializeConcepts);
