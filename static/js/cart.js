/**
 * cart.js - Shopping Cart State Management & Menu Rendering
 * Smart Chatbot for Restaurant Order Automation
 */

// Global State
let currentCategoryId = 'all';
let currentSearchQuery = '';
let currentDietFilter = 'all';

document.addEventListener('DOMContentLoaded', () => {
    initMenu();
    fetchAndRenderCart();
    initCheckout();
    initRecommendationFilters();
});

// -------------------------------------------------------------
// MENU RENDERING & FILTERING
// -------------------------------------------------------------
function initMenu() {
    const searchInput = document.getElementById('menuSearchInput');
    const dietRadios = document.querySelectorAll('input[name="dietRadio"]');
    const categoryButtons = document.querySelectorAll('.btn-category');

    // Debounced search
    let searchTimeout;
    if (searchInput) {
        searchInput.addEventListener('input', (e) => {
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(() => {
                currentSearchQuery = e.target.value.trim();
                fetchAndRenderMenu();
            }, 300);
        });
    }

    // Veg / Non-veg radio change
    dietRadios.forEach(radio => {
        radio.addEventListener('change', (e) => {
            currentDietFilter = e.target.value;
            fetchAndRenderMenu();
        });
    });

    // Category tab selection
    categoryButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            categoryButtons.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            currentCategoryId = btn.getAttribute('data-category');
            fetchAndRenderMenu();
        });
    });

    // Initial load
    fetchAndRenderMenu();
}

function fetchAndRenderMenu() {
    const menuGrid = document.getElementById('menuGrid');
    if (!menuGrid) return;

    let url = `/api/menu?category_id=${encodeURIComponent(currentCategoryId)}&q=${encodeURIComponent(currentSearchQuery)}`;
    if (currentDietFilter !== 'all') {
        url += `&is_veg=${encodeURIComponent(currentDietFilter)}`;
    }

    fetch(url)
        .then(res => res.json())
        .then(data => {
            if (!data.success || !data.items || data.items.length === 0) {
                menuGrid.innerHTML = `
                    <div class="col-12 text-center py-5">
                        <i class="bi bi-search text-muted fs-1 mb-2 d-block"></i>
                        <h5 class="fw-bold text-dark">No dishes matched your search</h5>
                        <p class="text-muted small">Try searching for pizza, burgers, starters or clear the filter.</p>
                        <button class="btn btn-sm btn-outline-primary rounded-pill mt-2" onclick="resetFilters()">Reset Filters</button>
                    </div>
                `;
                return;
            }

            menuGrid.innerHTML = data.items.map(item => createFoodCardHtml(item)).join('');
        })
        .catch(err => {
            console.error("Error loading menu:", err);
            menuGrid.innerHTML = `<div class="col-12 text-center text-danger py-4">Failed to load menu. Please refresh.</div>`;
        });
}

function resetFilters() {
    const searchInput = document.getElementById('menuSearchInput');
    const dietAll = document.getElementById('dietAll');
    if (searchInput) searchInput.value = '';
    if (dietAll) dietAll.checked = true;
    currentSearchQuery = '';
    currentDietFilter = 'all';
    currentCategoryId = 'all';

    document.querySelectorAll('.btn-category').forEach(b => {
        b.classList.toggle('active', b.getAttribute('data-category') === 'all');
    });
    fetchAndRenderMenu();
}

