(function () {
  var stationId  = document.body.dataset.stationId;
  var clockEl    = document.getElementById("kv2-clock");
  var dateEl     = document.getElementById("kv2-date");
  var countEl    = document.getElementById("kv2-count");
  var snameEl    = document.getElementById("kv2-station-name");
  var gridEl     = document.getElementById("kv2-bike-grid");
  var errorEl    = document.getElementById("kv2-error");
  var loraBanner = document.getElementById("lora-banner");

  // ── Live clock ──────────────────────────────────────────────────
  function updateClock() {
    var now = new Date();
    clockEl.textContent = now.toLocaleTimeString("es-GT", { hour: "2-digit", minute: "2-digit" });
    dateEl.textContent  = now.toLocaleDateString("es-GT", { weekday: "long", day: "numeric", month: "long" });
  }
  updateClock();
  setInterval(updateClock, 1000);

  // ── Bike icon SVG ───────────────────────────────────────────────
  function bikeIcon(col) {
    return '<svg width="18" height="13" viewBox="0 0 32 23" fill="none">'
      + '<circle cx="6"  cy="17" r="4.5" stroke="' + col + '" stroke-width="2"/>'
      + '<circle cx="26" cy="17" r="4.5" stroke="' + col + '" stroke-width="2"/>'
      + '<polyline points="6,17 13,5 19,5 23,17" fill="none" stroke="' + col + '" stroke-width="2" stroke-linejoin="round"/>'
      + '<line x1="16" y1="5" x2="26" y2="17" stroke="' + col + '" stroke-width="2"/>'
      + '<line x1="9"  y1="5" x2="19" y2="5"  stroke="' + col + '" stroke-width="2" stroke-linecap="round"/>'
      + '<line x1="13" y1="5" x2="13" y2="2"  stroke="' + col + '" stroke-width="2" stroke-linecap="round"/>'
      + '<line x1="10" y1="2" x2="16" y2="2"  stroke="' + col + '" stroke-width="2" stroke-linecap="round"/>'
      + '</svg>';
  }

  // ── Station status poll ──────────────────────────────────────────
  async function loadStationStatus() {
    try {
      var r = await fetch("/api/stations/" + stationId + "/status");
      var d = await r.json();
      if (!r.ok || !d.ok) throw new Error(d.reason || "Estado desconocido.");

      loraBanner.style.display = d.lora_ok === false ? "block" : "none";

      countEl.textContent = String(d.available_count);
      if (d.station && d.station.name) snameEl.textContent = d.station.name;

      gridEl.innerHTML = "";
      if (!d.available_bikes || !d.available_bikes.length) {
        gridEl.innerHTML = '<div class="idle-empty">Sin bicicletas disponibles en este momento.</div>';
        return;
      }

      d.available_bikes.forEach(function (bike) {
        var card = document.createElement("div");
        card.className = "idle-bike-card";
        card.innerHTML = '<div class="idle-bike-icon">' + bikeIcon("#5a514a") + '</div>'
          + '<div class="idle-bike-id">' + bike.bike_id + '</div>'
          + '<div class="idle-bike-stat">Lista</div>';
        gridEl.appendChild(card);
      });
    } catch (err) {
      countEl.textContent = "--";
      gridEl.innerHTML = '<div class="idle-empty">No se pudo cargar la lista de bicicletas.</div>';
      errorEl.textContent = err.message;
      errorEl.style.display = "block";
    }
  }

  loadStationStatus();
  setInterval(loadStationStatus, 5000);
})();
