document.addEventListener('DOMContentLoaded', function() {
    const searchBtn = document.getElementById('searchBtn');
    const productInput = document.getElementById('productInput');
    const loader = document.getElementById('loader');
    const resultsContainer = document.getElementById('resultsContainer');
    const resultsGrid = document.getElementById('resultsGrid');
    const productName = document.getElementById('productName');
    
    // Determine backend URL based on environment
    const isLocal = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';
    const BACKEND_URL = isLocal ? 'http://127.0.0.1:5000' : 'https://your-backend-app-name.onrender.com';
    
    searchBtn.addEventListener('click', initiateSearch);
    productInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            initiateSearch();
        }
    });
    
    function initiateSearch() {
        const query = productInput.value.trim();
        if (query.length === 0) {
            alert('Please enter a product name to search');
            return;
        }
        
        // Show loader, hide results
        loader.style.display = 'block';
        resultsContainer.style.display = 'none';
        
        // Clear previous results
        resultsGrid.innerHTML = '';
        productName.textContent = query;
        
        // Send request to backend
        fetchPrices(query);
    }
    
    function fetchPrices(query) {
        fetch(`${BACKEND_URL}/search?product=${encodeURIComponent(query)}`)
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                displayResults(data);
            })
            .catch(error => {
                console.error('Error fetching prices:', error);
                loader.style.display = 'none';
                alert('Error fetching prices. Please make sure the backend server is running and check the console for details.');
            });
    }
    
    function displayResults(results) {
        // Hide loader, show results
        loader.style.display = 'none';
        resultsContainer.style.display = 'block';
        
        resultsGrid.innerHTML = '';
        
        if (results.length === 0) {
            resultsGrid.innerHTML = '<p class="no-results">No results found. Please try a different search term.</p>';
            return;
        }
        
        results.forEach(result => {
            const card = document.createElement('div');
            card.className = 'result-card';
            
            card.innerHTML = `
                <div class="store-header ${result.store}">
                    <i class="fas fa-store"></i>
                    <span>${result.storeName}</span>
                </div>
                <div class="product-info">
                    ${result.available ? 
                        `<p class="price">${result.price}</p>
                         <a href="${result.url}" target="_blank" class="product-link">View Product</a>` :
                        `<p class="not-available">Product not available on ${result.storeName}</p>
                         <a href="${result.url}" target="_blank" class="product-link">Browse Store</a>`
                    }
                </div>
            `;
            
            resultsGrid.appendChild(card);
        });
    }
});
