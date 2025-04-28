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
    
    // Handle delete account confirmation
    window.confirmDelete = function() {
        if (confirm("Are you sure you want to delete your account? This action cannot be undone.")) {
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