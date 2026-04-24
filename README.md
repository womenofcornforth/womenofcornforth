# Women of Cornforth

Source for the [Women of Cornforth archive](https://womenofcornforth.github.io/womenofcornforth/) — a collection of stories, photographs and memories from the County Durham village of Cornforth, known locally as *Doggie*.

## Running locally

The site uses Jekyll via the `github-pages` gem so local builds match what
GitHub Pages serves.

```sh
# one-time: install Ruby + headers
sudo dnf install ruby rubygems ruby-devel gcc-c++ redhat-rpm-config

# install gems into ./vendor/bundle so nothing leaks into /usr
bundle config set --local path 'vendor/bundle'
bundle install

# preview at http://127.0.0.1:4000/womenofcornforth/
bundle exec jekyll serve --livereload
```

## Content pipeline

Content lives in sibling folder `../Women of Cornforth Website Information/`
(the working archive of RTF/DOCX sources and photographs). Two scripts ingest
it:

```sh
# Convert essays + biographies to Jekyll collection entries.
python3 scripts/convert_content.py

# Copy photos into assets/ with normalised filenames and write _data/photos.yml.
python3 scripts/ingest_photos.py
```

Both scripts are idempotent — safe to re-run after editing the sources. Hand
work goes in:

- `_data/photo_overrides.yml` — captions and story/tale associations for photos
- Small cleanups to `_stories/*.md` / `_tales/*.md` front matter

Anything else you hand-edit on the generated files will be overwritten the
next time the converter runs; prefer fixing the source RTF, or the script's
`TITLE_OVERRIDES` / `ESSAY_PICKS` maps.

## Structure

```
_config.yml           Jekyll + site config (title, baseurl, collections)
_layouts/             default.html, story.html, tale.html
_includes/            header.html, footer.html
_stories/             Biographies (one markdown file per person)
_tales/               Essays and memory collections
_data/photos.yml      Auto-generated photo manifest
_data/photo_overrides.yml   Hand-curated captions / associations
assets/css/main.css   Site stylesheet
assets/js/nav.js      Tiny nav toggle
assets/photos/        All photographs (normalised filenames)
index.md              Home
stories/index.html    Stories index
tales/index.html      Tales index
photos/index.html     Photo gallery
about/index.md        About page
scripts/              Ingestion scripts
```
