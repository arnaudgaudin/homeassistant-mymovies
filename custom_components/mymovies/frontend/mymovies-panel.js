/*
 * My Movies panel for Home Assistant: the collection as a wall of covers,
 * with the sort options of My Movies, filters, watched badges, box sets that
 * can be expanded, and a details dialog to mark titles as watched.
 * Plain web component, no build step and no external dependency.
 */

const STRINGS = {
  en: {
    search: "Search", ascending: "Ascending", descending: "Descending",
    allTypes: "All types", movies: "Movies", series: "TV series", documentaries: "Documentaries",
    allTitles: "All titles", watchedOnly: "Watched", unwatchedOnly: "Not watched",
    expand: "Expand box sets", refresh: "Refresh", titles: "titles", films: "films",
    boxSet: "Box set", markWatched: "Mark as watched", clearWatched: "Clear watched",
    close: "Close", director: "Director", cast: "Cast", genres: "Genres", runtime: "Runtime",
    rating: "Rating", personalRating: "Personal rating", parental: "Parental rating",
    released: "Released", added: "Added", disc: "Disc", edition: "Edition",
    number: "Collection no.", group: "Group", inBoxSet: "In box set",
    contents: "Box set contents", loading: "Loading…", error: "Could not load the collection",
    empty: "No title matches", watched: "Watched", failed: "Action failed",
    sort: {
      title: "Title", collection_number: "Collection number", rating: "Rating",
      personal_rating: "Personal rating", runtime: "Running time", year: "Production year",
      release_date: "Release date", parental_rating: "Parental rating", added: "Added date",
    },
  },
  fr: {
    search: "Rechercher", ascending: "Croissant", descending: "Décroissant",
    allTypes: "Tous les types", movies: "Films", series: "Séries", documentaries: "Documentaires",
    allTitles: "Tous les titres", watchedOnly: "Vus", unwatchedOnly: "Non vus",
    expand: "Déplier les coffrets", refresh: "Actualiser", titles: "titres", films: "films",
    boxSet: "Coffret", markWatched: "Marquer comme vu", clearWatched: "Effacer le « vu »",
    close: "Fermer", director: "Réalisation", cast: "Avec", genres: "Genres", runtime: "Durée",
    rating: "Note", personalRating: "Note personnelle", parental: "Classification",
    released: "Sortie", added: "Ajouté le", disc: "Support", edition: "Édition",
    number: "N° de collection", group: "Groupe", inBoxSet: "Dans le coffret",
    contents: "Contenu du coffret", loading: "Chargement…",
    error: "Impossible de charger la collection", empty: "Aucun titre ne correspond",
    watched: "Vu", failed: "L'action a échoué",
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
const CHECK = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M9 16.17 4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z"/></svg>';
const SORT_ICON = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M7 4v13H4l4 4 4-4H9V4zm7 0-4 4h3v13h2V8h3z"/></svg>';
const REFRESH = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M17.65 6.35A7.96 7.96 0 0 0 12 4a8 8 0 1 0 7.73 10h-2.08A6 6 0 1 1 12 6c1.66 0 3.14.69 4.22 1.78L13 11h7V4z"/></svg>';

const esc = (value) =>
  String(value ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);

const norm = (value) =>
  String(value ?? "").normalize("NFKD").replace(/[̀-ͯ]/g, "").toLowerCase();

function loadState() {
  const defaults = { sort: "title", dir: "asc", type: "all", watched: "all", expand: false, q: "" };
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
    this._dialog = null; // { key } of the item shown in the dialog
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
    if (this._dialog) this._renderDialog();
  }

  // ---- data -------------------------------------------------------------

  _allItems() {
    const items = [];
    for (const t of this._titles || []) {
      const children = t.children || [];
      if (this._state.expand && children.length) {
        for (const c of children) {
          items.push({
            ...c,
            key: `c:${c.id}`,
            child: true,
            parent: t,
            sort_title: c.title,
            collection_number: t.collection_number,
            added: t.added,
            media_type: t.media_type,
            group: t.group,
            parental_rating: t.parental_rating,
            disc_type: c.disc_type || t.disc_type,
            watched: false,
          });
        }
      } else {
        items.push({ ...t, key: `t:${t.id}` });
      }
    }
    return items;
  }

  _findItem(key) {
    for (const t of this._titles || []) {
      if (`t:${t.id}` === key) return { ...t, key };
      for (const c of t.children || []) {
        if (`c:${c.id}` === key) return { ...c, key, child: true, parent: t, watched: false };
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

  _date(iso) {
    if (!iso) return "";
    const d = new Date(`${iso}T00:00:00`);
    return isNaN(d) ? iso : d.toLocaleDateString(this._lang, { year: "numeric", month: "long", day: "numeric" });
  }

  // ---- rendering --------------------------------------------------------

  _renderShell() {
    const t = this._t;
    const st = this._state;
    const sortOptions = Object.keys(SORT_KEYS)
      .map((k) => `<option value="${k}" ${st.sort === k ? "selected" : ""}>${esc(t.sort[k])}</option>`)
      .join("");
    const option = (value, label, current) =>
      `<option value="${value}" ${current === value ? "selected" : ""}>${esc(label)}</option>`;
    this.shadowRoot.innerHTML = `
      <style>${STYLE}</style>
      <div class="header">
        <span class="menu"></span>
        <div class="title">My Movies</div>
        <div class="count"></div>
        <button class="icon" id="refresh" title="${esc(t.refresh)}">${REFRESH}</button>
      </div>
      <div class="toolbar">
        <input id="q" type="search" placeholder="${esc(t.search)}" />
        <select id="sort" aria-label="sort">${sortOptions}</select>
        <button class="icon dir ${st.dir}" id="dir" title="${esc(st.dir === "asc" ? t.ascending : t.descending)}">${SORT_ICON}</button>
        <select id="type">
          ${option("all", t.allTypes, st.type)}${option("movies", t.movies, st.type)}
          ${option("series", t.series, st.type)}${option("documentaries", t.documentaries, st.type)}
        </select>
        <select id="watched">
          ${option("all", t.allTitles, st.watched)}${option("watched", t.watchedOnly, st.watched)}
          ${option("unwatched", t.unwatchedOnly, st.watched)}
        </select>
        <label class="check"><input id="expand" type="checkbox" ${st.expand ? "checked" : ""} /> ${esc(t.expand)}</label>
      </div>
      <div class="grid" id="grid"><div class="message">${esc(t.loading)}</div></div>
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
    $("q").addEventListener("input", (ev) => update({ q: ev.target.value }));
    $("sort").addEventListener("change", (ev) => update({ sort: ev.target.value }));
    $("type").addEventListener("change", (ev) => update({ type: ev.target.value }));
    $("watched").addEventListener("change", (ev) => update({ watched: ev.target.value }));
    $("expand").addEventListener("change", (ev) => update({ expand: ev.target.checked }));
    $("dir").addEventListener("click", (ev) => {
      update({ dir: this._state.dir === "asc" ? "desc" : "asc" });
      const btn = ev.currentTarget;
      btn.classList.toggle("desc", this._state.dir === "desc");
      btn.title = this._state.dir === "asc" ? this._t.ascending : this._t.descending;
    });
    $("refresh").addEventListener("click", () => this._load());
    $("grid").addEventListener("click", (ev) => {
      const card = ev.target.closest("[data-key]");
      if (card) this._openDialog(card.dataset.key);
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

  _card(i) {
    const title = i.title || `#${i.collection_number}`;
    const count = i.children?.length;
    return `
      <button class="card" data-key="${esc(i.key)}" title="${esc(title)}">
        <div class="poster">
          ${i.poster ? `<img loading="lazy" src="${esc(i.poster)}" alt="" />` : `<div class="noposter">${esc(title)}</div>`}
          ${i.watched ? `<span class="badge" title="${esc(this._t.watched)}">${CHECK}</span>` : ""}
          ${!i.child && count ? `<span class="tag">${esc(this._t.boxSet)} · ${count} ${esc(this._t.films)}</span>` : ""}
          ${i.child ? `<span class="tag">${esc(i.parent.title || "")}</span>` : ""}
        </div>
        <div class="name">${esc(title)}</div>
        <div class="sub">${esc(i.year || "")}</div>
      </button>`;
  }

  _renderGrid() {
    const grid = this.shadowRoot.getElementById("grid");
    const count = this.shadowRoot.querySelector(".count");
    if (!grid) return;
    if (this._error) {
      grid.innerHTML = `<div class="message">${esc(this._t.error)} : ${esc(this._error)}</div>`;
      count.textContent = "";
      return;
    }
    if (!this._titles) return;
    const items = this._visibleItems();
    count.textContent = `${items.length} ${this._t.titles}`;
    grid.innerHTML = items.length
      ? items.map((i) => this._card(i)).join("")
      : `<div class="message">${esc(this._t.empty)}</div>`;
  }

  _openDialog(key) {
    this._dialog = { key, error: null };
    window.addEventListener("keydown", this._onKey);
    this._renderDialog();
  }

  _closeDialog() {
    this._dialog = null;
    window.removeEventListener("keydown", this._onKey);
    this.shadowRoot.getElementById("dialog").innerHTML = "";
  }

  _row(label, value) {
    return value || value === 0 ? `<div class="row"><span>${esc(label)}</span><span>${esc(value)}</span></div>` : "";
  }

  _renderDialog() {
    const t = this._t;
    const i = this._findItem(this._dialog.key);
    const root = this.shadowRoot.getElementById("dialog");
    if (!i) return this._closeDialog();
    const title = i.title || `#${i.collection_number}`;
    const meta = [i.year, this._runtime(i.runtime), i.parental_rating, i.disc_type, i.edition].filter(Boolean);
    const children = !i.child ? i.children || [] : [];
    root.innerHTML = `
      <div class="backdrop" data-action="close">
        <div class="dialog" role="dialog" aria-modal="true" aria-label="${esc(title)}">
          <button class="icon close" data-action="close" title="${esc(t.close)}">×</button>
          <div class="body">
            <div class="cover">
              ${i.poster ? `<img src="${esc(i.poster)}" alt="" />` : `<div class="noposter">${esc(title)}</div>`}
              ${i.watched ? `<span class="badge" title="${esc(t.watched)}">${CHECK}</span>` : ""}
            </div>
            <div class="info">
              <h2>${esc(title)}</h2>
              ${i.original_title && i.original_title !== title ? `<div class="original">${esc(i.original_title)}</div>` : ""}
              <div class="meta">${meta.map(esc).join(" · ")}</div>
              ${i.genres?.length ? `<div class="chips">${i.genres.map((g) => `<span>${esc(g)}</span>`).join("")}</div>` : ""}
              ${i.description ? `<p class="description">${esc(i.description)}</p>` : ""}
              <div class="rows">
                ${this._row(t.director, i.director)}
                ${this._row(t.cast, (i.actors || []).join(", "))}
                ${this._row(t.rating, i.rating != null ? `★ ${i.rating}/10` : "")}
                ${this._row(t.personalRating, i.personal_rating != null ? `★ ${i.personal_rating}` : "")}
                ${this._row(t.released, this._date(i.release_date))}
                ${this._row(t.added, this._date(i.added))}
                ${this._row(t.number, i.child ? "" : i.collection_number)}
                ${this._row(t.group, i.group)}
              </div>
              ${i.child ? `<div class="rows"><div class="row"><span>${esc(t.inBoxSet)}</span><a href="#" data-open="t:${esc(i.parent.id)}">${esc(i.parent.title || "")}</a></div></div>` : ""}
              ${children.length ? `
                <h3>${esc(t.contents)}</h3>
                <div class="children">
                  ${children.map((c) => `
                    <button class="mini" data-open="c:${esc(c.id)}" title="${esc(c.title)}">
                      ${c.poster ? `<img loading="lazy" src="${esc(c.poster)}" alt="" />` : `<div class="noposter">${esc(c.title)}</div>`}
                      <span>${esc(c.title)}${c.year ? ` (${esc(c.year)})` : ""}</span>
                    </button>`).join("")}
                </div>` : ""}
              ${!i.child ? `
                <div class="actions">
                  ${this._dialog.error ? `<span class="error">${esc(t.failed)} : ${esc(this._dialog.error)}</span>` : ""}
                  ${i.watched ? `<button class="secondary" data-action="clear" ${this._busy ? "disabled" : ""}>${esc(t.clearWatched)}</button>` : ""}
                  <button class="primary" data-action="mark" ${this._busy ? "disabled" : ""}>${esc(t.markWatched)}</button>
                </div>` : ""}
            </div>
          </div>
        </div>
      </div>`;
  }

  async _onDialogClick(ev) {
    const open = ev.target.closest("[data-open]");
    if (open) {
      ev.preventDefault();
      this._dialog = { key: open.dataset.open, error: null };
      return this._renderDialog();
    }
    const action = ev.target.closest("[data-action]")?.dataset.action;
    if (action === "close" && (ev.target.dataset.action === "close" || ev.target.closest(".close"))) {
      return this._closeDialog();
    }
    if (action !== "mark" && action !== "clear") return;
    const item = this._findItem(this._dialog.key);
    this._busy = true;
    this._renderDialog();
    try {
      await this._hass.callService("mymovies", action === "mark" ? "mark_watched" : "clear_watched", { title: item.id });
      this._dialog.error = null;
      await this._load();
    } catch (err) {
      this._dialog.error = err.message || String(err);
    } finally {
      this._busy = false;
      if (this._dialog) this._renderDialog();
    }
  }
}

const STYLE = `
  :host { display: block; min-height: 100vh; background: var(--primary-background-color); color: var(--primary-text-color); font-family: var(--paper-font-body1_-_font-family, Roboto, sans-serif); }
  svg { width: 20px; height: 20px; fill: currentColor; }
  .header { display: flex; align-items: center; gap: 8px; height: var(--header-height, 56px); padding: 0 12px; background: var(--app-header-background-color, var(--primary-color)); color: var(--app-header-text-color, #fff); position: sticky; top: 0; z-index: 2; }
  .header .title { font-size: 20px; flex: 1; }
  .header .count { opacity: 0.85; font-size: 14px; }
  .toolbar { display: flex; flex-wrap: wrap; align-items: center; gap: 8px; padding: 12px 16px; }
  .toolbar input[type="search"], .toolbar select { height: 36px; padding: 0 10px; border-radius: 8px; border: 1px solid var(--divider-color); background: var(--card-background-color); color: var(--primary-text-color); font-size: 14px; }
  .toolbar input[type="search"] { flex: 1 1 180px; min-width: 140px; }
  .check { display: flex; align-items: center; gap: 6px; font-size: 14px; cursor: pointer; user-select: none; }
  button { font: inherit; color: inherit; }
  .icon { display: inline-flex; align-items: center; justify-content: center; width: 36px; height: 36px; border: none; border-radius: 50%; background: transparent; cursor: pointer; }
  .icon:hover { background: rgba(127, 127, 127, 0.15); }
  .dir { border: 1px solid var(--divider-color); border-radius: 8px; background: var(--card-background-color); }
  .dir.desc svg { transform: scaleY(-1); }
  .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(140px, 1fr)); gap: 16px; padding: 0 16px 24px; }
  .message { grid-column: 1 / -1; padding: 32px; text-align: center; color: var(--secondary-text-color); }
  .card { display: flex; flex-direction: column; gap: 4px; padding: 0; border: none; background: none; text-align: left; cursor: pointer; }
  .card:focus-visible { outline: 2px solid var(--primary-color); outline-offset: 2px; border-radius: 8px; }
  .poster, .cover { position: relative; aspect-ratio: 2 / 3; border-radius: 8px; overflow: hidden; background: var(--secondary-background-color, #2224); box-shadow: 0 2px 6px rgba(0, 0, 0, 0.25); }
  .poster img, .cover img { width: 100%; height: 100%; object-fit: cover; display: block; transition: transform 0.15s; }
  .card:hover .poster img { transform: scale(1.04); }
  .noposter { display: flex; align-items: center; justify-content: center; height: 100%; padding: 8px; text-align: center; font-size: 13px; color: var(--secondary-text-color); }
  .badge { position: absolute; top: 6px; right: 6px; width: 28px; height: 28px; border-radius: 50%; display: flex; align-items: center; justify-content: center; background: var(--success-color, #43a047); color: #fff; box-shadow: 0 1px 4px rgba(0, 0, 0, 0.5); }
  .badge svg { width: 18px; height: 18px; }
  .tag { position: absolute; left: 6px; bottom: 6px; max-width: calc(100% - 12px); padding: 2px 8px; border-radius: 10px; background: rgba(0, 0, 0, 0.72); color: #fff; font-size: 11px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .name { font-size: 13px; line-height: 1.25; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
  .sub { font-size: 12px; color: var(--secondary-text-color); }
  .backdrop { position: fixed; inset: 0; z-index: 10; display: flex; align-items: center; justify-content: center; padding: 16px; background: rgba(0, 0, 0, 0.6); }
  .dialog { position: relative; width: min(900px, 100%); max-height: calc(100vh - 32px); overflow: auto; border-radius: 16px; background: var(--card-background-color); box-shadow: 0 8px 32px rgba(0, 0, 0, 0.5); }
  .close { position: absolute; top: 8px; right: 8px; font-size: 26px; z-index: 1; }
  .body { display: flex; gap: 24px; padding: 24px; }
  .cover { flex: 0 0 240px; align-self: flex-start; }
  .info { flex: 1; min-width: 0; }
  .info h2 { margin: 0 32px 4px 0; font-size: 24px; font-weight: 500; }
  .original { font-style: italic; color: var(--secondary-text-color); margin-bottom: 4px; }
  .meta { color: var(--secondary-text-color); font-size: 14px; margin-bottom: 8px; }
  .chips { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 12px; }
  .chips span { padding: 2px 10px; border-radius: 12px; font-size: 12px; background: rgba(127, 127, 127, 0.18); }
  .description { line-height: 1.5; margin: 0 0 12px; white-space: pre-line; }
  .rows { display: grid; gap: 4px; margin-bottom: 12px; font-size: 14px; }
  .row { display: grid; grid-template-columns: 150px 1fr; gap: 8px; }
  .row span:first-child { color: var(--secondary-text-color); }
  .row a { color: var(--primary-color); }
  h3 { margin: 16px 0 8px; font-size: 16px; font-weight: 500; }
  .children { display: grid; grid-template-columns: repeat(auto-fill, minmax(96px, 1fr)); gap: 10px; }
  .mini { display: flex; flex-direction: column; gap: 4px; padding: 0; border: none; background: none; text-align: left; cursor: pointer; font-size: 12px; }
  .mini img, .mini .noposter { width: 100%; aspect-ratio: 2 / 3; object-fit: cover; border-radius: 6px; background: var(--secondary-background-color, #2224); }
  .actions { display: flex; flex-wrap: wrap; align-items: center; justify-content: flex-end; gap: 8px; margin-top: 16px; }
  .actions .error { color: var(--error-color, #db4437); font-size: 13px; margin-right: auto; }
  .primary, .secondary { height: 36px; padding: 0 16px; border-radius: 18px; border: none; cursor: pointer; font-weight: 500; }
  .primary { background: var(--primary-color); color: var(--text-primary-color, #fff); }
  .secondary { background: transparent; color: var(--primary-color); border: 1px solid var(--primary-color); }
  .primary[disabled], .secondary[disabled] { opacity: 0.5; cursor: default; }
  @media (max-width: 600px) {
    .grid { grid-template-columns: repeat(auto-fill, minmax(104px, 1fr)); gap: 12px; padding: 0 12px 16px; }
    .body { flex-direction: column; padding: 16px; }
    .cover { flex-basis: auto; width: 160px; align-self: center; }
    .row { grid-template-columns: 120px 1fr; }
  }
`;

if (!customElements.get("mymovies-panel")) {
  customElements.define("mymovies-panel", MyMoviesPanel);
}
