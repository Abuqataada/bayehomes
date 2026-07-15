// Live search suggestions
const searchInput = document.querySelector('input[name="search"]');
if (searchInput) {
    let timeout;
    searchInput.addEventListener('input', function() {
        clearTimeout(timeout);
        timeout = setTimeout(() => {
            const query = this.value;
            if (query.length > 2) {
                fetch(`/search-suggestions?q=${encodeURIComponent(query)}`)
                    .then(res => res.json())
                    .then(data => {
                        // Simple alert for demo – you can implement a dropdown
                        console.log(data);
                    });
            }
        }, 500);
    });
}

// Price range validation (if using sliders, but we have number inputs)
// Smooth scroll for anchor links
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function(e) {
        e.preventDefault();
        const target = document.querySelector(this.getAttribute('href'));
        if (target) target.scrollIntoView({ behavior: 'smooth' });
    });
});
