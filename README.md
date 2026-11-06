# My Movies for Home Assistant

Connect your [My Movies](https://www.mymovies.dk) collection to Home Assistant:

- see how many titles you own and how many you have watched;
- mark a title as watched (or clear it) from an automation, a script or a voice assistant;
- browse your collection in a **My Movies sidebar panel**: a wall of covers with the
  sort options of My Movies, filters, watched badges, expandable box sets and a
  details dialog to mark titles as watched.

> **Unofficial integration.** It is not affiliated with or endorsed by My Movies.
> It uses the My Movies cloud API with your own account, which is not documented
> for third parties and may change without notice.

> **My Movies API switched off.** On 2026-11-04 My Movies closed its API to
> third-party apps. The integration now works from the collection export (CSV) of the
> My Movies app, completed by TMDB, and setup asks for no account. Marking a title as
> watched still works: each viewing is kept in Home Assistant with its date (it wins over
> the export's Watched column), as My Movies does. The API code is kept and comes
> back by setting `API_ENABLED = True` in `const.py` if access is granted again.

## Installation

### HACS (custom repository)

1. In HACS, open the menu ⋮ → **Custom repositories**.
2. Add `https://github.com/arnaudgaudin/homeassistant-mymovies` with the type **Integration**.
3. Install **My Movies**, then restart Home Assistant.

### Manual

Copy `custom_components/mymovies` into the `custom_components` folder of your
Home Assistant configuration, then restart Home Assistant.

## Configuration

1. **Settings → Devices & services → Add integration → My Movies.**
2. Sign in with the username (or e-mail) and password of your My Movies account.

### Titles and covers (integration options)

The My Movies API only gives the titles' names and IMDb IDs to the official
apps. To get them, the integration imports the **collection export** of the
My Movies app:

1. In the My Movies app, export your collection to a CSV file.
2. In Home Assistant, open the My Movies integration → **Configure**, and upload the file.
3. Re-import a fresh export after adding titles; a repair notice tells you when
   titles are missing.

Add a free [TMDB API key](https://www.themoviedb.org/settings/api) (v3) in the
same options form for high-resolution posters. Each title is looked up once (by
IMDb ID, by title and year, or as a collection for box sets; season discs get
their season's poster) and the sharpest cover between TMDB and My Movies is shown.
TMDB also gives the production countries and fills in the genres the export leaves
empty (box sets and the films inside them); titles added by a new import are looked up
the same way.
Without a key, the smaller My Movies covers are used. An administrator can pick
another cover from the title's dialog: any TMDB poster, the My Movies cover or an
uploaded image (JPEG or PNG, stored in `/config/mymovies/covers`).

## Entities

| Entity | Description |
| --- | --- |
| `sensor.my_movies_<account>_titles` | Number of titles in the collection |
| `sensor.my_movies_<account>_watched_titles` | Number of titles marked as watched |

The collection is refreshed every hour and right after each change.

## Actions

| Action | Description |
| --- | --- |
| `mymovies.mark_watched` | Logs a viewing of a title (`title`, optional `notes`) |
| `mymovies.clear_watched` | Removes every logged viewing of a title |
| `mymovies.get_titles` | Returns the collection with names, IMDb IDs, watched flags and posters |

`title` accepts the title name, the original title, the IMDb ID, the collection
number or the My Movies title ID. Films inside box sets can be marked by name too:
they have their own watched state in My Movies. When several titles match (for example the
Blu-ray and the 4K edition of the same film), use the collection number.

```yaml
action: mymovies.mark_watched
data:
  title: "Sin City"
  notes: "Home cinema"
```

```yaml
action: mymovies.get_titles
response_variable: collection
```

## My Movies panel

A **My Movies** entry is added to the sidebar. It shows the collection as a wall
of covers and offers:

- the sort options of My Movies (title, collection number, rating, personal rating,
  running time, production year, release date, parental rating, added date),
  ascending or descending;
- a wall of covers or a list with more details per title;
- search (title, original title, director, cast) and filters: type, genre,
  classification (the six of My Movies: not rated, all audiences, parental
  guidance, not under 12, 16 or 18; other systems' ratings are mapped onto them),
  disc (4K, Blu-ray, DVD, 3D),
  a production year range with two handles
  and a Watched / All / Not watched switch;
- editions of the same film (same IMDb ID) share one tile and its dialog lists them,
  or, with **Editions: Expanded**, get one tile each with their disc and edition;
- a ✓ badge on watched titles, including films inside box sets;
- **Expand box sets**: show the films of each box set instead of the box set itself;
- a details dialog (synopsis, director, cast, genres, runtime, ratings, dates,
  box set contents) with **Mark as watched** / **Clear watched** buttons.
- a **Statistics** button: disc format, media type, genres, ratings, classification,
  running time (by 30 minutes), production decade and production countries (from
  TMDB, so a TMDB key is needed), each as a pie, bar or column chart;
- for administrators, a **Choose genres** button on titles the export and TMDB leave
  without genre (the choice is kept in Home Assistant);
- for administrators, an **Import** button to load a new collection export directly
  from the panel.

The details come from the imported export: re-import it after updating the
integration to fill in new columns.

## Privacy

Your credentials are stored in Home Assistant and only sent to the My Movies API.
The integration reads and writes nothing but your own collection and watched state.
The TMDB key, when set, is only used to look up posters.

## Development

```bash
python3 -m venv .venv && .venv/bin/pip install pytest-homeassistant-custom-component
.venv/bin/pytest tests
```

## Credits

- Collection data comes from [My Movies](https://www.mymovies.dk), through your
  own account. This integration is
  unofficial and not affiliated with or endorsed by My Movies: get the app and
  manage your collection on [mymovies.dk](https://www.mymovies.dk).
- Posters are provided by [TMDB](https://www.themoviedb.org).
  This product uses the TMDB API but is not endorsed or certified by TMDB.

The My Movies panel shows these credits and a link to the official My Movies
website.

## License

MIT
