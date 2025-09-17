/**
 * Feedback Visualization JS
 * 
 * This file provides additional interactivity for the review feedback
 * and visualization components.
 */

// Function to select feedback options
function selectFeedback(element, groupName) {
    // Remove selected class from all buttons in the group
    const buttons = document.querySelectorAll(`[data-group="${groupName}"]`);
    buttons.forEach(btn => btn.classList.remove('selected'));
    
    // Add selected class to clicked button
    element.classList.add('selected');
    
    // Send event to Streamlit
    const data = {
        group: groupName,
        value: element.getAttribute('data-value')
    };
    
    // This would normally communicate with Streamlit's component API
    console.log('Feedback selected:', data);
}

// Create dynamic score bars
function createScoreBars() {
    const scoreBars = document.querySelectorAll('.score-bar-container');
    
    scoreBars.forEach(container => {
        const score = parseFloat(container.getAttribute('data-score'));
        const maxScore = parseFloat(container.getAttribute('data-max-score') || '5');
        
        const percentage = (score / maxScore) * 100;
        const bar = container.querySelector('.score-bar-inner');
        
        if (bar) {
            bar.style.width = `${percentage}%`;
            
            // Add color based on score
            if (percentage >= 80) {
                bar.style.background = 'linear-gradient(90deg, #48bb78 0%, #38a169 100%)';
            } else if (percentage >= 60) {
                bar.style.background = 'linear-gradient(90deg, #4299e1 0%, #3182ce 100%)';
            } else if (percentage >= 40) {
                bar.style.background = 'linear-gradient(90deg, #ecc94b 0%, #d69e2e 100%)';
            } else {
                bar.style.background = 'linear-gradient(90deg, #f56565 0%, #e53e3e 100%)';
            }
        }
    });
}

// Create tooltips
function initTooltips() {
    const tooltips = document.querySelectorAll('.tooltip');
    
    tooltips.forEach(tooltip => {
        tooltip.addEventListener('mouseenter', () => {
            const tooltipText = tooltip.querySelector('.tooltiptext');
            if (tooltipText) {
                tooltipText.style.visibility = 'visible';
                tooltipText.style.opacity = '1';
            }
        });
        
        tooltip.addEventListener('mouseleave', () => {
            const tooltipText = tooltip.querySelector('.tooltiptext');
            if (tooltipText) {
                tooltipText.style.visibility = 'hidden';
                tooltipText.style.opacity = '0';
            }
        });
    });
}

// Evidence highlighting
function highlightEvidence() {
    const evidenceItems = document.querySelectorAll('.evidence-item');
    
    evidenceItems.forEach(item => {
        item.addEventListener('mouseenter', () => {
            item.style.backgroundColor = '#f0f4ff';
        });
        
        item.addEventListener('mouseleave', () => {
            item.style.backgroundColor = 'transparent';
        });
    });
}

// Initialize all components
function initComponents() {
    createScoreBars();
    initTooltips();
    highlightEvidence();
    
    console.log('Feedback visualization components initialized');
}

// Run initialization when the page loads
document.addEventListener('DOMContentLoaded', initComponents);

// Also run when Streamlit reloads the component
window.addEventListener('message', function(event) {
    if (event.data.type === 'streamlit:render') {
        setTimeout(initComponents, 100); // Small delay to ensure DOM is ready
    }
});
