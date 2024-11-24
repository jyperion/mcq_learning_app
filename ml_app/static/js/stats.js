// Chart instances
let conceptChart = null;
let progressChart = null;

// Initialize the page
async function initializeStats() {
    await Promise.all([
        loadOverviewStats(),
        loadConceptPerformance(),
        loadProgressOverTime(),
        loadRecentActivity()
    ]);
}

// Load overview statistics
async function loadOverviewStats() {
    try {
        const response = await fetch('/api/stats/overview');
        if (!response.ok) throw new Error('Failed to fetch overview stats');
        
        const stats = await response.json();
        document.getElementById('totalQuestions').textContent = stats.totalQuestions;
        document.getElementById('averageScore').textContent = `${Math.round(stats.averageScore)}%`;
        document.getElementById('practiceTime').textContent = formatTime(stats.totalTime);
    } catch (error) {
        showError('Failed to load overview statistics: ' + error.message);
    }
}

// Load and display concept performance chart
async function loadConceptPerformance() {
    try {
        const response = await fetch('/api/stats/concepts');
        if (!response.ok) throw new Error('Failed to fetch concept stats');
        
        const data = await response.json();
        const ctx = document.getElementById('conceptChart').getContext('2d');
        
        if (conceptChart) conceptChart.destroy();
        
        conceptChart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: data.concepts,
                datasets: [{
                    label: 'Performance (%)',
                    data: data.scores,
                    backgroundColor: 'rgba(79, 70, 229, 0.8)',
                    borderColor: 'rgba(79, 70, 229, 1)',
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                scales: {
                    y: {
                        beginAtZero: true,
                        max: 100
                    }
                },
                plugins: {
                    legend: {
                        display: false
                    }
                }
            }
        });
    } catch (error) {
        showError('Failed to load concept performance: ' + error.message);
    }
}

// Load and display progress over time chart
async function loadProgressOverTime() {
    try {
        const response = await fetch('/api/stats/progress');
        if (!response.ok) throw new Error('Failed to fetch progress stats');
        
        const data = await response.json();
        const ctx = document.getElementById('progressChart').getContext('2d');
        
        if (progressChart) progressChart.destroy();
        
        progressChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: data.dates,
                datasets: [{
                    label: 'Score',
                    data: data.scores,
                    borderColor: 'rgba(16, 185, 129, 1)',
                    backgroundColor: 'rgba(16, 185, 129, 0.1)',
                    fill: true,
                    tension: 0.4
                }]
            },
            options: {
                responsive: true,
                scales: {
                    y: {
                        beginAtZero: true,
                        max: 100
                    }
                }
            }
        });
    } catch (error) {
        showError('Failed to load progress chart: ' + error.message);
    }
}

// Load recent activity
async function loadRecentActivity() {
    try {
        const response = await fetch('/api/stats/activity');
        if (!response.ok) throw new Error('Failed to fetch activity');
        
        const activities = await response.json();
        const tableBody = document.getElementById('activityTable');
        tableBody.innerHTML = '';
        
        activities.forEach(activity => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td class="px-6 py-4 whitespace-nowrap">${formatDate(activity.date)}</td>
                <td class="px-6 py-4">${activity.concept}</td>
                <td class="px-6 py-4">${activity.score}%</td>
                <td class="px-6 py-4">${formatTime(activity.timeSpent)}</td>
            `;
            tableBody.appendChild(row);
        });
    } catch (error) {
        showError('Failed to load recent activity: ' + error.message);
    }
}

// Utility functions
function formatDate(dateString) {
    return new Date(dateString).toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
    });
}

function formatTime(minutes) {
    if (minutes < 60) return `${minutes}m`;
    const hours = Math.floor(minutes / 60);
    const remainingMinutes = minutes % 60;
    return remainingMinutes > 0 ? `${hours}h ${remainingMinutes}m` : `${hours}h`;
}

// Event Listeners
document.addEventListener('DOMContentLoaded', initializeStats);

// Handle window resize for charts
window.addEventListener('resize', () => {
    if (conceptChart) conceptChart.resize();
    if (progressChart) progressChart.resize();
});
