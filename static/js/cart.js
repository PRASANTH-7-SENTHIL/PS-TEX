// Cart & Wishlist AJAX Operations - PS-TEX

document.addEventListener('DOMContentLoaded', () => {
    const getCsrfToken = () => {
        const meta = document.querySelector('meta[name="csrf-token"]');
        return meta ? meta.getAttribute('content') : '';
    };

    // Add to Cart Handler (Dynamic AJAX)
    const addToCartForms = document.querySelectorAll('.add-to-cart-form');
    addToCartForms.forEach(form => {
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            const submitBtn = form.querySelector('button[type="submit"]');
            const originalText = submitBtn.innerHTML;
            
            submitBtn.disabled = true;
            submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Adding...';

            const formData = new FormData(form);
            
            try {
                const response = await fetch('/cart/add', {
                    method: 'POST',
                    headers: {
                        'X-CSRFToken': getCsrfToken()
                    },
                    body: formData
                });
                
                const data = await response.json();
                
                if (data.success) {
                    // Show notification
                    showNotification(data.message, 'success');
                    
                    // Update cart badge in navbar
                    const cartBadges = document.querySelectorAll('.cart-badge');
                    cartBadges.forEach(badge => {
                        badge.textContent = data.cart_count;
                        badge.classList.remove('d-none');
                    });
                } else {
                    showNotification(data.message || 'Error adding item.', 'danger');
                }
            } catch (err) {
                console.error(err);
                showNotification('Something went wrong. Please try again.', 'danger');
            } finally {
                submitBtn.disabled = false;
                submitBtn.innerHTML = originalText;
            }
        });
    });

    // Wishlist Add Handler
    const wishlistBtns = document.querySelectorAll('.btn-wishlist-ajax');
    wishlistBtns.forEach(btn => {
        btn.addEventListener('click', async (e) => {
            e.preventDefault();
            const productId = btn.getAttribute('data-product-id');
            if (!productId) return;
            
            const formData = new FormData();
            formData.append('product_id', productId);
            
            try {
                const response = await fetch('/wishlist/add', {
                    method: 'POST',
                    headers: {
                        'X-CSRFToken': getCsrfToken()
                    },
                    body: formData
                });
                
                const data = await response.json();
                if (data.success) {
                    showNotification(data.message, 'success');
                    btn.classList.add('active');
                    btn.querySelector('i').classList.replace('bi-heart', 'bi-heart-fill');
                } else {
                    // If not authenticated, redirect to login
                    if (response.status === 401) {
                        window.location.href = '/login?next=' + encodeURIComponent(window.location.pathname);
                    } else {
                        showNotification(data.message || 'Error updating wishlist.', 'danger');
                    }
                }
            } catch (err) {
                console.error(err);
                showNotification('Unable to update wishlist.', 'danger');
            }
        });
    });

    // Cart Quantity Update Handler (Direct Page Update)
    const qtyInputs = document.querySelectorAll('.cart-qty-input');
    qtyInputs.forEach(input => {
        input.addEventListener('change', async (e) => {
            const productId = input.getAttribute('data-product-id');
            let quantity = parseInt(input.value);
            const maxVal = parseInt(input.getAttribute('max'));
            
            if (quantity > maxVal) {
                showNotification(`Only ${maxVal} items available in stock.`, 'warning');
                quantity = maxVal;
                input.value = maxVal;
            }
            
            if (quantity < 1 || isNaN(quantity)) {
                quantity = 1;
                input.value = 1;
            }
            
            const formData = new FormData();
            formData.append('product_id', productId);
            formData.append('quantity', quantity);
            
            try {
                const response = await fetch('/cart/update', {
                    method: 'POST',
                    headers: {
                        'X-CSRFToken': getCsrfToken()
                    },
                    body: formData
                });
                
                const data = await response.json();
                if (data.success) {
                    // Update item total price in row
                    const rowTotal = document.querySelector(`.item-total-[data-product-id="${productId}"]`);
                    if (rowTotal) {
                        rowTotal.textContent = `₹${parseFloat(data.item_total).toFixed(2)}`;
                    }
                    
                    // Update Cart Subtotal and Grand Totals
                    const subtotalEl = document.getElementById('cart-subtotal');
                    if (subtotalEl) {
                        subtotalEl.textContent = `₹${parseFloat(data.subtotal).toFixed(2)}`;
                    }
                    const grandTotalEl = document.getElementById('cart-grandtotal');
                    if (grandTotalEl) {
                        grandTotalEl.textContent = `₹${parseFloat(data.subtotal).toFixed(2)}`;
                    }
                    
                    showNotification('Cart updated.', 'success');
                } else {
                    showNotification(data.message || 'Error updating quantity.', 'danger');
                }
            } catch (err) {
                console.error(err);
                showNotification('Could not update cart quantity.', 'danger');
            }
        });
    });

    // Toast Notification Maker
    const showNotification = (message, type = 'success') => {
        // Create container if it doesn't exist
        let container = document.getElementById('toast-container');
        if (!container) {
            container = document.createElement('div');
            container.id = 'toast-container';
            container.className = 'toast-container position-fixed bottom-0 end-0 p-3';
            container.style.zIndex = '9999';
            document.body.appendChild(container);
        }

        const toastId = 'toast-' + Date.now();
        const iconClass = type === 'success' ? 'bi-check-circle-fill text-success' : 'bi-exclamation-triangle-fill text-danger';
        
        const toastHtml = `
            <div id="${toastId}" class="toast align-items-center border-0 show" role="alert" aria-live="assertive" aria-atomic="true">
                <div class="d-flex bg-white shadow-sm rounded">
                    <div class="toast-body d-flex align-items-center">
                        <i class="bi ${iconClass} me-2 fs-5"></i>
                        <span>${message}</span>
                    </div>
                    <button type="button" class="btn-close me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
                </div>
            </div>
        `;
        
        container.insertAdjacentHTML('beforeend', toastHtml);
        const toastEl = document.getElementById(toastId);
        
        // Remove toast automatically after 4 seconds
        setTimeout(() => {
            if (toastEl) {
                toastEl.classList.remove('show');
                setTimeout(() => toastEl.remove(), 500);
            }
        }, 4000);
        
        // Add manual close event
        const closeBtn = toastEl.querySelector('.btn-close');
        closeBtn.addEventListener('click', () => {
            toastEl.classList.remove('show');
            setTimeout(() => toastEl.remove(), 500);
        });
    };
});
