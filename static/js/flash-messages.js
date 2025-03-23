// Auto-hide flash messages after 5 seconds
document.addEventListener('DOMContentLoaded', function() {
    const alerts = document.querySelectorAll('.alert');
    if (alerts.length > 0) {
        alerts.forEach(alert => {
            setTimeout(function() {
                // Add fade-out effect
                alert.style.transition = 'opacity 1s ease';
                alert.style.opacity = '0';
                
                // Remove the element after fade completes
                setTimeout(function() {
                    alert.remove();
                }, 1000);
            }, 5000); // 5 seconds before starting fade
        });
    }
}); 