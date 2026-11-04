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
same options form for high-resolution posters: titles are looked up by IMDb ID,
box sets by collection name and the films of box sets by title. Without a key, or
when TMDB has no poster, the smaller My Movies covers are used.

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
number or the My Movies title ID. When several titles match (for example the
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
- search (title, original title, director, cast) and filters (type, watched);
- a ✓ badge on watched titles;
- **Expand box sets**: show the films of each box set instead of the box set itself;
- a details dialog (synopsis, director, cast, genres, runtime, ratings, dates,
  box set contents) with **Mark as watched** / **Clear watched** buttons.

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

Posters are provided by [TMDB](https://www.themoviedb.org).
This product uses the TMDB API but is not endorsed or certified by TMDB.

## License

MIT
