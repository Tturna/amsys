var map = L.map('map').setView([57.34839467541909, 16.092050838746783], 4);

L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19,
    attribution: '&copy; <a href="http://www.openstreetmap.org/copyright">OpenStreetMap</a>'
}).addTo(map);

// Assume the template defines locations and connections
locations.forEach(location => {
    let name = location["location_name"];
    let lat = parseFloat(location["latitude"]);
    let lng = parseFloat(location["longitude"]);
    let info = location["info"];
    let code = location["code"];
    let apps = location["apps"];

    let code_string = code && code.length > 0 ? ` - ${code}` : "";
    let info_string = info && info.length > 0 ? `${info}<br>` : "";
    let apps_string;

    if (apps.length > 0) {
        apps_string = "<strong>Apps:</strong><br>" + apps
            .map(app => `<a href=/view_instance/${app["app_name"]}>${app["app_name"]}</a>`)
            .join("<br>")
    } else {
        apps_string = "No apps in this location."
    }

    L.marker([lat, lng]).addTo(map)
        .bindPopup(`<strong>${name}</strong>${code_string}<br>${lat},${lng}<br>${info_string}${apps_string}`);
});

connections.forEach(connection => {
    var polyLine = L.polyline(connection, { color: "red" });
    polyLine.addTo(map);
});
