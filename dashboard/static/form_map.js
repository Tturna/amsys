var map = L.map('map').setView([57.34839467541909, 16.092050838746783], 4);

L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19,
    attribution: '&copy; <a href="http://www.openstreetmap.org/copyright">OpenStreetMap</a>'
}).addTo(map);

let org_marker;
const input_lat = document.getElementById("id_latitude");
const input_lng = document.getElementById("id_longitude");

function update_org_marker(lat, lng) {
    if (org_marker) {
        org_marker.remove();
    }

    org_marker = L.marker([lat, lng])
        .addTo(map)
        .bindPopup(`Organization location: ${lat}, ${lng}`);

    input_lat.value = lat;
    input_lng.value = lng;
}

input_lat.addEventListener("input", e => { update_org_marker(input_lat.value, input_lng.value) });
input_lng.addEventListener("input", e => { update_org_marker(input_lat.value, input_lng.value) });
map.on("click", e => { update_org_marker(e.latlng.lat, e.latlng.lng) });

