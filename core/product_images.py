from io import BytesIO
from pathlib import Path, PurePath
from uuid import uuid4

from django.conf import settings
from django.core.files import File
from django.core.files.base import ContentFile
from PIL import Image, ImageOps, UnidentifiedImageError


MAX_PRODUCT_IMAGE_SIZE = 10 * 1024 * 1024
MAX_PRODUCT_IMAGE_TOTAL_SIZE = 60 * 1024 * 1024
MAX_PRODUCT_IMAGE_COUNT = 20
MAX_PRODUCT_IMAGE_PIXELS = 40_000_000
MAX_PRODUCT_IMAGE_DIMENSION = 2400
WEBP_QUALITY = 88

SUPPORTED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
SUPPORTED_IMAGE_FORMATS = {
    ".jpg": "JPEG",
    ".jpeg": "JPEG",
    ".png": "PNG",
    ".webp": "WEBP",
}


class ProductImageUploadError(ValueError):
    def __init__(self, errors):
        self.errors = errors
        super().__init__("; ".join(errors))


def get_product_image_source_directory():
    return Path(settings.PRODUCT_IMAGE_SOURCE_DIR).expanduser().resolve()


def get_source_product_image(name):
    if not isinstance(name, str) or not name or name in {".", ".."}:
        raise ProductImageUploadError(["نام تصویر انتخاب‌شده معتبر نیست."])
    if "/" in name or "\\" in name or PurePath(name).name != name:
        raise ProductImageUploadError(["مسیر فایل مجاز نیست؛ فقط نام تصویر پذیرفته می‌شود."])

    root = get_product_image_source_directory()
    if not root.is_dir():
        raise ProductImageUploadError(["پوشهٔ پیش‌فرض تصاویر در سرور در دسترس نیست."])

    try:
        candidate = (root / name).resolve(strict=True)
    except (OSError, RuntimeError, ValueError) as error:
        raise ProductImageUploadError(["تصویر انتخاب‌شده در پوشهٔ پیش‌فرض یافت نشد."]) from error

    try:
        if candidate.parent != root or not candidate.is_file():
            raise ProductImageUploadError(["دسترسی به این مسیر مجاز نیست."])
        file_size = candidate.stat().st_size
    except OSError as error:
        raise ProductImageUploadError(["تصویر انتخاب‌شده در پوشهٔ پیش‌فرض یافت نشد."]) from error

    if candidate.suffix.lower() not in SUPPORTED_IMAGE_EXTENSIONS:
        raise ProductImageUploadError(["فقط JPEG، PNG و WebP پشتیبانی می‌شوند."])
    if file_size > MAX_PRODUCT_IMAGE_SIZE:
        raise ProductImageUploadError(["حجم هر تصویر باید حداکثر ۱۰ مگابایت باشد."])

    return candidate


def list_source_product_images():
    root = get_product_image_source_directory()
    if not root.is_dir():
        raise ProductImageUploadError(["پوشهٔ پیش‌فرض تصاویر در سرور در دسترس نیست."])

    images = []
    try:
        for candidate in sorted(root.iterdir(), key=lambda item: item.name.casefold()):
            if candidate.suffix.lower() not in SUPPORTED_IMAGE_EXTENSIONS:
                continue
            image_info = {
                "name": candidate.name,
                "size": 0,
                "preview_url": "",
                "selectable": False,
                "error": "",
            }
            try:
                safe_path = get_source_product_image(candidate.name)
                with Image.open(safe_path) as image:
                    expected_format = SUPPORTED_IMAGE_FORMATS[safe_path.suffix.lower()]
                    if image.format != expected_format:
                        image_info["error"] = "محتوای تصویر با پسوند فایل هم‌خوانی ندارد."
                        images.append(image_info)
                        continue
                    if image.width * image.height > MAX_PRODUCT_IMAGE_PIXELS:
                        image_info["error"] = "ابعاد تصویر بیش از حد مجاز است."
                        images.append(image_info)
                        continue
                    image.verify()
                image_info.update(
                    {
                        "size": safe_path.stat().st_size,
                        "selectable": True,
                    }
                )
            except ProductImageUploadError as error:
                image_info["error"] = " ".join(error.errors)
            except (
                OSError,
                Image.DecompressionBombError,
                UnidentifiedImageError,
                ValueError,
            ):
                image_info["error"] = "فایل تصویر معتبر یا قابل پردازش نیست."
            images.append(image_info)
    except OSError as error:
        raise ProductImageUploadError(["خواندن پوشهٔ پیش‌فرض تصاویر ممکن نشد."]) from error

    return images


def convert_source_product_images(names):
    unique_names = list(dict.fromkeys(names))
    if not unique_names:
        return []
    if len(unique_names) > MAX_PRODUCT_IMAGE_COUNT:
        raise ProductImageUploadError(
            [f"برای هر محصول حداکثر {MAX_PRODUCT_IMAGE_COUNT} تصویر انتخاب کنید."]
        )

    uploads = []
    try:
        for name in unique_names:
            path = get_source_product_image(name)
            try:
                uploads.append(path.open("rb"))
            except OSError as error:
                raise ProductImageUploadError(
                    [f"{name}: فایل تصویر هنگام خواندن در دسترس نبود."]
                ) from error
        return convert_product_images(
            [
                File(upload, name=Path(name).name)
                for upload, name in zip(uploads, unique_names)
            ]
        )
    finally:
        for upload in uploads:
            upload.close()


