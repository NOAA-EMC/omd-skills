# Scientific Database Reference

## arXiv

Preprint server for physics, mathematics, computer science, quantitative biology, quantitative finance, statistics, electrical engineering, and economics.

### Search Syntax

```
site:arxiv.org "<exact phrase>"
site:arxiv.org author:"LastName"
site:arxiv.org cs.LG "<machine learning topic>"
site:arxiv.org 2024 "<recent work>"
```

### Category Codes

| Code | Field |
|------|-------|
| `cs.LG` | Machine Learning |
| `cs.AI` | Artificial Intelligence |
| `cs.CL` | Computation and Language (NLP) |
| `cs.CV` | Computer Vision |
| `physics.comp-ph` | Computational Physics |
| `cond-mat` | Condensed Matter |
| `quant-ph` | Quantum Physics |
| `astro-ph` | Astrophysics |
| `math.NA` | Numerical Analysis |
| `stat.ML` | Machine Learning (Statistics) |
| `q-bio` | Quantitative Biology |

For the geoscience categories (`physics.ao-ph` and friends), see
[arXiv categories for geoscience](#arxiv-categories-for-geoscience).

### arXiv IDs

Format: `YYMM.NNNNN` (e.g., `2301.07041`)

Direct URL: `https://arxiv.org/abs/2301.07041`
PDF: `https://arxiv.org/pdf/2301.07041.pdf`

### Notes

- Preprints are not peer-reviewed
- Many papers have published versions — look for DOI links
- Check version history (`v1`, `v2`, etc.) for updates

---

## PubMed

Biomedical and life sciences literature from MEDLINE, life science journals, and online books.

### Search Syntax

```
site:pubmed.ncbi.nlm.nih.gov "<topic>"
site:pubmed.ncbi.nlm.nih.gov "<gene name>" review
site:pubmed.ncbi.nlm.nih.gov "<disease>" clinical trial
```

### PubMed Advanced Search

For complex queries, use PubMed directly:

- `[Title/Abstract]` — Search title and abstract
- `[Author]` — Author name
- `[Journal]` — Journal name
- `[MeSH Terms]` — Medical Subject Headings

Example: `"machine learning"[Title/Abstract] AND "drug discovery"[Title/Abstract]`

### PMIDs

PubMed IDs are numeric (e.g., `34567890`)

Direct URL: `https://pubmed.ncbi.nlm.nih.gov/34567890/`

### Notes

- All indexed articles are peer-reviewed
- PMC (PubMed Central) provides free full text for some articles
- Use MeSH terms for precise medical/biological searches

---

## Semantic Scholar

AI-powered academic search with citation analysis and paper recommendations.

### Search Syntax

```
site:semanticscholar.org "<topic>"
site:semanticscholar.org author:"<name>"
```

### Features

- **Citation counts** — Useful for identifying influential papers
- **Influential citations** — Distinguishes significant from peripheral citations
- **TLDR** — AI-generated paper summaries
- **Related papers** — Algorithmic recommendations
- **Citation graphs** — Visualize citation networks

### Semantic Scholar API

For programmatic access:

```bash
curl "https://api.semanticscholar.org/graph/v1/paper/search?query=machine+learning&limit=10"
```

### Corpus IDs

Semantic Scholar uses Corpus IDs and supports DOIs, arXiv IDs, and PMIDs.

---

## Google Scholar

Broad coverage across disciplines, including books, theses, and conference papers.

### Search Syntax

```
"<exact phrase>"
author:"<name>"
intitle:"<word in title>"
source:"<journal name>"
```

### Date Filtering

- Click "Since Year" in sidebar
- Or add to query: `"topic" 2023..2025`

### Features

- **Cited by** — Find papers citing a given work
- **Related articles** — Similar papers
- **Versions** — Find different versions (preprint, published)
- **Create alert** — Email notifications for new papers

### Notes

- Broadest coverage but noisiest results
- Citation counts may differ from other sources
- No API access — use web search

---

## Earth System Modeling and Geosciences

The earth-system-modeling literature (GCMs, regional climate, data assimilation,
cryosphere, ocean, carbon and biogeochemistry, impacts) lives mostly outside
arXiv and PubMed. Search the publisher archives and index them through OpenAlex.

### Core journals

| Journal | Publisher | ISSN-L | Open access |
|---------|-----------|--------|-------------|
| Geoscientific Model Development (GMD) | Copernicus | 1991-959X | Full |
| Earth System Science Data (ESSD) | Copernicus | 1866-3508 | Full |
| Atmospheric Chemistry and Physics (ACP) | Copernicus | 1680-7316 | Full |
| The Cryosphere (TC) | Copernicus | 1994-0416 | Full |
| Ocean Science (OS) | Copernicus | 1812-0784 | Full |
| Climate of the Past (CP) | Copernicus | 1814-9324 | Full |
| Biogeosciences (BG) | Copernicus | 1726-4170 | Full |
| Nonlinear Processes in Geophysics (NPG) | Copernicus | 1023-5809 | Full |
| Earth System Dynamics (ESD) | Copernicus | 2190-4979 | Full |
| Atmospheric Measurement Techniques (AMT) | Copernicus | 1867-1381 | Full |
| Journal of Advances in Modeling Earth Systems (JAMES) | AGU / Wiley | 1942-2466 | Full |
| Journal of Climate | American Meteorological Society | 0894-8755 | No |
| Monthly Weather Review | American Meteorological Society | 0027-0644 | No |
| Weather and Forecasting | American Meteorological Society | 0882-8156 | No |
| Journal of the Atmospheric Sciences | American Meteorological Society | 0022-4928 | No |
| Journal of Physical Oceanography | American Meteorological Society | 0022-3670 | No |
| Journal of Hydrometeorology | American Meteorological Society | 1525-7541 | No |
| Bulletin of the American Meteorological Society | American Meteorological Society | 0003-0007 | No |
| Artificial Intelligence for the Earth Systems | American Meteorological Society | 2769-7525 | No |
| Quarterly Journal of the Royal Meteorological Society | RMetS / Wiley | 0035-9009 | No |
| International Journal of Climatology | RMetS / Wiley | 0899-8418 | No |
| Geophysical Research Letters | AGU / Wiley | 0094-8276 | Full |
| Water Resources Research | AGU / Wiley | 0043-1397 | Full |
| Paleoceanography and Paleoclimatology | AGU / Wiley | 2572-4517 | No |
| Climate Dynamics | Springer | 0930-7575 | No |
| Advances in Atmospheric Sciences | Springer | 0256-1530 | No |
| Nature Climate Change | Nature Portfolio | 1758-678X | No |
| Nature Geoscience | Nature Portfolio | 1752-0894 | No |
| npj Climate and Atmospheric Science | Nature Portfolio | 2397-3722 | Full |
| Environmental Research Letters | IOP Publishing | 1748-9326 | Full |
| Journal of Glaciology | Cambridge University Press | 0022-1430 | Full |
| Tellus A: Dynamic Meteorology and Oceanography | Stockholm University Press | 0280-6495 | Full |
| Tellus B: Chemical and Physical Meteorology | Stockholm University Press | 0280-6509 | Full |
| Ocean Modelling | Elsevier | 1463-5003 | No |
| Environmental Modelling & Software | Elsevier | 1364-8152 | No |
| Ecological Modelling | Elsevier | 0304-3800 | No |
| Climate Risk Management | Elsevier | 2212-0963 | Full |
| Annual Review of Earth and Planetary Sciences | Annual Reviews | 0084-6597 | No |
| The Journal of Open Source Software | Open Journals | 2475-9066 | Full |

### Publisher archives

```
site:gmd.copernicus.org "<model name>"
site:essd.copernicus.org "<dataset description>"
site:acp.copernicus.org "<topic>"
site:tc.copernicus.org "<topic>"
site:os.copernicus.org "<topic>"
site:journals.ametsoc.org "<topic>"
site:agupubs.onlinelibrary.wiley.com "<topic>"
site:rmets.onlinelibrary.wiley.com "<topic>"
site:link.springer.com "<topic>" "Climate Dynamics"
site:nature.com "<topic>" "Nature Climate Change"
```

Copernicus manuscripts are posted as citable preprints in **EGUsphere**
(DOI `10.5194/egusphere-<year>-<number>`) before the journal version appears, so
the newest model descriptions are often preprint-only. Each journal also keeps an
archive of the older per-journal `* Discussions` track (for example
Geoscientific Model Development Discussions, ISSN-L 1991-962X), which still
carries the public review comments and replies but no longer takes new
submissions:

```
site:egusphere.copernicus.org "<topic>"
site:gmd.copernicus.org "<topic>"
```

### DOI prefixes

Useful for recognizing a venue from a bare DOI:

| Prefix | Publisher |
|--------|-----------|
| `10.5194` | Copernicus (GMD, ESSD, ACP, TC, OS, CP, BG, ESD, NPG, AMT) |
| `10.1175` | American Meteorological Society |
| `10.1029` | American Geophysical Union |
| `10.1002` | Wiley (includes RMetS journals) |
| `10.1038` | Nature Portfolio |
| `10.1007` | Springer |
| `10.1088` | IOP Publishing |
| `10.1146` | Annual Reviews |
| `10.16993` | Stockholm University Press (Tellus A, Tellus B) |

### arXiv categories for geoscience

Earth-system work is thinly represented on arXiv, but these categories carry
modeling, dynamics, and ML-for-science preprints:

| Code | Field |
|------|-------|
| `physics.ao-ph` | Atmospheric and Oceanic Physics |
| `physics.geo-ph` | Geophysics |
| `physics.flu-dyn` | Fluid Dynamics |
| `physics.space-ph` | Space Physics |
| `nlin` | Nonlinear Sciences (chaos, pattern formation) |
| `physics.comp-ph` | Computational Physics |
| `stat.ML` / `cs.LG` | Machine learning methods |

```
site:arxiv.org physics.ao-ph "<topic>"
site:arxiv.org "emulation" "climate" cs.LG
```

### Indexing APIs

Publisher sites block automated requests, so resolve journals through OpenAlex
by ISSN-L first, then search inside that source:

```bash
# Resolve a journal from its ISSN
curl -s "https://api.openalex.org/sources?filter=issn_l:1991-959X" \
  | python3 -c "import json,sys; r=json.load(sys.stdin)['results'][0]; print(r['display_name'], r['ids']['openalex'])"

# Search within that journal, most-cited first
curl -s "https://api.openalex.org/works?search=ensemble%20kalman%20filter&filter=primary_location.source.id:S60406085&sort=cited_by_count:desc&per-page=10&select=title,publication_year,cited_by_count,doi"

# Newest papers in a journal
curl -s "https://api.openalex.org/works?filter=primary_location.source.id:S60406085&sort=publication_date:desc&per-page=10&select=title,publication_date,doi"
```

A `mailto=<address>` parameter identifies the requester but does not raise the
rate limit; an `api_key` gives a dedicated daily request budget instead of the
shared anonymous one.

Crossref resolves DOIs and lists recent works by ISSN for most publishers:

```bash
curl -s "https://api.crossref.org/works/10.1175/jcli-d-22-0216.1"
curl -s "https://api.crossref.org/journals/0894-8755/works?rows=5&select=title,DOI,issued"
```

Note that `api.crossref.org/journals/<issn>/works` answers 404 for the
Copernicus journals even though their DOIs resolve fine by DOI — use OpenAlex
source filters for those.

### Model intercomparison and data literature

- **ESGF / CMIP6** — model output and the publications describing the runs:
  <https://esgf-node.llnl.gov/search/cmip6/>
- **NASA ADS** — the index of record for geoscience and space-science
  bibliography, with full-text search across older journal volumes:
  <https://ui.adsabs.harvard.edu/>
- **NOAA Institutional Repository** — NOAA technical reports, journal articles
  by NOAA authors, and operational-model documentation:
  <https://repository.library.noaa.gov/>
- **NOAA NCEI** — archived observational and reanalysis datasets that papers
  cite as their source: <https://www.ncei.noaa.gov/access/>
- **Copernicus Climate Data Store** — ERA5 and related reanalysis products and
  documentation: <https://cds.climate.copernicus.eu/>
- **IPCC reports** — assessment-report chapters are the standard citations for
  consensus statements: <https://www.ipcc.ch/reports/>

---

## Specialized Databases

### ChemRxiv / ACS Publications

Chemistry preprints and published work.

```
site:chemrxiv.org "<chemistry topic>"
site:pubs.acs.org "<chemistry topic>"
```

### IEEE Xplore

Electrical engineering, computer science, electronics.

```
site:ieeexplore.ieee.org "<topic>"
```

### Nature / Science

High-impact general science. For the earth-system-modeling titles in this family,
see [Earth System Modeling and Geosciences](#earth-system-modeling-and-geosciences).

```
site:nature.com "<topic>"
site:science.org "<topic>"
```

### bioRxiv / medRxiv

Biology and medicine preprints.

```
site:biorxiv.org "<topic>"
site:medrxiv.org "<topic>"
```

---

## Choosing a Database

| Research Area | Primary | Secondary |
|--------------|---------|-----------|
| Machine Learning | arXiv (cs.LG) | Semantic Scholar |
| Biomedicine | PubMed | Google Scholar |
| Physics | arXiv | Google Scholar |
| Chemistry | ACS, ChemRxiv | Semantic Scholar |
| Earth system modeling / climate | Copernicus, AMS, AGU journals | OpenAlex, NASA ADS |
| Engineering | IEEE Xplore | Google Scholar |
| Cross-disciplinary | Semantic Scholar | Google Scholar |
| Finding citations | Semantic Scholar | Google Scholar |
