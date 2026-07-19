# GAINS website

Public site for **GAINS** — Geospatial Artificial Intelligence in Nature Services.

## Local preview

Open `docs/index.html` in a browser, or serve the folder:

```bash
python3 -m http.server 8080 --directory docs
```

Then visit `http://localhost:8080`.

## Publish on GitHub Pages + gains.org

1. In the GitHub repo: **Settings → Pages**.
2. Source: **Deploy from a branch**.
3. Branch: `main` (or this feature branch after merge), folder: `/docs`.
4. After the first deploy, under **Custom domain**, enter `gains.org` and save.
   - This repo already includes `docs/CNAME` with `gains.org`.
5. Enable **Enforce HTTPS** once DNS is verified.

### DNS at your registrar (Namecheap or other)

If you **own** `gains.org`, add:

| Type | Host | Value |
|------|------|--------|
| A | `@` | `185.199.108.153` |
| A | `@` | `185.199.109.153` |
| A | `@` | `185.199.110.153` |
| A | `@` | `185.199.111.153` |
| CNAME | `www` | `<your-github-username>.github.io` |

For this repository, `www` should point to `mizanfwt04.github.io`.

> **Note:** `gains.org` must be registered to you. If another party owns it, register the domain first (or choose an available alternative), then apply these DNS records.
