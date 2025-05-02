document.addEventListener('DOMContentLoaded', function() {
    // Check if we're on the profile page and the user is logged in
    const userItemsElement = document.getElementById('user_items');
    if (userItemsElement) {
        // Get the user_pk from the data attribute
        const userPk = userItemsElement.getAttribute('data-user-pk');
        if (userPk) {
            fetch(`/items/user/${userPk}`)
                .then(response => {
                    if (!response.ok) {
                        throw new Error('Failed to load items');
                    }
                    return response.text();
                })
                .then(html => {
                    // Process the mixhtml response
                    const parser = new DOMParser();
                    const doc = parser.parseFromString(html, 'text/html');
                    const content = doc.querySelector('mixhtml[mix-replace="#user_items"]').innerHTML;
                    userItemsElement.innerHTML = content;
                    // Re-initialize mixhtml
                    mix_convert();
                })
                .catch(error => {
                    console.error('Error loading items:', error);
                    userItemsElement.innerHTML = '<p>Error loading your items</p>';
                });
        } else {
            userItemsElement.innerHTML = '<p>User information not available</p>';
        }
    }
    
    // Modal functionality
    const modal = document.getElementById('edit-item-modal');
    const closeBtn = document.querySelector('.close-modal');
    
    // Close modal when clicking the × button
    if(closeBtn) {
        closeBtn.onclick = function() {
            modal.style.display = "none";
        }
    }
    
    // Close modal when clicking outside of it
    window.onclick = function(event) {
        if (event.target == modal) {
            modal.style.display = "none";
        }
    }
        window.confirmDelete = function() {
            const confirmMessage = getLanguageText('confirm-delete-account', 'Are you sure you want to delete your account? This action cannot be undone.');
            if (confirm(confirmMessage)) {
                document.getElementById('delete-form').dispatchEvent(new Event('submit'));
            }
        }
});

// Function to open the modal and populate it with the item data
function openEditModal(itemPk, name, price, lon, lat, image) {
    const modal = document.getElementById('edit-item-modal');
    
    // Populate form fields
    document.getElementById('edit-item-pk').value = itemPk;
    document.getElementById('edit-name').value = name;
    document.getElementById('edit-price').value = price;
    document.getElementById('edit-lon').value = lon;
    document.getElementById('edit-lat').value = lat;
    document.getElementById('edit-current-image').src = `/static/uploads/${image}`;
    
    // Display the modal
    modal.style.display = "block";
}

function showErrorMessage(errorMessage) {
    const passwordError = document.getElementById('password-error');
    if (passwordError) {
        passwordError.textContent = errorMessage || document.documentElement.getAttribute('data-error-default');
        passwordError.style.display = "block";
    }
}

function getLanguageText(key, defaultText) {
    const htmlElement = document.documentElement;
    const lang = htmlElement ? htmlElement.getAttribute('lang') || 'en' : 'en';
    const dataKey = `data-text-${key}`;
    
    return htmlElement.getAttribute(dataKey) || defaultText;
}


// Delete account modal functionality
const deleteModal = document.getElementById('delete-account-modal');
const closeDeleteBtn = document.getElementById('close-delete-modal');
const cancelDeleteBtn = document.getElementById('cancel-delete');
const deletePasswordForm = document.getElementById('delete-password-form');
const passwordError = document.getElementById('password-error');

// Function to open delete confirmation modal
window.openDeleteModal = function() {
    deleteModal.style.display = "block";
    // Reset form and error message
    deletePasswordForm.reset();
    passwordError.style.display = "none";
}

// Close modal when clicking the × button
if(closeDeleteBtn) {
    closeDeleteBtn.onclick = function() {
        deleteModal.style.display = "none";
    }
}

// Close modal when clicking the cancel button
if(cancelDeleteBtn) {
    cancelDeleteBtn.onclick = function() {
        deleteModal.style.display = "none";
    }
}

// Update window.onclick to handle both modals
window.onclick = function(event) {
    if (event.target == deleteModal) {
        deleteModal.style.display = "none";
    } else if (event.target == modal) {
        modal.style.display = "none";
    }
}

if(deletePasswordForm) {
    deletePasswordForm.addEventListener('submit', function(event) {
        event.preventDefault();
        
        const password = document.getElementById('confirm-password').value;
        
        if (!password) {
            passwordError.textContent = "Please enter your password to confirm";
            passwordError.style.display = "block";
            return;
        }
        
        // Use fetch to submit the form with the password
        fetch('/user', {
            method: 'DELETE',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
            },
            body: `password=${encodeURIComponent(password)}`
        })
        .then(response => response.text())  
        .then(html => {
            // Now process the HTML content
        if (html.includes('mix-redirect="/login') || html.includes('success-message')) {
        // Success, get the success message language from HTML
        const deleteSuccessMsg = document.documentElement.getAttribute('data-delete-success') || 
                               "Account deleted successfully. A confirmation email has been sent.";
        
        // Redirect to login page with the success message
        window.location.href = "/login?message=" + encodeURIComponent(deleteSuccessMsg);
        } else {
        // Extract and display error message
        const errorMatch = html.match(/<div id="error-message">(.*?)<\/div>/);
        if (errorMatch && errorMatch[1]) {
            passwordError.textContent = errorMatch[1];
        } else {
            // Get the language-specific error message or fall back to default
            const defaultErrorMsg = document.documentElement.getAttribute('data-error-default') || 
                                "An error occurred. Please try again.";
            passwordError.textContent = defaultErrorMsg;
        }
        passwordError.style.display = "block";
            }
        })
    });
}



