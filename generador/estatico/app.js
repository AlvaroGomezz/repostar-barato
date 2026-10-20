(function () {
  "use strict";
  var BASE = window.BASE || "";
  var raiz = document.documentElement;
  var COMBS = ["diesel", "g95", "g98", "glp"];
  var NOMBRES = { diesel: "diésel", g95: "gasolina 95", g98: "gasolina 98", glp: "GLP" };
  var euros = new Intl.NumberFormat("es-ES", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  var litro = new Intl.NumberFormat("es-ES", { minimumFractionDigits: 3, maximumFractionDigits: 3 });
  var km = new Intl.NumberFormat("es-ES", { minimumFractionDigits: 1, maximumFractionDigits: 1 });

  function $$(sel, el) { return Array.prototype.slice.call((el || document).querySelectorAll(sel)); }
  function guardar(k, v) { try { localStorage.setItem(k, v); } catch (e) {} }
  function sinAcentos(t) { return (t || "").toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, ""); }
  function esc(t) { var d = document.createElement("div"); d.textContent = t == null ? "" : t; return d.innerHTML; }
  function comb() { return raiz.getAttribute("data-comb") || "diesel"; }
  // Estadísticas sin cookies: cuántas veces se usa cada herramienta (GoatCounter).
  function contar(nombre) {
    try { if (window.goatcounter && window.goatcounter.count) window.goatcounter.count({ path: "evento/" + nombre, title: nombre, event: true }); } catch (e) {}
  }
  var alCambiarComb = [];
  var movimientoReducido = !!(window.matchMedia && matchMedia("(prefers-reduced-motion: reduce)").matches);
  function precioHTML(p) {
    return p == null ? '<span class="sin-dato">—</span>' :
      '<span class="cifra">' + litro.format(p) + '</span><span class="unidad"> €/l</span>';
  }
  function distancia(a, b, c, d) {
    var r = Math.PI / 180, x = Math.sin((c - a) * r / 2), y = Math.sin((d - b) * r / 2);
    return 12742 * Math.asin(Math.sqrt(x * x + Math.cos(a * r) * Math.cos(c * r) * y * y));
  }
  function ordenarPor(lista, clave) {
    var filas = $$(":scope > li", lista);
    filas.sort(function (a, b) {
      var x = parseFloat(a.getAttribute("data-" + clave)), y = parseFloat(b.getAttribute("data-" + clave));
      if (isNaN(x)) x = Infinity;
      if (isNaN(y)) y = Infinity;
      return x - y || (+a.getAttribute("data-i") - +b.getAttribute("data-i"));
    });
    filas.forEach(function (f) { lista.appendChild(f); });
  }
  function ordenOriginal(lista) {
    var filas = $$(":scope > li", lista);
    filas.sort(function (a, b) { return +a.getAttribute("data-i") - +b.getAttribute("data-i"); });
    filas.forEach(function (f) { lista.appendChild(f); });
  }
  $$("[data-lista], [data-orden-auto], [id$='-lista']").forEach(function (lista) {
    $$(":scope > li", lista).forEach(function (f, i) { f.setAttribute("data-i", i); });
  });

  // ---------- combustible ----------
  function aplicarComb(c, desdeUsuario) {
    raiz.setAttribute("data-comb", c);
    $$("[data-elegir]").forEach(function (a) {
      a.setAttribute("aria-current", a.getAttribute("data-elegir") === c ? "true" : "false");
    });
    // Listas ordenadas por precio: se reordenan con el combustible elegido.
    $$("[data-lista]").forEach(function (l) { if (!l.hasAttribute("data-por-distancia")) ordenarPor(l, c); });
    $$("[data-orden-auto], [data-por-precio]").forEach(function (l) { ordenarPor(l, c); });
    alCambiarComb.forEach(function (f) { f(c); });
    if (desdeUsuario) {
      guardar("rb-comb", c);
      try {
        var u = new URL(location.href);
        u.searchParams.set("c", c);
        history.replaceState(null, "", u.pathname + u.search + u.hash);
      } catch (e) {}
    }
  }
  document.addEventListener("click", function (ev) {
    var a = ev.target.closest && ev.target.closest("[data-elegir]");
    if (!a || ev.metaKey || ev.ctrlKey || ev.shiftKey || ev.button === 1) return;
    ev.preventDefault();
    aplicarComb(a.getAttribute("data-elegir"), true);
  });

  // ---------- litros del depósito ----------
  function aplicarLitros(l, desdeUsuario) {
    raiz.setAttribute("data-litros", l);
    $$("[data-litros]").forEach(function (b) {
      if (b.tagName === "BUTTON") b.setAttribute("aria-pressed", b.getAttribute("data-litros") === String(l) ? "true" : "false");
    });
    $$("[data-ahorro]").forEach(function (p) {
      var min = parseFloat(p.getAttribute("data-min")), max = parseFloat(p.getAttribute("data-max"));
      $$("[data-l]", p).forEach(function (x) { x.textContent = l; });
      var v = { min: min * l, max: max * l, ahorro: (max - min) * l };
      $$("[data-coste]", p).forEach(function (x) { x.textContent = euros.format(v[x.getAttribute("data-coste")]) + " €"; });
    });
    $$("[data-coste-l]").forEach(function (x) { x.textContent = euros.format(parseFloat(x.getAttribute("data-coste-l")) * l) + " €"; });
    if (desdeUsuario) guardar("rb-litros", l);
  }
  $$("button[data-litros]").forEach(function (b) {
    b.addEventListener("click", function () { aplicarLitros(+b.getAttribute("data-litros"), true); });
  });

  // ---------- ubicación ----------
  function ubicar(ok, mal) {
    if (!navigator.geolocation) { mal("Tu navegador no permite obtener la ubicación."); return; }
    navigator.geolocation.getCurrentPosition(function (pos) { ok(pos.coords.latitude, pos.coords.longitude); },
      function () { mal("No hemos podido acceder a tu ubicación. Revisa el permiso del navegador o busca tu municipio."); },
      { enableHighAccuracy: false, timeout: 10000, maximumAge: 300000 });
  }

  // Ordenar la lista de un municipio por cercanía.
  $$("[data-cercania]").forEach(function (boton) {
    var bloque = boton.closest(".bloque");
    var lista = bloque.querySelector("[data-lista]");
    var aviso = bloque.querySelector("[data-aviso-cercania]");
    boton.addEventListener("click", function () {
      if (boton.getAttribute("aria-pressed") === "true") {
        boton.setAttribute("aria-pressed", "false");
        lista.removeAttribute("data-por-distancia");
        aviso.hidden = true;
        ordenarPor(lista, comb());
        return;
      }
      aviso.hidden = false;
      aviso.textContent = "Buscando tu ubicación…";
      ubicar(function (lat, lon) {
        $$(":scope > li", lista).forEach(function (f) {
          var la = parseFloat(f.getAttribute("data-lat")), lo = parseFloat(f.getAttribute("data-lon"));
          var d = isNaN(la) ? Infinity : distancia(lat, lon, la, lo);
          f.setAttribute("data-dist", d);
          var s = f.querySelector("[data-distancia]");
          if (s) s.textContent = isFinite(d) ? "a " + km.format(d) + " km" : "";
        });
        lista.setAttribute("data-por-distancia", "");
        ordenarPor(lista, "dist");
        boton.setAttribute("aria-pressed", "true");
        aviso.textContent = "Ordenadas por distancia a tu ubicación. Pulsa otra vez para volver al orden por precio.";
      }, function (msg) { aviso.textContent = msg; });
    });
  });

  // Solo abiertas 24 horas.
  $$("[data-solo24]").forEach(function (boton) {
    var lista = boton.closest(".bloque").querySelector("[data-lista]");
    boton.addEventListener("click", function () {
      var activo = boton.getAttribute("aria-pressed") !== "true";
      boton.setAttribute("aria-pressed", activo ? "true" : "false");
      if (activo) lista.setAttribute("data-solo24-activo", ""); else lista.removeAttribute("data-solo24-activo");
    });
  });

  // Filtrar una lista por nombre.
  $$("[data-filtro-lista]").forEach(function (input) {
    var lista = document.getElementById(input.getAttribute("data-filtro-lista"));
    var vacio = lista.parentNode.querySelector("[data-sin-resultados]");
    input.addEventListener("input", function () {
      var q = sinAcentos(input.value.trim()), visibles = 0;
      $$(":scope > li", lista).forEach(function (f) {
        var ver = !q || sinAcentos(f.getAttribute("data-nombre")).indexOf(q) !== -1;
        f.hidden = !ver;
        if (ver) visibles++;
      });
      if (vacio) vacio.hidden = visibles > 0;
    });
  });

  // Ordenar una lista por precio o volver al orden alfabético.
  $$("[data-ordenar-lista]").forEach(function (boton) {
    var lista = document.getElementById(boton.getAttribute("data-ordenar-lista"));
    boton.addEventListener("click", function () {
      var activo = boton.getAttribute("aria-pressed") !== "true";
      boton.setAttribute("aria-pressed", activo ? "true" : "false");
      if (activo) { lista.setAttribute("data-por-precio", ""); ordenarPor(lista, comb()); }
      else { lista.removeAttribute("data-por-precio"); ordenOriginal(lista); }
    });
  });

  // ---------- buscador de municipios ----------
  // En la ruta, elegir un municipio no lleva a su página: guarda su nombre y sus coordenadas en el campo.
  function recoger(input, caja, a) {
    input.value = a.getAttribute("data-nombre");
    input.setAttribute("data-lat", a.getAttribute("data-lat"));
    input.setAttribute("data-lon", a.getAttribute("data-lon"));
    caja.hidden = true;
    input.setAttribute("aria-expanded", "false");
  }
  var indice = null;
  function cargarIndice() {
    if (!indice) {
      indice = fetch(BASE + "/buscar.json").then(function (r) { return r.json(); }).then(function (lista) {
        return lista.map(function (x) { return { n: x[0], p: x[1], u: x[2], c: x[3], la: x[4], lo: x[5], k: sinAcentos(x[0]) }; });
      });
    }
    return indice;
  }
  $$("[data-buscador]").forEach(function (input) {
    var caja = input.parentNode.querySelector("[data-sugerencias]");
    var activo = -1;
    input.addEventListener("focus", cargarIndice);
    input.addEventListener("input", function () {
      var q = sinAcentos(input.value.trim());
      if (q.length < 2) { caja.hidden = true; input.setAttribute("aria-expanded", "false"); return; }
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
          return '<li role="option"><a href="' + m.u + '" data-nombre="' + esc(m.n) + '" data-lat="' + m.la + '" data-lon="' + m.lo + '"><span>' + esc(m.n) + '</span><small>' + esc(m.p) + " · " + m.c +
            (m.c === 1 ? " gasolinera" : " gasolineras") + "</small></a></li>";
        }).join("") : '<li class="vacio">Ningún municipio con gasolinera se llama así. Prueba con otro nombre.</li>';
        caja.hidden = false;
        input.setAttribute("aria-expanded", "true");
      });
    });
    input.addEventListener("keydown", function (ev) {
      var enlaces = $$("a", caja);
      if (ev.key === "Escape") { caja.hidden = true; input.setAttribute("aria-expanded", "false"); return; }
      if (!enlaces.length) return;
      if (ev.key === "ArrowDown" || ev.key === "ArrowUp") {
        ev.preventDefault();
        activo = (activo + (ev.key === "ArrowDown" ? 1 : -1) + enlaces.length) % enlaces.length;
        enlaces.forEach(function (a, i) { a.classList.toggle("activo", i === activo); });
      } else if (ev.key === "Enter") {
        ev.preventDefault();
        var elegido = enlaces[activo >= 0 ? activo : 0];
        if (input.hasAttribute("data-recoger")) {
          recoger(input, caja, elegido);
        } else if (input.hasAttribute("data-zona-buscar") && window.__ponerMunicipio) {
          caja.hidden = true; input.setAttribute("aria-expanded", "false");
          window.__ponerMunicipio(elegido.getAttribute("href"), elegido.getAttribute("data-nombre"), input);
        } else {
          window.location.href = elegido.href;
        }
      }
    });
    caja.addEventListener("click", function (ev) {
      var a = ev.target.closest("a");
      if (a && input.hasAttribute("data-recoger") && !(ev.metaKey || ev.ctrlKey || ev.shiftKey)) {
        ev.preventDefault();
        recoger(input, caja, a);
        return;
      }
      if (!a || !input.hasAttribute("data-zona-buscar") || !window.__ponerMunicipio) return;
      if (ev.metaKey || ev.ctrlKey || ev.shiftKey) return;
      ev.preventDefault();
      caja.hidden = true; input.setAttribute("aria-expanded", "false");
      window.__ponerMunicipio(a.getAttribute("href"), a.getAttribute("data-nombre"), input);
    });
    document.addEventListener("click", function (ev) {
      if (!input.parentNode.contains(ev.target)) caja.hidden = true;
    });
  });
  $$("[data-abrir-menu]").forEach(function (b) {
    var zona = document.getElementById(b.getAttribute("aria-controls"));
    b.addEventListener("click", function () {
      var abrir = zona.hidden;
      zona.hidden = !abrir;
      b.setAttribute("aria-expanded", abrir ? "true" : "false");
    });
    $$("a", zona).forEach(function (a) { a.addEventListener("click", function () { zona.hidden = true; b.setAttribute("aria-expanded", "false"); }); });
  });
  $$("[data-abrir-busqueda]").forEach(function (b) {
    var zona = document.getElementById(b.getAttribute("aria-controls"));
    b.addEventListener("click", function () {
      var abrir = zona.hidden;
      zona.hidden = !abrir;
      b.setAttribute("aria-expanded", abrir ? "true" : "false");
      if (abrir) zona.querySelector("input").focus();
    });
  });

  // ---------- cifras que ruedan ----------
  function construirRodillo(el, texto) {
    var dig = document.createElement("span");
    dig.className = "roll__digits";
    dig.setAttribute("aria-hidden", "true");
    var i = 0;
    for (var k = 0; k < texto.length; k++) {
      var ch = texto[k];
      if (!/\d/.test(ch)) { var sep = document.createElement("span"); sep.className = "roll__sep"; sep.textContent = ch; dig.appendChild(sep); continue; }
      var col = document.createElement("span"); col.className = "roll__col";
      var tira = document.createElement("span"); tira.className = "roll__strip";
      tira.style.setProperty("--d", ch); tira.style.setProperty("--i", i++);
      col.appendChild(tira); dig.appendChild(col);
    }
    var dicho = document.createElement("span"); dicho.className = "oculto"; dicho.textContent = texto;
    el.replaceChildren(dicho, dig);
    el.classList.add("roll");
  }
  // Cifras grandes de la portada: ruedan una vez al entrar en pantalla.
  var rodillos = $$("[data-roll]");
  rodillos.forEach(function (el) { construirRodillo(el, el.textContent.trim()); });

  // ---------- entradas al hacer scroll ----------
  var aparecen = $$("[data-reveal]").concat(rodillos);
  if ("IntersectionObserver" in window && !movimientoReducido) {
    var io = new IntersectionObserver(function (entradas) {
      entradas.forEach(function (e) {
        if (!e.isIntersecting) return;
        e.target.classList.add("is-in");
        io.unobserve(e.target);
      });
    }, { rootMargin: "0px 0px -12% 0px", threshold: 0.1 });
    aparecen.forEach(function (el) { io.observe(el); });
  } else {
    aparecen.forEach(function (el) { el.classList.add("is-in"); });
  }

  // ---------- ¿abierta ahora? (horario compacto: ver generador/horario.py) ----------
  var NOMBRE_DIA = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"];
  function diasDe(h) {
    if (h == null) return null;
    if (h === "24") return ["*", "*", "*", "*", "*", "*", "*"];
    var p = String(h).split("|");
    return p.length === 7 ? p : [h, h, h, h, h, h, h];
  }
  function tramosDe(campo) {
    if (!campo || campo === "?") return [];
    if (campo === "*") return [[0, 1440]];
    return campo.split(",").map(function (t) { var x = t.split("-"); return [+x[0], +x[1]]; });
  }
  function hhmm(min) {
    min = ((min % 1440) + 1440) % 1440;
    return String(Math.floor(min / 60)).padStart(2, "0") + ":" + String(min % 60).padStart(2, "0");
  }
  function estadoAhora(h, ahora) {
    var dias = diasDe(h);
    if (!dias) return null;
    ahora = ahora || new Date();
    if (dias.every(function (x) { return x === "*"; })) return { abierta: true, h24: true, texto: "Abierta 24 h" };
    var d = (ahora.getDay() + 6) % 7, m = ahora.getHours() * 60 + ahora.getMinutes(), i;
    var hoy = tramosDe(dias[d]), ayer = tramosDe(dias[(d + 6) % 7]);
    for (i = 0; i < hoy.length; i++) {
      if (m >= hoy[i][0] && m < hoy[i][1]) {
        return { abierta: true, texto: hoy[i][1] - hoy[i][0] >= 1440 ? "Abierta hoy todo el día" : "Abierta · cierra a las " + hhmm(hoy[i][1]) };
      }
    }
    for (i = 0; i < ayer.length; i++) {
      if (ayer[i][1] > 1440 && m < ayer[i][1] - 1440) return { abierta: true, texto: "Abierta · cierra a las " + hhmm(ayer[i][1]) };
    }
    for (i = 0; i < hoy.length; i++) if (hoy[i][0] > m) return { abierta: false, texto: "Cerrada · abre a las " + hhmm(hoy[i][0]) };
    for (var k = 1; k <= 7; k++) {
      var t = tramosDe(dias[(d + k) % 7]);
      if (t.length) return { abierta: false, texto: "Cerrada · abre " + (k === 1 ? "mañana" : "el " + NOMBRE_DIA[(d + k) % 7]) + " a las " + hhmm(t[0][0]) };
    }
    return { abierta: false, texto: "Cerrada" };
  }
  function ahoraHTML(s) {
    if (!s) return "";
    return '<span class="ahora ' + (s.abierta ? "si" : "no") + '">' + esc(s.texto) + "</span>";
  }
  // En la lista de un municipio: el estado de cada gasolinera y el filtro «Abiertas ahora».
  $$("[data-ahora][data-h]").forEach(function (el) {
    var s = estadoAhora(el.getAttribute("data-h")), li = el.closest("li");
    if (!s) return;
    if (li) li.setAttribute("data-abierta", s.abierta ? "1" : "0");
    if (s.h24) return;  // ya pone «Abierta 24 horas»
    el.textContent = s.texto;
    el.classList.add(s.abierta ? "si" : "no");
  });
  $$("[data-solo-abiertas]").forEach(function (boton) {
    var lista = boton.closest(".bloque").querySelector("[data-lista]");
    boton.addEventListener("click", function () {
      var activo = boton.getAttribute("aria-pressed") !== "true";
      boton.setAttribute("aria-pressed", activo ? "true" : "false");
      if (activo) lista.setAttribute("data-abiertas-activo", ""); else lista.removeAttribute("data-abiertas-activo");
    });
  });

  // ---------- mapa de precios (Leaflet y OpenStreetMap; se cargan solo al abrir un mapa) ----------
  var leafletP = null;
  function cargarLeaflet() {
    if (window.L) return Promise.resolve(window.L);
    if (!leafletP) {
      leafletP = new Promise(function (ok, mal) {
        var css = document.createElement("link");
        css.rel = "stylesheet";
        css.href = "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.css";
        document.head.appendChild(css);
        var s = document.createElement("script");
        s.src = "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.js";
        s.onload = function () { ok(window.L); };
        s.onerror = function () { leafletP = null; mal(new Error("leaflet")); };
        document.head.appendChild(s);
      });
    }
    return leafletP;
  }
  // puntos: [{e, d, ahora}] ya ordenados por precio; idx: posición del precio en e.
  function mapaDePrecios(div, puntos, idx, extra) {
    extra = extra || {};
    div.innerHTML = '<p class="mapa-cargando">Cargando el mapa…</p>';
    cargarLeaflet().then(function (L) {
      div.innerHTML = "";
      var mapa = L.map(div, { scrollWheelZoom: false, zoomControl: true });
      L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
        maxZoom: 19, attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
      }).addTo(mapa);
      var limites = [];
      if (extra.linea && extra.linea.length) {
        L.polyline(extra.linea, { color: "#17191b", weight: 4, opacity: .7 }).addTo(mapa);
        limites = limites.concat(extra.linea);
      }
      var visibles = puntos.slice(0, extra.max || 80);
      visibles.forEach(function (x, i) {
        var e = x.e, cerrada = x.ahora && !x.ahora.abierta;
        var icono = L.divIcon({
          className: "pin" + (i < 3 ? " pin-barata" : "") + (cerrada ? " pin-cerrada" : ""),
          html: "<span>" + litro.format(e[idx]) + "</span>", iconSize: [0, 0]
        });
        L.marker([e[0], e[1]], { icon: icono, zIndexOffset: 1000 - i, keyboard: true, title: e[2] + ", " + litro.format(e[idx]) + " €/l" })
          .addTo(mapa)
          .bindPopup('<b translate="no">' + esc(e[2]) + "</b><br>" + esc(e[3]) + ", " + esc(e[4]) +
            '<br><b class="pop-precio">' + litro.format(e[idx]) + " €/l</b>" + (x.ahora ? "<br>" + esc(x.ahora.texto) : "") +
            '<br><a href="https://www.google.com/maps/dir/?api=1&destination=' + e[0] + "," + e[1] + '" target="_blank" rel="nofollow noopener">Cómo llegar</a>');
        limites.push([e[0], e[1]]);
      });
      if (extra.yo) {
        L.circleMarker(extra.yo, { radius: 8, color: "#fff", weight: 3, fillColor: "#1a73e8", fillOpacity: 1 }).addTo(mapa).bindTooltip("Tú");
        limites.push(extra.yo);
      }
      if (limites.length) mapa.fitBounds(limites, { padding: [28, 28], maxZoom: 15 });
      else mapa.setView([40.4, -3.7], 6);
    }).catch(function () { div.innerHTML = '<p class="mapa-cargando">No se pudo cargar el mapa. Comprueba la conexión.</p>'; });
  }

  // ---------- portada: las gasolineras de tu zona ----------
  // Cada estación: [lat, lon, rótulo, dirección, municipio, url, diésel, 95, 98, GLP, 24 h]
  var zona = document.querySelector("[data-zona]");
  if (zona) (function () {
    var inicial = zona.querySelector("[data-zona-inicial]");
    var salida = zona.querySelector("[data-zona-resultado]");
    var aviso = zona.querySelector("[data-zona-aviso]");
    var input = document.querySelector("[data-zona-buscar]");
    var RADIOS = [3, 5, 10, 25];
    var VISIBLES = 8;
    var estado = null, radio = 5, orden = "precio", solo24 = false, todasVisibles = false, vista = "lista";
    var estacionesP = null;
    function cargar() {
      if (!estacionesP) estacionesP = fetch(BASE + "/estaciones.json").then(function (r) {
        if (!r.ok) throw new Error("http " + r.status);
        return r.json();
      });
      return estacionesP;
    }
    function avisar(t) { aviso.textContent = t || ""; aviso.hidden = !t; }
    function leerLugar() { try { return JSON.parse(localStorage.getItem("rb-lugar") || "null"); } catch (e) { return null; } }
    function olvidarLugar() { try { localStorage.removeItem("rb-lugar"); } catch (e) {} }
    function mapa(e) { return "https://www.google.com/maps/dir/?api=1&destination=" + e[0] + "," + e[1]; }
    function plural(n, uno, varios) { return n + " " + (n === 1 ? uno : varios); }
    function sinErrores(con, idx) {  // fuera los precios imposibles de la fuente, como en el resto de la web
      if (con.length < 20) return con;
      var orden = con.map(function (x) { return x.e[idx]; }).sort(function (a, b) { return a - b; });
      var suelo = orden[Math.floor(orden.length / 2)] * 0.8;
      return con.filter(function (x) { return x.e[idx] >= suelo; });
    }
    function cts(d) {
      var c = d * 100;
      return Math.abs(c) < 0.05 ? "mismo precio" : "+" + km.format(c) + " cts";
    }
    function chip(attr, valor, texto, activo) {
      return '<button type="button" class="chip" ' + attr + '="' + valor + '" aria-pressed="' + activo + '">' + texto + "</button>";
    }

    function pintar() {
      if (!estado) return;
      var c = comb(), idx = 6 + COMBS.indexOf(c), gps = estado.tipo === "gps";
      var base = gps ? estado.todas.filter(function (x) { return x.d <= radio; }) : estado.todas;
      var con = sinErrores(base.filter(function (x) { return x.e[idx] != null; }), idx);
      con.forEach(function (x) { if (x.ahora === undefined) x.ahora = estadoAhora(x.e[11]); });
      var hayCerradas = con.some(function (x) { return x.ahora && !x.ahora.abierta; });
      // solo24 = «Abiertas ahora»: fuera las que sabemos cerradas (las de horario desconocido se quedan).
      if (solo24) con = con.filter(function (x) { return !(x.ahora && !x.ahora.abierta); });
      var porPrecio = con.slice().sort(function (a, b) { return a.e[idx] - b.e[idx] || (a.d || 0) - (b.d || 0); });

      var titulo = gps ? (estado.aprox ? "Cerca de tu última ubicación" : "Cerca de ti") : estado.nombre;
      var sub = plural(con.length, "gasolinera", "gasolineras") + " con " + NOMBRES[c] +
        (gps ? " a menos de " + radio + " km" : " en " + estado.nombre);
      var html = '<div class="zona-cab"><div><p class="zona-titulo">' + esc(titulo) + '</p><p class="zona-sub">' + esc(sub) +
        '</p></div><button type="button" class="zona-cambiar" data-zona-cambiar>Cambiar</button></div>';

      var controles = '<div class="chips" role="group" aria-label="Vista">' + chip("data-vista", "lista", "Lista", vista === "lista") +
        chip("data-vista", "mapa", "Mapa", vista === "mapa") + "</div>";
      if (gps) {
        controles += '<div class="chips" role="group" aria-label="Distancia">' + RADIOS.map(function (r) {
          return chip("data-radio", r, r + " km", r === radio);
        }).join("") + "</div>";
        controles += '<div class="chips" role="group" aria-label="Orden">' + chip("data-orden", "precio", "Más baratas", orden === "precio") +
          chip("data-orden", "distancia", "Más cerca", orden === "distancia") + "</div>";
      }
      if (hayCerradas || solo24) controles += '<div class="chips">' + chip("data-solo24z", "1", "Abiertas ahora", solo24) + "</div>";
      if (controles) html += '<div class="zona-controles">' + controles + "</div>";

      if (!porPrecio.length) {
        salida.innerHTML = html + '<p class="zona-vacio">' + (solo24 ? "Ninguna está abierta ahora con este combustible." :
          gps ? "Ninguna gasolinera vende " + NOMBRES[c] + " a menos de " + radio + " km." + (radio < 25 ? " Prueba con más distancia." : "")
            : "Ninguna gasolinera de " + esc(estado.nombre) + " vende " + NOMBRES[c] + ".") + "</p>";
        return;
      }
      var mejor = porPrecio[0], e = mejor.e;
      var media = con.reduce(function (s, x) { return s + x.e[idx]; }, 0) / con.length;
      var litros = +(raiz.getAttribute("data-litros") || 50);
      var ahorro = (media - e[idx]) * litros;
      var lugar = esc(e[3]) + (gps || e[4] !== estado.nombre ? ", " + esc(e[4]) : "");
      html += '<div class="zona-mejor">' +
        '<p class="zm-etq">' + (con.length > 1 ? (c === "g95" || c === "g98" ? "La más barata" : "El más barato") : "Precio") +
        (mejor.d != null ? " · a " + km.format(mejor.d) + " km" : "") + "</p>" +
        '<p class="zm-precio"><span class="cifra" data-cifra data-v="' + e[idx] + '">' + litro.format(e[idx]) + '</span><span class="unidad"> €/l</span></p>' +
        '<p class="zm-sitio"><b translate="no">' + esc(e[2]) + "</b> " + lugar + "</p>" +
        (mejor.ahora ? '<p class="zm-ahora">' + ahoraHTML(mejor.ahora) + "</p>" : "") +
        (function () {
          if (!mejor.ahora || mejor.ahora.abierta) return "";
          var abierta = porPrecio.filter(function (y) { return !(y.ahora && !y.ahora.abierta); })[0];
          return abierta ? '<p class="zm-aviso">La más barata abierta ahora: <b translate="no">' + esc(abierta.e[2]) + "</b>, " +
            esc(abierta.e[3]) + ", a " + litro.format(abierta.e[idx]) + " €/l.</p>" : "";
        })() +
        '<p class="zm-ahorro">Llenar ' + litros + " litros: <b>" + euros.format(e[idx] * litros) + " €</b>" +
        (con.length > 2 && ahorro >= 0.5 ? '. Ahorras <b class="dato">' + euros.format(ahorro) + " €</b> frente a la media de " + (gps ? "la zona" : esc(estado.nombre)) : "") + ".</p>" +
        '<div class="zm-acciones"><a class="boton zm-ir" href="' + mapa(e) + '" target="_blank" rel="nofollow noopener">Cómo llegar</a>' +
        '<a class="zm-compartir" data-compartir href="https://wa.me/?text=' + encodeURIComponent(e[2] + ", " + e[3] + " (" + e[4] + "): " +
          NOMBRES[c] + " a " + litro.format(e[idx]) + " €/l. Cómo llegar: " + mapa(e)) + '" target="_blank" rel="nofollow noopener">Compartir</a></div></div>';

      var resto = (orden === "distancia" ? con.slice().sort(function (a, b) { return a.d - b.d; }) : porPrecio)
        .filter(function (x) { return x !== mejor; });
      var vis = todasVisibles ? resto : resto.slice(0, VISIBLES);
      if (vista === "mapa") {
        html += '<div class="zona-mapa" data-zona-mapa role="region" aria-label="Mapa de las gasolineras"></div>';
        vis = [];
      }
      if (vis.length) {
        html += '<p class="zona-lista-t">' + (orden === "distancia" ? "Las demás, de más cerca a más lejos" : "Las siguientes más baratas") + "</p>" +
          '<ol class="zona-lista">' + vis.map(function (x) {
            var f = x.e;
            return '<li class="zl"><span class="zl-id"><b translate="no">' + esc(f[2]) + '</b><span class="zl-dir">' +
              (x.d != null ? "a " + km.format(x.d) + " km · " : "") + esc(f[3]) + (gps || f[4] !== estado.nombre ? ", " + esc(f[4]) : "") +
              "</span>" + (x.ahora ? '<span class="zl-ahora">' + ahoraHTML(x.ahora) + "</span>" : "") + '</span><span class="zl-precio"><span class="cifra">' + litro.format(f[idx]) +
              "</span><small>" + cts(f[idx] - e[idx]) + '</small></span><a class="zl-ir" href="' + mapa(f) +
              '" target="_blank" rel="nofollow noopener" aria-label="Cómo llegar a ' + esc(f[2]) + ", " + esc(f[3]) + '">Ir</a></li>';
          }).join("") + "</ol>";
        if (resto.length > vis.length) html += '<button type="button" class="zona-mas" data-ver-todas>Ver las ' + resto.length + " restantes</button>";
      }
      var url = gps ? e[5] : estado.url, nombreMun = gps ? e[4] : estado.nombre;
      html += '<p class="zona-pie"><a href="' + url + '">Todo sobre las gasolineras de ' + esc(nombreMun) + "</a>" +
        "<span>" + (gps ? "Distancias en línea recta. " : "") + "Precios oficiales de las " + esc(window.HORA || "") + "</span></p>";
      salida.innerHTML = html;
      $$("[data-cifra]", salida).forEach(function (el) { cifraQueRueda(el, parseFloat(el.getAttribute("data-v"))); });
      var divMapa = salida.querySelector("[data-zona-mapa]");
      if (divMapa) mapaDePrecios(divMapa, porPrecio, idx, { yo: gps && estado.lat != null ? [estado.lat, estado.lon] : null });
    }
    // La cifra grande: la parte entera fija y los decimales rodando desde cero.
    function cifraQueRueda(el, valor) {
      if (movimientoReducido || isNaN(valor)) return;
      var texto = litro.format(valor), partes = texto.split(",");
      var dig = document.createElement("span");
      dig.className = "roll__digits";
      dig.setAttribute("aria-hidden", "true");
      dig.appendChild(document.createTextNode(partes[0]));
      var sep = document.createElement("span"); sep.className = "roll__sep"; sep.textContent = ","; dig.appendChild(sep);
      var tiras = [];
      for (var k = 0; k < partes[1].length; k++) {
        var col = document.createElement("span"); col.className = "roll__col";
        var tira = document.createElement("span"); tira.className = "roll__strip";
        tira.style.setProperty("--d", 0); tira.style.setProperty("--i", k);
        col.appendChild(tira); dig.appendChild(col); tiras.push(tira);
      }
      var dicho = document.createElement("span"); dicho.className = "oculto"; dicho.textContent = texto;
      el.replaceChildren(dicho, dig);
      el.classList.add("roll", "is-in");
      requestAnimationFrame(function () {
        requestAnimationFrame(function () { tiras.forEach(function (t, j) { t.style.setProperty("--d", partes[1][j]); }); });
      });
      // Al terminar de rodar vuelve a ser texto normal, con el espaciado propio de cada cifra.
      setTimeout(function () { if (el.isConnected) { el.classList.remove("roll", "is-in"); el.textContent = texto; } }, 1400);
    }

    function mostrar(nuevo, desplazar) {
      estado = nuevo; orden = "precio"; solo24 = false; todasVisibles = false;
      avisar("");
      inicial.hidden = true;
      salida.hidden = false;
      pintar();
      if (desplazar && innerWidth < 960) zona.scrollIntoView({ behavior: movimientoReducido ? "auto" : "smooth", block: "start" });
    }
    function ponerGps(lat, lon, aprox, desplazar) {
      avisar("Buscando gasolineras a tu alrededor…");
      return cargar().then(function (lista) {
        var todas = [];
        lista.forEach(function (e) { var d = distancia(lat, lon, e[0], e[1]); if (d <= 25) todas.push({ e: e, d: d }); });
        if (!todas.length) { avisar("No hay gasolineras a menos de 25 km. Escribe tu municipio."); return; }
        radio = 25;
        for (var i = 0; i < RADIOS.length; i++) {
          var r = RADIOS[i];
          if (todas.filter(function (x) { return x.d <= r; }).length >= 6) { radio = r; break; }
        }
        guardar("rb-lugar", JSON.stringify({ tipo: "gps", lat: +lat.toFixed(3), lon: +lon.toFixed(3) }));
        if (input) input.value = "";
        mostrar({ tipo: "gps", todas: todas, aprox: aprox, lat: lat, lon: lon }, desplazar);
      }).catch(function () { avisar("No se pudieron cargar los precios. Comprueba la conexión e inténtalo de nuevo."); });
    }
    function ponerMunicipio(url, nombre, desplazar) {
      if (input) input.value = nombre || "";
      avisar("Cargando las gasolineras de " + nombre + "…");
      return cargar().then(function (lista) {
        var todas = lista.filter(function (e) { return e[5] === url; }).map(function (e) { return { e: e }; });
        if (!todas.length) { olvidarLugar(); avisar(""); return; }
        guardar("rb-lugar", JSON.stringify({ tipo: "mun", url: url, nombre: nombre }));
        mostrar({ tipo: "mun", url: url, nombre: nombre, todas: todas }, desplazar);
      }).catch(function () { avisar("No se pudieron cargar los precios. Comprueba la conexión e inténtalo de nuevo."); });
    }
    function porUbicacion(auto) {
      if (!auto) avisar("Buscando tu ubicación…");
      ubicar(function (lat, lon) { ponerGps(lat, lon, false, !auto); }, function (msg) {
        if (!auto) { avisar(msg); return; }
        var g = leerLugar();
        if (estado == null && g && g.tipo === "gps") ponerGps(g.lat, g.lon, true, false);
      });
    }
    window.__ponerMunicipio = function (url, nombre) { ponerMunicipio(url, nombre, true); };

    salida.addEventListener("click", function (ev) {
      var b = ev.target.closest("button");
      if (!b) return;
      if (b.hasAttribute("data-radio")) { radio = +b.getAttribute("data-radio"); todasVisibles = false; pintar(); }
      else if (b.hasAttribute("data-orden")) { orden = b.getAttribute("data-orden"); pintar(); }
      else if (b.hasAttribute("data-vista")) { vista = b.getAttribute("data-vista"); if (vista === "mapa") contar("mapa"); pintar(); }
      else if (b.hasAttribute("data-solo24z")) { solo24 = !solo24; pintar(); }
      else if (b.hasAttribute("data-ver-todas")) { todasVisibles = true; pintar(); }
      else if (b.hasAttribute("data-zona-cambiar")) {
        estado = null; olvidarLugar();
        salida.hidden = true; salida.innerHTML = ""; inicial.hidden = false;
        if (input) { input.value = ""; input.focus(); }
      }
    });
    $$("[data-zona-ciudad]").forEach(function (a) {
      a.addEventListener("click", function (ev) {
        if (ev.metaKey || ev.ctrlKey || ev.shiftKey || ev.button === 1) return;
        ev.preventDefault();
        ponerMunicipio(a.getAttribute("href"), a.getAttribute("data-nombre"), true);
      });
    });
    $$("[data-zona-ubicacion]").forEach(function (b) { b.addEventListener("click", function () { contar("ubicacion"); porUbicacion(false); }); });
    alCambiarComb.push(function () { pintar(); });
    $$("button[data-litros]").forEach(function (b) { b.addEventListener("click", function () { pintar(); }); });

    // Al entrar: la última zona consultada o, si ya diste permiso, tu ubicación.
    // Desde el acceso «Cerca de mí» de otra página se pide la ubicación directamente.
    if (/[?&]cerca=1/.test(location.search)) {
      try { history.replaceState(null, "", location.pathname + location.hash); } catch (e) {}
      porUbicacion(false);
      return;
    }
    var antes = leerLugar();
    var conPermiso = navigator.permissions && navigator.permissions.query ?
      navigator.permissions.query({ name: "geolocation" }).then(function (p) { return p.state === "granted"; }, function () { return false; }) :
      Promise.resolve(false);
    if (antes && antes.tipo === "mun") ponerMunicipio(antes.url, antes.nombre, false);
    else conPermiso.then(function (si) {
      if (si) porUbicacion(true);
      else if (antes && antes.tipo === "gps") ponerGps(antes.lat, antes.lon, true, false);
    });
  })();

  // En la página de un municipio: se recuerda para enseñarlo en la portada la próxima vez.
  $$("[data-recordar-lugar]").forEach(function (el) {
    guardar("rb-lugar", JSON.stringify({ tipo: "mun", url: el.getAttribute("data-url"), nombre: el.getAttribute("data-nombre") }));
  });

  // ---------- accesos rápidos del móvil ----------
  $$("[data-buscar-rapido]").forEach(function (b) {
    b.addEventListener("click", function () {
      var input = document.querySelector("[data-zona-buscar]");
      if (!input) {
        var abrir = document.querySelector("[data-abrir-busqueda]");
        var zonaB = document.getElementById("busqueda-barra");
        if (zonaB && zonaB.hidden && abrir) abrir.click();
        input = zonaB && zonaB.querySelector("input");
      }
      if (!input) return;
      scrollTo({ top: 0, behavior: movimientoReducido ? "auto" : "smooth" });
      input.focus({ preventScroll: true });
    });
  });
  $$("[data-cerca-rapido]").forEach(function (a) {
    a.addEventListener("click", function (ev) {
      var boton = document.querySelector("[data-zona-ubicacion]");
      if (!boton) return;  // fuera de la portada, el enlace lleva a ella y allí se pide la ubicación
      ev.preventDefault();
      boton.click();
    });
  });

  // ---------- compartir y copiar ----------
  document.addEventListener("click", function (ev) {
    var a = ev.target.closest && ev.target.closest("[data-compartir]");
    if (!a || !navigator.share) return;
    ev.preventDefault();
    var texto = decodeURIComponent(a.getAttribute("href").split("text=")[1] || "");
    contar("compartir");
    navigator.share({ text: texto }).catch(function () {});
  });
  $$("[data-copiar]").forEach(function (b) {
    b.addEventListener("click", function () {
      var hecho = function () { var t = b.textContent; b.textContent = "Enlace copiado"; setTimeout(function () { b.textContent = t; }, 2000); };
      if (navigator.clipboard) navigator.clipboard.writeText(b.getAttribute("data-copiar")).then(hecho, function () {});
    });
  });

  // ---------- calculadora de viaje ----------
  $$("[data-calc]").forEach(function (form) {
    var precios = JSON.parse(form.getAttribute("data-precios") || "{}");
    var q = function (s) { return form.querySelector(s); };
    var km = q("[data-calc-km]"), vuelta = q("[data-calc-vuelta]"), consumo = q("[data-calc-consumo]");
    var precio = q("[data-calc-precio]"), personas = q("[data-calc-personas]"), origen = q("[data-calc-origen]");
    var total = document.querySelector("[data-calc-total]"), detalle = document.querySelector("[data-calc-detalle]");
    var porPersona = document.querySelector("[data-calc-persona]"), ahorro = document.querySelector("[data-calc-ahorro]");
    var editado = false;
    function num(el) { return parseFloat(String(el.value).replace(",", ".")); }
    function calcular() {
      var d = num(km) * (vuelta.checked ? 2 : 1), l = d * num(consumo) / 100, p = num(precio), n = Math.max(1, Math.round(num(personas)) || 1);
      if (!(d > 0) || !(l > 0) || !(p > 0)) { total.textContent = "—"; detalle.textContent = "Rellena la distancia, el consumo y el precio."; porPersona.hidden = true; return; }
      total.textContent = euros.format(l * p);
      detalle.textContent = kmf.format(d) + " km: " + kmf.format(l) + " litros a " + litro.format(p) + " €/l.";
      porPersona.hidden = n < 2;
      porPersona.textContent = "Entre " + n + " personas: " + euros.format(l * p / n) + " € cada una.";
      ahorro.innerHTML = "Cada 10 céntimos menos por litro te ahorran <b class=\"dato\">" + euros.format(l * 0.1) + " €</b> en este viaje.";
    }
    var kmf = new Intl.NumberFormat("es-ES", { maximumFractionDigits: 1 });
    function precioDelComb() {
      var c = comb();
      if (!editado && precios[c]) {
        precio.value = precios[c].toFixed(3);
        origen.textContent = "Media de hoy de" + (c === "g95" || c === "g98" ? " la " : "l ") + NOMBRES[c] + " en España.";
      }
      calcular();
    }
    precio.addEventListener("input", function () { editado = true; origen.textContent = "Precio que has puesto tú."; calcular(); });
    [km, consumo, personas].forEach(function (el) { el.addEventListener("input", calcular); });
    vuelta.addEventListener("change", calcular);
    alCambiarComb.push(precioDelComb);
    precioDelComb();
  });

  // ---------- gasolineras en tu ruta ----------
  // La ruta por carretera la calcula el servidor público de OSRM (OpenStreetMap). Las gasolineras se buscan
  // aquí, en el navegador: las que quedan a pocos kilómetros de la línea de la ruta.
  var formRuta = document.querySelector("[data-ruta]");
  if (formRuta) (function () {
    var origen = formRuta.querySelector("[data-ruta-origen]"), destino = formRuta.querySelector("[data-ruta-destino]");
    var salida = document.querySelector("[data-ruta-resultado]"), aviso = document.querySelector("[data-ruta-aviso]");
    var DESVIOS = [1, 3, 5], TRAMO = 100;
    var calculo = null, desvio = 3, orden = "precio", vista = "lista", todas = false;
    function avisar(t) { aviso.textContent = t || ""; aviso.hidden = !t; }
    function chip(attr, valor, texto, activo) {
      return '<button type="button" class="chip" ' + attr + '="' + valor + '" aria-pressed="' + activo + '">' + texto + "</button>";
    }
    function mapa(e) { return "https://www.google.com/maps/dir/?api=1&destination=" + e[0] + "," + e[1]; }
    function duracion(seg) {
      var h = Math.floor(seg / 3600), m = Math.round((seg % 3600) / 60);
      return (h ? h + " h " : "") + m + " min";
    }
    formRuta.querySelector("[data-ruta-yo]").addEventListener("click", function () {
      avisar("Buscando tu ubicación…");
      ubicar(function (lat, lon) {
        origen.value = "Mi ubicación";
        origen.setAttribute("data-lat", lat); origen.setAttribute("data-lon", lon);
        avisar("");
        destino.focus();
      }, avisar);
    });
    formRuta.querySelector("[data-ruta-cambiar]").addEventListener("click", function () {
      var v = origen.value, la = origen.getAttribute("data-lat"), lo = origen.getAttribute("data-lon");
      origen.value = destino.value; destino.value = v;
      ["data-lat", "data-lon"].forEach(function (k) {
        var x = destino.getAttribute(k);
        if (x == null) origen.removeAttribute(k); else origen.setAttribute(k, x);
      });
      if (la == null) { destino.removeAttribute("data-lat"); destino.removeAttribute("data-lon"); }
      else { destino.setAttribute("data-lat", la); destino.setAttribute("data-lon", lo); }
    });
    [origen, destino].forEach(function (i) {
      i.addEventListener("input", function () { i.removeAttribute("data-lat"); i.removeAttribute("data-lon"); });
    });

    formRuta.addEventListener("submit", function (ev) {
      ev.preventDefault();
      contar("ruta");
      var a = [parseFloat(origen.getAttribute("data-lat")), parseFloat(origen.getAttribute("data-lon"))];
      var b = [parseFloat(destino.getAttribute("data-lat")), parseFloat(destino.getAttribute("data-lon"))];
      if (isNaN(a[0])) { avisar("Elige el origen en la lista (escribe y toca un municipio) o usa tu ubicación."); origen.focus(); return; }
      if (isNaN(b[0])) { avisar("Elige el destino en la lista: escribe y toca un municipio."); destino.focus(); return; }
      avisar("Calculando la ruta…");
      salida.hidden = true;
      var url = "https://router.project-osrm.org/route/v1/driving/" + a[1] + "," + a[0] + ";" + b[1] + "," + b[0] +
        "?overview=full&geometries=geojson";
      Promise.all([
        fetch(url).then(function (r) { if (!r.ok) throw new Error("osrm"); return r.json(); }),
        fetch(BASE + "/estaciones.json").then(function (r) { return r.json(); })
      ]).then(function (res) {
        var ruta = res[0].routes && res[0].routes[0];
        if (!ruta) throw new Error("sin ruta");
        calculo = preparar(ruta, res[1]);
        calculo.nombre = origen.value.split(",")[0] + " → " + destino.value.split(",")[0];
        todas = false;
        avisar("");
        pintar();
        salida.hidden = false;
        salida.scrollIntoView({ behavior: movimientoReducido ? "auto" : "smooth", block: "start" });
      }).catch(function () {
        avisar("No se pudo calcular la ruta ahora mismo. Comprueba la conexión e inténtalo otra vez en un momento.");
      });
    });

    // Puntos de la ruta cada medio kilómetro, con su kilómetro desde el origen; y las gasolineras cercanas.
    function preparar(ruta, lista) {
      var coords = ruta.geometry.coordinates, puntos = [], acum = 0, ultimo = -1, linea = [];
      for (var i = 0; i < coords.length; i++) {
        var la = coords[i][1], lo = coords[i][0];
        if (i) acum += distancia(coords[i - 1][1], coords[i - 1][0], la, lo);
        if (acum - ultimo >= 0.5 || i === coords.length - 1) { puntos.push([la, lo, acum]); ultimo = acum; }
        if (i % 4 === 0 || i === coords.length - 1) linea.push([la, lo]);
      }
      var minLa = 90, maxLa = -90, minLo = 180, maxLo = -180;
      puntos.forEach(function (p) { minLa = Math.min(minLa, p[0]); maxLa = Math.max(maxLa, p[0]); minLo = Math.min(minLo, p[1]); maxLo = Math.max(maxLo, p[1]); });
      var margen = 0.07, cerca = [];
      lista.forEach(function (e) {
        if (e[0] < minLa - margen || e[0] > maxLa + margen || e[1] < minLo - margen || e[1] > maxLo + margen) return;
        var cos = Math.cos(e[0] * Math.PI / 180), mejor = Infinity, km = 0;
        for (var j = 0; j < puntos.length; j++) {
          var dy = e[0] - puntos[j][0], dx = (e[1] - puntos[j][1]) * cos, d2 = dx * dx + dy * dy;
          if (d2 < mejor) { mejor = d2; km = puntos[j][2]; }
        }
        var d = Math.sqrt(mejor) * 111.2;
        if (d <= 5) cerca.push({ e: e, d: d, km: km, ahora: estadoAhora(e[11]) });
      });
      return { km: acum, segundos: ruta.duration, cerca: cerca, linea: linea };
    }

    function pintar() {
      if (!calculo) return;
      var c = comb(), idx = 6 + COMBS.indexOf(c);
      var con = calculo.cerca.filter(function (x) { return x.d <= desvio && x.e[idx] != null; });
      if (con.length >= 20) {  // fuera los precios imposibles de la fuente
        var ord = con.map(function (x) { return x.e[idx]; }).sort(function (p, q) { return p - q; });
        var suelo = ord[Math.floor(ord.length / 2)] * 0.8;
        con = con.filter(function (x) { return x.e[idx] >= suelo; });
      }
      var porPrecio = con.slice().sort(function (p, q) { return p.e[idx] - q.e[idx] || p.d - q.d; });
      var html = '<div class="zona-cab"><div><p class="zona-titulo">' + esc(calculo.nombre) + '</p><p class="zona-sub">' +
        km.format(calculo.km).replace(/,\d$/, "") + " km · unas " + duracion(calculo.segundos) + " · " + con.length +
        " gasolineras con " + NOMBRES[c] + " a menos de " + desvio + " km de la ruta</p></div></div>";
      html += '<div class="zona-controles"><div class="chips" role="group" aria-label="Vista">' +
        chip("data-r-vista", "lista", "Lista", vista === "lista") + chip("data-r-vista", "mapa", "Mapa", vista === "mapa") + "</div>" +
        '<div class="chips" role="group" aria-label="Desvío máximo">' + DESVIOS.map(function (d) {
          return chip("data-r-desvio", d, "A " + d + " km", d === desvio);
        }).join("") + "</div>" +
        '<div class="chips" role="group" aria-label="Orden">' + chip("data-r-orden", "precio", "Más baratas", orden === "precio") +
        chip("data-r-orden", "km", "Por el camino", orden === "km") + "</div></div>";
      if (!porPrecio.length) {
        salida.innerHTML = html + '<p class="zona-vacio">No hay gasolineras con ' + NOMBRES[c] + " a menos de " + desvio +
          " km de la ruta." + (desvio < 5 ? " Prueba con más desvío." : "") + "</p>";
        return;
      }
      var mejor = porPrecio[0], e = mejor.e;
      var media = con.reduce(function (s, x) { return s + x.e[idx]; }, 0) / con.length;
      var litros = +(raiz.getAttribute("data-litros") || 50);
      html += '<div class="zona-mejor"><p class="zm-etq">La más barata de la ruta · en el km ' + Math.round(mejor.km) + "</p>" +
        '<p class="zm-precio"><span class="cifra">' + litro.format(e[idx]) + '</span><span class="unidad"> €/l</span></p>' +
        '<p class="zm-sitio"><b translate="no">' + esc(e[2]) + "</b> " + esc(e[3]) + ", " + esc(e[4]) + " · a " + km.format(mejor.d) + " km de la ruta</p>" +
        (mejor.ahora ? '<p class="zm-ahora">' + ahoraHTML(mejor.ahora) + "</p>" : "") +
        (function () {
          if (!mejor.ahora || mejor.ahora.abierta) return "";
          var ab = porPrecio.filter(function (y) { return !(y.ahora && !y.ahora.abierta); })[0];
          return ab ? '<p class="zm-aviso">La más barata abierta ahora: <b translate="no">' + esc(ab.e[2]) + "</b>, " + esc(ab.e[4]) +
            " (km " + Math.round(ab.km) + "), a " + litro.format(ab.e[idx]) + " €/l.</p>" : "";
        })() +
        '<p class="zm-ahorro">Llenar ' + litros + " litros: <b>" + euros.format(e[idx] * litros) + " €</b>" +
        (con.length > 2 && (media - e[idx]) * litros >= 0.5 ? '. Ahorras <b class="dato">' + euros.format((media - e[idx]) * litros) + " €</b> frente a la media de la ruta" : "") + ".</p>" +
        '<div class="zm-acciones"><a class="boton zm-ir" href="' + mapa(e) + '" target="_blank" rel="nofollow noopener">Cómo llegar</a></div></div>';

      // Tramo a tramo: dónde parar si quieres repostar a mitad de camino.
      var tramos = [];
      for (var t = 0; t * TRAMO < calculo.km; t++) {
        var del = porPrecio.filter(function (x) { return x.km >= t * TRAMO && x.km < (t + 1) * TRAMO; })[0];
        tramos.push({ desde: t * TRAMO, hasta: Math.min((t + 1) * TRAMO, Math.round(calculo.km)), x: del });
      }
      if (tramos.length > 1) {
        html += '<p class="zona-lista-t">Dónde parar, tramo a tramo</p><ol class="tramos">' + tramos.map(function (tr) {
          if (!tr.x) return '<li><span class="tr-km">Km ' + tr.desde + "–" + tr.hasta + '</span><span class="tr-sin">Sin gasolineras cerca de la ruta</span></li>';
          var f = tr.x.e;
          return '<li><span class="tr-km">Km ' + tr.desde + "–" + tr.hasta + '</span><span class="zl-id"><b translate="no">' + esc(f[2]) +
            '</b><span class="zl-dir">' + esc(f[4]) + " · km " + Math.round(tr.x.km) + "</span></span>" +
            '<span class="zl-precio"><span class="cifra">' + litro.format(f[idx]) + '</span></span><a class="zl-ir" href="' + mapa(f) +
            '" target="_blank" rel="nofollow noopener" aria-label="Cómo llegar a ' + esc(f[2]) + ", " + esc(f[4]) + '">Ir</a></li>';
        }).join("") + "</ol>";
      }
      var consumo = 6.5, litrosViaje = calculo.km * consumo / 100;
      html += '<p class="ruta-coste">Gasolina para el viaje: unos <b>' + km.format(litrosViaje) + " litros</b> con un coche que gasta " +
        km.format(consumo) + " l/100 km; repostando en la más barata, <b>" + euros.format(litrosViaje * e[idx]) +
        ' €</b>. <a href="' + BASE + '/calculadora/">Calcúlalo con tu coche</a>.</p>';

      if (vista === "mapa") {
        html += '<div class="zona-mapa ruta-mapa" data-ruta-mapa role="region" aria-label="Mapa de la ruta"></div>';
      } else {
        var lista = (orden === "km" ? con.slice().sort(function (p, q) { return p.km - q.km; }) : porPrecio).filter(function (x) { return x !== mejor; });
        var vis = todas ? lista : lista.slice(0, 10);
        html += '<p class="zona-lista-t">' + (orden === "km" ? "Todas, en el orden del camino" : "Las siguientes más baratas") + '</p><ol class="zona-lista">' +
          vis.map(function (x) {
            var f = x.e;
            return '<li class="zl"><span class="zl-id"><b translate="no">' + esc(f[2]) + '</b><span class="zl-dir">Km ' + Math.round(x.km) +
              " · a " + km.format(x.d) + " km de la ruta · " + esc(f[4]) + "</span>" +
              (x.ahora ? '<span class="zl-ahora">' + ahoraHTML(x.ahora) + "</span>" : "") + '</span><span class="zl-precio"><span class="cifra">' +
              litro.format(f[idx]) + "</span><small>" + (Math.abs(f[idx] - e[idx]) < 0.0005 ? "mismo precio" : "+" + km.format((f[idx] - e[idx]) * 100) + " cts") +
              '</small></span><a class="zl-ir" href="' + mapa(f) + '" target="_blank" rel="nofollow noopener" aria-label="Cómo llegar a ' +
              esc(f[2]) + ", " + esc(f[4]) + '">Ir</a></li>';
          }).join("") + "</ol>";
        if (lista.length > vis.length) html += '<button type="button" class="zona-mas" data-r-todas>Ver las ' + lista.length + " restantes</button>";
      }
      html += '<p class="zona-pie"><span>Ruta calculada con OpenStreetMap (OSRM). Distancias a la ruta en línea recta.</span><span>Precios de las ' + esc(window.HORA || "") + "</span></p>";
      salida.innerHTML = html;
      var div = salida.querySelector("[data-ruta-mapa]");
      if (div) mapaDePrecios(div, porPrecio, idx, { linea: calculo.linea, max: 120 });
    }
    salida.addEventListener("click", function (ev) {
      var b = ev.target.closest("button");
      if (!b) return;
      if (b.hasAttribute("data-r-desvio")) { desvio = +b.getAttribute("data-r-desvio"); todas = false; }
      else if (b.hasAttribute("data-r-orden")) orden = b.getAttribute("data-r-orden");
      else if (b.hasAttribute("data-r-vista")) vista = b.getAttribute("data-r-vista");
      else if (b.hasAttribute("data-r-todas")) todas = true;
      else return;
      pintar();
    });
    alCambiarComb.push(pintar);
    $$("button[data-litros]").forEach(function (b) { b.addEventListener("click", pintar); });
  })();

  // ---------- estado inicial ----------
  aplicarComb(comb(), false);
  aplicarLitros(+(raiz.getAttribute("data-litros") || 50), false);
})();
