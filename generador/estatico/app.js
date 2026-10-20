(function () {
  "use strict";
  var BASE = window.BASE || "";

  function sinAcentos(t) {
    return t.toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "");
  }
  function precio(p) {
    return p == null ? "—" : p.toFixed(3).replace(".", ",") + " €";
  }
  function esc(t) {
    var d = document.createElement("div");
    d.textContent = t;
    return d.innerHTML;
  }

  // ---------- buscador de municipios ----------
  var indice = null;
  function cargarIndice() {
    if (!indice) {
      indice = fetch(BASE + "/buscar.json").then(function (r) { return r.json(); }).then(function (lista) {
        return lista.map(function (x) { return { n: x[0], p: x[1], u: x[2], c: x[3], k: sinAcentos(x[0]) }; });
      });
    }
    return indice;
  }
  document.querySelectorAll("[data-buscador]").forEach(function (input) {
    var caja = input.parentNode.querySelector("[data-sugerencias]");
    var activo = -1;
    input.addEventListener("focus", cargarIndice);
    input.addEventListener("input", function () {
      var q = sinAcentos(input.value.trim());
      if (q.length < 2) { caja.hidden = true; return; }
      cargarIndice().then(function (lista) {
        var empiezan = [], contienen = [];
        lista.forEach(function (m) {
          var i = m.k.indexOf(q);
          if (i === 0) empiezan.push(m); else if (i > 0) contienen.push(m);
        });
        var orden = function (a, b) { return b.c - a.c; };
        var res = empiezan.sort(orden).concat(contienen.sort(orden)).slice(0, 8);
        activo = -1;
        caja.innerHTML = res.length ? res.map(function (m) {
          return '<li><a href="' + m.u + '">' + esc(m.n) + ' <small>' + esc(m.p) + " · " + m.c +
            (m.c === 1 ? " gasolinera" : " gasolineras") + "</small></a></li>";
        }).join("") : '<li><span class="nota" style="padding:10px 12px;display:block">No hay gasolineras con ese nombre de municipio</span></li>';
        caja.hidden = false;
      });
    });
    input.addEventListener("keydown", function (ev) {
      var enlaces = caja.querySelectorAll("a");
      if (!enlaces.length) return;
      if (ev.key === "ArrowDown" || ev.key === "ArrowUp") {
        ev.preventDefault();
        activo = (activo + (ev.key === "ArrowDown" ? 1 : -1) + enlaces.length) % enlaces.length;
        enlaces.forEach(function (a, i) { a.classList.toggle("activo", i === activo); });
      } else if (ev.key === "Enter") {
        ev.preventDefault();
        window.location.href = enlaces[activo >= 0 ? activo : 0].href;
      }
    });
    document.addEventListener("click", function (ev) {
      if (!input.parentNode.contains(ev.target)) caja.hidden = true;
    });
  });

  // ---------- gasolineras cerca de mí ----------
  function distancia(a, b, c, d) {
    var r = Math.PI / 180, x = Math.sin((c - a) * r / 2), y = Math.sin((d - b) * r / 2);
    var h = x * x + Math.cos(a * r) * Math.cos(c * r) * y * y;
    return 12742 * Math.asin(Math.sqrt(h));
  }
  document.querySelectorAll("[data-cerca]").forEach(function (boton) {
    var salida = document.querySelector("[data-cerca-resultado]");
    boton.addEventListener("click", function () {
      if (!navigator.geolocation) { salida.hidden = false; salida.textContent = "Tu navegador no permite obtener la ubicación."; return; }
      salida.hidden = false;
      salida.innerHTML = '<p class="nota">Buscando tu ubicación…</p>';
      navigator.geolocation.getCurrentPosition(function (pos) {
        var lat = pos.coords.latitude, lon = pos.coords.longitude;
        fetch(BASE + "/estaciones.json").then(function (r) { return r.json(); }).then(function (lista) {
          var cerca = lista.map(function (e) { return { e: e, d: distancia(lat, lon, e[0], e[1]) }; })
            .filter(function (x) { return x.d <= 10; });
          if (!cerca.length) { salida.innerHTML = '<p class="nota">No hay gasolineras a menos de 10 km.</p>'; return; }
          function bloque(titulo, idx) {
            var top = cerca.filter(function (x) { return x.e[idx] != null; })
              .sort(function (a, b) { return a.e[idx] - b.e[idx] || a.d - b.d; }).slice(0, 5);
            return '<section class="bloque"><h2>' + titulo + ' a menos de 10 km</h2><ol class="ranking">' +
              top.map(function (x) {
                var e = x.e;
                return '<li><span class="ranking-precio">' + precio(e[idx]) + '</span><span class="ranking-nombre"><strong>' +
                  esc(e[2]) + "</strong> · " + esc(e[3]) + '</span><span class="ranking-lugar"><a href="' + e[5] + '">' +
                  esc(e[4]) + "</a> · a " + x.d.toFixed(1).replace(".", ",") + ' km · <a href="https://www.google.com/maps/dir/?api=1&destination=' +
                  e[0] + "," + e[1] + '" target="_blank" rel="nofollow noopener">Cómo llegar</a></span></li>';
              }).join("") + "</ol></section>";
          }
          salida.innerHTML = '<div class="dos-columnas">' + bloque("Diésel más barato", 6) + bloque("Gasolina 95 más barata", 7) + "</div>";
        }).catch(function () { salida.innerHTML = '<p class="nota">No se pudieron cargar los precios. Inténtalo de nuevo.</p>'; });
      }, function () {
        salida.innerHTML = '<p class="nota">No hemos podido acceder a tu ubicación. Usa el buscador para elegir tu municipio.</p>';
      }, { enableHighAccuracy: false, timeout: 10000, maximumAge: 300000 });
    });
  });

  // ---------- ordenar tablas ----------
  document.querySelectorAll("table.ordenable").forEach(function (tabla) {
    tabla.querySelectorAll("th[data-orden]").forEach(function (th) {
      th.addEventListener("click", function () {
        var col = Array.prototype.indexOf.call(th.parentNode.children, th);
        var cuerpo = tabla.tBodies[0];
        var filas = Array.prototype.slice.call(cuerpo.rows);
        var asc = !(th.classList.contains("ordenado") && th.dataset.dir === "asc");
        filas.sort(function (a, b) {
          var x = parseFloat(a.cells[col].dataset.valor), y = parseFloat(b.cells[col].dataset.valor);
          return asc ? x - y : y - x;
        });
        filas.forEach(function (f) { cuerpo.appendChild(f); });
        tabla.querySelectorAll("th").forEach(function (t) { t.classList.remove("ordenado"); });
        th.classList.add("ordenado");
        th.dataset.dir = asc ? "asc" : "desc";
      });
    });
  });
})();
