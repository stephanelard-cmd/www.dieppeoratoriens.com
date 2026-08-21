from pathlib import Path

path = Path("_site/index.html")
html = path.read_text(encoding="utf-8")
script = '<script>if(location.pathname==="/index.html"){location.replace("/");}</script>'
if script not in html:
    if "<head>" not in html:
        raise SystemExit("Balise <head> introuvable")
    html = html.replace("<head>", "<head>" + script, 1)
    path.write_text(html, encoding="utf-8")
print("Redirection /index.html -> / intégrée")
