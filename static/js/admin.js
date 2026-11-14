/**
 * admin.js - Administrative Dashboard, Analytics & Menu CRUD
 * Smart Chatbot for Restaurant Order Automation
 */

let categoryChartInstance = null;
let statusChartInstance = null;

document.addEventListener('DOMContentLoaded', () => {
    initAdminAnalytics();
    initOrderFilters();
    initMenuFormHandlers();
});

// -------------------------------------------------------------
// ANALYTICS CHARTS (CHART.JS)
// -------------------------------------------------------------
function initAdminAnalytics() {
    fetch('/api/admin/analytics')
        .then(res => res.json())
        .then(data => {
            if (!data.success) return;

            // 1. Category Revenue Doughnut Chart
            const catCtx = document.getElementById('categorySalesChart');
            if (catCtx && data.category_sales) {
                const labels = data.category_sales.map(c => c.category_name);
                const sales = data.category_sales.map(c => c.total_sales);

                if (categoryChartInstance) categoryChartInstance.destroy();
                categoryChartInstance = new Chart(catCtx, {
                    type: 'doughnut',
                    data: {
                        labels: labels,
                        datasets: [{
                            data: sales,
                            backgroundColor: [
                                '#ff6b35', '#f77f00', '#fcbf49', '#10b981', '#3b82f6', '#8b5cf6'
                            ],
                            borderWidth: 2,
                            borderColor: '#ffffff'
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {
                            legend: { position: 'bottom' },
                            tooltip: {
                                callbacks: {
                                    label: function(ctx) {
                                        return ` ${ctx.label}: ₹${ctx.parsed.toFixed(2)}`;
                                    }
                                }
                            }
                        }
                    }
                });
            }

            // 2. Order Status Bar Chart
            const statusCtx = document.getElementById('statusChart');
            if (statusCtx && data.status_counts) {
                const sLabels = data.status_counts.map(s => s.status);
                const sCounts = data.status_counts.map(s => s.count);

                if (statusChartInstance) statusChartInstance.destroy();
                statusChartInstance = new Chart(statusCtx, {
                    type: 'bar',
                    data: {
                        labels: sLabels,
                        datasets: [{
                            label: 'Number of Orders',
                            data: sCounts,
                            backgroundColor: '#2b2d42',
                            borderRadius: 6
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {
                            legend: { display: false }
                        },
                        scales: {
                            y: {
                                beginAtZero: true,
                                ticks: { stepSize: 1 }
                            }
                        }
                    }
                });
            }
        })
        .catch(err => console.error("Error loading admin analytics:", err));
}

// -------------------------------------------------------------
// ORDERS TABLE FILTER & STATUS UPDATER
// -------------------------------------------------------------
function initOrderFilters() {
    const searchInput = document.getElementById('orderSearchInput');
    const statusFilter = document.getElementById('orderStatusFilter');
    const table = document.getElementById('adminOrdersTable');

    function filterRows() {
        const query = (searchInput ? searchInput.value : '').toLowerCase().trim();
        const selectedStatus = statusFilter ? statusFilter.value : 'all';
        const rows = table.querySelectorAll('tbody tr');

        rows.forEach(row => {
            const rowText = row.textContent.toLowerCase();
            const rowStatus = row.getAttribute('data-status');

            const matchesQuery = !query || rowText.includes(query);
            const matchesStatus = selectedStatus === 'all' || rowStatus === selectedStatus;

            row.style.display = (matchesQuery && matchesStatus) ? '' : 'none';
        });
    }

    if (searchInput) searchInput.addEventListener('input', filterRows);
    if (statusFilter) statusFilter.addEventListener('change', filterRows);
}

function updateOrderStatus(orderId, newStatus) {
    if (!confirm(`Are you sure you want to change order #${orderId} status to "${newStatus}"?`)) {
        location.reload();
        return;
    }

    fetch(`/api/admin/orders/${orderId}/status`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: newStatus })
    })
    .then(res => res.json())
    .then(data => {
        if (data.success) {
            alert(data.message);
            location.reload();
        } else {
            alert("Error updating status: " + data.error);
            location.reload();
        }
    })
    .catch(err => {
        alert("Network error updating status.");
        location.reload();
    });
}

function viewOrderDetails(orderId) {
    const modalEl = document.getElementById('orderDetailsModal');
    const body = document.getElementById('orderDetailsBody');
    const title = document.getElementById('detailOrderCode');
    const bsModal = bootstrap.Modal.getOrCreateInstance(modalEl);

    body.innerHTML = `
        <div class="text-center py-4">
            <div class="spinner-border text-primary" role="status"></div>
            <p class="small text-muted mt-2">Loading order details...</p>
        </div>
    `;
    bsModal.show();

    fetch(`/api/admin/orders/${orderId}/details`)
        .then(res => res.json())
        .then(data => {
            if (!data.success) {
                body.innerHTML = `<div class="alert alert-danger">${data.error}</div>`;
                return;
            }

            const o = data.order;
            title.textContent = `Order: ${o.order_code}`;

            const itemsRows = data.items.map(it => `
                <tr>
                    <td>${it.item_name}</td>
                    <td class="text-center">${it.quantity}</td>
                    <td class="text-end">₹${it.item_price.toFixed(2)}</td>
                    <td class="text-end fw-semibold">₹${it.subtotal.toFixed(2)}</td>
                </tr>
            `).join('');

            body.innerHTML = `
                <div class="mb-3 small">
                    <p class="mb-1"><strong>Customer:</strong> ${o.user_name} (${o.user_phone})</p>
                    <p class="mb-1"><strong>Address:</strong> ${o.user_address}</p>
                    <p class="mb-1"><strong>Payment:</strong> ${o.payment_method}</p>
                    <p class="mb-1"><strong>Status:</strong> <span class="badge bg-primary">${o.status}</span></p>
                    ${o.special_instructions ? `<p class="mb-1 text-danger"><strong>Instructions:</strong> ${o.special_instructions}</p>` : ''}
                </div>
                <div class="table-responsive">
                    <table class="table table-sm small align-middle">
                        <thead class="table-light">
                            <tr>
                                <th>Item</th>
                                <th class="text-center">Qty</th>
                                <th class="text-end">Price</th>
                                <th class="text-end">Subtotal</th>
                            </tr>
                        </thead>
                        <tbody>${itemsRows}</tbody>
                        <tfoot class="border-top">
                            <tr>
                                <td colspan="3" class="text-end">Subtotal:</td>
                                <td class="text-end">₹${o.subtotal.toFixed(2)}</td>
                            </tr>
                            <tr>
                                <td colspan="3" class="text-end">Tax (5%):</td>
                                <td class="text-end">₹${o.tax_amount.toFixed(2)}</td>
                            </tr>
                            <tr class="fw-bold">
                                <td colspan="3" class="text-end">Total Amount:</td>
                                <td class="text-end text-success">₹${o.total_amount.toFixed(2)}</td>
                            </tr>
                        </tfoot>
                    </table>
                </div>
            `;
        })
        .catch(err => {
            body.innerHTML = `<div class="alert alert-danger">Error loading details.</div>`;
        });
}

// -------------------------------------------------------------
// MENU MANAGEMENT (CRUD)
// -------------------------------------------------------------
function toggleDishAvailability(dishId) {
    fetch(`/api/admin/menu/${dishId}/toggle-availability`, { method: 'POST' })
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                // Flash alert or refresh
                location.reload();
            } else {
                alert("Error toggling availability: " + data.error);
            }
        })
        .catch(err => alert("Network error."));
}

