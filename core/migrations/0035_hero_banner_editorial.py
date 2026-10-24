"""Move the hero visuals out of uploaded media and into shipped WebP art.

The two live hero banners pointed at JPEG files under ``media/``. One of
them (``hero-banner-collection.jpg``) had Persian marketing text burned
into the pixels, which makes an HTML headline impossible — the two texts
sit on top of each other — and it cannot be restyled to cream/gold.

Clearing those two image fields lets the template fall back to the WebP
hero art that ships with the code (``static/assets/imgs/beauty/hero/``),
so the hero survives a deployment where ``media/`` is not persisted.
An admin upload still overrides the fallback, because the template only
uses the static art when the banner has no image.
"""

from django.db import migrations

LEGACY_IMAGES = (
    "storefront/banners/barber-hero.jpg",
    "storefront/banners/hero-banner-collection.jpg",
)

SECOND_BANNER_OLD_TITLE = "کالکشن جدید Hazhirmarket"
SECOND_BANNER_NEW_TITLE = "کالکشن جدید هژیر مارکت"

# Eyebrows are chosen from what the banner is actually about, so a
# grooming banner does not end up labelled as a styling collection.
EYEBROW_KEYWORDS = (
    ("مراقبت", "مراقبت روزانه"),
    ("کالکشن", "کلکسیون استایلینگ"),
)
DEFAULT_EYEBROW = "کلکسیون استایلینگ"


def _eyebrow_for(title):
    for keyword, eyebrow in EYEBROW_KEYWORDS:
        if keyword in title:
            return eyebrow
    return DEFAULT_EYEBROW


def forwards(apps, schema_editor):
    HeroBanner = apps.get_model("core", "HeroBanner")

    for banner in HeroBanner.objects.all():
        changed = []
        if banner.image and banner.image.name in LEGACY_IMAGES:
            banner.image = ""
            changed.append("image")

        if banner.title == SECOND_BANNER_OLD_TITLE:
            banner.title = SECOND_BANNER_NEW_TITLE
            changed.append("title")

        if not banner.eyebrow:
            banner.eyebrow = _eyebrow_for(banner.title)
            changed.append("eyebrow")

        if not banner.description:
            banner.description = (
                "ابزارهای استایلینگ مو در یک کلکسیون هم‌خانواده؛ "
                "انتخاب سریع‌تر برای یک نتیجهٔ یکدست."
            )
            changed.append("description")

        if "Hazhirmarket" in (banner.image_alt or ""):
            banner.image_alt = banner.image_alt.replace("Hazhirmarket", "هژیر مارکت")
            changed.append("image_alt")

        if changed:
            banner.save(update_fields=changed)


def backwards(apps, schema_editor):
    """The original JPEG paths are recoverable from git history only."""


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0034_digital_parts_category"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
