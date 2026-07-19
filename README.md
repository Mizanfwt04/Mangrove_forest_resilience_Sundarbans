# GAINS website

Public site for **GAINS** — Geospatial Artificial Intelligence in Nature Services.

## Local preview

```bash
python3 -m http.server 8080 --directory docs
```

Visit `http://localhost:8080`.

## GitHub Pages status

Pages is already configured for this repo:

- Branch: `gh-pages` → `/` (root)
- Custom domain: `gains.org`

The site also lives in `docs/` on `main` for editing.

## Fix: “Domain gains.org is not eligible for HTTPS”

That message means **DNS does not point at GitHub yet**. GitHub can only issue a certificate after DNS is correct.

### What DNS shows today (broken)

| Record | Current value | Problem |
|--------|---------------|---------|
| `gains.org` A | `54.69.149.217` (AWS) | Must be GitHub Pages IPs |
| `www.gains.org` | `54.69.149.217` | Must be CNAME → `mizanfwt04.github.io` |

### Fix in Namecheap (or your registrar)

1. Log in → **Domain List** → **gains.org** → **Advanced DNS**.
2. **Delete** every old `A` / `AAAA` / `CNAME` / URL Redirect / Parking record for `@` and `www` (including any pointing to `54.69.149.217`).
3. **Add exactly these records:**

| Type | Host | Value | TTL |
|------|------|--------|-----|
| A Record | `@` | `185.199.108.153` | Automatic |
| A Record | `@` | `185.199.109.153` | Automatic |
| A Record | `@` | `185.199.110.153` | Automatic |
| A Record | `@` | `185.199.111.153` | Automatic |
| CNAME Record | `www` | `mizanfwt04.github.io` | Automatic |

4. Optional but recommended (helps HTTPS):

| Type | Host | Value |
|------|------|--------|
| AAAA Record | `@` | `2606:50c0:8000::153` |
| AAAA Record | `@` | `2606:50c0:8001::153` |
| AAAA Record | `@` | `2606:50c0:8002::153` |
| AAAA Record | `@` | `2606:50c0:8003::153` |

5. Wait 5–60 minutes (sometimes up to a few hours). Check with:

```bash
dig +short gains.org A
# must show only: 185.199.108.153 … 185.199.111.153
dig +short www.gains.org CNAME
# must show: mizanfwt04.github.io.
```

6. GitHub → **Settings → Pages**:
   - Remove custom domain → Save
   - Re-enter `gains.org` → Save (forces a new certificate request)
   - When the checkmark appears, enable **Enforce HTTPS**

Until step 3 is done at Namecheap, HTTPS will stay unavailable. I cannot change Namecheap DNS from this agent — only you can, while logged into the registrar.