function createFoodCardHtml(item) {
    const isAvail = item.is_available === 1;
    const vegBadge = item.is_veg === 1 ? 'veg' : 'non-veg';
    const vegText = item.is_veg === 1 ? 'Veg' : 'Non-Veg';
    const imgUrl = item.image_url ? (item.image_url.startsWith('http') ? item.image_url : `https://images.unsplash.com/photo-1546069901-ba9599a7e63c?auto=format&fit=crop&w=600&q=80`) : 'https://images.unsplash.com/photo-1546069901-ba9599a7e63c?auto=format&fit=crop&w=600&q=80';

    return `
        <div class="col-lg-4 col-md-6">
            <div class="card h-100 food-card border-0 shadow-sm overflow-hidden position-relative">
                <div class="position-relative">
                    <img src="${imgUrl}" class="card-img-top food-card-img" alt="${item.name}" loading="lazy"
                         onerror="this.src='/static/images/food-placeholder.svg'; this.onerror=null;">
                    ${!isAvail ? '<div class="sold-out-overlay">SOLD OUT TODAY</div>' : ''}
                    <span class="position-absolute top-0 start-0 m-2 badge bg-white text-dark shadow-sm d-flex align-items-center gap-1 rounded-pill small py-1 px-2">
                        <span class="food-type-icon ${vegBadge}"></span>
                        <span class="fw-bold">${vegText}</span>
                    </span>
                    <span class="position-absolute top-0 end-0 m-2 badge bg-dark bg-opacity-75 rounded-pill small py-1 px-2">
                        <i class="bi bi-star-fill text-warning me-1"></i> ${item.rating}
                    </span>
                </div>
                <div class="card-body d-flex flex-column p-4">
                    <div class="d-flex justify-content-between align-items-start mb-1">
                        <h5 class="fw-bold text-dark mb-0">${item.name}</h5>
                        <span class="fs-5 fw-extrabold text-primary">₹${Math.round(item.price)}</span>
                    </div>
                    <small class="text-secondary mb-2 d-block">${item.category_name || ''}</small>
                    <p class="small text-muted flex-grow-1">${item.description || ''}</p>
                    
                    <div class="d-flex justify-content-between align-items-center pt-3 border-top mt-auto">
                        ${isAvail ? `
                            <div class="qty-stepper">
                                <button type="button" onclick="decrementLocalQty(${item.id})"><i class="bi bi-dash"></i></button>
                                <span id="qty-input-${item.id}">1</span>
                                <button type="button" onclick="incrementLocalQty(${item.id})"><i class="bi bi-plus"></i></button>
                            </div>
                            <button class="btn btn-sm btn-primary rounded-pill px-3 shadow-sm" onclick="addCardItemToCart(${item.id})">
                                <i class="bi bi-cart-plus me-1"></i> Add to Cart
                            </button>
                        ` : `
                            <span class="badge bg-danger-subtle text-danger px-3 py-2 rounded-pill fw-semibold">
                                <i class="bi bi-x-circle me-1"></i> Unavailable
                            </span>
                            <button class="btn btn-sm btn-secondary rounded-pill px-3" disabled>Sold Out</button>
                        `}
                    </div>
                </div>
            </div>
        </div>
    `;
}

function incrementLocalQty(itemId) {
    const el = document.getElementById(`qty-input-${itemId}`);
    if (el) {
        let val = parseInt(el.textContent) || 1;
        if (val < 20) el.textContent = val + 1;
    }
}

function decrementLocalQty(itemId) {
    const el = document.getElementById(`qty-input-${itemId}`);
    if (el) {
        let val = parseInt(el.textContent) || 1;
        if (val > 1) el.textContent = val - 1;
    }
}

function addCardItemToCart(itemId) {
    const el = document.getElementById(`qty-input-${itemId}`);
    const qty = el ? parseInt(el.textContent) || 1 : 1;
    addToCart(itemId, qty);
}

// -------------------------------------------------------------
// CART OPERATIONS
// -------------------------------------------------------------
function fetchAndRenderCart() {
    fetch('/api/cart')
        .then(res => res.json())
        .then(data => {
            if (data.success && data.cart) {
                renderCartUI(data.cart);
            }
        })
        .catch(err => console.error("Error fetching cart:", err));
}

function addToCart(itemId, quantity = 1) {
    fetch('/api/cart/add', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ item_id: itemId, quantity: quantity })
    })
    .then(res => res.json())
    .then(data => {
        if (data.success) {
            renderCartUI(data.cart);
            // Open offcanvas drawer to show added item
            const offcanvasEl = document.getElementById('cartOffcanvas');
            if (offcanvasEl && !offcanvasEl.classList.contains('show')) {
                const bsOffcanvas = bootstrap.Offcanvas.getOrCreateInstance(offcanvasEl);
                bsOffcanvas.show();
            }
        } else {
            alert(data.error || "Could not add item to cart.");
        }
    })
    .catch(err => console.error("Error adding to cart:", err));
}

function updateCartQuantity(itemId, newQty) {
    fetch('/api/cart/update', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ item_id: itemId, quantity: newQty })
    })
    .then(res => res.json())
    .then(data => {
        if (data.success) {
            renderCartUI(data.cart);
        }
    })
    .catch(err => console.error("Error updating cart:", err));
}

function removeFromCart(itemId) {
    fetch('/api/cart/remove', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ item_id: itemId })
    })
    .then(res => res.json())
    .then(data => {
        if (data.success) {
            renderCartUI(data.cart);
        }
    })
    .catch(err => console.error("Error removing item:", err));
}