function initMenuFormHandlers() {
    // Add Dish Form
    const addForm = document.getElementById('addDishForm');
    if (addForm) {
        addForm.addEventListener('submit', (e) => {
            e.preventDefault();
            const payload = {
                name: document.getElementById('dishName').value.trim(),
                category_id: document.getElementById('dishCategory').value,
                price: parseFloat(document.getElementById('dishPrice').value),
                is_veg: parseInt(document.getElementById('dishVeg').value),
                is_available: parseInt(document.getElementById('dishAvailable').value),
                description: document.getElementById('dishDesc').value.trim(),
                image_url: document.getElementById('dishImg').value.trim()
            };

            fetch('/api/admin/menu/add', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            })
            .then(res => res.json())
            .then(data => {
                if (data.success) {
                    alert(data.message);
                    location.reload();
                } else {
                    alert("Error: " + data.error);
                }
            })
            .catch(err => alert("Network error adding dish."));
        });
    }

    // Edit Dish Form
    const editForm = document.getElementById('editDishForm');
    if (editForm) {
        editForm.addEventListener('submit', (e) => {
            e.preventDefault();
            const itemId = document.getElementById('editDishId').value;
            const payload = {
                name: document.getElementById('editDishName').value.trim(),
                category_id: document.getElementById('editDishCategory').value,
                price: parseFloat(document.getElementById('editDishPrice').value),
                is_veg: parseInt(document.getElementById('editDishVeg').value),
                is_available: parseInt(document.getElementById('editDishAvailable').value),
                description: document.getElementById('editDishDesc').value.trim(),
                image_url: document.getElementById('editDishImg').value.trim()
            };

            fetch(`/api/admin/menu/${itemId}/edit`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            })
            .then(res => res.json())
            .then(data => {
                if (data.success) {
                    alert(data.message);
                    location.reload();
                } else {
                    alert("Error: " + data.error);
                }
            })
            .catch(err => alert("Network error updating dish."));
        });
    }
}

function openEditDishModal(dish) {
    document.getElementById('editDishId').value = dish.id;
    document.getElementById('editDishName').value = dish.name;
    document.getElementById('editDishCategory').value = dish.category_id;
    document.getElementById('editDishPrice').value = dish.price;
    document.getElementById('editDishVeg').value = dish.is_veg;
    document.getElementById('editDishAvailable').value = dish.is_available;
    document.getElementById('editDishDesc').value = dish.description || '';
    document.getElementById('editDishImg').value = dish.image_url || '';

    const modalEl = document.getElementById('editDishModal');
    const bsModal = bootstrap.Modal.getOrCreateInstance(modalEl);
    bsModal.show();
}

function deleteDish(dishId, dishName) {
    if (!confirm(`Are you sure you want to permanently delete "${dishName}" from the menu?`)) {
        return;
    }

    fetch(`/api/admin/menu/${dishId}/delete`, { method: 'POST' })
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                alert(data.message);
                location.reload();
            } else {
                alert("Error deleting dish: " + data.error);
            }
        })
        .catch(err => alert("Network error deleting dish."));
}
