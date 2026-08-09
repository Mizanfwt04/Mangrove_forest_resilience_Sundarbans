# CLEAR subdomain setup — clear.thegains.org

CLEAR should use its **own GitHub Pages site** with custom domain **clear.thegains.org**.  
(GAINS stays on **thegains.org**; one Pages site can only own one primary custom domain.)

## You do these 3 steps

### 1) Create a new GitHub repository
1. Open https://github.com/new  
2. Owner: **Mizanfwt04**  
3. Repository name: **CLEAR**  
4. Public  
5. **Do not** add README / .gitignore / license  
6. Create repository  

### 2) Add DNS at Namecheap
1. Namecheap → **Domain List** → **thegains.org** → **Advanced DNS**  
2. Add record:

| Type | Host | Value | TTL |
|------|------|--------|-----|
| **CNAME** | `clear` | `mizanfwt04.github.io` | Automatic |

3. Save  

Do **not** remove the existing A records for `@` (those keep thegains.org online).

### 3) Tell Cursor / push the site
After the empty **CLEAR** repo exists, say: **“CLEAR repo is ready”**  
and the site will be pushed with Pages + `CNAME = clear.thegains.org`.

Or push yourself from this repo (after creating CLEAR on GitHub):

```bash
# from a machine with this project
git fetch origin
git checkout origin/clear-gh-pages
git remote add clear-site https://github.com/Mizanfwt04/CLEAR.git
git push -u clear-site clear-gh-pages:main
git push clear-site clear-gh-pages:gh-pages
```

Then on GitHub → **CLEAR** repo → **Settings** → **Pages**:
- Source: **Deploy from a branch**
- Branch: **gh-pages** / root  
- Custom domain: **clear.thegains.org**  
- Wait for DNS check → enable **Enforce HTTPS**

## Result
| URL | Site |
|-----|------|
| https://thegains.org | GAINS |
| https://clear.thegains.org | CLEAR |
| https://thegains.org/clear/ | Mirror / backup of CLEAR (same content) |

## Checklist
- [ ] Repo `Mizanfwt04/CLEAR` created  
- [ ] Namecheap CNAME `clear` → `mizanfwt04.github.io`  
- [ ] Pages live with custom domain  
- [ ] HTTPS certificate approved (can take a few minutes to hours)  
