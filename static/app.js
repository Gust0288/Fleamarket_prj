const search_results = document.querySelector("#search_results")
const input_search = document.querySelector("#input_search")
let my_timer = null

// setTimeout - runs only 1 time
// setInterval - runs forever in intervals
function search(){
    clearInterval(my_timer)
    if (input_search.value != ""){
        my_timer = setTimeout( async function(){
            try{                
                const search_for = input_search.value
                const conn = await fetch(`/search?q=${search_for}`)
                const data = await conn.json()
                search_results.innerHTML = ""
                console.log(data)
                data.forEach(item => {
                    const a = `<div class="instant-item" mix-get="/items/${item.item_pk}">
                                <img src="/static/uploads/${item.item_image}">
                                <a href="/${item.item_name}">${item.item_name}</a>
                                </div>`
                    search_results.insertAdjacentHTML("beforeend", a)
                })
                mix_convert()
                search_results.classList.remove("hidden")
            }catch(err){
                console.error(err)
            }
        }, 500 )
    }else{
        search_results.innerHTML = ""
        search_results.classList.add("hidden")
    }
}



addEventListener("click", function(event){
    if( ! search_results.contains(event.target) ){
        search_results.classList.add("hidden")
    }
    if( input_search.contains(event.target) ){
        search_results.classList.remove("hidden")
    }
})

function add_markers_to_map(data){
    console.log(data)
    data = JSON.parse(data)
    console.log(data)
    data.forEach(item=>{
        // Create custom icon with image instead of text
        var customIcon = L.divIcon({
            className: 'custom-marker-image',
            html: `<div mix-get="/items/${item.item_pk}?show_address=true" class="custom-marker-container">
                    <img src="/static/uploads/${item.item_image}" class="marker-image">
                   </div>`,
            iconSize: [50, 50],
            iconAnchor: [25, 25],
        });
        
        // Use the custom icon for the marker
        var marker = L.marker([item.item_lat, item.item_lon], { icon: customIcon }).addTo(map);
        marker.on('click', function() {
            // Use fetch to get item details and update the right panel
            fetch(`/items/${item.item_pk}?show_address=true`)
                .then(response => response.text())
                .then(html => {
                    const parser = new DOMParser();
                    const doc = parser.parseFromString(html, 'text/html');
                    const itemContent = doc.querySelector('mixhtml[mix-replace="#item"]').innerHTML;
                    document.querySelector('#item').innerHTML = itemContent;
                    // Add this line to load address after content is updated
                    loadItemAddress();
                });
        });
    })
}


function onMarkerClick(event) {
    alert("Marker clicked at " + event.latlng);
}

// function confirmDelete() {
//     if (confirm("Are you sure you want to delete your account? This action cannot be undone.")) {
//         document.getElementById('delete-form').dispatchEvent(new Event('submit'));
//     }
// }

function loadItemAddress() {
    // Find all item address elements that need loading
    document.querySelectorAll('.item-address').forEach(addressEl => {
        // Get the item element (parent or ancestor of the address element)
        const itemEl = addressEl.closest('#item');
        if (!itemEl) return;
        
        const lat = itemEl.dataset.lat;
        const lon = itemEl.dataset.lon;
        
        // Check if we have valid coordinates
        if (lat && lon && addressEl) {
            // Don't reload if already loaded (not showing loading message)
            if (!addressEl.querySelector('i')) return;

            const htmlElement = document.documentElement;
            const viewOnMapText = htmlElement.getAttribute('data-view-on-map') || 'View on map';
            const addressNotFoundText = htmlElement.getAttribute('data-address-not-found') || 'Address not found';
            const coordinatesText = htmlElement.getAttribute('data-coordinates') || 'Coordinates';
            
            // Use Nominatim API for reverse geocoding (free, no API key required)
            fetch(`https://nominatim.openstreetmap.org/reverse?format=json&lat=${lat}&lon=${lon}&zoom=18&addressdetails=1`)
                .then(response => response.json())
                .then(data => {
                    if (data && data.display_name) {
                        // Create nicely formatted address
                        let address = data.address;
                        let formattedAddress = '';
                        
                        if (address) {
                            const parts = [];
                            if (address.road) parts.push(address.road);
                            if (address.house_number) parts.push(address.house_number);
                            if (address.suburb) parts.push(address.suburb);
                            if (address.city || address.town) parts.push(address.city || address.town);
                            if (address.postcode) parts.push(address.postcode);
                            
                            formattedAddress = parts.join(', ');
                        }
                        
                        // Use formatted address or fall back to display_name
                        addressEl.innerHTML = formattedAddress || data.display_name;
                        
                        // Add map link
                        const mapLink = document.createElement('a');
                        mapLink.href = `https://www.openstreetmap.org/?mlat=${lat}&mlon=${lon}#map=17/${lat}/${lon}`;
                        mapLink.target = '_blank';
                        mapLink.classList.add('map-link');
                        mapLink.innerHTML = ` <small>${viewOnMapText}</small>`;
                        addressEl.appendChild(mapLink);
                    } else {
                        addressEl.textContent = addressNotFoundText;
                    }
                })
                .catch(error => {
                    console.error('Error fetching address:', error);
                    addressEl.textContent = `${coordinatesText}: ${lat}, ${lon}`;
                });
        } else {
            addressEl.textContent = "Coordinates: " + lat + ", " + lon;
        }
    });
}

// Add an event listener for when DOM content is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Load addresses for items on initial page load
    loadItemAddress();
});

// Run this function after any AJAX updates that might change the item content
function afterItemUpdate() {
    loadItemAddress();
}