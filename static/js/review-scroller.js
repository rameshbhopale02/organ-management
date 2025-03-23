document.addEventListener('DOMContentLoaded', function() {
    const reviewScroller = document.querySelector('.review-scroller');
    if (!reviewScroller) return;

    const reviewContainer = reviewScroller.querySelector('.review-container');
    const prevBtn = reviewScroller.querySelector('#scroll-left');
    const nextBtn = reviewScroller.querySelector('#scroll-right');
    
    let isLoading = false;
    let currentPage = 1;
    let hasMore = reviewScroller.dataset.hasMore === 'true';
    
    // Function to check if an element is in viewport
    function isInViewport(element) {
        const rect = element.getBoundingClientRect();
        return (
            rect.top >= 0 &&
            rect.left >= 0 &&
            rect.bottom <= (window.innerHeight || document.documentElement.clientHeight) &&
            rect.right <= (window.innerWidth || document.documentElement.clientWidth)
        );
    }
    
    // Function to handle scroll buttons visibility
    function updateScrollButtons() {
        if (!prevBtn || !nextBtn) return;
        
        const isAtStart = reviewContainer.scrollLeft <= 0;
        const isAtEnd = reviewContainer.scrollLeft >= (reviewContainer.scrollWidth - reviewContainer.clientWidth - 10);
        
        prevBtn.style.opacity = isAtStart ? '0.5' : '0.8';
        prevBtn.style.pointerEvents = isAtStart ? 'none' : 'auto';
        
        nextBtn.style.opacity = (isAtEnd && !hasMore) ? '0.5' : '0.8';
        nextBtn.style.pointerEvents = (isAtEnd && !hasMore) ? 'none' : 'auto';
    }
    
    // Function to scroll to previous/next review
    function scrollReviews(direction) {
        const cardWidth = reviewContainer.querySelector('.review-card').offsetWidth;
        const scrollAmount = cardWidth + 32; // card width + gap
        const currentScroll = reviewContainer.scrollLeft;
        
        if (direction === 'prev') {
            reviewContainer.scrollTo({
                left: currentScroll - scrollAmount,
                behavior: 'smooth'
            });
        } else {
            // If near the end and has more reviews, load them
            if (currentScroll + reviewContainer.clientWidth >= reviewContainer.scrollWidth - cardWidth && hasMore) {
                loadMoreReviews();
            }
            
            reviewContainer.scrollTo({
                left: currentScroll + scrollAmount,
                behavior: 'smooth'
            });
        }
    }
    
    // Function to load more reviews
    function loadMoreReviews() {
        if (isLoading || !hasMore) return;
        
        isLoading = true;
        currentPage++;
        
        fetch(`/get_more_reviews?page=${currentPage}`)
            .then(response => response.json())
            .then(data => {
                if (data.error) {
                    console.error('Error loading reviews:', data.error);
                    return;
                }
                
                hasMore = data.has_more;
                
                // Add new reviews to the container
                data.reviews.forEach(review => {
                    const reviewCard = document.createElement('div');
                    reviewCard.className = 'review-card';
                    
                    // Create stars HTML
                    let starsHtml = '';
                    const fullStars = Math.floor(review.rating);
                    const hasHalfStar = review.rating % 1 >= 0.5;
                    
                    for (let i = 0; i < fullStars; i++) {
                        starsHtml += '<i class="fas fa-star"></i>';
                    }
                    
                    if (hasHalfStar) {
                        starsHtml += '<i class="fas fa-star-half-alt"></i>';
                    }
                    
                    reviewCard.innerHTML = `
                        <div class="review-header">
                            <h3>${review.patient_name}</h3>
                            <div class="stars">
                                ${starsHtml}
                            </div>
                        </div>
                        <p class="text">${review.review_text}</p>
                        <div class="review-date">
                            <small>${review.date_submitted}</small>
                        </div>
                    `;
                    
                    reviewContainer.appendChild(reviewCard);
                });
                
                updateScrollButtons();
            })
            .catch(error => {
                console.error('Error:', error);
            })
            .finally(() => {
                isLoading = false;
            });
    }
    
    // Event Listeners
    if (prevBtn) {
        prevBtn.addEventListener('click', () => scrollReviews('prev'));
    }
    
    if (nextBtn) {
        nextBtn.addEventListener('click', () => scrollReviews('next'));
    }
    
    // Update scroll buttons on scroll
    reviewContainer.addEventListener('scroll', () => {
        requestAnimationFrame(updateScrollButtons);
    });
    
    // Initial update of scroll buttons
    updateScrollButtons();
    
    // Intersection Observer for lazy loading
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting && hasMore && !isLoading) {
                loadMoreReviews();
            }
        });
    }, {
        root: null,
        rootMargin: '0px',
        threshold: 0.1
    });
    
    // Observe the last review card
    function observeLastReview() {
        const reviewCards = reviewContainer.querySelectorAll('.review-card');
        if (reviewCards.length > 0) {
            observer.observe(reviewCards[reviewCards.length - 1]);
        }
    }
    
    observeLastReview();
}); 