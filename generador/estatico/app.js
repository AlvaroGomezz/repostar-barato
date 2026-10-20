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
    if (cercaUltima) pintarCerca();
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
          return '<li role="option"><a href="' + m.u + '" data-nombre="' + esc(m.n) + '"><span>' + esc(m.n) + '</span><small>' + esc(m.p) + " · " + m.c +
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
        if (input.hasAttribute("data-poste-buscar") && window.__ponerMunicipio) {
          caja.hidden = true; input.setAttribute("aria-expanded", "false");
          window.__ponerMunicipio(elegido.getAttribute("href"), elegido.getAttribute("data-nombre"), input);
        } else {
          window.location.href = elegido.href;
        }
      }
    });
    caja.addEventListener("click", function (ev) {
      var a = ev.target.closest("a");
      if (!a || !input.hasAttribute("data-poste-buscar") || !window.__ponerMunicipio) return;
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

  // Poste: cambia de valor rodando cada vez.
  function rodar(el, valor) {
    var texto = valor == null ? "—" : litro.format(valor);
    if (movimientoReducido || valor == null) { el.textContent = texto; el.classList.remove("roll", "is-in"); return; }
    var tiras = $$(".roll__strip", el);
    var digitos = texto.replace(/\D/g, "");
    if (tiras.length !== digitos.length) {
      construirRodillo(el, texto);
      el.classList.add("is-in");
      return;
    }
    el.querySelector(".oculto").textContent = texto;
    tiras.forEach(function (t, j) { t.style.setProperty("--d", digitos[j]); });
  }

  // ---------- entradas al hacer scroll ----------
  var aparecen = $$("[data-reveal]").concat(rodillos);
  // Una foto que se abre empieza recortada a cero: se vigila su contenedor, no ella.
  var obturadores = $$(".obturador");
  if ("IntersectionObserver" in window && !movimientoReducido) {
    var io = new IntersectionObserver(function (entradas) {
      entradas.forEach(function (e) {
        if (!e.isIntersecting) return;
        var objetivo = e.target.__obturador || e.target;
        objetivo.classList.add("is-in");
        io.unobserve(e.target);
      });
    }, { rootMargin: "0px 0px -12% 0px", threshold: 0.1 });
    aparecen.forEach(function (el) { io.observe(el); });
    obturadores.forEach(function (el) { el.parentElement.__obturador = el; io.observe(el.parentElement); });
  } else {
    aparecen.concat(obturadores).forEach(function (el) { el.classList.add("is-in"); });
  }

  // ---------- vídeo: solo se mueve cuando se ve ----------
  $$("[data-video]").forEach(function (v) {
    if (movimientoReducido || !("IntersectionObserver" in window)) return;
    v.preload = "auto";
    new IntersectionObserver(function (entradas) {
      entradas.forEach(function (e) {
        if (e.isIntersecting) { var p = v.play(); if (p && p.catch) p.catch(function () {}); } else { v.pause(); }
      });
    }, { threshold: 0.2 }).observe(v);
  });

  // ---------- escaparate: la pieza del centro se enciende ----------
  $$("[data-escaparate]").forEach(function (pista) {
    var seccion = pista.closest("[data-escaparate-seccion]");
    var piezas = $$(".pieza", pista);
    var nombre = document.querySelector("[data-esc-nombre]");
    var texto = document.querySelector("[data-esc-texto]");
    var cuenta = document.querySelector("[data-esc-cuenta]");
    var encendida = null;
    function encender(p) {
      if (p === encendida) return;
      encendida = p;
      piezas.forEach(function (x) { x.classList.toggle("encendida", x === p); });
      nombre.textContent = p.getAttribute("data-nombre");
      texto.textContent = p.getAttribute("data-texto");
      if (cuenta) cuenta.textContent = (piezas.indexOf(p) + 1) + " de " + piezas.length;
    }
    var centroFijo = null;  // con la fila fija, el centro se mide sin el desplazamiento
    function laDelCentro() {
      var r = pista.getBoundingClientRect();
      var centro = centroFijo != null ? centroFijo : r.left + r.width / 2, mejor = piezas[0], dmin = Infinity;
      piezas.forEach(function (p) {
        var q = p.getBoundingClientRect(), d = Math.abs(q.left + q.width / 2 - centro);
        if (d < dmin) { dmin = d; mejor = p; }
      });
      encender(mejor);
    }
    // En pantallas anchas, el scroll vertical mueve la fila (un píxel por píxel) mientras el escenario se queda fijo.
    var ancho = window.matchMedia ? matchMedia("(min-width: 1100px)") : { matches: false };
    var dx = 0, pendiente = false;
    var VELOCIDAD = 0.6;  // píxeles de scroll por píxel de fila: el tramo fijo dura menos de dos pantallas
    function colocar() {
      pendiente = false;
      if (seccion.classList.contains("fijo")) {
        var p = Math.min(1, Math.max(0, -seccion.getBoundingClientRect().top / (dx * VELOCIDAD)));
        pista.style.transform = "translate3d(" + (-p * dx).toFixed(1) + "px,0,0)";
      }
      laDelCentro();
    }
    function medir() {
      seccion.classList.add("fijo");
      pista.style.transform = "";
      dx = pista.scrollWidth - pista.clientWidth;
      var rr = pista.getBoundingClientRect();
      centroFijo = rr.left + rr.width / 2;
      var fijar = ancho.matches && !movimientoReducido && dx > 0 && dx < innerHeight * 3;
      seccion.classList.toggle("fijo", fijar);
      if (!fijar) centroFijo = null;
      seccion.style.height = fijar ? (innerHeight + dx * VELOCIDAD) + "px" : "";
      colocar();
    }
    function pedir() { if (!pendiente) { pendiente = true; requestAnimationFrame(colocar); } }
    addEventListener("scroll", pedir, { passive: true });
    pista.addEventListener("scroll", pedir, { passive: true });
    addEventListener("resize", medir);
    addEventListener("load", medir);
    medir();
    function irA(p) {
      if (seccion.classList.contains("fijo")) {
        var i = piezas.indexOf(p), objetivo = seccion.getBoundingClientRect().top + scrollY + (dx * VELOCIDAD * i / (piezas.length - 1));
        scrollTo({ top: objetivo, behavior: movimientoReducido ? "auto" : "smooth" });
      } else {
        p.scrollIntoView({ behavior: movimientoReducido ? "auto" : "smooth", inline: "center", block: "nearest" });
      }
    }
    piezas.forEach(function (p) { p.addEventListener("click", function () { if (p !== encendida) irA(p); }); });
    pista.addEventListener("keydown", function (ev) {
      if (ev.key !== "ArrowRight" && ev.key !== "ArrowLeft") return;
      var i = piezas.indexOf(encendida);
      irA(piezas[Math.max(0, Math.min(piezas.length - 1, i + (ev.key === "ArrowRight" ? 1 : -1)))]);
      ev.preventDefault();
    });
  });

  // ---------- el poste de la portada ----------
  var poste = document.querySelector("[data-poste]");
  if (poste) {
    var pEl = {
      contexto: poste.querySelector("[data-poste-contexto]"),
      rotulo: poste.querySelector("[data-poste-rotulo]"),
      lugar: poste.querySelector("[data-poste-lugar]"),
      nota: poste.querySelector("[data-poste-nota]"),
      ver: poste.querySelector("[data-poste-ver]"),
      ir: poste.querySelector("[data-poste-ir]")
    };
    var notaInicial = pEl.nota.textContent;
    $$("[data-poste-precio]", poste).forEach(function (el) {
      var t = el.textContent.trim();
      if (/\d/.test(t) && !movimientoReducido) { construirRodillo(el, t); el.classList.add("is-in"); }
    });
    var estacionesP = null;
    var cargarEstaciones = function () {
      if (!estacionesP) estacionesP = fetch(BASE + "/estaciones.json").then(function (r) { return r.json(); });
      return estacionesP;
    };
    // Cada estación: [lat, lon, rótulo, dirección, municipio, url, diésel, 95, 98, GLP]
    var peninsula = function (e) {
      var lat = e[0], lon = e[1];
      if (lat < 30) return false;                                              // Canarias
      if (lat > 35.1 && lat < 36 && lon > -5.45 && lon < -2.85) return false;  // Ceuta y Melilla
      return true;
    };
    var masBarata = function (conjunto, c) {
      var idx = 6 + COMBS.indexOf(c);
      var con = conjunto.filter(function (x) { return x.e[idx] != null; });
      if (con.length >= 20) {
        var orden = con.map(function (x) { return x.e[idx]; }).sort(function (a, b) { return a - b; });
        var suelo = orden[Math.floor(orden.length / 2)] * 0.8;  // fuera los errores evidentes de la fuente
        con = con.filter(function (x) { return x.e[idx] >= suelo; });
      }
      con.sort(function (a, b) { return a.e[idx] - b.e[idx] || (a.d || 0) - (b.d || 0); });
      return { mejor: con[0] || null, n: con.length };
    };
    var actual = { tipo: "inicial", conjunto: null, texto: null };
    var pintar = function () {
      if (!actual.conjunto) return;
      var c = comb(), r = masBarata(actual.conjunto, c), x = r.mejor;
      if (!x) { pEl.contexto.textContent = actual.texto.vacio(c); return; }
      var e = x.e;
      pEl.contexto.textContent = actual.texto.cabeza(c, r.n);
      pEl.rotulo.textContent = e[2];
      pEl.lugar.innerHTML = esc(e[3]) + ' · <a href="' + e[5] + '">' + esc(e[4]) + "</a>";
      COMBS.forEach(function (k, i) { rodar(poste.querySelector('[data-poste-precio="' + k + '"]'), e[6 + i]); });
      pEl.nota.textContent = actual.texto.nota(x);
      pEl.ver.href = actual.texto.verUrl(e);
      pEl.ver.textContent = actual.texto.verTexto(e);
      if (pEl.ir) pEl.ir.href = "https://www.google.com/maps/dir/?api=1&destination=" + e[0] + "," + e[1];
    };
    alCambiarComb.push(function () {
      if (actual.tipo !== "inicial") { pintar(); return; }
      cargarEstaciones().then(function (lista) {
        if (actual.tipo !== "inicial") return;
        actual.conjunto = lista.filter(peninsula).map(function (e) { return { e: e }; });
        actual.texto = {
          cabeza: function () { return "La más barata de la Península, ahora"; },
          vacio: function () { return "Sin datos de este combustible"; },
          nota: function () { return notaInicial; },
          verUrl: function (e) { return e[5]; },
          verTexto: function (e) { return "Ver " + e[4]; }
        };
        pintar();
      });
    });
    window.__ponerMunicipio = function (url, nombre, input) {
      if (input) input.value = nombre || "";
      poste.classList.add("cargando");
      cargarEstaciones().then(function (lista) {
        poste.classList.remove("cargando");
        var del = lista.filter(function (e) { return e[5] === url; }).map(function (e) { return { e: e }; });
        actual = {
          tipo: "municipio", conjunto: del,
          texto: {
            cabeza: function () { return "La más barata de " + nombre; },
            vacio: function (c) { return "Ninguna gasolinera de " + nombre + " vende " + NOMBRES[c]; },
            nota: function () { return del.length + (del.length === 1 ? " gasolinera" : " gasolineras") + " · € por litro"; },
            verUrl: function () { return url; },
            verTexto: function () { return del.length > 1 ? "Ver las " + del.length : "Ver la gasolinera"; }
          }
        };
        pintar();
      }).catch(function () {
        poste.classList.remove("cargando");
        pEl.nota.textContent = "No se pudieron cargar los precios. Inténtalo de nuevo.";
      });
    };
    $$("[data-poste-ubicacion]").forEach(function (b) {
      b.addEventListener("click", function () {
        var r = poste.getBoundingClientRect();
        if (r.top < 0 || r.bottom > innerHeight) poste.scrollIntoView({ behavior: movimientoReducido ? "auto" : "smooth", block: "center" });
        pEl.nota.textContent = "Buscando tu ubicación…";
        ubicar(function (lat, lon) {
          poste.classList.add("cargando");
          cargarEstaciones().then(function (lista) {
            poste.classList.remove("cargando");
            var cerca = lista.map(function (e) { return { e: e, d: distancia(lat, lon, e[0], e[1]) }; })
              .filter(function (x) { return x.d <= 10; });
            if (!cerca.length) { pEl.nota.textContent = "No hay gasolineras a menos de 10 km. Escribe tu municipio."; return; }
            actual = {
              tipo: "ubicacion", conjunto: cerca,
              texto: {
                cabeza: function (c, n) { return "La más barata a menos de 10 km, entre " + n; },
                vacio: function (c) { return "Ninguna gasolinera cercana vende " + NOMBRES[c]; },
                nota: function (x) { return "A " + km.format(x.d) + " km de ti · € por litro"; },
                verUrl: function (e) { return e[5]; },
                verTexto: function (e) { return "Ver " + e[4]; }
              }
            };
            pintar();
          });
        }, function (msg) { pEl.nota.textContent = msg; });
      });
    });
  }

  // ---------- estado inicial ----------
  aplicarComb(comb(), false);
  aplicarLitros(+(raiz.getAttribute("data-litros") || 50), false);
})();
