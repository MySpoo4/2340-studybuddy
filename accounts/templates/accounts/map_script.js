function initializeProfileMap() {
    const mapContainer = document.getElementById('map');
    // If the map container doesn't exist, or if it already has been initialized, do nothing.
    if (!mapContainer || mapContainer._leaflet_id) {
        return;
    }

    const latInput = document.getElementById('latitude');
    const lngInput = document.getElementById('longitude');

    // Default to a central US location if no coordinates are set
    const initialLat = parseFloat(latInput.value) || 39.8283;
    const initialLng = parseFloat(lngInput.value) || -98.5795;
    const initialZoom = latInput.value ? 13 : 4;

    const map = L.map('map').setView([initialLat, initialLng], initialZoom);

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
    }).addTo(map);

    // --- Robust Map Invalidation ---
    // This is the most critical part. It ensures the map recalculates its size.
    setTimeout(() => map.invalidateSize(), 100);
    document.getElementById('sidebar-toggle')?.addEventListener('click', () => setTimeout(() => map.invalidateSize(), 350));
    window.addEventListener('resize', () => map.invalidateSize());

    let marker = null;
    if (latInput.value && lngInput.value) {
        marker = L.marker([initialLat, initialLng]).addTo(map);
    }

    function updateMarkerAndInputs(lat, lng) {
        latInput.value = lat;
        lngInput.value = lng;
        if (marker) {
            marker.setLatLng([lat, lng]);
        } else {
            marker = L.marker([lat, lng]).addTo(map);
        }
        map.setView([lat, lng], 13);
    }

    map.on('click', function(e) {
        updateMarkerAndInputs(e.latlng.lat, e.latlng.lng);
    });

    document.getElementById('use-current-location').addEventListener('click', function() {
        if (navigator.geolocation) {
            navigator.geolocation.getCurrentPosition(function(position) {
                updateMarkerAndInputs(position.coords.latitude, position.coords.longitude);
            }, function() {
                alert('Error: The Geolocation service failed.');
            });
        } else {
            alert("Error: Your browser doesn't support geolocation.");
        }
    });
}

// Run the initialization function
initializeProfileMap();