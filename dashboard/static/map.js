var map = L.map('map').setView([57.34839467541909, 16.092050838746783], 4);

L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19,
    attribution: '&copy; <a href="http://www.openstreetmap.org/copyright">OpenStreetMap</a>'
}).addTo(map);

orgs.forEach(org => {
    let name = org["org_name"];
    let lat = parseFloat(org["latitude"]);
    let lng = parseFloat(org["longitude"]);

    L.marker([lat, lng]).addTo(map)
        .bindPopup(`${name}<br>${lat},${lng}`);
});

