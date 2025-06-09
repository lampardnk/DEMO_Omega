document.addEventListener('DOMContentLoaded', function() {
    // Get the current days parameter from the URL or default to 7
    const urlParams = new URLSearchParams(window.location.search);
    const currentDays = urlParams.get('days') || 7;
    
    // Add event listeners for time range buttons
    const timeRangeButtons = document.querySelectorAll('.time-range .btn');
    
    // Mark the active button based on the current days parameter
    timeRangeButtons.forEach(button => {
        // Remove active class from all buttons
        button.classList.remove('active');
        
        // Determine which button should be active
        if (button.textContent.includes('7 days') && currentDays == 7) {
            button.classList.add('active');
        } else if (button.textContent.includes('14 days') && currentDays == 14) {
            button.classList.add('active');
        } else if (button.textContent.includes('30 days') && currentDays == 30) {
            button.classList.add('active');
        }
        
        // Add click event listener
        button.addEventListener('click', function() {
            let days = 7;
            if (this.textContent.includes('14 days')) {
                days = 14;
            } else if (this.textContent.includes('30 days')) {
                days = 30;
            }
            
            // Update URL and reload page
            window.location.href = `${window.location.pathname}?days=${days}`;
        });
    });
}); 