function clearCart() {
    if (!confirm("Are you sure you want to empty your shopping cart?")) return;
    fetch('/api/cart/clear', { method: 'POST' })
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                renderCartUI(data.cart);
            }
        })
        .catch(err => console.error("Error clearing cart:", err));
}

function renderCartUI(cart) {
    // 1. Update Badges
    const navBadge = document.getElementById('navbarCartBadge');
    const drawerBadge = document.getElementById('drawerCartCount');
    if (navBadge) navBadge.textContent = cart.item_count || 0;
    if (drawerBadge) drawerBadge.textContent = cart.item_count || 0;

    // 2. Elements
    const emptyState = document.getElementById('cartEmptyState');
    const itemsContainer = document.getElementById('cartItemsContainer');
    const itemsList = document.getElementById('cartItemsList');
    const cartFooter = document.getElementById('cartFooter');

    const subtotalEl = document.getElementById('cartSubtotal');
    const taxEl = document.getElementById('cartTax');
    const totalEl = document.getElementById('cartTotal');

    const modalSubtotal = document.getElementById('modalSubtotal');
    const modalTax = document.getElementById('modalTax');
    const modalTotal = document.getElementById('modalTotal');

    if (!cart.items || cart.items.length === 0) {
        if (emptyState) emptyState.classList.remove('d-none');
        if (itemsContainer) itemsContainer.classList.add('d-none');
        if (cartFooter) cartFooter.classList.add('d-none');
        return;
    }

    if (emptyState) emptyState.classList.add('d-none');
    if (itemsContainer) itemsContainer.classList.remove('d-none');
    if (cartFooter) cartFooter.classList.remove('d-none');

    // Render item rows
    if (itemsList) {
        itemsList.innerHTML = cart.items.map(item => `
            <div class="card border rounded-3 p-2 bg-white shadow-sm">
                <div class="d-flex justify-content-between align-items-start mb-1">
                    <div class="pe-2">
                        <span class="food-type-icon ${item.is_veg ? 'veg' : 'non-veg'} me-1"></span>
                        <strong class="text-dark small">${item.name}</strong>
                        <div class="small text-muted">₹${item.price.toFixed(2)} each</div>
                    </div>
                    <button class="btn btn-sm btn-link text-danger p-0" onclick="removeFromCart(${item.id})" title="Remove">
                        <i class="bi bi-trash3"></i>
                    </button>
                </div>
                <div class="d-flex justify-content-between align-items-center mt-2 pt-2 border-top">
                    <div class="qty-stepper">
                        <button type="button" onclick="updateCartQuantity(${item.id}, ${item.quantity - 1})"><i class="bi bi-dash"></i></button>
                        <span>${item.quantity}</span>
                        <button type="button" onclick="updateCartQuantity(${item.id}, ${item.quantity + 1})"><i class="bi bi-plus"></i></button>
                    </div>
                    <span class="fw-bold text-primary small">₹${item.subtotal.toFixed(2)}</span>
                </div>
            </div>
        `).join('');
    }

    // Update Totals
    const formattedSub = `₹${cart.subtotal.toFixed(2)}`;
    const formattedTax = `₹${cart.tax.toFixed(2)}`;
    const formattedTotal = `₹${cart.total.toFixed(2)}`;

    if (subtotalEl) subtotalEl.textContent = formattedSub;
    if (taxEl) taxEl.textContent = formattedTax;
    if (totalEl) totalEl.textContent = formattedTotal;

    if (modalSubtotal) modalSubtotal.textContent = formattedSub;
    if (modalTax) modalTax.textContent = formattedTax;
    if (modalTotal) modalTotal.textContent = formattedTotal;
}

