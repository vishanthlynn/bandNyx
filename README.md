# Band NYX (bandnyx)

Official press kit site for **Band NYX** — rock, melody, energy.

## Live site

**https://vishanthlynn.github.io/bandNyx/**

### Enable GitHub Pages (required once — fixes 404)

The **failed** runs that mention `actions/deploy-pages@v4` are from an **old workflow**. The current workflow publishes to the **`gh-pages`** branch (see latest green runs).

1. Open **https://github.com/vishanthlynn/bandNyx/settings/pages**
2. Under **Build and deployment** → **Source**, choose **Deploy from a branch**
3. **Branch:** `gh-pages` · **Folder:** `/ (root)` → **Save**
4. Wait 2–5 minutes, then open **https://vishanthlynn.github.io/bandNyx/**

To redeploy after changes: push to `main`, or **Actions** → **Deploy Band NYX site to GitHub Pages** → **Run workflow**.

## Local preview

```bash
cd nyx-website
python3 -m http.server 8080
```

Open http://localhost:8080

## Repository

https://github.com/vishanthlynn/bandNyx
