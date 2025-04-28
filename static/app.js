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
        // Create custom icon with image instead of just text
        var customIcon = L.divIcon({
            className: 'custom-marker-image',
            html: `<div mix-get="/items/${item.item_pk}" class="custom-marker-container">
                    <img src="/static/uploads/${item.item_image}" class="marker-image">
                   </div>`,
            iconSize: [50, 50],
            iconAnchor: [25, 25],
        });
        
        // Use the custom icon for the marker
        var marker = L.marker([item.item_lat, item.item_lon], { icon: customIcon }).addTo(map);
        marker.on('click', function() {
            // Use fetch to get item details and update the right panel
            fetch(`/items/${item.item_pk}`)
                .then(response => response.text())
                .then(html => {
                    const parser = new DOMParser();
                    const doc = parser.parseFromString(html, 'text/html');
                    const itemContent = doc.querySelector('mixhtml[mix-replace="#item"]').innerHTML;
                    document.querySelector('#item').innerHTML = itemContent;
                    mix_convert(); // Re-initialize mixhtml functionality
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