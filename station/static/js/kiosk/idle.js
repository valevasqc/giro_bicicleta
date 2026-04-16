(function () {
    const body = document.body;
    const stationId = body.dataset.stationId;

    const stationNameEl = document.getElementById("station-name");
    const stationIdEl = document.getElementById("station-id");
    const countEl = document.getElementById("available-count");
    const bikeListEl = document.getElementById("bike-list");
    const errorEl = document.getElementById("error-message");

    async function loadStationStatus() {
        try {
            const response = await fetch(`/api/stations/${stationId}/status`);
            const payload = await response.json();

            if (!response.ok || !payload.ok) {
                throw new Error(payload.reason || "No se pudo cargar el estado de la estación.");
            }

            stationNameEl.textContent = payload.station.name;
            stationIdEl.textContent = payload.station.station_id;
            countEl.textContent = String(payload.available_count);

            bikeListEl.innerHTML = "";
            if (!payload.available_bikes.length) {
                const item = document.createElement("li");
                item.className = "placeholder";
                item.textContent = "No hay bicicletas disponibles en este momento.";
                bikeListEl.appendChild(item);
                return;
            }

            payload.available_bikes.forEach(function (bike) {
                const item = document.createElement("li");
                item.textContent = bike.bike_id;
                bikeListEl.appendChild(item);
            });
        } catch (error) {
            countEl.textContent = "--";
            bikeListEl.innerHTML = '<li class="placeholder">No se pudo cargar la lista de bicicletas.</li>';
            errorEl.hidden = false;
            errorEl.textContent = error.message;
        }
    }

    loadStationStatus();
})();
