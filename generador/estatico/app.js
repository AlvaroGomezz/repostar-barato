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
    if (cercaUltima) pintarCerca();
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
  var indice = null;
  function cargarIndice() {
    if (!indice) {
      indice = fetch(BASE + "/buscar.json").then(function (r) { return r.json(); }).then(function (lista) {
        return lista.map(function (x) { return { n: x[0], p: x[1], u: x[2], c: x[3], k: sinAcentos(x[0]) }; });
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
          return '<li role="option"><a href="' + m.u + '"><span>' + esc(m.n) + '</span><small>' + esc(m.p) + " · " + m.c +
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
        window.location.href = enlaces[activo >= 0 ? activo : 0].href;
      }
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

  // ---------- portada: las más baratas cerca de mí ----------
  var cercaUltima = null;
  var cercaBloque = document.querySelector("[data-cerca-bloque]");
  var cercaSalida = document.querySelector("[data-cerca-resultado]");
  function pintarCerca() {
    var c = comb(), idx = 6 + COMBS.indexOf(c);
    var top = cercaUltima.filter(function (x) { return x.e[idx] != null; })
      .sort(function (a, b) { return a.e[idx] - b.e[idx] || a.d - b.d; }).slice(0, 8);
    if (!top.length) {
      cercaSalida.innerHTML = '<p class="vacio">No hay gasolineras que vendan ' + NOMBRES[c] + " a menos de 10 km.</p>";
      return;
    }
    cercaSalida.innerHTML = '<ol class="ranking">' + top.map(function (x, i) {
      var e = x.e;
      return '<li><span class="ranking-id"><strong>' + esc(e[2]) + "</strong><span>" + esc(e[3]) + '</span><span><a href="' +
        e[5] + '">' + esc(e[4]) + "</a> · a " + km.format(x.d) + ' km · <a href="https://www.google.com/maps/dir/?api=1&amp;destination=' +
        e[0] + "," + e[1] + '" target="_blank" rel="nofollow noopener">Cómo llegar</a></span></span><span class="ranking-precio' +
        (i === 0 ? " dato" : "") + '">' + precioHTML(e[idx]) + "</span></li>";
    }).join("") + "</ol>";
  }
  $$("[data-cerca]").forEach(function (boton) {
    boton.addEventListener("click", function () {
      cercaBloque.hidden = false;
      cercaSalida.innerHTML = '<p class="nota">Buscando tu ubicación…</p>';
      var suave = !(window.matchMedia && matchMedia("(prefers-reduced-motion: reduce)").matches);
      cercaBloque.scrollIntoView({ behavior: suave ? "smooth" : "auto", block: "start" });
      ubicar(function (lat, lon) {
        cercaSalida.innerHTML = '<p class="nota">Cargando precios…</p>';
        fetch(BASE + "/estaciones.json").then(function (r) { return r.json(); }).then(function (lista) {
          cercaUltima = lista.map(function (e) { return { e: e, d: distancia(lat, lon, e[0], e[1]) }; })
            .filter(function (x) { return x.d <= 10; });
          if (!cercaUltima.length) {
            cercaSalida.innerHTML = '<p class="vacio">No hay gasolineras a menos de 10 km. Busca tu municipio arriba.</p>';
            return;
          }
          pintarCerca();
        }).catch(function () {
          cercaSalida.innerHTML = '<p class="vacio">No se pudieron cargar los precios. Comprueba la conexión e inténtalo de nuevo.</p>';
        });
      }, function (msg) { cercaSalida.innerHTML = '<p class="vacio">' + esc(msg) + "</p>"; });
    });
  });
  $$("[data-cerca-cerrar]").forEach(function (b) {
    b.addEventListener("click", function () { cercaBloque.hidden = true; });
  });

  // ---------- estado inicial ----------
  aplicarComb(comb(), false);
  aplicarLitros(+(raiz.getAttribute("data-litros") || 50), false);
})();
