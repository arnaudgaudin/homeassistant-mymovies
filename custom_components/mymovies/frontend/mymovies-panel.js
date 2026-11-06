/*
 * My Movies panel for Home Assistant: the collection as a wall of covers or a
 * list, with the sort options of My Movies, filters, watched badges, box sets
 * that can be expanded, a details dialog to mark titles as watched and an
 * import of the collection export.
 * Plain web component, no build step and no external dependency.
 */

const STRINGS = {
  en: {
    search: "Title, director, actor…", ascending: "Ascending", descending: "Descending",
    allTypes: "All types", allGenres: "All genres", allDiscs: "All discs", threeD: "Blu-ray 3D", movies: "Movies", series: "TV series", documentaries: "Documentaries",
    segWatched: "Watched", segAll: "All", segUnwatched: "Not watched", watchedFilter: "Watched filter",
    boxSets: "Box sets", editionsLabel: "Editions", collapsed: "Grouped", expanded: "Expanded", refresh: "Refresh", titles: "titles", films: "films",
    grid: "Wall", list: "List", view: "View",
    viewings: "Watched on", chooseGenres: "Choose genres", editGenres: "Edit genres", genresTitle: "Genres of this title",
    genresHint: "The export and TMDB give no genre for this title: choose them here.", save: "Save", resetChoice: "Remove my choice",
    boxSet: "Box set", markWatched: "Mark as watched", clearWatched: "Clear watched",
    close: "Close", director: "Director", cast: "Cast", genres: "Genres", runtime: "Runtime",
    rating: "Rating", personalRating: "Personal rating", parental: "Parental rating",
    released: "Released", discReleased: "Disc released", added: "Added", disc: "Disc", edition: "Edition",
    number: "Collection no.", group: "Group", inBoxSet: "In box set",
    contents: "Box set contents", loading: "Loading…", error: "Could not load the collection",
    empty: "No title matches", watched: "Watched", failed: "Action failed",
    officialSite: "Official My Movies website",
    creditCollection: "Collection data", creditCovers: "Covers",
    tmdbNotice: "This product uses the TMDB API but is not endorsed or certified by TMDB.",
    unofficial: "Unofficial integration, not affiliated with or endorsed by My Movies.",
    years: "Years", ratingsRange: "Rating", filters: "Filters", resetFilters: "Reset filters",
    allClasses: "All classifications",
    stats: "Statistics", statTitles: "titles", withoutData: "{n} titles without this information", noData: "No data yet.",
    over: "≥ {n}", minutes: "minutes", withoutDataOne: "1 title without this information",
    statNames: { disc: "Disc format", media: "Media type", genres: "Genres", ratings: "Ratings", classif: "Classification", runtime: "Running time", decade: "Production decade", countries: "Production countries" },
    classes: { none: "Not rated", tp: "All audiences", parental: "Parental guidance", 12: "Not under 12", 16: "Not under 16", 18: "Not under 18" },
    editions: "editions", editionsTitle: "Editions in the collection",
    changeCover: "Change cover", coverTitle: "Choose the cover", coverAuto: "Automatic (best resolution)",
    coverUpload: "Use my own image (JPEG or PNG)", coverUploadButton: "Upload", back: "Back",
    chosen: "chosen", current: "current", noTmdb: "TMDB does not know this title: only the My Movies cover and your own image are available.",
    noTmdbKey: "Add a TMDB API key in the integration options to choose among TMDB posters.",
    sources: { tmdb: "TMDB", mymovies: "My Movies", upload: "Your image" },
    importCsv: "Import the collection export",
    importTitle: "Import the My Movies export",
    importText: "In the My Movies app, export your collection to a CSV file, then choose it here. It gives the titles their names, IMDb IDs, details and watched state.",
    exportHelp: "How to export from the My Movies app",
    exportSteps: ["Open Settings → Sharing → Export collection.", "Choose the CSV format (not TXT).", "Send the file somewhere you can reach from here (Google Drive, e-mail…), then choose it below."],
    importModes: {
      update: ["Update", "Adds the new discs and the viewings of the export; keeps what was set here (viewings, genres, covers)."],
      replace: ["Full replace", "The export becomes the whole collection: viewings, genres and covers set here are erased."],
    },
    importedUpdate: "{n} titles in the export: {a} new discs, {w} new viewings.",
    importButton: "Import", importing: "Importing…", imported: "{n} titles imported.",
    sort: {
      title: "Title", collection_number: "Collection number", rating: "Rating",
      personal_rating: "Personal rating", runtime: "Running time", year: "Production year",
      release_date: "Release date", parental_rating: "Parental rating", added: "Added date",
    },
  },
  fr: {
    search: "Titre, réalisateur, acteur…", ascending: "Croissant", descending: "Décroissant",
    allTypes: "Tous les types", allGenres: "Tous les genres", allDiscs: "Tous les supports", threeD: "Blu-ray 3D", movies: "Films", series: "Séries", documentaries: "Documentaires",
    segWatched: "Vus", segAll: "Tous", segUnwatched: "Non vus", watchedFilter: "Filtre vu",
    boxSets: "Coffrets", editionsLabel: "Éditions", collapsed: "Repliés", expanded: "Dépliés", refresh: "Actualiser", titles: "titres", films: "films",
    grid: "Mur", list: "Liste", view: "Affichage",
    viewings: "Vu le", chooseGenres: "Choisir les genres", editGenres: "Modifier les genres", genresTitle: "Genres de ce titre",
    genresHint: "Ni l'export ni TMDB ne donnent de genre pour ce titre : choisis-les ici.", save: "Enregistrer", resetChoice: "Retirer mon choix",
    boxSet: "Coffret", markWatched: "Marquer comme vu", clearWatched: "Effacer le « vu »",
    close: "Fermer", director: "Réalisation", cast: "Avec", genres: "Genres", runtime: "Durée",
    rating: "Note", personalRating: "Note personnelle", parental: "Classification",
    released: "Sortie", discReleased: "Sortie du disque", added: "Ajouté le", disc: "Support", edition: "Édition",
    number: "N° de collection", group: "Groupe", inBoxSet: "Dans le coffret",
    contents: "Contenu du coffret", loading: "Chargement…",
    error: "Impossible de charger la collection", empty: "Aucun titre ne correspond",
    watched: "Vu", failed: "L'action a échoué",
    officialSite: "Site officiel de My Movies",
    creditCollection: "Données de la collection", creditCovers: "Jaquettes",
    tmdbNotice: "Ce produit utilise l'API TMDB mais n'est ni approuvé ni certifié par TMDB.",
    unofficial: "Intégration non officielle, ni affiliée à My Movies ni approuvée par My Movies.",
    years: "Années", ratingsRange: "Note", filters: "Filtres", resetFilters: "Réinitialiser les filtres",
    allClasses: "Toutes les classifications",
    stats: "Statistiques", statTitles: "titres", withoutData: "{n} titres sans cette information", noData: "Aucune donnée pour l'instant.",
    over: "≥ {n}", minutes: "minutes", withoutDataOne: "1 titre sans cette information",
    statNames: { disc: "Format de disque", media: "Type de média", genres: "Genres", ratings: "Notations", classif: "Classification", runtime: "Durée", decade: "Décennie de production", countries: "Pays de production" },
    classes: { none: "Sans classification", tp: "Tous publics", parental: "Accord parental", 12: "Interdit aux moins de 12 ans", 16: "Interdit aux moins de 16 ans", 18: "Interdit aux moins de 18 ans" },
    editions: "éditions", editionsTitle: "Éditions dans la collection",
    changeCover: "Changer la jaquette", coverTitle: "Choisir la jaquette", coverAuto: "Automatique (meilleure résolution)",
    coverUpload: "Utiliser ma propre image (JPEG ou PNG)", coverUploadButton: "Importer", back: "Retour",
    chosen: "choisie", current: "actuelle", noTmdb: "TMDB ne connaît pas ce titre : seules la jaquette My Movies et ta propre image sont disponibles.",
    noTmdbKey: "Ajoute une clé API TMDB dans les options de l'intégration pour choisir parmi les affiches TMDB.",
    sources: { tmdb: "TMDB", mymovies: "My Movies", upload: "Ton image" },
    importCsv: "Importer l'export de la collection",
    importTitle: "Importer l'export My Movies",
    importText: "Dans l'application My Movies, exportez votre collection en fichier CSV, puis choisissez-le ici. Il donne aux titres leur nom, leur ID IMDb, leurs détails et leur statut « vu ».",
    exportHelp: "Comment exporter depuis l'application My Movies",
    exportSteps: ["Ouvrez Paramètres → Partage → Exporter la collection.", "Choisissez le format CSV (pas TXT).", "Envoyez le fichier là où vous pourrez le récupérer ici (Google Drive, e-mail…), puis choisissez-le ci-dessous."],
    importModes: {
      update: ["Mise à jour", "Ajoute les nouveaux disques et les visionnages de l'export ; garde ce qui a été réglé ici (visionnages, genres, jaquettes)."],
      replace: ["Remplacement complet", "L'export devient toute la collection : les visionnages, genres et jaquettes réglés ici sont effacés."],
    },
    importedUpdate: "{n} titres dans l'export : {a} nouveaux disques, {w} nouveaux visionnages.",
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
  // The film's release (TMDB), else its production year; not the disc's release.
  release_date: (i) => i.film_release_date || (i.year ? `${i.year}-12-31` : null),
  parental_rating: (i) => RATING_CLASSES.indexOf(ratingClass(i.parental_rating)),
  added: (i) => i.added || null,
};

const TYPES = { movies: "Movie", series: "TV Serie", documentaries: "Documentary" };
// My Movies genres are English; French labels for the French interface.
const GENRES_FR = {
  Action: "Action", Adventure: "Aventure", Animation: "Animation", Anime: "Anime",
  Biography: "Biographie", Comedy: "Comédie", Crime: "Policier", Documentary: "Documentaire",
  Drama: "Drame", Family: "Famille", Fantasy: "Fantastique", "Film-Noir": "Film noir",
  History: "Histoire", Horror: "Horreur", "Martial Arts": "Arts martiaux", Music: "Musique",
  Musical: "Comédie musicale", Mystery: "Mystère", Other: "Autre", Romance: "Romance",
  "Science-Fiction": "Science-fiction", Sport: "Sport", Sports: "Sport",
  "Suspense/Thriller": "Thriller", Thriller: "Thriller", Television: "Télévision",
  War: "Guerre", Western: "Western",
};
// Genres spelled two ways in My Movies are filtered together.
const GENRE_ALIASES = { Anime: "Animation", Sports: "Sport", Thriller: "Suspense/Thriller" };
const canonGenre = (g) => GENRE_ALIASES[g] || g;
// Range filters with two handles: production year and rating.
const RANGES = {
  year: { value: (i) => i.year || null, step: 1, from: "yearFrom", to: "yearTo" },
  rating: { value: (i) => i.rating ?? null, step: 0.5, from: "ratingFrom", to: "ratingTo" },
};
// Classifications of My Movies, in order; other systems' ratings are mapped onto them.
const RATING_CLASSES = ["none", "tp", "parental", "12", "16", "18"];
function ratingClass(rating) {
  const r = String(rating || "").trim().toLowerCase();
  if (!r || /unrated|not rated|^nr$|non class|sans class/.test(r)) return "none";
  if (/tous publics|^tp$|^u$|^g$|all ages/.test(r)) return "tp";
  if (/accord parental|^pg$/.test(r)) return "parental";
  if (r === "pg-13") return "12";
  if (r === "r") return "16";
  if (r === "nc-17") return "18";
  const n = r.match(/(\d{1,2})/);
  if (!n) return "none";
  const age = Number(n[1]);
  return age <= 6 ? "tp" : age < 12 ? "parental" : age < 16 ? "12" : age < 18 ? "16" : "18";
}
// Edition shown on the tile of a film owned in several editions: 4K first.
const DISC_RANK = { "4K Ultra HD": 0, "Blu-ray": 1, DVD: 2 };
const STATE_KEY = "mymovies-panel";
const icon = (path) => `<svg viewBox="0 0 24 24" aria-hidden="true"><path d="${path}"/></svg>`;
const CHECK = icon("M9 16.17 4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z");
const SORT_ICON = icon("M7 4v13H4l4 4 4-4H9V4zm7 0-4 4h3v13h2V8h3z");
const REFRESH = icon("M17.65 6.35A7.96 7.96 0 0 0 12 4a8 8 0 1 0 7.73 10h-2.08A6 6 0 1 1 12 6c1.66 0 3.14.69 4.22 1.78L13 11h7V4z");
const UPLOAD = icon("M9 16v-6H5l7-7 7 7h-4v6zm-4 4v-2h14v2z");
const FILTER = icon("M6 13h12v-2H6zM3 6v2h18V6zm7 12h4v-2h-4z");
const CHART = icon("M11 2v20c-5.07-.5-9-4.79-9-10s3.93-9.5 9-10m2.03 0v8.99H22c-.47-4.74-4.24-8.52-8.97-8.99m0 11.01V22c4.74-.47 8.5-4.25 8.97-8.99z");
const CHEVRON = icon("M8.59 16.58 13.17 12 8.59 7.41 10 6l6 6-6 6z");
// Statistics: [key, icon, chart]. Pies for a few parts, bars for many, columns for ordered buckets.
const STATS = [
  ["disc", icon("M12 14a2 2 0 1 1 0-4 2 2 0 0 1 0 4m0-10a8 8 0 1 0 0 16 8 8 0 0 0 0-16"), "pie"],
  ["media", icon("M18 9h-2V7h2m0 6h-2v-2h2m0 6h-2v-2h2M8 9H6V7h2m0 6H6v-2h2m0 6H6v-2h2M18 3v2h-2V3H8v2H6V3H4v18h2v-2h2v2h8v-2h2v2h2V3z"), "pie"],
  ["genres", icon("M5.5 7A1.5 1.5 0 1 1 7 5.5 1.5 1.5 0 0 1 5.5 7m15.91 4.58-9-9A2 2 0 0 0 11 2H4a2 2 0 0 0-2 2v7a2 2 0 0 0 .59 1.41l9 9A2 2 0 0 0 13 22a2 2 0 0 0 1.41-.59l7-7A2 2 0 0 0 22 13a2 2 0 0 0-.59-1.42"), "bars"],
  ["ratings", icon("M12 17.27 18.18 21l-1.64-7.03L22 9.24l-7.19-.62L12 2 9.19 8.62 2 9.24l5.45 4.73L5.82 21z"), "columns"],
  ["classif", icon("M12 1 3 5v6c0 5.55 3.84 10.74 9 12 5.16-1.26 9-6.45 9-12V5z"), "pie"],
  ["runtime", icon("M12 20a8 8 0 1 0 0-16 8 8 0 0 0 0 16m0-18a10 10 0 1 1 0 20 10 10 0 0 1 0-20m.5 5v5.25l4.5 2.67-.75 1.23L11 13V7z"), "columns"],
  ["decade", icon("M19 19H5V8h14M16 1v2H8V1H6v2H5a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V5a2 2 0 0 0-2-2h-1V1m1 11h-5v5h5z"), "columns"],
  ["countries", icon("M17.9 17.39A2 2 0 0 0 16 16h-1v-3a1 1 0 0 0-1-1H8v-2h2a1 1 0 0 0 1-1V7h2a2 2 0 0 0 2-2v-.41A7.99 7.99 0 0 1 20 12a8 8 0 0 1-2.1 5.39M11 19.93A8 8 0 0 1 4 12c0-.62.08-1.22.21-1.79L9 15v1a2 2 0 0 0 2 2M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20"), "bars"],
];
// Categorical slots validated for colour-blind separation (light / dark surfaces).
const PIE_COLORS = {
  light: ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300"],
  dark: ["#3987e5", "#d95926", "#199e70", "#c98500", "#d55181", "#008300"],
};
const OTHER_COLOR = "#8a8a86";
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
  const defaults = { sort: "title", dir: "asc", type: "all", genre: "all", classif: "all", yearFrom: null, yearTo: null, ratingFrom: null, ratingTo: null, disc: "all", watched: "all", expand: false, editions: "collapsed", view: "grid", q: "" };
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
      this._api = result.api !== false;
      this._error = null;
    } catch (err) {
      this._error = err.message || String(err);
    }
    this._renderDiscOptions();
    this._renderGenreOptions();
    this._renderRanges();
    this._renderGrid();
    if (this._dialog?.kind === "title") this._renderDialog(false);
  }

  _genre(name) {
    return this._lang === "fr" ? GENRES_FR[name] || name : name;
  }

  _renderGenreOptions() {
    // Offer the genres present in the collection, sorted by their displayed name.
    const select = this.shadowRoot.getElementById("genre");
    if (!select || !this._titles) return;
    const genres = [...new Set(this._titles.flatMap((t) => (t.genres || []).map(canonGenre)))];
    genres.sort((a, b) => this._genre(a).localeCompare(this._genre(b), this._lang));
    if (this._state.genre !== "all" && !genres.includes(this._state.genre)) this._state.genre = "all";
    select.innerHTML = ["all", ...genres]
      .map((g) => `<option value="${esc(g)}" ${this._state.genre === g ? "selected" : ""}>${esc(g === "all" ? this._t.allGenres : this._genre(g))}</option>`)
      .join("");
  }

  _activeFilters() {
    // Filters narrowing the collection (sort, view and box sets are not filters).
    const st = this._state;
    return [st.type, st.genre, st.classif, st.disc, st.watched].filter((v) => v !== "all").length
      + Object.values(RANGES).filter((r) => st[r.from] != null || st[r.to] != null).length;
  }

  _renderRanges() {
    for (const name of Object.keys(RANGES)) this._renderRange(name);
  }

  _renderRange(name) {
    // The range goes from the smallest to the largest value in the collection, films of box sets included.
    const r = RANGES[name];
    const values = (this._titles || []).flatMap((t) => [t, ...(t.children || [])]).map(r.value).filter((v) => v != null);
    if (!values.length) return;
    const lo = Math.floor(Math.min(...values) / r.step) * r.step;
    const hi = Math.ceil(Math.max(...values) / r.step) * r.step;
    this._bounds = { ...this._bounds, [name]: [lo, hi] };
    const clamp = (v, fallback) => (v == null ? fallback : Math.min(hi, Math.max(lo, v)));
    const from = clamp(this._state[r.from], lo);
    const to = clamp(this._state[r.to], hi);
    for (const [end, value] of [["from", from], ["to", to]]) {
      const input = this.shadowRoot.getElementById(`${name}-${end}`);
      input.min = lo;
      input.max = hi;
      input.step = r.step;
      input.value = value;
    }
    this._paintRange(name, from, to);
  }

  _paintRange(name, from, to) {
    const [lo, hi] = this._bounds?.[name] || [from, to];
    const span = hi - lo || 1;
    const fill = this.shadowRoot.getElementById(`${name}-fill`);
    fill.style.left = `${((from - lo) / span) * 100}%`;
    fill.style.right = `${((hi - to) / span) * 100}%`;
    const fmt = (v) => v.toLocaleString(this._lang, { useGrouping: false });
    this.shadowRoot.getElementById(`${name}-label`).textContent = from === to ? fmt(from) : `${fmt(from)} – ${fmt(to)}`;
  }

  _renderDiscOptions() {
    // Offer the disc types present in the collection, plus 3D when some titles are.
    const select = this.shadowRoot.getElementById("disc");
    if (!select || !this._titles) return;
    const titles = this._titles.flatMap((t) => [t, ...(t.children || [])]);
    const types = [...new Set(titles.map((t) => t.disc_type).filter(Boolean))].sort();
    const values = ["all", ...types, ...(titles.some((t) => t.three_d) ? ["3d"] : [])];
    if (!values.includes(this._state.disc)) this._state.disc = "all";
    const label = (v) => (v === "all" ? this._t.allDiscs : v === "3d" ? this._t.threeD : v);
    select.innerHTML = values
      .map((v) => `<option value="${esc(v)}" ${this._state.disc === v ? "selected" : ""}>${esc(label(v))}</option>`)
      .join("");
  }

  // ---- data -------------------------------------------------------------

  _byId() {
    return new Map((this._titles || []).map((t) => [t.id.toLowerCase(), t]));
  }

  _allItems() {
    // Discs of a box set scanned as their own titles appear only in place of their
    // box set (expanded), never next to it.
    const byId = this._byId();
    const items = [];
    for (const t of this._titles || []) {
      if (t.box_set_id && byId.has(t.box_set_id)) continue;
      const children = t.children || [];
      if (this._state.expand && children.length) {
        for (const c of children) {
          const own = c.title_id && byId.get(c.title_id);
          items.push(own ? { ...own, key: `t:${own.id}`, parent: t } : this._childItem(t, c));
        }
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
    if (key.startsWith("g:")) return this._groups?.get(key) || null;
    const byId = this._byId();
    for (const t of this._titles || []) {
      if (`t:${t.id}` === key) return { ...t, key, parent: (t.box_set_id && byId.get(t.box_set_id)) || undefined };
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
      if (st.genre !== "all" && !(i.genres || []).some((g) => canonGenre(g) === st.genre)) return false;
      for (const r of Object.values(RANGES)) {
        if (st[r.from] == null && st[r.to] == null) continue;
        const v = r.value(i);
        if (v == null || (st[r.from] != null && v < st[r.from]) || (st[r.to] != null && v > st[r.to])) return false;
      }
      if (st.classif !== "all" && ratingClass(i.parental_rating) !== st.classif) return false;
      if (st.disc === "3d" && !i.three_d) return false;
      if (st.disc !== "all" && st.disc !== "3d" && i.disc_type !== st.disc) return false;
      if (st.watched === "watched" && !i.watched) return false;
      if (st.watched === "unwatched" && i.watched) return false;
      if (q) {
        const text = [i.title, i.original_title, i.director, ...(i.actors || []), i.parent?.title].join(" ");
        if (!norm(text).includes(q)) return false;
      }
      return true;
    });
    // Editions of a film share a tile, or are shown one by one with their disc on the tile.
    const grouped = this._groupEditions(items);
    if (st.editions === "expanded") grouped.splice(0, grouped.length, ...grouped.flatMap((g) => g.editions?.map((e) => ({ ...e, editionTag: true })) || [g]));
    const sign = st.dir === "desc" ? -1 : 1;
    grouped.sort((a, b) => {
      const va = getKey(a);
      const vb = getKey(b);
      let r = 0;
      if (va == null && vb == null) r = 0;
      else if (va == null) return 1; // unknown values always last
      else if (vb == null) return -1;
      else r = typeof va === "number" && typeof vb === "number" ? va - vb : collator.compare(String(va), String(vb));
      return sign * r || collator.compare(a.sort_title || a.title || "", b.sort_title || b.title || "");
    });
    return grouped;
  }

  _groupEditions(items) {
    // Editions of one film (same IMDb ID) share a tile; its dialog lists them.
    this._groups = new Map();
    const byImdb = new Map();
    // A series keeps one IMDb ID for all its seasons: its discs are not editions.
    const groupable = (i) => i.imdb && !i.children?.length && i.media_type !== "TV Serie";
    for (const i of items) {
      if (!groupable(i)) continue;
      if (!byImdb.has(i.imdb)) byImdb.set(i.imdb, []);
      byImdb.get(i.imdb).push(i);
    }
    const out = [];
    const seen = new Set();
    for (const i of items) {
      const editions = groupable(i) ? byImdb.get(i.imdb) : null;
      if (!editions || editions.length < 2) {
        out.push(i);
        continue;
      }
      if (seen.has(i.imdb)) continue;
      seen.add(i.imdb);
      editions.sort((a, b) => (DISC_RANK[a.disc_type] ?? 9) - (DISC_RANK[b.disc_type] ?? 9) || a.collection_number - b.collection_number);
      const group = { ...editions[0], key: `g:${i.imdb}`, editions, watched: editions.some((e) => e.watched), parent: undefined };
      this._groups.set(group.key, group);
      out.push(group);
    }
    return out;
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
    const rangeBox = (name, label) => `
        <div class="years" title="${esc(label)}">
          <span class="seg-label">${esc(label)}</span>
          <span class="years-label" id="${name}-label"></span>
          <div class="range">
            <span class="track"></span><span class="fill" id="${name}-fill"></span>
            <input type="range" id="${name}-from" aria-label="${esc(label)} min" />
            <input type="range" id="${name}-to" aria-label="${esc(label)} max" />
          </div>
        </div>`;
    this.shadowRoot.innerHTML = `
      <style>${STYLE}</style>
      <div class="header">
        <span class="menu"></span>
        <div class="title">My Movies <a class="source" href="https://www.mymovies.dk" target="_blank" rel="noopener noreferrer" title="${esc(t.officialSite)}">mymovies.dk ↗</a></div>
        <div class="count"></div>
        <button class="icon" id="stats" title="${esc(t.stats)}" aria-label="${esc(t.stats)}">${CHART}</button>
        ${isAdmin ? `<button class="icon" id="import" title="${esc(t.importCsv)}" aria-label="${esc(t.importCsv)}">${UPLOAD}</button>` : ""}
        <button class="icon" id="refresh" title="${esc(t.refresh)}" aria-label="${esc(t.refresh)}">${REFRESH}</button>
      </div>
      <div class="toolbar">
        <div class="toolbar-main">
          <input id="q" type="search" placeholder="${esc(t.search)}" aria-label="${esc(t.search)}" value="${esc(st.q)}" />
          <button type="button" class="filters-toggle" id="filters-toggle" aria-controls="filters" aria-expanded="${this._filtersOpen ? "true" : "false"}">
            ${FILTER}<span>${esc(t.filters)}</span><span class="filters-count" id="filters-count"></span>
          </button>
          <div class="segmented icons" id="view" role="radiogroup" aria-label="${esc(t.view)}">
            ${seg("view", "grid", GRID, st.view, `title="${esc(t.grid)}" aria-label="${esc(t.grid)}"`)}${seg("view", "list", LIST, st.view, `title="${esc(t.list)}" aria-label="${esc(t.list)}"`)}
          </div>
        </div>
        <div class="filters ${this._filtersOpen ? "open" : ""}" id="filters">
        <div class="sortgroup">
          <span class="select"><select id="sort" aria-label="${esc(t.sort.title)}">${sortOptions}</select></span>
          <button class="icon dir ${st.dir}" id="dir" title="${esc(st.dir === "asc" ? t.ascending : t.descending)}" aria-label="${esc(st.dir === "asc" ? t.ascending : t.descending)}">${SORT_ICON}</button>
        </div>
        <span class="select"><select id="type" aria-label="${esc(t.allTypes)}">
          ${option("all", t.allTypes, st.type)}${option("movies", t.movies, st.type)}
          ${option("series", t.series, st.type)}${option("documentaries", t.documentaries, st.type)}
        </select></span>
        <span class="select"><select id="genre" aria-label="${esc(t.allGenres)}">${option("all", t.allGenres, "all")}</select></span>
        <span class="select wide"><select id="classif" aria-label="${esc(t.allClasses)}">
          ${option("all", t.allClasses, st.classif)}
          ${RATING_CLASSES.map((c) => option(c, t.classes[c], st.classif)).join("")}
        </select></span>
        ${rangeBox("year", t.years)}
        ${rangeBox("rating", t.ratingsRange)}
        <span class="select wide"><select id="disc" aria-label="${esc(t.allDiscs)}">${option("all", t.allDiscs, "all")}</select></span>
        <div class="segmented" id="watched" role="radiogroup" aria-label="${esc(t.watchedFilter)}">
          ${seg("watched", "watched", esc(t.segWatched), st.watched)}${seg("watched", "all", esc(t.segAll), st.watched)}${seg("watched", "unwatched", esc(t.segUnwatched), st.watched)}
        </div>
        <div class="segmented" id="expand" role="radiogroup" aria-label="${esc(t.boxSets)}">
          <span class="seg-label">${esc(t.boxSets)}</span>${seg("expand", "collapsed", esc(t.collapsed), st.expand ? "expanded" : "collapsed")}${seg("expand", "expanded", esc(t.expanded), st.expand ? "expanded" : "collapsed")}
        </div>
        <div class="segmented" id="editions" role="radiogroup" aria-label="${esc(t.editionsLabel)}">
          <span class="seg-label">${esc(t.editionsLabel)}</span>${seg("editions", "collapsed", esc(t.collapsed), st.editions)}${seg("editions", "expanded", esc(t.expanded), st.editions)}
        </div>
        <button type="button" class="secondary small filters-reset" id="filters-reset">${esc(t.resetFilters)}</button>
        </div>
      </div>
      <div class="items ${st.view}" id="grid"><div class="message">${esc(t.loading)}</div></div>
      <footer class="credits">
        ${esc(t.creditCollection)} : <a href="https://www.mymovies.dk" target="_blank" rel="noopener noreferrer">My Movies</a>
        · ${esc(t.creditCovers)} : <a href="https://www.themoviedb.org" target="_blank" rel="noopener noreferrer">TMDB</a>.
        ${esc(t.tmdbNotice)} ${esc(t.unofficial)}
      </footer>
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
    const segmented = (id, attr, toState = (value) => value) =>
      $(id).addEventListener("click", (ev) => {
        const btn = ev.target.closest(`[data-${attr}]`);
        if (!btn) return;
        for (const b of $(id).querySelectorAll("button")) {
          b.classList.toggle("active", b === btn);
          b.setAttribute("aria-checked", String(b === btn));
        }
        update({ [attr]: toState(btn.dataset[attr]) });
      });
    $("q").addEventListener("input", (ev) => update({ q: ev.target.value }));
    $("filters-toggle").addEventListener("click", () => {
      this._filtersOpen = !this._filtersOpen;
      $("filters").classList.toggle("open", this._filtersOpen);
      // Animate only on a click, not when the shell re-renders already open.
      $("filters").classList.toggle("opening", this._filtersOpen);
      $("filters-toggle").setAttribute("aria-expanded", String(this._filtersOpen));
    });
    $("filters-reset").addEventListener("click", () => {
      Object.assign(this._state, { type: "all", genre: "all", classif: "all", disc: "all", watched: "all", yearFrom: null, yearTo: null, ratingFrom: null, ratingTo: null });
      this._saveState();
      this._renderShell();
      this._renderDiscOptions();
      this._renderGenreOptions();
      this._renderRanges();
      this._renderGrid();
    });
    $("sort").addEventListener("change", (ev) => update({ sort: ev.target.value }));
    $("type").addEventListener("change", (ev) => update({ type: ev.target.value }));
    $("disc").addEventListener("change", (ev) => update({ disc: ev.target.value }));
    $("genre").addEventListener("change", (ev) => update({ genre: ev.target.value }));
    $("classif").addEventListener("change", (ev) => update({ classif: ev.target.value }));
    const onRange = (name, moved) => {
      const r = RANGES[name];
      const [lo, hi] = this._bounds?.[name] || [0, 0];
      let from = Number($(`${name}-from`).value);
      let to = Number($(`${name}-to`).value);
      if (from > to) {
        if (moved === "from") to = from;
        else from = to;
        $(`${name}-from`).value = from;
        $(`${name}-to`).value = to;
      }
      this._paintRange(name, from, to);
      update({ [r.from]: from > lo ? from : null, [r.to]: to < hi ? to : null });
    };
    for (const name of Object.keys(RANGES)) {
      $(`${name}-from`).addEventListener("input", () => onRange(name, "from"));
      $(`${name}-to`).addEventListener("input", () => onRange(name, "to"));
    }
    segmented("watched", "watched");
    segmented("view", "view");
    segmented("expand", "expand", (value) => value === "expanded");
    segmented("editions", "editions");
    $("dir").addEventListener("click", (ev) => {
      update({ dir: this._state.dir === "asc" ? "desc" : "asc" });
      const btn = ev.currentTarget;
      btn.classList.toggle("desc", this._state.dir === "desc");
      btn.title = this._state.dir === "asc" ? this._t.ascending : this._t.descending;
    });
    $("refresh").addEventListener("click", () => this._load());
    $("import")?.addEventListener("click", () => this._openDialog({ kind: "import" }));
    $("stats").addEventListener("click", () => this._openDialog({ kind: "stats", stat: null }));
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
    if (i.editions) return `<span class="tag">${i.editions.length} ${esc(this._t.editions)}</span>`;
    const count = i.children?.length;
    if (i.parent) return `<span class="tag">${esc(i.parent.title || "")}</span>`;
    if (count) return `<span class="tag">${esc(this._t.boxSet)} · ${count} ${esc(this._t.films)}</span>`;
    return "";
  }

  _card(i) {
    const title = i.title || `#${i.collection_number}`;
    return `
      <button class="card" data-key="${esc(i.key)}" title="${esc(title)}">
        <div class="poster">${this._cover(i, title)}${this._tag(i)}</div>
        <div class="name">${esc(title)}</div>
        <div class="sub">${esc([...new Set([i.year, i.editionTag && (i.three_d ? "3D" : i.disc_type), i.editionTag && i.edition].filter(Boolean))].join(" · "))}</div>
      </button>`;
  }

  _row(i) {
    const t = this._t;
    const title = i.title || `#${i.collection_number}`;
    const meta = [this._runtime(i.runtime), i.disc_type, i.three_d ? "3D" : "", i.parental_rating && t.classes[ratingClass(i.parental_rating)], i.edition].filter(Boolean);
    const people = [i.director, (i.genres || []).map((g) => this._genre(g)).join(", ")].filter(Boolean);
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
          ${i.parent ? `<span class="line-meta">${esc(t.inBoxSet)} : ${esc(i.parent.title || "")}</span>` : ""}
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
    const active = this._activeFilters();
    const badge = this.shadowRoot.getElementById("filters-count");
    badge.textContent = active ? String(active) : "";
    badge.hidden = !active;
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
    const bodies = { genres: () => this._genresBody(), stats: () => this._statsBody(), import: () => this._importBody(), cover: () => this._coverBody(), title: () => this._titleBody() };
    const body = bodies[this._dialog.kind]();
    if (body === null) return this._closeDialog();
    root.innerHTML = `
      <div class="backdrop ${animate ? "" : "static"}" data-action="close">
        <div class="dialog dialog-${this._dialog.kind}" role="dialog" aria-modal="true">
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
    const meta = [i.year, this._runtime(i.runtime), i.parental_rating && t.classes[ratingClass(i.parental_rating)], i.disc_type, i.three_d ? "3D" : "", i.edition].filter(Boolean);
    const children = !i.child ? i.children || [] : [];
    return `
      <div class="body">
        <div class="cover-col">
          <div class="cover">${this._cover(i, title)}</div>
          ${this._hass.user?.is_admin && !i.editions ? `<button class="secondary small" data-action="change-cover">${esc(t.changeCover)}</button>` : ""}
        </div>
        <div class="info">
          <h2>${esc(title)}</h2>
          ${i.original_title && i.original_title !== title ? `<div class="original">${esc(i.original_title)}</div>` : ""}
          <div class="meta">${meta.map(esc).join(" · ")}</div>
          ${i.genres?.length ? `<div class="chips">${i.genres.map((g) => `<span>${esc(this._genre(g))}</span>`).join("")}</div>` : ""}
          ${this._hass.user?.is_admin && !i.editions && (!i.genres?.length || i.genres_manual)
            ? `<button class="secondary small genres-edit" data-action="choose-genres">${esc(i.genres?.length ? t.editGenres : t.chooseGenres)}</button>` : ""}
          ${i.description ? `<p class="description">${esc(paragraphs(i.description))}</p>` : ""}
          <div class="info-rows">
            ${this._info(t.director, i.director)}
            ${this._info(t.cast, (i.actors || []).slice(0, 8).join(", "))}
            ${this._info(t.rating, i.rating != null ? `★ ${i.rating}/10` : "")}
            ${this._info(t.personalRating, i.personal_rating != null ? `★ ${i.personal_rating}` : "")}
            ${this._info(t.released, this._date(i.film_release_date))}
            ${this._info(t.discReleased, this._date(i.release_date))}
            ${this._info(t.added, this._date(i.added))}
            ${this._info(t.viewings, (i.viewings || []).slice().reverse().map((d) => this._date(d.slice(0, 10))).join(", "))}
            ${this._info(t.number, i.child ? "" : i.collection_number)}
            ${this._info(t.group, i.group)}
          </div>
          ${i.parent ? `<div class="info-rows"><div class="info-row"><span>${esc(t.inBoxSet)}</span><a href="#" data-open="t:${esc(i.parent.id)}">${esc(i.parent.title || "")}</a></div></div>` : ""}
          ${i.editions ? `
            <h3>${esc(t.editionsTitle)}</h3>
            <div class="editions">
              ${i.editions.map((e) => `
                <button class="edition" data-open="t:${esc(e.id)}">
                  <span>${esc([e.disc_type, e.three_d ? "3D" : "", e.edition].filter(Boolean).join(" · ") || e.title)}</span>
                  <span class="edition-meta">#${esc(e.collection_number)}${e.parent ? ` · ${esc(e.parent.title || "")}` : ""}</span>
                  ${e.watched ? `<span class="badge inline" title="${esc(t.watched)}">${CHECK}</span>` : ""}
                </button>`).join("")}
            </div>` : ""}
          ${children.length ? `
            <h3>${esc(t.contents)}</h3>
            <div class="children">
              ${children.map((c) => {
                const own = c.title_id && this._byId().get(c.title_id);
                return `
                <button class="mini" data-open="${own ? `t:${esc(own.id)}` : `c:${esc(c.id)}`}" title="${esc(c.title)}">
                  <span class="mini-cover">
                    ${c.poster ? `<img loading="lazy" src="${esc(c.poster)}" alt="" />` : `<div class="noposter">${esc(c.title)}</div>`}
                    ${c.watched ? `<span class="badge small" title="${esc(t.watched)}">${CHECK}</span>` : ""}
                  </span>
                  <span>${esc(c.title)}${c.year ? ` (${esc(c.year)})` : ""}</span>
                </button>`;
              }).join("")}
            </div>` : ""}
          ${i.editions ? "" : `<div class="actions">
            ${this._dialog.error ? `<span class="error">${esc(t.failed)} : ${esc(this._dialog.error)}</span>` : ""}
            ${i.watched ? `<button class="secondary" data-action="clear" ${this._busy ? "disabled" : ""}>${esc(t.clearWatched)}</button>` : ""}
            <button class="primary" data-action="mark" ${this._busy ? "disabled" : ""}>${esc(t.markWatched)}</button>
          </div>`}
        </div>
      </div>`;
  }

  _coverBody() {
    const t = this._t;
    const d = this._dialog;
    const current = d.result?.current || {};
    const isCurrent = (c) =>
      c.source === current.source && (c.source !== "tmdb" || c.path === current.path);
    const notice = !d.result
      ? `<p>${esc(t.loading)}</p>`
      : !d.result.tmdb_key
        ? `<p class="hint">${esc(t.noTmdbKey)}</p>`
        : !d.result.tmdb_known
          ? `<p class="hint">${esc(t.noTmdb)}</p>`
          : "";
    return `
      <div class="import-body">
        <h2>${esc(t.coverTitle)}</h2>
        <div class="meta">${esc(d.title || "")}</div>
        ${notice}
        <div class="choices">
          ${(d.result?.choices || []).map((c, n) => `
            <button class="choice ${isCurrent(c) ? "current" : ""}" data-action="pick" data-index="${n}" ${this._busy ? "disabled" : ""}>
              <img loading="lazy" src="${esc(c.url)}" alt="" />
              <span>${esc(t.sources[c.source] || c.source)}${c.lang ? ` · ${esc(c.lang)}` : ""}</span>
              <span class="dims">${c.width ? `${c.width}×${c.height}` : ""}${isCurrent(c) ? ` · ${esc(t.current)}` : ""}</span>
            </button>`).join("")}
        </div>
        <p>${esc(t.coverUpload)}</p>
        <input id="cover-file" type="file" accept="image/jpeg,image/png" ${this._busy ? "disabled" : ""} />
        <div class="actions">
          ${d.error ? `<span class="error">${esc(t.failed)} : ${esc(d.error)}</span>` : ""}
          <button class="secondary" data-action="back">${esc(t.back)}</button>
          <button class="secondary" data-action="auto" ${this._busy || !d.result?.chosen ? "disabled" : ""}>${esc(t.coverAuto)}</button>
          <button class="primary" data-action="upload-cover" ${this._busy ? "disabled" : ""}>${esc(t.coverUploadButton)}</button>
        </div>
      </div>`;
  }

  async _openCoverDialog() {
    const item = this._findItem(this._dialog.key);
    this._dialog = { kind: "cover", id: item.id, title: item.title, back: this._dialog.key, error: null, result: null };
    this._renderDialog(false);
    try {
      this._dialog.result = await this._hass.connection.sendMessagePromise({ type: "mymovies/cover_choices", title_id: item.id });
    } catch (err) {
      this._dialog.error = err.message || String(err);
    }
    if (this._dialog?.kind === "cover") this._renderDialog(false);
  }

  async _setCover(choice) {
    const d = this._dialog;
    this._busy = true;
    d.error = null;
    this._renderDialog(false);
    try {
      let message = { type: "mymovies/set_cover", title_id: d.id, source: choice.source };
      if (choice.source === "tmdb") message = { ...message, path: choice.path, width: choice.width, height: choice.height };
      if (choice.source === "upload") {
        const file = this.shadowRoot.getElementById("cover-file")?.files?.[0];
        if (!file) throw new Error(this._t.coverUpload);
        const form = new FormData();
        form.append("file", file);
        const resp = await this._hass.fetchWithAuth("/api/file_upload", { method: "POST", body: form });
        if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
        message.file_id = (await resp.json()).file_id;
      }
      await this._hass.connection.sendMessagePromise(message);
      this._busy = false;
      this._dialog = { kind: "title", key: d.back, error: null };
      await this._load();
    } catch (err) {
      d.error = err.message || String(err);
    } finally {
      this._busy = false;
      if (this._dialog) this._renderDialog(false);
    }
  }

  // ---- statistics ------------------------------------------------------

  // [[label, count]] of a statistic over the collection's titles, and how many lack the information.
  _statRows(key) {
    const t = this._t;
    const titles = this._titles || [];
    const counts = new Map();
    let missing = 0;
    const add = (k) => counts.set(k, (counts.get(k) || 0) + 1);
    const byCount = () => [...counts].sort((a, b) => b[1] - a[1] || String(a[0]).localeCompare(String(b[0]), this._lang));
    // Ordered numeric buckets, empty ones in between included.
    const buckets = (label) => {
      const keys = [...counts.keys()];
      if (!keys.length) return [];
      const rows = [];
      for (let k = Math.min(...keys), step = key === "decade" ? 10 : 1; k <= Math.max(...keys); k += step) rows.push([label(k), counts.get(k) || 0]);
      return rows;
    };
    const each = (value) => (value == null || value === "" ? missing++ : add(value));
    let rows;
    if (key === "disc") {
      titles.forEach((i) => each(i.three_d ? t.threeD : i.disc_type));
      rows = byCount();
    } else if (key === "media") {
      const names = { Movie: t.movies, "TV Serie": t.series, Documentary: t.documentaries };
      titles.forEach((i) => each(names[i.media_type] || i.media_type));
      rows = byCount();
    } else if (key === "classif") {
      titles.forEach((i) => add(ratingClass(i.parental_rating)));
      rows = RATING_CLASSES.filter((c) => counts.has(c)).map((c) => [t.classes[c], counts.get(c)]);
    } else if (key === "genres" || key === "countries") {
      const region = key === "countries" && typeof Intl.DisplayNames === "function" ? new Intl.DisplayNames([this._lang], { type: "region" }) : null;
      const name = (c) => { try { return region ? region.of(c) : c; } catch { return c; } };
      titles.forEach((i) => {
        const values = key === "genres" ? new Set((i.genres || []).map((g) => this._genre(canonGenre(g)))) : new Set((i.countries || []).map(name));
        if (!values.size) missing++;
        values.forEach(add);
      });
      rows = byCount();
    } else if (key === "ratings") {
      titles.forEach((i) => each(i.rating ? Math.max(4, Math.min(9, Math.floor(i.rating))) : null));
      rows = buckets((k) => (k === 4 ? "< 5" : `${k}–${k + 1}`));
    } else if (key === "runtime") {
      // 0–60, then 30-minute slices up to 240 and more.
      titles.forEach((i) => each(i.runtime ? (i.runtime < 60 ? 0 : Math.min(7, Math.floor((i.runtime - 60) / 30) + 1)) : null));
      rows = buckets((k) => (k === 0 ? "0–\n60" : k === 7 ? t.over.replace("{n}", 240) : `${30 + 30 * k}–\n${60 + 30 * k}`));
    } else if (key === "decade") {
      titles.forEach((i) => each(i.year ? Math.floor(i.year / 10) * 10 : null));
      rows = buckets((k) => String(k));
    }
    return { rows, missing };
  }

  _statsBody() {
    const t = this._t;
    const d = this._dialog;
    if (!d.stat) {
      return `
        <div class="import-body stats-body">
          <h2>${esc(t.stats)}</h2>
          <div class="stat-list">
            ${STATS.map(([key, svg]) => `
              <button class="stat-item" data-action="stat" data-stat="${key}">
                <span class="stat-icon">${svg}</span><span class="stat-name">${esc(t.statNames[key])}</span>${CHEVRON}
              </button>`).join("")}
          </div>
        </div>`;
    }
    const [key, svg, chart] = STATS.find(([k]) => k === d.stat);
    const { rows, missing } = this._statRows(key);
    const body = !rows.length
      ? `<p class="hint">${esc(t.noData)}</p>`
      : chart === "pie" ? this._pie(rows) : chart === "bars" ? this._bars(rows) : this._columns(rows);
    const series = PIE_COLORS[this._hass.themes?.darkMode ? "dark" : "light"][0];
    return `
      <div class="import-body stats-body" style="--mm-series:${series}">
        <h2><span class="stat-icon">${svg}</span>${esc(t.statNames[key])}</h2>
        ${key === "runtime" ? `<div class="meta">${esc(t.minutes)}</div>` : ""}
        ${body}
        ${missing ? `<p class="hint">${esc(missing === 1 ? t.withoutDataOne : t.withoutData.replace("{n}", missing))}</p>` : ""}
        <div class="actions"><button class="secondary" data-action="stats-back">${esc(t.back)}</button></div>
      </div>`;
  }

  _pie(rows) {
    const colors = PIE_COLORS[this._hass.themes?.darkMode ? "dark" : "light"];
    // Six slices at most: the smallest parts are folded into "Other".
    if (rows.length > colors.length) {
      const rest = rows.slice(colors.length - 1).reduce((sum, [, v]) => sum + v, 0);
      rows = [...rows.slice(0, colors.length - 1), [this._lang === "fr" ? "Autres" : "Other", rest]];
    }
    const total = rows.reduce((sum, [, v]) => sum + v, 0);
    const color = (n, label) => (n === colors.length - 1 && /^(Autres|Other)$/.test(label) ? OTHER_COLOR : colors[n]);
    const pct = (v) => (v / total < 0.005 ? "< 1 %" : `${Math.round((v / total) * 100)} %`);
    const R = 70, C = 2 * Math.PI * R;
    let offset = 0;
    const arcs = rows.map(([label, v], n) => {
      const len = (v / total) * C;
      // A 2px gap between slices, unless one slice is the whole.
      const dash = rows.length > 1 ? Math.max(len - 2, 0.5) : C;
      const arc = `<circle cx="100" cy="100" r="${R}" fill="none" stroke="${color(n, label)}" stroke-width="34" stroke-dasharray="${dash} ${C}" stroke-dashoffset="${-offset}" transform="rotate(-90 100 100)"><title>${esc(label)} : ${v} (${pct(v)})</title></circle>`;
      offset += len;
      return arc;
    });
    return `
      <div class="pie">
        <svg viewBox="0 0 200 200" role="img" aria-label="${esc(rows.map(([l, v]) => `${l} ${v}`).join(", "))}">
          ${arcs.join("")}
          <text x="100" y="98" text-anchor="middle" class="pie-total">${total}</text>
          <text x="100" y="118" text-anchor="middle" class="pie-unit">${esc(this._t.statTitles)}</text>
        </svg>
        <ul class="legend">
          ${rows.map(([label, v], n) => `<li><span class="swatch" style="background:${color(n, label)}"></span><span class="lbl">${esc(label)}</span><span class="val">${v}</span><span class="pct">${pct(v)}</span></li>`).join("")}
        </ul>
      </div>`;
  }

  _bars(rows) {
    const max = Math.max(...rows.map(([, v]) => v));
    return `<div class="hbars">${rows.map(([label, v]) => `
      <div class="hbar" title="${esc(label)} : ${v}"><span class="lbl">${esc(label)}</span><span class="track"><span class="fill" style="width:${(v / max) * 100}%"></span></span><span class="val">${v}</span></div>`).join("")}</div>`;
  }

  _columns(rows) {
    const max = Math.max(...rows.map(([, v]) => v), 1);
    return `<div class="cols">${rows.map(([label, v]) => `
      <div class="col" title="${esc(label)} : ${v}"><span class="val">${v || ""}</span><span class="bar" style="height:${(v / max) * 100}%"></span><span class="lbl">${esc(label)}</span></div>`).join("")}</div>`;
  }

  _genresBody() {
    const t = this._t;
    const d = this._dialog;
    // The genres of My Movies (one name per genre), sorted by their displayed name.
    const names = Object.keys(GENRES_FR).filter((g) => !GENRE_ALIASES[g]);
    names.sort((a, b) => this._genre(a).localeCompare(this._genre(b), this._lang));
    return `
      <div class="import-body">
        <h2>${esc(t.genresTitle)}</h2>
        <div class="meta">${esc(d.title || "")}</div>
        <p class="hint">${esc(t.genresHint)}</p>
        <div class="genre-choices">
          ${names.map((g) => `<label><input type="checkbox" value="${esc(g)}" ${d.chosen.includes(g) ? "checked" : ""} ${this._busy ? "disabled" : ""} /> ${esc(this._genre(g))}</label>`).join("")}
        </div>
        <div class="actions">
          ${d.error ? `<span class="error">${esc(t.failed)} : ${esc(d.error)}</span>` : ""}
          <button class="secondary" data-action="back">${esc(t.back)}</button>
          ${d.chosen.length ? `<button class="secondary" data-action="reset-genres" ${this._busy ? "disabled" : ""}>${esc(t.resetChoice)}</button>` : ""}
          <button class="primary" data-action="save-genres" ${this._busy ? "disabled" : ""}>${esc(t.save)}</button>
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
        <details class="export-help" ${this._titles?.length ? "" : "open"}>
          <summary>${esc(t.exportHelp)}</summary>
          <ol>${t.exportSteps.map((step) => `<li>${esc(step)}</li>`).join("")}</ol>
        </details>
        <input id="file" type="file" accept=".csv,text/csv" ${this._busy ? "disabled" : ""} />
        ${this._titles?.length ? `<div class="import-modes" role="radiogroup">
          ${Object.entries(t.importModes).map(([mode, [label, hint]]) => `
            <label class="import-mode ${mode}"><input type="radio" name="import-mode" value="${mode}" ${mode === (d.mode || "update") ? "checked" : ""} ${this._busy ? "disabled" : ""} />
              <span><strong>${esc(label)}</strong><span class="hint">${esc(hint)}</span></span></label>`).join("")}
        </div>` : ""}
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
    if (action === "stat" || action === "stats-back") {
      this._dialog.stat = action === "stat" ? ev.target.closest("[data-stat]").dataset.stat : null;
      return this._renderDialog(false);
    }
    if (action === "change-cover") return this._openCoverDialog();
    if (action === "choose-genres") {
      const item = this._findItem(this._dialog.key);
      this._dialog = { kind: "genres", id: item.id, title: item.title, back: this._dialog.key, chosen: item.genres_manual ? [...item.genres] : [], error: null };
      return this._renderDialog(false);
    }
    if (action === "save-genres" || action === "reset-genres") {
      const d = this._dialog;
      const genres = action === "save-genres"
        ? [...this.shadowRoot.querySelectorAll(".genre-choices input:checked")].map((el) => el.value)
        : [];
      this._busy = true;
      this._renderDialog(false);
      try {
        await this._hass.connection.sendMessagePromise({ type: "mymovies/set_details", title_id: d.id, genres });
        await this._load();
        this._dialog = { kind: "title", key: d.back, error: null };
      } catch (err) {
        d.error = err.message || String(err);
      } finally {
        this._busy = false;
        if (this._dialog) this._renderDialog(false);
      }
      return;
    }
    if (action === "back") {
      this._dialog = { kind: "title", key: this._dialog.back, error: null };
      return this._renderDialog(false);
    }
    if (action === "pick") {
      const choice = this._dialog.result.choices[Number(ev.target.closest("[data-index]").dataset.index)];
      return this._setCover(choice);
    }
    if (action === "auto") return this._setCover({ source: "auto" });
    if (action === "upload-cover") return this._setCover({ source: "upload" });
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
      const mode = this.shadowRoot.querySelector('input[name="import-mode"]:checked')?.value || "update";
      if (this._dialog) this._dialog.mode = mode;
      const result = await this._hass.connection.sendMessagePromise({ type: "mymovies/import_export", file_id, mode });
      const t = this._t;
      if (this._dialog) {
        this._dialog.status = mode === "update" && this._titles?.length
          ? t.importedUpdate.replace("{n}", result.count).replace("{a}", result.added).replace("{w}", result.watched)
          : t.imported.replace("{n}", result.count);
      }
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
  .header .source { margin-left: 8px; font-size: 12px; color: inherit; opacity: 0.7; text-decoration: none; white-space: nowrap; }
  .header .source:hover { opacity: 1; text-decoration: underline; }
  .credits { padding: 8px 16px 24px; font-size: 12px; line-height: 1.5; color: var(--secondary-text-color); text-align: center; }
  .credits a { color: inherit; }
  .header .count { opacity: 0.85; font-size: 14px; margin-right: 8px; }
  .toolbar { display: flex; flex-wrap: wrap; align-items: center; gap: 8px 12px; padding: 12px 16px; }
  .toolbar input[type="search"], .toolbar select { height: 36px; padding: 0 10px; border-radius: 8px; border: 1px solid var(--divider-color); background: var(--card-background-color); color: var(--primary-text-color); font-size: 14px; box-sizing: border-box; }
  .toolbar input[type="search"] { flex: 0 1 260px; min-width: 140px; }
  .toolbar-main { display: flex; align-items: center; gap: 8px 12px; width: 100%; }
  #view { margin-left: auto; }
  .filters { display: none; width: 100%; flex-wrap: wrap; align-items: center; gap: 8px 12px; }
  .filters.open { display: flex; }
  .filters.opening { animation: filters-in 220ms ease-out; transform-origin: top; }
  @keyframes filters-in { from { opacity: 0; transform: translateY(-10px) scaleY(0.96); } }
  @media (prefers-reduced-motion: reduce) { .filters.opening { animation: none; } }
  .filters-toggle { display: inline-flex; }
  .filters-reset { margin-left: auto; }
  .filters-toggle { align-items: center; gap: 6px; height: 36px; padding: 0 12px; border: 1px solid var(--divider-color); border-radius: 8px; background: var(--card-background-color); cursor: pointer; flex: none; font-size: 14px; }
  .filters-toggle[aria-expanded="true"] { border-color: var(--primary-color); color: var(--primary-color); }
  .filters-toggle svg { width: 18px; height: 18px; }
  .filters-count { min-width: 18px; height: 18px; padding: 0 5px; border-radius: 9px; background: var(--primary-color); color: var(--text-primary-color, #fff); font-size: 11px; line-height: 18px; text-align: center; box-sizing: border-box; }
  .filters-count[hidden] { display: none; }
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
  .years { display: inline-flex; align-items: center; gap: 6px; flex: 0 1 320px; min-width: 240px; height: 36px; padding: 0 12px 0 2px; border: 1px solid var(--divider-color); border-radius: 10px; background: var(--card-background-color); box-sizing: border-box; }
  .years-label { min-width: 84px; font-size: 13px; text-align: center; white-space: nowrap; font-variant-numeric: tabular-nums; }
  .range { position: relative; flex: 1; height: 20px; min-width: 80px; }
  .range .track, .range .fill { position: absolute; top: 50%; height: 4px; margin-top: -2px; border-radius: 2px; }
  .range .track { left: 0; right: 0; background: var(--divider-color); }
  .range .fill { background: var(--primary-color); }
  .range input { position: absolute; inset: 0; width: 100%; height: 20px; margin: 0; background: none; pointer-events: none; -webkit-appearance: none; appearance: none; }
  .range input::-webkit-slider-runnable-track { height: 20px; background: transparent; }
  .range input::-moz-range-track { background: transparent; }
  .range input::-webkit-slider-thumb { -webkit-appearance: none; pointer-events: auto; width: 16px; height: 16px; margin-top: 2px; border-radius: 50%; background: var(--primary-color); border: 2px solid var(--card-background-color); cursor: pointer; }
  .range input::-moz-range-thumb { pointer-events: auto; width: 14px; height: 14px; border-radius: 50%; background: var(--primary-color); border: 2px solid var(--card-background-color); cursor: pointer; }
  .seg-label { align-self: center; padding: 0 8px 0 10px; font-size: 13px; color: var(--secondary-text-color); white-space: nowrap; }
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
  .dialog-import { width: min(520px, 100%); }
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
  .genres-edit { margin: -4px 0 12px; }
  .genre-choices { display: grid; grid-template-columns: repeat(auto-fill, minmax(160px, 1fr)); gap: 6px 12px; margin: 12px 0; }
  .genre-choices label { display: flex; align-items: center; gap: 8px; font-size: 14px; cursor: pointer; }
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
  .cover-col { flex: 0 0 240px; display: flex; flex-direction: column; gap: 8px; align-items: stretch; }
  .cover-col .cover { flex: none; }
  .secondary.small { height: 30px; font-size: 13px; }
  .editions { display: flex; flex-direction: column; gap: 6px; }
  .edition { position: relative; display: flex; flex-direction: column; align-items: flex-start; gap: 2px; padding: 8px 40px 8px 12px; border: 1px solid var(--divider-color); border-radius: 8px; background: transparent; text-align: left; cursor: pointer; }
  .edition:hover { background: rgba(127, 127, 127, 0.12); }
  .edition-meta { font-size: 12px; color: var(--secondary-text-color); }
  .badge.inline { top: 50%; right: 10px; margin-top: -10px; width: 20px; height: 20px; }
  .badge.inline svg { width: 14px; height: 14px; }
  .choices { display: grid; grid-template-columns: repeat(auto-fill, minmax(110px, 1fr)); gap: 12px; margin: 12px 0; }
  .choice { display: flex; flex-direction: column; gap: 2px; padding: 4px; border: 2px solid transparent; border-radius: 8px; background: none; text-align: left; cursor: pointer; font-size: 12px; }
  .choice.current { border-color: var(--primary-color); }
  .choice img { width: 100%; aspect-ratio: 2 / 3; object-fit: cover; border-radius: 6px; background: var(--secondary-background-color, #2224); }
  .choice .dims { color: var(--secondary-text-color); }
  .hint { color: var(--secondary-text-color); font-size: 13px; }
  .dialog-cover { width: min(760px, 100%); }
  .import-body { padding: 24px; }
  .export-help { margin: 0 0 12px; font-size: 14px; }
  .export-help summary { cursor: pointer; color: var(--primary-color); }
  .export-help ol { margin: 8px 0 0; padding-left: 20px; line-height: 1.6; color: var(--secondary-text-color); }
  .import-modes { display: flex; flex-direction: column; gap: 8px; margin: 12px 0; }
  .import-mode { display: flex; gap: 10px; align-items: flex-start; padding: 10px 12px; border: 1px solid var(--divider-color); border-radius: 10px; cursor: pointer; }
  .import-mode input { margin-top: 3px; }
  .import-mode .hint { display: block; font-size: 13px; color: var(--secondary-text-color); margin-top: 2px; }
  .import-mode.replace:has(input:checked) { border-color: var(--error-color, #db4437); }
  .dialog-stats { width: min(560px, 100%); }
  .stats-body h2 { display: flex; align-items: center; gap: 10px; }
  .stat-list { display: flex; flex-direction: column; margin-top: 12px; }
  .stat-item { display: flex; align-items: center; gap: 14px; padding: 10px 4px; border: none; border-bottom: 1px solid var(--divider-color); background: none; color: inherit; font-size: 16px; text-align: left; cursor: pointer; }
  .stat-item:hover { background: var(--secondary-background-color); }
  .stat-item .stat-name { flex: 1; }
  .stat-item > svg { width: 22px; height: 22px; fill: var(--secondary-text-color); }
  .stat-icon { display: inline-flex; align-items: center; justify-content: center; width: 36px; height: 36px; border-radius: 50%; background: var(--secondary-background-color); flex: none; }
  .stat-icon svg { width: 20px; height: 20px; fill: var(--primary-color); }
  .pie { display: flex; flex-wrap: wrap; align-items: center; gap: 16px 24px; margin-top: 16px; }
  .pie svg { width: 180px; height: 180px; flex: none; margin: 0 auto; }
  .pie-total { font-size: 28px; font-weight: 500; fill: var(--primary-text-color); }
  .pie-unit { font-size: 13px; fill: var(--secondary-text-color); }
  .legend { flex: 1 1 220px; list-style: none; margin: 0; padding: 0; }
  .legend li { display: flex; align-items: center; gap: 8px; padding: 5px 0; font-size: 14px; }
  .legend .swatch { width: 12px; height: 12px; border-radius: 3px; flex: none; }
  .legend .lbl { flex: 1; }
  .legend .val { font-weight: 500; }
  .legend .pct { width: 44px; text-align: right; color: var(--secondary-text-color); }
  .hbars { display: flex; flex-direction: column; gap: 6px; margin-top: 16px; max-height: 55vh; overflow: auto; }
  .hbar { display: grid; grid-template-columns: minmax(90px, 35%) 1fr 32px; align-items: center; gap: 8px; font-size: 14px; }
  .hbar .lbl { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .hbar .track { height: 14px; }
  .hbar .fill { display: block; height: 100%; min-width: 2px; border-radius: 0 4px 4px 0; background: var(--mm-series, #2a78d6); }
  .hbar .val { text-align: right; font-weight: 500; }
  .cols { display: flex; align-items: flex-end; gap: 2px; height: 220px; margin-top: 16px; padding-bottom: 34px; }
  .col { flex: 1; min-width: 0; height: 100%; display: flex; flex-direction: column; justify-content: flex-end; align-items: center; position: relative; border-bottom: 1px solid var(--divider-color); }
  .col .bar { width: 70%; max-width: 48px; border-radius: 4px 4px 0 0; background: var(--mm-series, #2a78d6); }
  .col .val { font-size: 12px; font-weight: 500; margin-bottom: 2px; }
  .col .lbl { position: absolute; top: calc(100% + 4px); font-size: 11px; line-height: 1.2; color: var(--secondary-text-color); white-space: pre-line; text-align: center; }
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
    .toolbar { padding: 8px 12px; gap: 8px; }
    .toolbar-main { gap: 8px; }
    .toolbar-main input[type="search"] { flex: 1 1 auto; min-width: 0; }
    #view { margin-left: 0; }
    .filters { display: none; width: 100%; grid-template-columns: 1fr 1fr; gap: 8px; padding-bottom: 4px; }
    .filters.open { display: grid; }
    .filters .select, .filters .select select { width: 100%; min-width: 0; }
    .filters .sortgroup, .filters .years, .filters .segmented, .filters .select.wide, .filters-reset { grid-column: 1 / -1; }
    .filters .sortgroup .select { flex: 1; }
    .filters .years { width: 100%; min-width: 0; }
    .filters .segmented { display: flex; }
    .filters .segmented button { flex: 1; }
    .filters-reset { display: block; justify-self: end; }
    .side { display: none; }
    .body { flex-direction: column; padding: 16px; }
    .cover-col { flex-basis: auto; width: 160px; align-self: center; }
    .info-row { grid-template-columns: 120px 1fr; }
  }
`;

if (!customElements.get("mymovies-panel")) {
  customElements.define("mymovies-panel", MyMoviesPanel);
}
