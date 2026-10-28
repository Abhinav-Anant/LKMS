"""What search engines and link previews see: the React app's index.html with the school's title,
description, canonical link, Open Graph tags and School structured data filled in, plus robots.txt and
sitemap.xml. Nginx sends /, /apply, /track, /robots.txt and /sitemap.xml here (see deploy/nginx-lkms.conf)."""
import json
import re
from html import escape

from django.conf import settings
from django.http import Http404, HttpResponse

from academics.models import SchoolClass

from .models import GalleryPhoto, SchoolProfile

# Public pages worth indexing: path -> (title prefix, description lead). The home page has none.
PAGES = {
    "": None,
    "apply": ("Apply for admission", "Apply online for admission to {name}. It takes about 10 minutes."),
    "track": ("Track your application", "Check the status of an admission application to {name}."),
}


def _base_url(request, school):
    return (school.website or f"{request.scheme}://{request.get_host()}").rstrip("/")


def _class_range():
    names = list(SchoolClass.objects.filter(is_active=True).values_list("name", flat=True))
    return f"{names[0]} to {names[-1]}" if len(names) > 1 else "".join(names)


def _head(request, path):
    school = SchoolProfile.get()
    base = _base_url(request, school)
    url = f"{base}/{path}"
    place = ", ".join(p for p in (school.district, school.state) if p)
    classes = _class_range()

    if PAGES[path]:
        prefix, lead = PAGES[path]
        title = f"{prefix} | {school.name}"
        description = lead.format(name=school.name)
    else:
        title = f"{school.name}, {school.district}" if school.district else school.name
        if classes:
            title += f" | {classes}"
        description = " ".join(filter(None, [
            f"{school.name}{', ' + place if place else ''}:",
            f"a {school.board_label} school" + (f" from {classes}." if classes else "."),
            "Apply for admission online.",
        ]))

    photo = GalleryPhoto.objects.first()
    image = (f"{base}/api/v1/school/gallery/{photo.pk}/image/" if photo
             else f"{base}/api/v1/school/logo/" if school.logo else "")

    tags = [
        f"<title>{escape(title)}</title>",
        f'<meta name="description" content="{escape(description)}" />',
        f'<link rel="canonical" href="{escape(url)}" />',
        '<meta property="og:type" content="website" />',
        '<meta property="og:locale" content="en_IN" />',
        f'<meta property="og:site_name" content="{escape(school.name)}" />',
        f'<meta property="og:title" content="{escape(title)}" />',
        f'<meta property="og:description" content="{escape(description)}" />',
        f'<meta property="og:url" content="{escape(url)}" />',
        f'<meta name="twitter:card" content="{"summary_large_image" if photo else "summary"}" />',
    ]
    if image:
        tags.append(f'<meta property="og:image" content="{escape(image)}" />')

    if not path:
        data = {
            "@context": "https://schema.org",
            "@type": "School",
            "name": school.name,
            "url": f"{base}/",
            "description": description,
            "address": {
                "@type": "PostalAddress",
                "streetAddress": school.address,
                "addressLocality": school.district,
                "addressRegion": school.state,
                "postalCode": school.pincode,
                "addressCountry": "IN",
            },
            "telephone": f"+91 {school.phone}" if len(school.phone) == 10 else school.phone,
            "email": school.email,
            "logo": f"{base}/api/v1/school/logo/" if school.logo else "",
            "image": image,
            "sameAs": [u for u in (school.facebook_url, school.instagram_url, school.youtube_url, school.x_url) if u],
        }
        if school.map_latitude is not None and school.map_longitude is not None:
            data["geo"] = {"@type": "GeoCoordinates", "latitude": float(school.map_latitude),
                           "longitude": float(school.map_longitude)}
        data["address"] = {k: v for k, v in data["address"].items() if v}
        data = {k: v for k, v in data.items() if v}
        # "<" escaped so a school name can never close the script tag
        tags.append('<script type="application/ld+json">'
                    + json.dumps(data, ensure_ascii=False).replace("<", "\\u003c") + "</script>")
    return "\n    ".join(tags)


def page(request, path=""):
    if path not in PAGES:
        raise Http404
    html = (settings.FRONTEND_DIST / "index.html").read_text(encoding="utf-8")
    html = re.sub(r"<title>.*?</title>", lambda _: _head(request, path), html, count=1, flags=re.S)
    response = HttpResponse(html)
    response["Cache-Control"] = "no-cache"
    return response


def robots(request):
    base = _base_url(request, SchoolProfile.get())
    lines = ["User-agent: *", "Allow: /api/v1/school/"]
    lines += [f"Disallow: /{p}/" for p in ("staff", "parent", "pay", "api", "admin")]
    lines += ["", f"Sitemap: {base}/sitemap.xml", ""]
    return HttpResponse("\n".join(lines), content_type="text/plain")


def sitemap(request):
    school = SchoolProfile.get()
    base = _base_url(request, school)
    lastmod = school.updated_at.date().isoformat()
    urls = "".join(f"<url><loc>{escape(base)}/{p}</loc><lastmod>{lastmod}</lastmod></url>" for p in PAGES)
    return HttpResponse('<?xml version="1.0" encoding="UTF-8"?>'
                        f'<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{urls}</urlset>',
                        content_type="application/xml")