// -------------------------------------------------------------
// CHECKOUT SUBMISSION
// -------------------------------------------------------------
function initCheckout() {
    const btnOpenCheckout = document.getElementById('btnOpenCheckoutModal');
    const checkoutForm = document.getElementById('checkoutForm');
    const btnClear = document.getElementById('btnClearCart');

    if (btnClear) {
        btnClear.addEventListener('click', clearCart);
    }

    if (btnOpenCheckout) {
        btnOpenCheckout.addEventListener('click', () => {
            // Close cart offcanvas
            const offcanvasEl = document.getElementById('cartOffcanvas');
            if (offcanvasEl) {
                const bsOffcanvas = bootstrap.Offcanvas.getInstance(offcanvasEl);
                if (bsOffcanvas) bsOffcanvas.hide();
            }
            // Show checkout modal
            const checkoutModalEl = document.getElementById('checkoutModal');
            if (checkoutModalEl) {
                const bsModal = bootstrap.Modal.getOrCreateInstance(checkoutModalEl);
                bsModal.show();
            }
        });
    }

    if (checkoutForm) {
        checkoutForm.addEventListener('submit', (e) => {
            e.preventDefault();
            const alertBox = document.getElementById('checkoutAlert');
            const submitBtn = document.getElementById('btnPlaceOrder');
            const spinner = document.getElementById('placeOrderSpinner');

            const name = document.getElementById('custName').value.trim();
            const phone = document.getElementById('custPhone').value.trim();
            const address = document.getElementById('custAddress').value.trim();
            const payment = document.getElementById('custPayment').value;
            const instructions = document.getElementById('custInstructions').value.trim();

            if (alertBox) alertBox.classList.add('d-none');
            if (submitBtn) submitBtn.disabled = true;
            if (spinner) spinner.classList.remove('d-none');

            fetch('/api/checkout', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    name: name,
                    phone: phone,
                    address: address,
                    payment_method: payment,
                    special_instructions: instructions
                })
            })
            .then(res => res.json())
            .then(data => {
                if (data.success && data.redirect_url) {
                    window.location.href = data.redirect_url;
                } else {
                    if (alertBox) {
                        alertBox.textContent = data.error || "Order placement failed. Please try again.";
                        alertBox.classList.remove('d-none');
                    }
                    if (submitBtn) submitBtn.disabled = false;
                    if (spinner) spinner.classList.add('d-none');
                }
            })
            .catch(err => {
                console.error("Checkout error:", err);
                if (alertBox) {
                    alertBox.textContent = "Network error. Please check your connection and retry.";
                    alertBox.classList.remove('d-none');
                }
                if (submitBtn) submitBtn.disabled = false;
                if (spinner) spinner.classList.add('d-none');
            });
        });
    }
}

// -------------------------------------------------------------
// RECOMMENDATION FILTER BUTTONS
// -------------------------------------------------------------
function initRecommendationFilters() {
    const filterButtons = document.querySelectorAll('.rec-filter-btn');
    const recRow = document.getElementById('recommendationsRow');
    if (!recRow) return;

    filterButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            filterButtons.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');

            const filterType = btn.getAttribute('data-type');
            let url = '/api/recommendations?';
            if (filterType === 'veg') url += 'is_veg=1';
            else if (filterType === 'budget300') url += 'budget=300';

            fetch(url)
                .then(res => res.json())
                .then(data => {
                    if (data.success && data.recommendations) {
                        recRow.innerHTML = data.recommendations.map(item => `
                            <div class="col-lg-4 col-md-6">
                                <div class="card h-100 rec-card border-0 shadow-sm rounded-4 overflow-hidden">
                                    <div class="position-relative">
                                        <img src="https://images.unsplash.com/photo-1546069901-ba9599a7e63c?auto=format&fit=crop&w=600&q=80" 
                                             class="card-img-top rec-img" alt="${item.name}">
                                        <span class="position-absolute top-0 start-0 m-3 badge ${item.is_veg ? 'bg-success' : 'bg-danger'} rounded-pill">
                                            ${item.is_veg ? 'Veg' : 'Non-Veg'}
                                        </span>
                                        <span class="position-absolute top-0 end-0 m-3 badge bg-dark bg-opacity-75 rounded-pill">
                                            <i class="bi bi-star-fill text-warning me-1"></i> ${item.rating}
                                        </span>
                                    </div>
                                    <div class="card-body d-flex flex-column p-4">
                                        <div class="d-flex justify-content-between align-items-start mb-1">
                                            <h5 class="fw-bold mb-0 text-dark">${item.name}</h5>
                                            <span class="fs-5 fw-extrabold text-primary">₹${Math.round(item.price)}</span>
                                        </div>
                                        <small class="text-success fw-semibold mb-2 d-block">
                                            <i class="bi bi-lightbulb-fill me-1"></i> ${item.explanation || ''}
                                        </small>
                                        <p class="small text-muted flex-grow-1">${item.description || ''}</p>
                                        <div class="border-top pt-3 d-flex justify-content-between align-items-center">
                                            <span class="small text-secondary">${item.category_name || ''}</span>
                                            <button class="btn btn-sm btn-primary rounded-pill px-3" onclick="addToCart(${item.id}, 1)">
                                                <i class="bi bi-cart-plus me-1"></i> Add
                                            </button>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        `).join('');
                    }
                });
        });
    });
}
