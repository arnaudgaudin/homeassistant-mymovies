/*
 * My Movies panel for Home Assistant: the collection as a wall of covers or a
 * list, with the sort options of My Movies, filters, watched badges, box sets
 * that can be expanded, a details dialog to mark titles as watched and an
 * import of the collection export.
 * Plain web component, no build step and no external dependency.
 */

const STRINGS = {
  en: {
    search: "Search", ascending: "Ascending", descending: "Descending",
    allTypes: "All types", movies: "Movies", series: "TV series", documentaries: "Documentaries",
    segWatched: "Watched", segAll: "All", segUnwatched: "Not watched", watchedFilter: "Watched filter",
    expand: "Expand box sets", refresh: "Refresh", titles: "titles", films: "films",
    grid: "Wall", list: "List", view: "View",
    boxSet: "Box set", markWatched: "Mark as watched", clearWatched: "Clear watched",
    close: "Close", director: "Director", cast: "Cast", genres: "Genres", runtime: "Runtime",
    rating: "Rating", personalRating: "Personal rating", parental: "Parental rating",
    released: "Released", added: "Added", disc: "Disc", edition: "Edition",
    number: "Collection no.", group: "Group", inBoxSet: "In box set",
    contents: "Box set contents", loading: "Loading…", error: "Could not load the collection",
    empty: "No title matches", watched: "Watched", failed: "Action failed",
    importCsv: "Import the collection export",
    importTitle: "Import the My Movies export",
    importText: "In the My Movies app, export your collection to a CSV file, then choose it here. It gives the titles their names, IMDb IDs and details; the watched state always comes from My Movies.",
    importButton: "Import", importing: "Importing…", imported: "{n} titles imported.",
    sort: {
      title: "Title", collection_number: "Collection number", rating: "Rating",
      personal_rating: "Personal rating", runtime: "Running time", year: "Production year",
      release_date: "Release date", parental_rating: "Parental rating", added: "Added date",
    },
  },
  fr: {
    search: "Rechercher", ascending: "Croissant", descending: "Décroissant",
    allTypes: "Tous les types", movies: "Films", series: "Séries", documentaries: "Documentaires",
    segWatched: "Vus", segAll: "Tous", segUnwatched: "Non vus", watchedFilter: "Filtre vu",
    expand: "Déplier les coffrets", refresh: "Actualiser", titles: "titres", films: "films",
    grid: "Mur", list: "Liste", view: "Affichage",
    boxSet: "Coffret", markWatched: "Marquer comme vu", clearWatched: "Effacer le « vu »",
    close: "Fermer", director: "Réalisation", cast: "Avec", genres: "Genres", runtime: "Durée",
    rating: "Note", personalRating: "Note personnelle", parental: "Classification",
    released: "Sortie", added: "Ajouté le", disc: "Support", edition: "Édition",
    number: "N° de collection", group: "Groupe", inBoxSet: "Dans le coffret",
    contents: "Contenu du coffret", loading: "Chargement…",
    error: "Impossible de charger la collection", empty: "Aucun titre ne correspond",
    watched: "Vu", failed: "L'action a échoué",
    importCsv: "Importer l'export de la collection",
    importTitle: "Importer l'export My Movies",
    importText: "Dans l'application My Movies, exportez votre collection en fichier CSV, puis choisissez-le ici. Il donne aux titres leur nom, leur ID IMDb et leurs détails ; le statut « vu » vient toujours de My Movies.",
    importButton: "Importer", importing: "Import en cours…", imported: "{n} titres importés.",
    sort: {
      title: "Titre", collection_number: "Numéro de collection", rating: "Note",
      personal_rating: "Note personnelle", runtime: "Durée", year: "Année de production",
      release_date: "Date de sortie", parental_rating: "Classification", added: "Date d'ajout",
    },
  },
};

const SORT_KEYS = {
  title: (i) => i.sort_title || i.title,
  collection_number: (i) => i.collection_number,
  rating: (i) => i.rating,
  personal_rating: (i) => i.personal_rating,
  runtime: (i) => i.runtime,
  year: (i) => i.year,
  release_date: (i) => i.release_date || null,
  parental_rating: (i) => i.parental_rating || null,
  added: (i) => i.added || null,
};