def convert_selected_product_images(uploaded_files, source_names):
    uploaded_files = list(uploaded_files)
    source_names = list(dict.fromkeys(source_names))
    if not uploaded_files and not source_names:
        raise ProductImageUploadError(["حداقل یک تصویر برای محصول انتخاب کنید."])
    if len(uploaded_files) + len(source_names) > MAX_PRODUCT_IMAGE_COUNT:
        raise ProductImageUploadError(
            [f"برای هر محصول حداکثر {MAX_PRODUCT_IMAGE_COUNT} تصویر انتخاب کنید."]
        )

    source_paths = [get_source_product_image(name) for name in source_names]
    try:
        total_size = sum(
            getattr(uploaded_file, "size", 0) for uploaded_file in uploaded_files
        ) + sum(path.stat().st_size for path in source_paths)
    except OSError as error:
        raise ProductImageUploadError(
            ["یکی از تصاویر پوشه هنگام آماده‌سازی در دسترس نبود."]
        ) from error
    if total_size > MAX_PRODUCT_IMAGE_TOTAL_SIZE:
        raise ProductImageUploadError(
            ["حجم مجموع تصاویر باید حداکثر ۶۰ مگابایت باشد."]
        )

    converted = []
    if uploaded_files:
        converted.extend(convert_product_images(uploaded_files))
    if source_names:
        converted.extend(convert_source_product_images(source_names))
    return converted


def convert_source_product_image(name):
    path = get_source_product_image(name)
    with path.open("rb") as upload:
        return convert_product_image(File(upload, name=path.name))


def _display_name(uploaded_file):
    name = str(getattr(uploaded_file, "name", "تصویر"))
    return name.replace("\\", "/").rsplit("/", 1)[-1] or "تصویر"


def convert_product_image(uploaded_file):
    display_name = _display_name(uploaded_file)
    extension = PurePath(display_name).suffix.lower()
    if extension not in SUPPORTED_IMAGE_EXTENSIONS:
        raise ProductImageUploadError(
            [f"{display_name}: فقط JPEG، PNG و WebP پشتیبانی می‌شوند."]
        )

    if uploaded_file.size <= 0:
        raise ProductImageUploadError([f"{display_name}: فایل تصویر خالی است."])
    if uploaded_file.size > MAX_PRODUCT_IMAGE_SIZE:
        raise ProductImageUploadError(
            [f"{display_name}: حجم هر تصویر باید حداکثر ۱۰ مگابایت باشد."]
        )

    uploaded_file.seek(0)
    raw_data = uploaded_file.read(MAX_PRODUCT_IMAGE_SIZE + 1)
    uploaded_file.seek(0)
    if len(raw_data) > MAX_PRODUCT_IMAGE_SIZE:
        raise ProductImageUploadError(
            [f"{display_name}: حجم هر تصویر باید حداکثر ۱۰ مگابایت باشد."]
        )

    try:
        with Image.open(BytesIO(raw_data)) as source:
            image_format = source.format
            width, height = source.size
            if image_format != SUPPORTED_IMAGE_FORMATS[extension]:
                raise ProductImageUploadError(
                    [f"{display_name}: محتوای تصویر با پسوند فایل هم‌خوانی ندارد."]
                )
            if width * height > MAX_PRODUCT_IMAGE_PIXELS:
                raise ProductImageUploadError(
                    [f"{display_name}: ابعاد تصویر بیش از حد مجاز است."]
                )
            source.verify()

        with Image.open(BytesIO(raw_data)) as source:
            image = ImageOps.exif_transpose(source)
            image.load()
            image.thumbnail(
                (MAX_PRODUCT_IMAGE_DIMENSION, MAX_PRODUCT_IMAGE_DIMENSION),
                Image.Resampling.LANCZOS,
            )
            has_transparency = (
                "A" in image.getbands()
                or "transparency" in image.info
            )
            image = image.convert("RGBA" if has_transparency else "RGB")
            output = BytesIO()
            image.save(
                output,
                format="WEBP",
                quality=WEBP_QUALITY,
                method=6,
            )
    except ProductImageUploadError:
        raise
    except (
        Image.DecompressionBombError,
        OSError,
        UnidentifiedImageError,
        ValueError,
    ) as error:
        raise ProductImageUploadError(
            [f"{display_name}: فایل تصویر معتبر یا قابل پردازش نیست."]
        ) from error

    converted = ContentFile(output.getvalue(), name=f"{uuid4().hex}.webp")
    converted._hjm_webp_processed = True
    converted._hjm_source_size = len(raw_data)
    return converted


def convert_product_images(uploaded_files):
    uploaded_files = list(uploaded_files)
    errors = []
    if not uploaded_files:
        raise ProductImageUploadError(["حداقل یک تصویر برای محصول انتخاب کنید."])
    if len(uploaded_files) > MAX_PRODUCT_IMAGE_COUNT:
        raise ProductImageUploadError(
            [f"برای هر محصول حداکثر {MAX_PRODUCT_IMAGE_COUNT} تصویر انتخاب کنید."]
        )

    total_size = sum(getattr(uploaded_file, "size", 0) for uploaded_file in uploaded_files)
    if total_size > MAX_PRODUCT_IMAGE_TOTAL_SIZE:
        raise ProductImageUploadError(
            ["حجم مجموع تصاویر باید حداکثر ۶۰ مگابایت باشد."]
        )

    converted = []
    for uploaded_file in uploaded_files:
        try:
            converted.append(convert_product_image(uploaded_file))
        except ProductImageUploadError as error:
            errors.extend(error.errors)

    if errors:
        raise ProductImageUploadError(errors)
    return converted
