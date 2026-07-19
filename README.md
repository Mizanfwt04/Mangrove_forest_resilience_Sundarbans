# GAINS website

Public site for **GAINS** — Geospatial Artificial Intelligence in Nature Services.

**Live domain:** [thegains.org](https://thegains.org)

## Local preview

```bash
python3 -m http.server 8080 --directory docs
```

Visit `http://localhost:8080`.

## GitHub Pages

- Publishing branch: `gh-pages` → `/`
- Custom domain: `thegains.org` (see `CNAME`)

## DNS at Namecheap (required once)

1. Namecheap → **Domain List** → **thegains.org** → **Manage**
2. Open **Advanced DNS**
3. Delete parking / old URL Redirect / old A records for `@` and `www`
4. Add:

| Type | Host | Value | TTL |
|------|------|--------|-----|
| A Record | `@` | `185.199.108.153` | Automatic |
| A Record | `@` | `185.199.109.153` | Automatic |
| A Record | `@` | `185.199.110.153` | Automatic |
| A Record | `@` | `185.199.111.153` | Automatic |
| CNAME Record | `www` | `mizanfwt04.github.io` | Automatic |

5. GitHub → repo **Settings → Pages** → Custom domain: `thegains.org` → **Save**
6. Wait for DNS check → enable **Enforce HTTPS**

## Email (optional, later)

- Free: Cloudflare Email Routing → forward `info@thegains.org` to Gmail  
- Or Namecheap Private Email for a full mailbox  