const TYPES = { movies: "Movie", series: "TV Serie", documentaries: "Documentary" };
const STATE_KEY = "mymovies-panel";
const icon = (path) => `<svg viewBox="0 0 24 24" aria-hidden="true"><path d="${path}"/></svg>`;
const CHECK = icon("M9 16.17 4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z");
const SORT_ICON = icon("M7 4v13H4l4 4 4-4H9V4zm7 0-4 4h3v13h2V8h3z");
const REFRESH = icon("M17.65 6.35A7.96 7.96 0 0 0 12 4a8 8 0 1 0 7.73 10h-2.08A6 6 0 1 1 12 6c1.66 0 3.14.69 4.22 1.78L13 11h7V4z");
const UPLOAD = icon("M9 16v-6H5l7-7 7 7h-4v6zm-4 4v-2h14v2z");
const GRID = icon("M3 11h8V3H3zm0 10h8v-8H3zm10 0h8v-8h-8zm0-18v8h8V3z");
const LIST = icon("M9 5v4h12V5zM4 9h4V5H4zm5 10h12v-4H9zm-5 0h4v-4H4zm5-5h12v-4H9zm-5 0h4v-4H4z");

const esc = (value) =>
  String(value ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);

// My Movies separates synopsis paragraphs with ";" (often without a full stop).
const paragraphs = (text) =>
  String(text ?? "").replace(/\s*;\s*(?=[A-ZÀ-ÖØ-Þ«"'(\[])/g, "\n");

const norm = (value) =>
  String(value ?? "").normalize("NFKD").replace(/[̀-ͯ]/g, "").toLowerCase();

function loadState() {
  const defaults = { sort: "title", dir: "asc", type: "all", watched: "all", expand: false, view: "grid", q: "" };
  try {
    return { ...defaults, ...JSON.parse(localStorage.getItem(STATE_KEY) || "{}"), q: "" };
  } catch (err) {
    return defaults;
  }
}

class MyMoviesPanel extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._state = loadState();
    this._titles = null;
    this._error = null;
    this._dialog = null; // { kind: "title", key } or { kind: "import" }
    this._busy = false;
    this._onKey = (ev) => ev.key === "Escape" && this._closeDialog();
  }

  set hass(hass) {
    const first = !this._hass;
    this._hass = hass;
    if (this._menu) this._menu.hass = hass;
    if (first) {
      const lang = hass.locale?.language || hass.language || "en";
      this._lang = lang.startsWith("fr") ? "fr" : "en";
      this._t = STRINGS[this._lang];
      this._renderShell();
      this._load();
    }
  }

  set narrow(value) {
    this._narrow = value;
    if (this._menu) this._menu.narrow = value;
  }

  disconnectedCallback() {
    window.removeEventListener("keydown", this._onKey);
  }

  _saveState() {
    try {
      const { q, ...kept } = this._state;
      localStorage.setItem(STATE_KEY, JSON.stringify(kept));
    } catch (err) {
      /* private mode: preferences are simply not remembered */
    }
  }

  async _load() {
    try {
      const result = await this._hass.connection.sendMessagePromise({ type: "mymovies/collection" });
      this._titles = result.titles;
      this._error = null;
    } catch (err) {
      this._error = err.message || String(err);
    }
    this._renderGrid();
    if (this._dialog?.kind === "title") this._renderDialog(false);
  }

  // ---- data -------------------------------------------------------------

  _allItems() {
    const items = [];
    for (const t of this._titles || []) {
      const children = t.children || [];
      if (this._state.expand && children.length) {
        for (const c of children) items.push(this._childItem(t, c));
      } else {
        items.push({ ...t, key: `t:${t.id}` });
      }
    }
    return items;
  }

  _childItem(parent, c) {
    return {
      ...c,
      key: `c:${c.id}`,
      child: true,
      parent,
      sort_title: c.title,
      collection_number: parent.collection_number,
      added: parent.added,
      media_type: parent.media_type,
      group: parent.group,
      parental_rating: parent.parental_rating,
      disc_type: c.disc_type || parent.disc_type,
      watched: !!c.watched,
    };
  }

  _findItem(key) {
    for (const t of this._titles || []) {
      if (`t:${t.id}` === key) return { ...t, key };
      for (const c of t.children || []) {
        if (`c:${c.id}` === key) return this._childItem(t, c);
      }
    }
    return null;
  }

  _visibleItems() {
    const st = this._state;
    const q = norm(st.q.trim());
    const getKey = SORT_KEYS[st.sort] || SORT_KEYS.title;
    const collator = new Intl.Collator(this._lang, { numeric: true, sensitivity: "base" });
    const items = this._allItems().filter((i) => {
      if (st.type !== "all" && i.media_type !== TYPES[st.type]) return false;
      if (st.watched === "watched" && !i.watched) return false;
      if (st.watched === "unwatched" && i.watched) return false;
      if (q) {
        const text = [i.title, i.original_title, i.director, ...(i.actors || []), i.parent?.title].join(" ");
        if (!norm(text).includes(q)) return false;
      }
      return true;
    });
    const sign = st.dir === "desc" ? -1 : 1;
    items.sort((a, b) => {
      const va = getKey(a);
      const vb = getKey(b);
      let r = 0;
      if (va == null && vb == null) r = 0;
      else if (va == null) return 1; // unknown values always last
      else if (vb == null) return -1;
      else r = typeof va === "number" && typeof vb === "number" ? va - vb : collator.compare(String(va), String(vb));
      return sign * r || collator.compare(a.sort_title || a.title || "", b.sort_title || b.title || "");
    });
    return items;
  }

  // ---- formatting -------------------------------------------------------

  _runtime(minutes) {
    if (!minutes) return "";
    const h = Math.floor(minutes / 60);
    const m = String(minutes % 60).padStart(2, "0");
    return this._lang === "fr" ? `${h} h ${m}` : `${h}h ${m}m`;
  }

  _date(iso, short = false) {
    if (!iso) return "";
    const d = new Date(`${iso}T00:00:00`);
    if (isNaN(d)) return iso;
    return d.toLocaleDateString(this._lang, short ? { year: "numeric", month: "short", day: "numeric" } : { year: "numeric", month: "long", day: "numeric" });
  }

  // ---- rendering --------------------------------------------------------

  _renderShell() {
    const t = this._t;
    const st = this._state;
    const isAdmin = !!this._hass.user?.is_admin;
    const sortOptions = Object.keys(SORT_KEYS)
      .map((k) => `<option value="${k}" ${st.sort === k ? "selected" : ""}>${esc(t.sort[k])}</option>`)
      .join("");
    const option = (value, label, current) =>
      `<option value="${value}" ${current === value ? "selected" : ""}>${esc(label)}</option>`;
    const seg = (attr, value, label, current, extra = "") =>
      `<button type="button" role="radio" data-${attr}="${value}" aria-checked="${current === value}" class="${current === value ? "active" : ""}" ${extra}>${label}</button>`;
    this.shadowRoot.innerHTML = `
      <style>${STYLE}</style>
      <div class="header">
        <span class="menu"></span>
        <div class="title">My Movies</div>
        <div class="count"></div>
        ${isAdmin ? `<button class="icon" id="import" title="${esc(t.importCsv)}" aria-label="${esc(t.importCsv)}">${UPLOAD}</button>` : ""}
        <button class="icon" id="refresh" title="${esc(t.refresh)}" aria-label="${esc(t.refresh)}">${REFRESH}</button>
      </div>
      <div class="toolbar">
        <input id="q" type="search" placeholder="${esc(t.search)}" aria-label="${esc(t.search)}" />
        <div class="sortgroup">
          <span class="select"><select id="sort" aria-label="${esc(t.sort.title)}">${sortOptions}</select></span>
          <button class="icon dir ${st.dir}" id="dir" title="${esc(st.dir === "asc" ? t.ascending : t.descending)}" aria-label="${esc(st.dir === "asc" ? t.ascending : t.descending)}">${SORT_ICON}</button>
        </div>
        <span class="select"><select id="type" aria-label="${esc(t.allTypes)}">
          ${option("all", t.allTypes, st.type)}${option("movies", t.movies, st.type)}
          ${option("series", t.series, st.type)}${option("documentaries", t.documentaries, st.type)}
        </select></span>
        <div class="segmented" id="watched" role="radiogroup" aria-label="${esc(t.watchedFilter)}">
          ${seg("watched", "watched", esc(t.segWatched), st.watched)}${seg("watched", "all", esc(t.segAll), st.watched)}${seg("watched", "unwatched", esc(t.segUnwatched), st.watched)}
        </div>
        <label class="check"><input id="expand" type="checkbox" ${st.expand ? "checked" : ""} /> ${esc(t.expand)}</label>
        <div class="segmented icons" id="view" role="radiogroup" aria-label="${esc(t.view)}">
          ${seg("view", "grid", GRID, st.view, `title="${esc(t.grid)}" aria-label="${esc(t.grid)}"`)}${seg("view", "list", LIST, st.view, `title="${esc(t.list)}" aria-label="${esc(t.list)}"`)}
        </div>
      </div>
      <div class="items ${st.view}" id="grid"><div class="message">${esc(t.loading)}</div></div>
      <div id="dialog"></div>`;

    this._menu = document.createElement("ha-menu-button");
    this._menu.hass = this._hass;
    this._menu.narrow = this._narrow;
    this.shadowRoot.querySelector(".menu").appendChild(this._menu);

    const $ = (id) => this.shadowRoot.getElementById(id);
    const update = (patch) => {
      Object.assign(this._state, patch);
      this._saveState();
      this._renderGrid();
    };
    const segmented = (id, attr) =>
      $(id).addEventListener("click", (ev) => {
        const btn = ev.target.closest(`[data-${attr}]`);
        if (!btn) return;
        for (const b of $(id).querySelectorAll("button")) {
          b.classList.toggle("active", b === btn);
          b.setAttribute("aria-checked", String(b === btn));
        }
        update({ [attr]: btn.dataset[attr] });
      });
    $("q").addEventListener("input", (ev) => update({ q: ev.target.value }));
    $("sort").addEventListener("change", (ev) => update({ sort: ev.target.value }));
    $("type").addEventListener("change", (ev) => update({ type: ev.target.value }));
    $("expand").addEventListener("change", (ev) => update({ expand: ev.target.checked }));
    segmented("watched", "watched");
    segmented("view", "view");
    $("dir").addEventListener("click", (ev) => {
      update({ dir: this._state.dir === "asc" ? "desc" : "asc" });
      const btn = ev.currentTarget;
      btn.classList.toggle("desc", this._state.dir === "desc");
      btn.title = this._state.dir === "asc" ? this._t.ascending : this._t.descending;
    });
    $("refresh").addEventListener("click", () => this._load());
    $("import")?.addEventListener("click", () => this._openDialog({ kind: "import" }));
    $("grid").addEventListener("click", (ev) => {
      const item = ev.target.closest("[data-key]");
      if (item) this._openDialog({ kind: "title", key: item.dataset.key });
    });
    $("dialog").addEventListener("click", (ev) => this._onDialogClick(ev));
    // A dead cover link shows the title tile instead of a broken image.
    this.shadowRoot.addEventListener(
      "error",
      (ev) => {
        const img = ev.target;
        if (img.tagName !== "IMG") return;
        const tile = document.createElement("div");
        tile.className = "noposter";
        tile.textContent = img.closest("[title], [aria-label]")?.getAttribute("title") || "";
        img.replaceWith(tile);
      },
      true,
    );
  }

  _cover(i, title) {
    return `
      ${i.poster ? `<img loading="lazy" src="${esc(i.poster)}" alt="" />` : `<div class="noposter">${esc(title)}</div>`}
      ${i.watched ? `<span class="badge" title="${esc(this._t.watched)}">${CHECK}</span>` : ""}`;
  }

  _tag(i) {
    const count = i.children?.length;
    if (i.child) return `<span class="tag">${esc(i.parent.title || "")}</span>`;
    if (count) return `<span class="tag">${esc(this._t.boxSet)} · ${count} ${esc(this._t.films)}</span>`;
    return "";
  }

  _card(i) {
    const title = i.title || `#${i.collection_number}`;
    return `
      <button class="card" data-key="${esc(i.key)}" title="${esc(title)}">
        <div class="poster">${this._cover(i, title)}${this._tag(i)}</div>
        <div class="name">${esc(title)}</div>
        <div class="sub">${esc(i.year || "")}</div>
      </button>`;
  }

  _row(i) {
    const t = this._t;
    const title = i.title || `#${i.collection_number}`;
    const meta = [this._runtime(i.runtime), i.disc_type, i.parental_rating, i.edition].filter(Boolean);
    const people = [i.director, (i.genres || []).join(", ")].filter(Boolean);
    const side = [
      i.rating != null ? `★ ${i.rating}` : "",
      i.child ? "" : `#${i.collection_number}`,
      i.added ? `${t.added} ${this._date(i.added, true)}` : "",
    ].filter(Boolean);
    return `
      <button class="line" data-key="${esc(i.key)}" title="${esc(title)}">
        <span class="thumb">${this._cover(i, title)}</span>
        <span class="main">
          <span class="line-title">${esc(title)}${i.year ? ` <span class="year">(${esc(i.year)})</span>` : ""}</span>
          ${i.original_title && i.original_title !== title ? `<span class="line-sub">${esc(i.original_title)}</span>` : ""}
          ${meta.length ? `<span class="line-meta">${meta.map(esc).join(" · ")}</span>` : ""}
          ${people.length ? `<span class="line-meta">${people.map(esc).join(" · ")}</span>` : ""}
          ${i.child ? `<span class="line-meta">${esc(t.inBoxSet)} : ${esc(i.parent.title || "")}</span>` : ""}
          ${!i.child && i.children?.length ? `<span class="line-meta">${esc(t.boxSet)} · ${i.children.length} ${esc(t.films)}</span>` : ""}
        </span>
        <span class="side">${side.map((s) => `<span>${esc(s)}</span>`).join("")}</span>
      </button>`;
  }

  _renderGrid() {
    const grid = this.shadowRoot.getElementById("grid");
    const count = this.shadowRoot.querySelector(".count");
    if (!grid) return;
    grid.className = `items ${this._state.view}`;
    if (this._error) {
      grid.innerHTML = `<div class="message">${esc(this._t.error)} : ${esc(this._error)}</div>`;
      count.textContent = "";
      return;
    }
    if (!this._titles) return;
    const items = this._visibleItems();
    count.textContent = `${items.length} ${this._t.titles}`;
    const render = this._state.view === "list" ? (i) => this._row(i) : (i) => this._card(i);
    grid.innerHTML = items.length ? items.map(render).join("") : `<div class="message">${esc(this._t.empty)}</div>`;
  }

  // ---- dialogs ----------------------------------------------------------

  _openDialog(dialog) {
    this._dialog = { ...dialog, error: null, status: null };
    window.addEventListener("keydown", this._onKey);
    this._renderDialog(true);
  }

  _closeDialog() {
    if (!this._dialog) return;
    this._dialog = null;
    window.removeEventListener("keydown", this._onKey);
    const root = this.shadowRoot.getElementById("dialog");
    const backdrop = root.querySelector(".backdrop");
    if (!backdrop) return;
    let done = false;
    const clear = () => {
      if (done) return;
      done = true;
      if (!this._dialog) root.innerHTML = "";
    };
    backdrop.classList.add("leaving");
    backdrop.addEventListener("animationend", clear, { once: true });
    setTimeout(clear, 250); // reduced motion: no animation event
  }

  _info(label, value) {
    return value || value === 0 ? `<div class="info-row"><span>${esc(label)}</span><span>${esc(value)}</span></div>` : "";
  }

  _renderDialog(animate) {
    const root = this.shadowRoot.getElementById("dialog");
    const body = this._dialog.kind === "import" ? this._importBody() : this._titleBody();
    if (body === null) return this._closeDialog();
    root.innerHTML = `
      <div class="backdrop ${animate ? "" : "static"}" data-action="close">
        <div class="dialog ${this._dialog.kind}" role="dialog" aria-modal="true">
          <button class="icon close" data-action="close" title="${esc(this._t.close)}" aria-label="${esc(this._t.close)}">×</button>
          ${body}
        </div>
      </div>`;
  }

  _titleBody() {
    const t = this._t;
    const i = this._findItem(this._dialog.key);
    if (!i) return null;
    const title = i.title || `#${i.collection_number}`;
    const meta = [i.year, this._runtime(i.runtime), i.parental_rating, i.disc_type, i.edition].filter(Boolean);
    const children = !i.child ? i.children || [] : [];
    return `
      <div class="body">
        <div class="cover">${this._cover(i, title)}</div>
        <div class="info">
          <h2>${esc(title)}</h2>
          ${i.original_title && i.original_title !== title ? `<div class="original">${esc(i.original_title)}</div>` : ""}
          <div class="meta">${meta.map(esc).join(" · ")}</div>
          ${i.genres?.length ? `<div class="chips">${i.genres.map((g) => `<span>${esc(g)}</span>`).join("")}</div>` : ""}
          ${i.description ? `<p class="description">${esc(paragraphs(i.description))}</p>` : ""}
          <div class="info-rows">
            ${this._info(t.director, i.director)}
            ${this._info(t.cast, (i.actors || []).join(", "))}
            ${this._info(t.rating, i.rating != null ? `★ ${i.rating}/10` : "")}
            ${this._info(t.personalRating, i.personal_rating != null ? `★ ${i.personal_rating}` : "")}
            ${this._info(t.released, this._date(i.release_date))}
            ${this._info(t.added, this._date(i.added))}
            ${this._info(t.number, i.child ? "" : i.collection_number)}
            ${this._info(t.group, i.group)}
          </div>
          ${i.child ? `<div class="info-rows"><div class="info-row"><span>${esc(t.inBoxSet)}</span><a href="#" data-open="t:${esc(i.parent.id)}">${esc(i.parent.title || "")}</a></div></div>` : ""}
          ${children.length ? `
            <h3>${esc(t.contents)}</h3>
            <div class="children">
              ${children.map((c) => `
                <button class="mini" data-open="c:${esc(c.id)}" title="${esc(c.title)}">
                  <span class="mini-cover">
                    ${c.poster ? `<img loading="lazy" src="${esc(c.poster)}" alt="" />` : `<div class="noposter">${esc(c.title)}</div>`}
                    ${c.watched ? `<span class="badge small" title="${esc(t.watched)}">${CHECK}</span>` : ""}
                  </span>
                  <span>${esc(c.title)}${c.year ? ` (${esc(c.year)})` : ""}</span>
                </button>`).join("")}
            </div>` : ""}
          <div class="actions">
            ${this._dialog.error ? `<span class="error">${esc(t.failed)} : ${esc(this._dialog.error)}</span>` : ""}
            ${i.watched ? `<button class="secondary" data-action="clear" ${this._busy ? "disabled" : ""}>${esc(t.clearWatched)}</button>` : ""}
            <button class="primary" data-action="mark" ${this._busy ? "disabled" : ""}>${esc(t.markWatched)}</button>
          </div>
        </div>
      </div>`;
  }

  _importBody() {
    const t = this._t;
    const d = this._dialog;
    return `
      <div class="import-body">
        <h2>${esc(t.importTitle)}</h2>
        <p>${esc(t.importText)}</p>
        <input id="file" type="file" accept=".csv,text/csv" ${this._busy ? "disabled" : ""} />
        <div class="actions">
          ${d.error ? `<span class="error">${esc(t.failed)} : ${esc(d.error)}</span>` : ""}
          ${d.status ? `<span class="ok">${esc(d.status)}</span>` : ""}
          <button class="primary" data-action="import" ${this._busy ? "disabled" : ""}>${esc(this._busy ? t.importing : t.importButton)}</button>
        </div>
      </div>`;
  }

  async _onDialogClick(ev) {
    const open = ev.target.closest("[data-open]");
    if (open) {
      ev.preventDefault();
      this._dialog = { kind: "title", key: open.dataset.open, error: null };
      return this._renderDialog(false);
    }
    const action = ev.target.closest("[data-action]")?.dataset.action;
    if (action === "close" && (ev.target.dataset.action === "close" || ev.target.closest(".close"))) {
      return this._closeDialog();
    }
    if (action === "import") return this._import();
    if (action !== "mark" && action !== "clear") return;
    const item = this._findItem(this._dialog.key);
    this._busy = true;
    this._renderDialog(false);
    try {
      await this._hass.callService("mymovies", action === "mark" ? "mark_watched" : "clear_watched", { title: item.id });
      this._dialog.error = null;
      await this._load();
    } catch (err) {
      if (this._dialog) this._dialog.error = err.message || String(err);
    } finally {
      this._busy = false;
      if (this._dialog) this._renderDialog(false);
    }
  }

  async _import() {
    const file = this.shadowRoot.getElementById("file")?.files?.[0];
    if (!file || this._busy) return;
    this._busy = true;
    this._dialog.error = null;
    this._dialog.status = null;
    this._renderDialog(false);
    try {
      const form = new FormData();
      form.append("file", file);
      const resp = await this._hass.fetchWithAuth("/api/file_upload", { method: "POST", body: form });
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const { file_id } = await resp.json();
      const result = await this._hass.connection.sendMessagePromise({ type: "mymovies/import_export", file_id });
      if (this._dialog) this._dialog.status = this._t.imported.replace("{n}", result.count);
      await this._load();
    } catch (err) {
      if (this._dialog) this._dialog.error = err.message || String(err);
    } finally {
      this._busy = false;
      if (this._dialog) this._renderDialog(false);
    }
  }
}

const STYLE = `
  :host { display: block; min-height: 100vh; background: var(--primary-background-color); color: var(--primary-text-color); font-family: var(--paper-font-body1_-_font-family, Roboto, sans-serif); }
  svg { width: 20px; height: 20px; fill: currentColor; }
  button { font: inherit; color: inherit; }
  .header { display: flex; align-items: center; gap: 4px; height: var(--header-height, 56px); padding: 0 8px 0 12px; background: var(--app-header-background-color, var(--primary-color)); color: var(--app-header-text-color, #fff); position: sticky; top: 0; z-index: 2; }
  .header .title { font-size: 20px; flex: 1; margin-left: 4px; }
  .header .count { opacity: 0.85; font-size: 14px; margin-right: 8px; }
  .toolbar { display: flex; flex-wrap: wrap; align-items: center; gap: 8px 12px; padding: 12px 16px; }
  .toolbar input[type="search"], .toolbar select { height: 36px; padding: 0 10px; border-radius: 8px; border: 1px solid var(--divider-color); background: var(--card-background-color); color: var(--primary-text-color); font-size: 14px; box-sizing: border-box; }
  .toolbar input[type="search"] { flex: 0 1 200px; min-width: 120px; }
  /* Own chevron: the native arrow of macOS sits against the border. */
  .select { position: relative; display: inline-flex; flex: none; }
  .select::after { content: ""; position: absolute; right: 10px; top: 50%; width: 18px; height: 18px; margin-top: -9px; pointer-events: none; background: var(--secondary-text-color);
    -webkit-mask: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'%3E%3Cpath d='M7.41 8.58 12 13.17l4.59-4.59L18 10l-6 6-6-6z'/%3E%3C/svg%3E") center / contain no-repeat;
    mask: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'%3E%3Cpath d='M7.41 8.58 12 13.17l4.59-4.59L18 10l-6 6-6-6z'/%3E%3C/svg%3E") center / contain no-repeat; }
  .toolbar select { -webkit-appearance: none; appearance: none; width: auto; padding: 0 36px 0 12px; cursor: pointer; }
  .toolbar select option { background: var(--card-background-color); color: var(--primary-text-color); }
  .sortgroup { display: flex; gap: 4px; }
  .check { display: flex; align-items: center; gap: 6px; font-size: 14px; cursor: pointer; user-select: none; white-space: nowrap; }
  .icon { display: inline-flex; align-items: center; justify-content: center; width: 36px; height: 36px; border: none; border-radius: 50%; background: transparent; cursor: pointer; flex: none; }
  .icon:hover { background: rgba(127, 127, 127, 0.15); }
  .dir { border: 1px solid var(--divider-color); border-radius: 8px; background: var(--card-background-color); }
  .dir.desc svg { transform: scaleY(-1); }
  .segmented { display: inline-flex; flex: none; padding: 2px; border-radius: 10px; border: 1px solid var(--divider-color); background: var(--card-background-color); }
  .segmented button { height: 30px; padding: 0 12px; border: none; border-radius: 8px; background: transparent; cursor: pointer; font-size: 13px; white-space: nowrap; color: var(--secondary-text-color); transition: background 0.15s, color 0.15s; }
  .segmented button.active { background: var(--primary-color); color: var(--text-primary-color, #fff); }
  .segmented.icons { margin-left: auto; }
  .segmented.icons button { width: 36px; padding: 0; display: inline-flex; align-items: center; justify-content: center; }
  .segmented.icons svg { width: 18px; height: 18px; }
  .items { padding: 0 16px 24px; }
  .items.grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(140px, 1fr)); gap: 16px; }
  .items.list { display: flex; flex-direction: column; gap: 6px; }
  .message { grid-column: 1 / -1; padding: 32px; text-align: center; color: var(--secondary-text-color); }
  .card { display: flex; flex-direction: column; gap: 4px; padding: 0; border: none; background: none; text-align: left; cursor: pointer; }
  .card:focus-visible, .line:focus-visible { outline: 2px solid var(--primary-color); outline-offset: 2px; border-radius: 8px; }
  .poster, .cover, .thumb { position: relative; aspect-ratio: 2 / 3; border-radius: 8px; overflow: hidden; background: var(--secondary-background-color, #2224); box-shadow: 0 2px 6px rgba(0, 0, 0, 0.25); }
  .poster img, .cover img, .thumb img { width: 100%; height: 100%; object-fit: cover; display: block; transition: transform 0.15s; }
  .card:hover .poster img { transform: scale(1.04); }
  .noposter { display: flex; align-items: center; justify-content: center; height: 100%; padding: 8px; text-align: center; font-size: 13px; color: var(--secondary-text-color); box-sizing: border-box; }
  .badge { position: absolute; top: 6px; right: 6px; width: 28px; height: 28px; border-radius: 50%; display: flex; align-items: center; justify-content: center; background: var(--success-color, #43a047); color: #fff; box-shadow: 0 1px 4px rgba(0, 0, 0, 0.5); }
  .badge svg { width: 18px; height: 18px; }
  .badge.small, .thumb .badge { width: 20px; height: 20px; top: 4px; right: 4px; }
  .badge.small svg, .thumb .badge svg { width: 14px; height: 14px; }
  .tag { position: absolute; left: 6px; bottom: 6px; max-width: calc(100% - 12px); padding: 2px 8px; border-radius: 10px; background: rgba(0, 0, 0, 0.72); color: #fff; font-size: 11px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; box-sizing: border-box; }
  .name { font-size: 13px; line-height: 1.25; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
  .sub { font-size: 12px; color: var(--secondary-text-color); }
  .line { display: flex; align-items: center; gap: 14px; padding: 8px; border: none; border-radius: 10px; background: var(--card-background-color); text-align: left; cursor: pointer; transition: background 0.15s; }
  .line:hover { background: rgba(127, 127, 127, 0.12); }
  .thumb { flex: 0 0 56px; border-radius: 6px; box-shadow: none; }
  .main { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 2px; }
  .line-title { font-size: 15px; font-weight: 500; }
  .line-title .year { font-weight: 400; color: var(--secondary-text-color); }
  .line-sub { font-size: 13px; font-style: italic; color: var(--secondary-text-color); }
  .line-meta { font-size: 13px; color: var(--secondary-text-color); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .side { flex: none; display: flex; flex-direction: column; align-items: flex-end; gap: 2px; font-size: 13px; color: var(--secondary-text-color); }
  .side span:first-child { color: var(--primary-text-color); }
  .backdrop { position: fixed; inset: 0; z-index: 10; display: flex; align-items: center; justify-content: center; padding: 16px; background: rgba(0, 0, 0, 0.6); animation: fade-in 0.18s ease-out; }
  .dialog { position: relative; width: min(900px, 100%); max-height: calc(100vh - 32px); overflow: auto; border-radius: 16px; background: var(--card-background-color); box-shadow: 0 8px 32px rgba(0, 0, 0, 0.5); animation: pop-in 0.22s cubic-bezier(0.2, 0.8, 0.2, 1); }
  .dialog.import { width: min(520px, 100%); }
  .backdrop.static, .backdrop.static .dialog { animation: none; }
  .backdrop.leaving { animation: fade-out 0.16s ease-in forwards; }
  .backdrop.leaving .dialog { animation: pop-out 0.16s ease-in forwards; }
  @keyframes fade-in { from { opacity: 0; } }
  @keyframes fade-out { to { opacity: 0; } }
  @keyframes pop-in { from { opacity: 0; transform: translateY(16px) scale(0.97); } }
  @keyframes pop-out { to { opacity: 0; transform: translateY(10px) scale(0.98); } }
  @media (prefers-reduced-motion: reduce) { .backdrop, .dialog, .backdrop.leaving, .backdrop.leaving .dialog { animation: none !important; } }
  .close { position: absolute; top: 8px; right: 8px; font-size: 26px; z-index: 1; }
  .body { display: flex; gap: 24px; padding: 24px; }
  .cover { flex: 0 0 240px; align-self: flex-start; }
  .info { flex: 1; min-width: 0; }
  .info h2, .import-body h2 { margin: 0 32px 4px 0; font-size: 24px; font-weight: 500; }
  .original { font-style: italic; color: var(--secondary-text-color); margin-bottom: 4px; }
  .meta { color: var(--secondary-text-color); font-size: 14px; margin-bottom: 8px; }
  .chips { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 12px; }
  .chips span { padding: 2px 10px; border-radius: 12px; font-size: 12px; background: rgba(127, 127, 127, 0.18); }
  .description { line-height: 1.5; margin: 0 0 12px; white-space: pre-line; }
  .info-rows { display: grid; gap: 4px; margin-bottom: 12px; font-size: 14px; }
  .info-row { display: grid; grid-template-columns: 150px 1fr; gap: 8px; }
  .info-row span:first-child { color: var(--secondary-text-color); }
  .info-row a { color: var(--primary-color); }
  h3 { margin: 16px 0 8px; font-size: 16px; font-weight: 500; }
  .children { display: grid; grid-template-columns: repeat(auto-fill, minmax(96px, 1fr)); gap: 10px; }
  .mini { display: flex; flex-direction: column; gap: 4px; padding: 0; border: none; background: none; text-align: left; cursor: pointer; font-size: 12px; }
  .mini-cover { position: relative; display: block; }
  .mini img, .mini .noposter { width: 100%; aspect-ratio: 2 / 3; object-fit: cover; border-radius: 6px; background: var(--secondary-background-color, #2224); display: block; }
  .import-body { padding: 24px; }
  .import-body p { line-height: 1.5; color: var(--secondary-text-color); }
  .import-body input[type="file"] { margin: 8px 0; max-width: 100%; }
  .actions { display: flex; flex-wrap: wrap; align-items: center; justify-content: flex-end; gap: 8px; margin-top: 16px; }
  .actions .error { color: var(--error-color, #db4437); font-size: 13px; margin-right: auto; }
  .actions .ok { color: var(--success-color, #43a047); font-size: 13px; margin-right: auto; }
  .primary, .secondary { height: 36px; padding: 0 16px; border-radius: 18px; border: none; cursor: pointer; font-weight: 500; }
  .primary { background: var(--primary-color); color: var(--text-primary-color, #fff); }
  .secondary { background: transparent; color: var(--primary-color); border: 1px solid var(--primary-color); }
  .primary[disabled], .secondary[disabled] { opacity: 0.5; cursor: default; }
  @media (max-width: 600px) {
    .items { padding: 0 12px 16px; }
    .items.grid { grid-template-columns: repeat(auto-fill, minmax(104px, 1fr)); gap: 12px; }
    .toolbar input[type="search"] { flex: 1 1 100%; }
    .segmented.icons { margin-left: 0; }
    .side { display: none; }
    .body { flex-direction: column; padding: 16px; }
    .cover { flex-basis: auto; width: 160px; align-self: center; }
    .info-row { grid-template-columns: 120px 1fr; }
  }
`;

if (!customElements.get("mymovies-panel")) {
  customElements.define("mymovies-panel", MyMoviesPanel);
}
