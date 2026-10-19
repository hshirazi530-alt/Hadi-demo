from io import BytesIO
from pathlib import Path
import tempfile

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from PIL import Image

from core.models import Category, Product, ProductImages
from core.product_images import (
    MAX_PRODUCT_IMAGE_DIMENSION,
    MAX_PRODUCT_IMAGE_SIZE,
    ProductImageUploadError,
    convert_product_image,
    get_source_product_image,
    list_source_product_images,
)
from core.upload_forms import (
    ProductDirectoryInput,
    ProductGalleryFormField,
)


def make_image_upload(
    name="product.png",
    image_format="PNG",
    size=(3200, 1800),
    color=(185, 140, 70),
):
    image = Image.new("RGB", size, color=color)
    output = BytesIO()
    image.save(output, format=image_format)
    return SimpleUploadedFile(
        name,
        output.getvalue(),
        content_type=f"image/{image_format.lower()}",
    )


class ProductImageConversionTests(TestCase):
    def test_image_is_converted_to_optimized_webp_and_resized(self):
        converted = convert_product_image(make_image_upload())

        with Image.open(converted) as image:
            self.assertEqual(image.format, "WEBP")
            self.assertLessEqual(max(image.size), MAX_PRODUCT_IMAGE_DIMENSION)
            self.assertEqual(image.size, (2400, 1350))
        self.assertTrue(converted.name.endswith(".webp"))
        self.assertEqual(len(converted.name), 37)

    def test_small_image_is_not_upscaled_and_oversized_file_is_rejected(self):
        small_image = convert_product_image(
            make_image_upload("small.png", size=(180, 120))
        )
        with Image.open(small_image) as image:
            self.assertEqual(image.size, (180, 120))

        oversized = SimpleUploadedFile(
            "oversized.jpg",
            b"x" * (MAX_PRODUCT_IMAGE_SIZE + 1),
            content_type="image/jpeg",
        )
        with self.assertRaises(ProductImageUploadError):
            convert_product_image(oversized)

    def test_image_content_must_match_a_supported_extension(self):
        upload = SimpleUploadedFile(
            "not-an-image.jpg",
            b"not an actual image",
            content_type="image/jpeg",
        )

        with self.assertRaises(ProductImageUploadError):
            convert_product_image(upload)

    def test_gallery_widget_allows_folder_and_multiple_file_selection(self):
        widget = ProductDirectoryInput(
            attrs={"multiple": True, "webkitdirectory": True, "directory": True}
        )

        self.assertTrue(widget.allow_multiple_selected)
        self.assertIn("webkitdirectory", widget.attrs)
        self.assertIsInstance(
            ProductGalleryFormField(required=False).widget,
            ProductDirectoryInput,
        )

    def test_gallery_form_field_converts_every_file_to_webp(self):
        converted = ProductGalleryFormField().clean(
            [
                make_image_upload("front.png"),
                make_image_upload("side.jpg", "JPEG"),
            ]
        )

        self.assertEqual(len(converted), 2)
        for image_file in converted:
            with Image.open(image_file) as image:
                self.assertEqual(image.format, "WEBP")


class ProductCreationUploadTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_superuser(
            username="product-upload-admin",
            email="product-upload-admin@example.com",
            password="product-upload-test-password",
            bio="مدیر",
        )
        self.category = Category.objects.create(title="مراقبت شخصی")
        self.client.force_login(self.user)
        self.media_directory = tempfile.TemporaryDirectory()
        self.media_root = Path(self.media_directory.name)
        self.source_directory = tempfile.TemporaryDirectory()
        self.source_root = Path(self.source_directory.name)
        self.override_media = override_settings(MEDIA_ROOT=self.media_root)
        self.override_source = override_settings(PRODUCT_IMAGE_SOURCE_DIR=self.source_root)
        self.override_media.enable()
        self.override_source.enable()
        self.write_source_image("source-cover.png", color=(220, 20, 30))
        self.write_source_image("source-gallery.jpg", "JPEG", color=(20, 40, 210))

    def tearDown(self):
        self.override_source.disable()
        self.override_media.disable()
        self.source_directory.cleanup()
        self.media_directory.cleanup()

    def write_source_image(self, name, image_format="PNG", color=(185, 140, 70)):
        upload = make_image_upload(name, image_format, (900, 700), color)
        self.source_root.joinpath(name).write_bytes(upload.read())

    def product_form_data(self):
        return {
            "title": "محصول آزمایشی",
            "description": "توضیحات محصول",
            "price": "125000",
            "approval": "on",
            "sale_price": "0",
            "type": "مراقبت شخصی",
            "stock_count": "8",
            "tags": "مراقبت شخصی, محصول آزمایشی",
            "life": "گارانتی یک ساله",
            "category": str(self.category.pk),
            "product_status": "in_review",
            "status": "on",
            "in_stock": "on",
        }

    def test_folder_selected_images_are_saved_as_product_cover_and_gallery(self):
        files = [
            make_image_upload("folder/cover.png", color=(220, 20, 30)),
            make_image_upload("folder/side.jpeg", "JPEG", (800, 600), (20, 40, 210)),
        ]

        response = self.client.post(
            reverse("useradmin:dashboard-add-products"),
            data={
                **self.product_form_data(),
                "product_images": files,
                "local_cover_index": "1",
            },
        )

        self.assertRedirects(response, reverse("useradmin:dashboard-products"))
        product = Product.objects.get(title="محصول آزمایشی")
        self.assertEqual(product.product_status, "in_review")
        self.assertTrue(product.image.name.startswith(f"user_{self.user.pk}/"))
        self.assertTrue(product.image.name.endswith(".webp"))
        self.assertEqual(product.p_images.count(), 1)
        gallery_image = product.p_images.get()
        self.assertTrue(gallery_image.images.name.startswith("product-images/"))
        self.assertTrue(gallery_image.images.name.endswith(".webp"))
        with Image.open(self.media_root / product.image.name) as image:
            self.assertEqual(image.format, "WEBP")
            cover_pixel = image.convert("RGB").getpixel((0, 0))
            self.assertGreater(cover_pixel[2], cover_pixel[0] + 80)
        with Image.open(self.media_root / gallery_image.images.name) as image:
            self.assertEqual(image.format, "WEBP")
        detail_response = self.client.get(
            reverse("core:product-detail", args=[product.pid])
        )
        self.assertEqual(detail_response.status_code, 200)
        self.assertContains(detail_response, product.image.url)
        self.assertContains(detail_response, gallery_image.images.url)
        self.assertEqual(
            Client().get(reverse("core:product-detail", args=[product.pid])).status_code,
            404,
        )

    def test_invalid_image_is_rejected_without_creating_a_product(self):
        response = self.client.post(
            reverse("useradmin:dashboard-add-products"),
            data={
                **self.product_form_data(),
                "local_cover_index": "0",
                "product_images": SimpleUploadedFile(
                    "invalid.jpg",
                    b"not an image",
                    content_type="image/jpeg",
                ),
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "فایل تصویر معتبر یا قابل پردازش نیست", status_code=200)
        self.assertFalse(Product.objects.filter(title="محصول آزمایشی").exists())
        self.assertFalse(list(self.media_root.rglob("*.webp")))

    def test_source_folder_image_can_be_reviewed_and_previewed_by_admin(self):
        response = self.client.get(reverse("useradmin:dashboard-add-products"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "source-cover.png")
        self.assertContains(response, "تصویر اصلی")
        preview = self.client.get(
            reverse(
                "useradmin:source-product-image",
                kwargs={"name": "source-cover.png"},
            )
        )
        self.assertEqual(preview.status_code, 200)
        self.assertEqual(preview["Content-Type"], "image/png")
        self.assertEqual(preview["X-Content-Type-Options"], "nosniff")
        self.assertEqual(preview["Cache-Control"], "private, no-store")
        preview_body = b"".join(preview.streaming_content)
        preview.close()
        with Image.open(BytesIO(preview_body)) as image:
            self.assertEqual(image.format, "PNG")

    def test_source_folder_reports_invalid_and_oversized_images(self):
        self.source_root.joinpath("broken.jpg").write_bytes(b"not an image")
        self.source_root.joinpath("oversized.png").write_bytes(
            b"x" * (MAX_PRODUCT_IMAGE_SIZE + 1)
        )

        images = {
            image["name"]: image
            for image in list_source_product_images()
        }
        response = self.client.get(reverse("useradmin:dashboard-add-products"))

        self.assertFalse(images["broken.jpg"]["selectable"])
        self.assertIn("معتبر", images["broken.jpg"]["error"])
        self.assertFalse(images["oversized.png"]["selectable"])
        self.assertIn("حداکثر ۱۰ مگابایت", images["oversized.png"]["error"])
        self.assertContains(response, "broken.jpg")
        self.assertContains(response, "oversized.png")
        response_html = response.content.decode()
        for name in ("broken.jpg", "oversized.png"):
            with self.subTest(image=name):
                self.assertRegex(
                    response_html,
                    rf'<input\b(?=[^>]*\bvalue="{name}")(?=[^>]*\bdisabled\b)[^>]*>',
                )

    def test_selected_source_cover_and_gallery_are_converted_and_associated(self):
        response = self.client.post(
            reverse("useradmin:dashboard-add-products"),
            data={
                **self.product_form_data(),
                "source_product_images": ["source-gallery.jpg", "source-cover.png"],
                "source_cover_image": "source-cover.png",
            },
        )

        self.assertRedirects(response, reverse("useradmin:dashboard-products"))
        product = Product.objects.get(title="محصول آزمایشی")
        self.assertTrue(product.image.name.endswith(".webp"))
        self.assertEqual(product.p_images.count(), 1)
        gallery_image = product.p_images.get()
        self.assertTrue(gallery_image.images.name.endswith(".webp"))
        with Image.open(self.media_root / product.image.name) as image:
            self.assertEqual(image.format, "WEBP")
            cover_pixel = image.convert("RGB").getpixel((0, 0))
            self.assertGreater(cover_pixel[0], cover_pixel[2] + 80)
        with Image.open(self.media_root / gallery_image.images.name) as image:
            self.assertEqual(image.format, "WEBP")

    def test_unselected_cover_and_path_traversal_are_rejected(self):
        with self.assertRaises(ProductImageUploadError):
            get_source_product_image("..\\outside.png")
        with self.assertRaises(ProductImageUploadError):
            get_source_product_image("missing-image.png")

        response = self.client.post(
            reverse("useradmin:dashboard-add-products"),
            data={
                **self.product_form_data(),
                "source_product_images": ["..\\outside.png"],
                "source_cover_image": "..\\outside.png",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "مسیر فایل مجاز نیست", status_code=200)
        self.assertFalse(Product.objects.filter(title="محصول آزمایشی").exists())
        self.assertFalse(list(self.media_root.rglob("*.webp")))

    def test_mixed_source_methods_are_rejected_without_saving(self):
        response = self.client.post(
            reverse("useradmin:dashboard-add-products"),
            data={
                **self.product_form_data(),
                "product_images": make_image_upload(),
                "source_product_images": ["source-cover.png"],
                "source_cover_image": "source-cover.png",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "تصاویر را فقط از یک روش انتخاب کنید", status_code=200)
        self.assertFalse(Product.objects.filter(title="محصول آزمایشی").exists())
        self.assertFalse(list(self.media_root.rglob("*.webp")))

    def test_existing_product_title_and_unknown_price_are_rejected(self):
        Product.objects.create(
            user=self.user,
            category=self.category,
            title="محصول آزمایشی",
            price=125000,
        )
        response = self.client.post(
            reverse("useradmin:dashboard-add-products"),
            data={
                **self.product_form_data(),
                "title": "محصول آزمایشی",
                "price": "0",
                "local_cover_index": "0",
                "product_images": make_image_upload(),
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "محصولی با این عنوان از قبل ثبت شده است", status_code=200)
        self.assertContains(response, "قیمت واقعی و مثبت لازم است", status_code=200)
        self.assertEqual(Product.objects.filter(title="محصول آزمایشی").count(), 1)
        self.assertFalse(list(self.media_root.rglob("*.webp")))

    def test_description_is_required_for_a_complete_product(self):
        form_data = self.product_form_data()
        form_data.pop("description")
        response = self.client.post(
            reverse("useradmin:dashboard-add-products"),
            data={
                **form_data,
                "title": "محصول بدون شرح",
                "local_cover_index": "0",
                "product_images": make_image_upload(),
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("description", response.context["form"].errors)
        self.assertFalse(Product.objects.filter(title="محصول بدون شرح").exists())
        self.assertFalse(list(self.media_root.rglob("*.webp")))

    def test_product_creation_requires_explicit_review_approval(self):
        form_data = self.product_form_data()
        form_data.pop("approval")
        response = self.client.post(
            reverse("useradmin:dashboard-add-products"),
            data={
                **form_data,
                "local_cover_index": "0",
                "product_images": make_image_upload(),
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("approval", response.context["form"].errors)
        self.assertFalse(Product.objects.filter(title="محصول آزمایشی").exists())
        self.assertFalse(list(self.media_root.rglob("*.webp")))

    def test_category_inventory_and_tags_are_required_on_creation(self):
        response = self.client.post(
            reverse("useradmin:dashboard-add-products"),
            data={
                **self.product_form_data(),
                "title": "محصول ناقص",
                "category": "",
                "stock_count": "",
                "tags": "",
                "local_cover_index": "0",
                "product_images": make_image_upload(),
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            {"category", "stock_count", "tags"}.issubset(
                response.context["form"].errors
            )
        )
        self.assertFalse(Product.objects.filter(title="محصول ناقص").exists())
        self.assertFalse(list(self.media_root.rglob("*.webp")))

    def test_django_admin_product_form_supports_folder_image_selection(self):
        response = self.client.get(reverse("admin:core_product_add"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'name="gallery_images"')
        self.assertContains(response, "webkitdirectory")
        self.assertContains(response, "تصاویر گالری محصول")
