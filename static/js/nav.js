document.addEventListener('DOMContentLoaded', function() {
    // Navigation active state management
    const currentLocation = location.pathname;
    const navLinks = document.querySelectorAll('.navbar a');
    let activeLink = null;
    
    // Function to set active state with animation
    const setActiveLink = (link) => {
        if (activeLink) {
            activeLink.classList.remove('active');
            activeLink.style.animation = '';
        }
        link.classList.add('active');
        link.style.animation = 'navItemLoad 0.3s ease forwards';
        activeLink = link;
    };
    
    // Set initial active state based on current path
    navLinks.forEach(link => {
        const href = link.getAttribute('href');
        // Add animation delay for each nav item
        link.style.animationDelay = `${Array.from(navLinks).indexOf(link) * 0.1}s`;
        
        // Enhanced path matching logic
        if (
            href === currentLocation || // Exact match
            (href === '/' && currentLocation === '') || // Home page
            (href === '/donor' && currentLocation.startsWith('/donor')) || // Donor pages
            (href === '/patient' && (currentLocation.startsWith('/patient') || 
                                   currentLocation.startsWith('/patient_login') || 
                                   currentLocation.startsWith('/patient_register'))) || // Patient pages
            (href === '/admin' && (currentLocation.startsWith('/admin') || 
                                 currentLocation.includes('details') || 
                                 currentLocation.includes('process') || 
                                 currentLocation.includes('management'))) // Admin pages
        ) {
            setActiveLink(link);
        }
        
        // Add hover effect
        link.addEventListener('mouseenter', function() {
            if (this !== activeLink) {
                this.style.transform = 'translateY(-2px)';
            }
        });
        
        link.addEventListener('mouseleave', function() {
            if (this !== activeLink) {
                this.style.transform = 'translateY(0)';
            }
        });
        
        // Add click handler for smooth transition
        link.addEventListener('click', function(e) {
            if (!this.href.includes('#')) {
                setActiveLink(this);
            }
        });
    });
    
    // Mobile menu toggle with smooth animation
    const menuBtn = document.querySelector('#menu-btn');
    const navbar = document.querySelector('.navbar');
    
    if (menuBtn && navbar) {
        menuBtn.addEventListener('click', () => {
            menuBtn.classList.toggle('fa-times');
            navbar.classList.toggle('active');
            
            if (navbar.classList.contains('active')) {
                // Animate menu items when menu opens
                navLinks.forEach((link, index) => {
                    link.style.animation = `navItemLoad 0.3s ease forwards ${index * 0.1}s`;
                });
            } else {
                // Reset animations when menu closes
                navLinks.forEach(link => {
                    link.style.animation = '';
                });
            }
        });
        
        // Close mobile menu when clicking outside
        document.addEventListener('click', (e) => {
            if (!navbar.contains(e.target) && !menuBtn.contains(e.target)) {
                navbar.classList.remove('active');
                menuBtn.classList.remove('fa-times');
            }
        });
    }
}); 