import tempfile
from pathlib import Path
from unittest.mock import patch

from django.core.management import call_command
from django.test import TestCase
from django.test import override_settings
from django.urls import reverse
from django.contrib.auth import get_user_model

from core.models import (
    Address,
    CartOrder,
    CartOrderProducts,
    Category,
    FAQ,
    HeroBanner,
    PaymentAttempt,
    Product,
    ProductBundle,
    ProductImages,
    ProductReview,
    StoreTrustFeature,
)
from core.storefront import HOME_CATEGORIES, SAMPLE_STORE_PRODUCTS
from core.payments import ZarinpalError
from userauths.models import ContactUs


class StorefrontTests(TestCase):
    def test_header_has_order_tracking_and_telegram_contact(self):
        response = self.client.get(reverse("core:index"))

        self.assertContains(
            response,
            f'href="{reverse("core:dashboard")}#track-orders"',
        )
        self.assertContains(response, 'href="https://t.me/+989186555100"')
        # The header prints the support number in Latin digits inside a <bdi dir="ltr">
        # wrapper (the value comes from STORE_PROFILE["phone"]), so match that
        # rendering instead of Persian digits.
        self.assertContains(response, 'href="tel:+989186555100"')
        self.assertContains(response, '<bdi class="hm-utility__number" dir="ltr">09186555100</bdi>')
        # Current header markup: desktop brand mark inside the category bar and the
        # brand logo inside the mobile drawer.
        self.assertContains(response, 'class="hm-brand-mark"')
        self.assertContains(response, 'class="store-brand-logo"')

    def test_sample_product_command_is_repeatable_and_publishes_personal_care_items(self):
        Category.objects.create(title="کادویی")
        with tempfile.TemporaryDirectory() as media_root:
            with override_settings(MEDIA_ROOT=Path(media_root)):
                call_command("seed_store_products", verbosity=0)
                seeded_products = {
                    item["title"]: Product.objects.get(title=item["title"])
                    for item in SAMPLE_STORE_PRODUCTS
                }
                spin_items = [
                    item for item in SAMPLE_STORE_PRODUCTS if item.get("spin_sequence")
                ]
                for index, item in enumerate(spin_items):
                    wrong_sequence = spin_items[
                        (index + 1) % len(spin_items)
                    ]["spin_sequence"]
                    ProductImages.objects.create(
                        product=seeded_products[item["title"]],
                        images=(
                            f"store-samples/360/{wrong_sequence}/frame-01.webp"
                        ),
                    )
                call_command("seed_store_products", verbosity=0)

                for item in spin_items:
                    product = seeded_products[item["title"]]
                    frames = list(
                        product.p_images.filter(
                            images__startswith="store-samples/360/"
                        ).values_list("images", flat=True)
                    )
                    expected_prefix = (
                        f"store-samples/360/{item['spin_sequence']}/frame-"
                    )
                    with self.subTest(spin_product=item["title"]):
                        self.assertEqual(len(frames), 24)
                        self.assertTrue(
                            all(frame.startswith(expected_prefix) for frame in frames)
                        )

                self.assertEqual(
                    Product.objects.filter(
                        title__contains="(نمونه)",
                        product_status="published",
                    ).count(),
                    len(SAMPLE_STORE_PRODUCTS),
                )
                sample_images = {item["image"] for item in SAMPLE_STORE_PRODUCTS}
                for image_name in sample_images:
                    with self.subTest(image=image_name):
                        self.assertTrue(
                            (Path(media_root) / "store-samples" / image_name).is_file()
                        )
                        self.assertGreater(
                            (Path(media_root) / "store-samples" / image_name).stat().st_size,
                            50_000,
                        )
                category_images = {
                    item["product_category"]: Path(item["image"]).name
                    for item in HOME_CATEGORIES
                }
                for category_name, image_name in category_images.items():
                    with self.subTest(category=category_name):
                        category = Category.objects.get(title=category_name)
                        self.assertEqual(
                            category.image.name,
                            f"store-samples/photos/{image_name}",
                        )
                        self.assertTrue(
                            (
                                Path(media_root)
                                / "store-samples"
                                / "photos"
                                / image_name
                            ).is_file()
                        )

                spin_product = Product.objects.get(
                    title="ماشین اصلاح چندکاره مدل هژیر M2 (نمونه)"
                )
                spin_images = ProductImages.objects.filter(product=spin_product).order_by(
                    "images"
                )
                self.assertEqual(spin_images.count(), 24)
                self.assertTrue(
                    (
                        Path(media_root)
                        / "store-samples"
                        / "360"
                        / "dsp-gold-clipper"
                        / "frame-24.webp"
                    ).is_file()
                )
                spin_detail = self.client.get(
                    reverse("core:product-detail", args=[spin_product.pid])
                )
                self.assertContains(spin_detail, "data-spin-viewer")
                self.assertContains(spin_detail, "frame-24.webp")
                self.assertContains(
                    spin_detail,
                    f'data-gallery-original-src="{spin_product.image.url}"',
                )
                self.assertNotContains(spin_detail, "data-gallery-thumb")

                engraved_product = Product.objects.get(
                    title="ماشین اصلاح خط‌زن طرح‌دار طلایی (نمونه)"
                )
                engraved_images = ProductImages.objects.filter(
                    product=engraved_product
                ).order_by("images")
                self.assertEqual(engraved_images.count(), 24)
                self.assertTrue(
                    (
                        Path(media_root)
                        / "store-samples"
                        / "360"
                        / "gold-engraved-trimmer"
                        / "frame-24.webp"
                    ).is_file()
                )
                engraved_detail = self.client.get(
                    reverse("core:product-detail", args=[engraved_product.pid])
                )
                self.assertContains(engraved_detail, "data-spin-viewer")
                self.assertContains(engraved_detail, "gold-engraved-trimmer/frame-01.webp")
                self.assertContains(engraved_detail, "ماشین اصلاح خط‌زن طرح‌دار طلایی")
                self.assertContains(
                    engraved_detail,
                    f'<img data-gallery-main data-gallery-original-src="{engraved_product.image.url}"',
                )
                self.assertNotContains(engraved_detail, "dsp-gold-clipper/frame-01.webp")

                kemei_product = Product.objects.get(
                    title="ماشین اصلاح Kemei مدل KM-1698 (نمونه)"
                )
                kemei_images = ProductImages.objects.filter(
                    product=kemei_product
                ).order_by("images")
                self.assertEqual(kemei_images.count(), 24)
                self.assertTrue(
                    (
                        Path(media_root)
                        / "store-samples"
                        / "360"
                        / "kemei-km1698"
                        / "frame-24.webp"
                    ).is_file()
                )
                kemei_detail = self.client.get(
                    reverse("core:product-detail", args=[kemei_product.pid])
                )
                self.assertContains(kemei_detail, "data-spin-viewer")
                self.assertContains(kemei_detail, "kemei-km1698/frame-01.webp")
                self.assertContains(kemei_detail, "Kemei مدل KM-1698")
                self.assertContains(
                    kemei_detail,
                    f'<img data-gallery-main data-gallery-original-src="{kemei_product.image.url}"',
                )

                styling_product = Product.objects.get(
                    title="حالت‌دهندهٔ مو مدل موج 360 (نمونه)"
                )
                styling_detail = self.client.get(
                    reverse("core:product-detail", args=[styling_product.pid])
                )
                self.assertContains(
                    styling_detail,
                    f'<img data-gallery-main data-gallery-original-src="{styling_product.image.url}"',
                )

        response = self.client.get(reverse("core:index"))
        self.assertContains(response, "تازه‌ترین محصولات فروشگاه")
        visible_sample_products = [
            item
            for item in SAMPLE_STORE_PRODUCTS
            if item["title"] in response.content.decode()
        ]
        self.assertTrue(visible_sample_products)
        # The demo labels moved from the homepage slider to the catalogue pages;
        # they still have to be visible wherever sample products are listed.
        catalogue = self.client.get(reverse("core:product-list"))
        self.assertContains(catalogue, "نمونهٔ نمایشی")
        self.assertContains(catalogue, "قیمت و موجودی فرضی‌اند")
        for item in visible_sample_products:
            with self.subTest(sample_title=item["title"]):
                self.assertContains(response, item["image"])
        for item in SAMPLE_STORE_PRODUCTS:
            with self.subTest(sample_title=item["title"]):
                self.assertIn(
                    "عکس این کالا برای پیش‌نمایش فروشگاه است",
                    Product.objects.get(title=item["title"]).description,
                )
        for image_name in {
            Path(item["image"]).name for item in HOME_CATEGORIES
        }:
            with self.subTest(category_image=image_name):
                self.assertContains(response, image_name)
        self.assertNotContains(response, "کادویی")
        self.assertEqual(
            response.context["products"].count(),
            min(len(SAMPLE_STORE_PRODUCTS), 12),
        )

        straightener_search = self.client.get(
            reverse("core:search"),
            {"q": "اتو مو"},
        )
        self.assertEqual(straightener_search.context["products"].count(), 3)

        sample_product = Product.objects.get(
            title="ریش‌تراش شارژی سری آرامیس (نمونه)"
        )
        legacy_add_response = self.client.get(
            reverse("core:add-to-cart"),
            {"id": sample_product.id, "qty": 1},
        )
        self.assertEqual(legacy_add_response.status_code, 405)
        add_to_cart_response = self.client.post(
            reverse("core:add-to-cart"),
            {"id": sample_product.id, "qty": 1},
        )
        self.assertEqual(add_to_cart_response.status_code, 200)
        self.assertEqual(
            self.client.session["cart_data_obj"][str(sample_product.id)]["qty"],
            1,
        )

    def test_homepage_renders_personal_care_categories(self):
        response = self.client.get(reverse("core:index"))

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "مراقبت از خودت")
        for category in HOME_CATEGORIES:
            with self.subTest(category=category["name"]):
                self.assertContains(response, category["name"])
        self.assertContains(response, "راهنمای خرید")
        self.assertContains(response, "09186555100")

    def test_homepage_uses_all_active_hero_banners_in_the_slider(self):
        HeroBanner.objects.create(
            title="پیشنهاد اول",
            button_label="دیدن پیشنهاد",
            button_url=reverse("core:search"),
        )
        HeroBanner.objects.create(
            title="پیشنهاد دوم",
            button_label="مشاهدهٔ کالاها",
            button_url=reverse("core:search"),
        )
        HeroBanner.objects.create(title="بنر غیرفعال", is_active=False)

        response = self.client.get(reverse("core:index"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'class="beauty-slider hm-hero swiper"')
        self.assertContains(response, "پیشنهاد اول")
        self.assertContains(response, "پیشنهاد دوم")
        self.assertNotContains(response, "بنر غیرفعال")
        self.assertContains(response, "همهٔ دسته‌بندی‌ها")
        self.assertContains(
            response,
            'class="hm-hero__cta" href="/search/"',
            count=2,
        )

    def test_homepage_shows_published_relevant_products(self):
        product = Product.objects.create(
            title="سشوار سرامیکی",
            product_status="published",
            status=True,
        )

        response = self.client.get(reverse("core:index"))

        self.assertContains(response, product.title)
        self.assertContains(response, reverse("core:product-detail", args=[product.pid]))

    def test_product_detail_uses_the_storefront_layout(self):
        product = Product.objects.create(
            title="ریش‌تراش برقی",
            price=1250000,
            product_status="published",
        )

        response = self.client.get(reverse("core:product-detail", args=[product.pid]))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "core/store-product-detail.html")
        self.assertContains(response, product.title)
        self.assertContains(response, "افزودن به سبد خرید")
        self.assertContains(response, "data-zoom-toggle")
        self.assertContains(response, "بزرگ‌نمایی تصویر محصول")
        self.assertContains(response, "data-image-zoom-dialog")
        self.assertContains(response, "برای دیدن عکس با وضوح اصلی")

    def test_category_pages_use_persian_storefront_templates(self):
        category = Category.objects.create(title="سشوار")
        Product.objects.create(
            title="سشوار سرامیکی",
            category=category,
            product_status="published",
        )

        category_list = self.client.get(reverse("core:category-list"))
        category_products = self.client.get(
            reverse("core:category-product-list", args=[category.cid])
        )

        self.assertTemplateUsed(category_list, "core/store-category-list.html")
        self.assertTemplateUsed(category_products, "core/store-category-products.html")
        self.assertContains(category_products, "سشوار سرامیکی")

    def test_product_list_and_search_use_storefront_layout(self):
        product = Product.objects.create(
            title="ریش‌تراش شارژی",
            product_status="published",
            status=True,
        )

        product_list = self.client.get(reverse("core:product-list"))
        search_results = self.client.get(
            reverse("core:search"),
            {"q": "ریش‌تراش"},
        )

        self.assertTemplateUsed(product_list, "core/store-product-list.html")
        self.assertContains(product_list, product.title)
        self.assertTemplateUsed(search_results, "core/store-search.html")
        self.assertContains(search_results, product.title)
        self.assertContains(search_results, "جست‌وجو")

    def test_empty_cart_displays_a_storefront_empty_state(self):
        response = self.client.get(reverse("core:cart"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "core/store-cart.html")
        self.assertContains(response, "سبد خریدت هنوز خالی است")

    def test_cart_renders_items_from_the_session(self):
        product = Product.objects.create(
            title="اتو مو سرامیکی",
            price=800000,
            product_status="published",
        )
        session = self.client.session
        session["cart_data_obj"] = {
            str(product.id): {
                "title": product.title,
                "qty": "2",
                "price": "800000",
                "image": product.image.url,
                "pid": product.pid,
            }
        }
        session.save()

        response = self.client.get(reverse("core:cart"))

        self.assertContains(response, product.title)
        self.assertContains(response, "1,600,000")
        self.assertContains(response, "2 عدد")
        self.assertEqual(response.context["cart_item_count"], 2)

    def test_cart_refreshes_price_and_product_details_from_the_database(self):
        product = Product.objects.create(
            title="سشوار سرامیکی به‌روز",
            price=1000000,
            product_status="published",
            status=True,
            in_stock=True,
        )
        session = self.client.session
        session["cart_data_obj"] = {
            str(product.id): {
                "title": "نام دست‌کاری‌شده",
                "qty": "2",
                "price": "1",
                "image": "/fake-image.jpg",
                "pid": "fake",
            }
        }
        session.save()
        product.price = 1250000
        product.save()

        response = self.client.get(reverse("core:cart"))

        self.assertContains(response, product.title)
        self.assertContains(response, "2,500,000")
        self.assertNotContains(response, "نام دست‌کاری‌شده")
        self.assertEqual(
            self.client.session["cart_data_obj"][str(product.id)]["price"],
            "1250000",
        )

    def test_cart_quantity_update_and_remove_require_post(self):
        product = Product.objects.create(
            title="اتو مو قابل سفارش",
            price=700000,
            product_status="published",
            status=True,
            in_stock=True,
        )
        session = self.client.session
        session["cart_data_obj"] = {
            str(product.id): {
                "title": product.title,
                "qty": 1,
                "price": "700000",
                "image": "",
                "pid": product.pid,
            }
        }
        session.save()

        update_url = reverse("core:update-cart")
        delete_url = reverse("core:delete-from-cart")
        self.assertEqual(self.client.get(update_url, {"id": product.id, "qty": 3}).status_code, 405)
        update_response = self.client.post(update_url, {"id": product.id, "qty": 3})
        self.assertEqual(update_response.status_code, 200)
        self.assertEqual(update_response.json()["totalcartitems"], 3)
        self.assertEqual(self.client.session["cart_data_obj"][str(product.id)]["qty"], 3)

        delete_response = self.client.post(delete_url, {"id": product.id})
        self.assertEqual(delete_response.status_code, 200)
        self.assertEqual(delete_response.json()["totalcartitems"], 0)
        self.assertEqual(self.client.session["cart_data_obj"], {})

    def test_add_to_cart_uses_database_price_and_product_details(self):
        product = Product.objects.create(
            title="سشوار حرفه‌ای",
            price=950000,
            product_status="published",
            status=True,
        )

        response = self.client.post(
            reverse("core:add-to-cart"),
            {
                "id": product.id,
                "pid": "tampered",
                "title": "کالای ساختگی",
                "price": "1",
                "image": "/fake-image.jpg",
                "qty": "2",
            },
        )

        self.assertEqual(response.status_code, 200)
        cart_item = self.client.session["cart_data_obj"][str(product.id)]
        self.assertEqual(cart_item["title"], product.title)
        self.assertEqual(cart_item["price"], "950000")
        self.assertEqual(cart_item["pid"], product.pid)
        self.assertEqual(cart_item["qty"], 2)

    def test_sample_products_can_use_demo_cart_and_checkout_without_real_payment(self):
        product = Product.objects.create(
            title="ماشین اصلاح نمونه (نمونه)",
            price=1900000,
            product_status="published",
            status=True,
            in_stock=False,
        )
        add_response = self.client.post(
            reverse("core:add-to-cart"),
            {"id": product.id, "qty": 2},
        )

        self.assertEqual(add_response.status_code, 200)
        self.assertEqual(add_response.json()["totalcartitems"], 2)
        self.assertEqual(
            self.client.session["cart_data_obj"][str(product.id)]["price"],
            "1900000",
        )
        cart_response = self.client.get(reverse("core:cart"))
        self.assertTrue(cart_response.context["has_demo_items"])
        self.assertContains(cart_response, "قیمت نمایشی واحد")
        self.assertContains(cart_response, "قیمت کالاهای نمونه فرضی است")

        update_response = self.client.post(
            reverse("core:update-cart"),
            {"id": product.id, "qty": 3},
        )
        self.assertEqual(update_response.status_code, 200)
        self.assertEqual(update_response.json()["totalcartitems"], 3)

        user = get_user_model().objects.create_user(
            username="demo-sample-customer",
            password="test-password",
        )
        self.client.force_login(user)
        checkout_response = self.client.post(
            reverse("core:save_checkout_info"),
            {
                "full_name": "مشتری آزمایشی",
                "email": "demo-sample@example.com",
                "mobile": "09186555100",
                "address": "نشانی آزمایشی",
                "city": "بانه",
                "state": "کردستان",
                "country": "ایران",
            },
        )

        order = CartOrder.objects.get(user=user)
        self.assertRedirects(checkout_response, reverse("core:checkout", args=[order.oid]))
        self.assertEqual(order.price, 5700000)
        self.assertFalse(order.paid_status)
        order_item = CartOrderProducts.objects.get(order=order)
        self.assertEqual(order_item.qty, 3)
        self.assertEqual(order_item.price, 1900000)
        self.assertEqual(self.client.session["cart_data_obj"], {})

        review_response = self.client.get(reverse("core:checkout", args=[order.oid]))
        self.assertTrue(review_response.context["has_demo_items"])
        self.assertContains(review_response, "قیمت‌ها فرضی‌اند")
        self.assertContains(review_response, "قیمت نمایشی")

        demo_response = self.client.post(
            reverse("core:payment-demo", args=[order.oid])
        )
        self.assertContains(demo_response, "هیچ مبلغی دریافت نمی‌شود")
        self.assertContains(demo_response, "برای ارسال واقعی ثبت نشده است")
        order.refresh_from_db()
        self.assertFalse(order.paid_status)

    def test_authenticated_cart_submission_creates_unpaid_order(self):
        user_model = get_user_model()
        user = user_model.objects.create_user(username="checkout-customer", password="test-pass")
        product = Product.objects.create(
            title="اتو مو حرفه‌ای",
            price=800000,
            product_status="published",
            status=True,
        )
        session = self.client.session
        session["cart_data_obj"] = {
            str(product.id): {
                "title": "نام و قیمت جعلی",
                "qty": "2",
                "price": "1",
                "image": product.image.url,
                "pid": "fake",
            }
        }
        session.save()
        self.client.force_login(user)

        response = self.client.post(
            reverse("core:save_checkout_info"),
            {
                "full_name": "آزمون کاربر",
                "email": "checkout@example.com",
                "mobile": "09186555100",
                "address": "نشانی آزمایشی",
                "city": "بانه",
                "state": "کردستان",
                "country": "ایران",
            },
        )

        order = CartOrder.objects.get(user=user)
        self.assertRedirects(response, reverse("core:checkout", args=[order.oid]))
        self.assertEqual(order.price, 1600000)
        self.assertFalse(order.paid_status)
        self.assertEqual(CartOrderProducts.objects.filter(order=order).count(), 1)
        order_item = CartOrderProducts.objects.get(order=order)
        self.assertEqual(order_item.item, product.title)
        self.assertEqual(order_item.price, 800000)
        self.assertEqual(self.client.session["cart_data_obj"], {})
        checkout_page = self.client.get(reverse("core:checkout", args=[order.oid]))
        self.assertTemplateUsed(checkout_page, "core/store-checkout.html")
        self.assertContains(checkout_page, "پرداخت آزمایشی")

    def test_checkout_rejects_unavailable_products_in_the_session_cart(self):
        user_model = get_user_model()
        user = user_model.objects.create_user(username="unavailable-customer")
        product = Product.objects.create(
            title="سشوار ناموجود",
            price=900000,
            product_status="published",
            status=True,
            in_stock=False,
        )
        session = self.client.session
        session["cart_data_obj"] = {
            str(product.id): {
                "title": product.title,
                "qty": 1,
                "price": "900000",
                "image": "",
                "pid": product.pid,
            }
        }
        session.save()
        self.client.force_login(user)

        add_response = self.client.post(
            reverse("core:add-to-cart"),
            {"id": product.id, "qty": 1},
        )
        self.assertEqual(add_response.status_code, 404)

        response = self.client.post(
            reverse("core:save_checkout_info"),
            {
                "full_name": "آزمون کاربر",
                "email": "checkout@example.com",
                "mobile": "09186555100",
                "address": "نشانی آزمایشی",
                "city": "بانه",
                "state": "کردستان",
                "country": "ایران",
            },
        )

        self.assertRedirects(response, reverse("core:cart"))
        self.assertFalse(CartOrder.objects.filter(user=user).exists())

    def test_demo_payment_never_marks_order_as_paid(self):
        user_model = get_user_model()
        user = user_model.objects.create_user(username="demo-customer", password="test-pass")
        order = CartOrder.objects.create(user=user, price=1250000)
        self.client.force_login(user)
        demo_url = reverse("core:payment-demo", args=[order.oid])

        response = self.client.post(demo_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "هیچ مبلغی دریافت نمی‌شود")
        order.refresh_from_db()
        self.assertFalse(order.paid_status)

    def test_payment_return_does_not_mark_order_paid_without_confirmation(self):
        user_model = get_user_model()
        user = user_model.objects.create_user(username="pending-customer", password="test-pass")
        order = CartOrder.objects.create(user=user, price=1250000)
        self.client.force_login(user)

        response = self.client.get(
            reverse("core:payment-completed", args=[order.oid]),
        )

        self.assertRedirects(response, reverse("core:checkout", args=[order.oid]))
        order.refresh_from_db()
        self.assertFalse(order.paid_status)

    def test_consultation_form_rejects_missing_required_fields(self):
        response = self.client.post(
            reverse("core:ajax-contact-form"),
            data={"full_name": "", "phone": "", "message": ""},
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["status"], "error")
        self.assertEqual(ContactUs.objects.count(), 0)

    def test_consultation_form_saves_request_and_normalizes_phone(self):
        response = self.client.post(
            reverse("core:ajax-contact-form"),
            data={
                "full_name": "نازنین احمدی",
                "phone": "0918 655 5100",
                "email": "",
                "subject": "",
                "message": "برای خرید سشوار راهنمایی می‌خواهم.",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "success")
        contact = ContactUs.objects.get(full_name="نازنین احمدی")
        self.assertEqual(contact.phone, "09186555100")
        self.assertEqual(contact.subject, "درخواست مشاوره خرید")


class StorefrontCompletionTests(TestCase):
    def test_demo_data_command_is_repeatable_and_installs_banner_image(self):
        with tempfile.TemporaryDirectory() as media_root:
            with override_settings(MEDIA_ROOT=Path(media_root)):
                HeroBanner.objects.create(
                    title="مراقبت روزانه، با انتخاب دقیق",
                    eyebrow="Hazhirmarket · انتخاب آگاهانه",
                )
                call_command("load_demo_data", verbosity=0)
                FAQ.objects.filter(question="چطور محصول مناسب خودم را انتخاب کنم؟").update(
                    answer="پاسخ ویرایش‌شده توسط مدیر"
                )
                StoreTrustFeature.objects.filter(title="انتخاب شفاف").update(
                    description="متن ویرایش‌شده توسط مدیر"
                )
                HeroBanner.objects.filter(
                    title="ابزارهای مراقبت شخصی مردانه"
                ).update(description="توضیح ویرایش‌شده توسط مدیر")
                ProductBundle.objects.filter(slug="daily-grooming-set").update(
                    title="پک ویرایش‌شده توسط مدیر"
                )
                call_command("load_demo_data", verbosity=0)

                banner = HeroBanner.objects.get(title="ابزارهای مراقبت شخصی مردانه")
                banner_image = Path(media_root) / banner.image.name
                self.assertTrue(banner_image.is_file())
                self.assertEqual(banner.eyebrow, "")
                self.assertEqual(FAQ.objects.count(), 4)
                self.assertEqual(StoreTrustFeature.objects.count(), 3)
                self.assertEqual(ProductBundle.objects.count(), 1)
                self.assertEqual(
                    FAQ.objects.get(question="چطور محصول مناسب خودم را انتخاب کنم؟").answer,
                    "پاسخ ویرایش‌شده توسط مدیر",
                )
                self.assertEqual(
                    StoreTrustFeature.objects.get(title="انتخاب شفاف").description,
                    "متن ویرایش‌شده توسط مدیر",
                )
                self.assertEqual(banner.description, "توضیح ویرایش‌شده توسط مدیر")
                self.assertEqual(
                    ProductBundle.objects.get(slug="daily-grooming-set").title,
                    "پک ویرایش‌شده توسط مدیر",
                )

                response = self.client.get(reverse("core:index"))
                self.assertContains(response, banner.image.url)
                self.assertContains(response, "پک ویرایش‌شده توسط مدیر")


class CustomerDashboardTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="dashboard-customer",
            email="dashboard-customer@example.com",
            password="safe-dashboard-password",
        )
        self.client.force_login(self.user)

    def test_dashboard_renders_account_sections_and_only_customers_orders(self):
        own_order = CartOrder.objects.create(
            user=self.user,
            email=self.user.email,
            price=1250000,
        )
        other_user = get_user_model().objects.create_user(
            username="another-dashboard-customer",
            email="another-dashboard-customer@example.com",
            password="safe-dashboard-password",
        )
        CartOrder.objects.create(user=other_user, price=999000)

        response = self.client.get(reverse("core:dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="dashboard"')
        self.assertContains(response, 'id="orders"')
        self.assertContains(response, 'id="track-orders"')
        self.assertContains(response, 'id="address"')
        self.assertContains(response, 'id="account-detail"')
        self.assertContains(response, str(own_order.oid))
        self.assertNotContains(response, "999000")
        self.assertNotContains(response, "page-login.html")

    def test_dashboard_saves_account_details_and_preserves_password_session(self):
        account_response = self.client.post(
            reverse("core:dashboard"),
            {
                "form_type": "account",
                "first_name": "هانی",
                "last_name": "آزمایشی",
                "username": self.user.username,
                "email": self.user.email,
            },
        )
        self.assertRedirects(
            account_response,
            f"{reverse('core:dashboard')}#account-detail",
        )
        self.user.refresh_from_db()
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.first_name, "هانی")

        profile_response = self.client.post(
            reverse("core:dashboard"),
            {
                "form_type": "profile",
                "full_name": "هانی آزمایشی",
                "bio": "خریدار هژیر مارکت",
                "phone": "09120000000",
            },
        )
        self.assertRedirects(
            profile_response,
            f"{reverse('core:dashboard')}#account-detail",
        )
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.full_name, "هانی آزمایشی")
        self.assertEqual(self.user.profile.phone, "09120000000")
        self.assertEqual(self.user.profile.bio, "خریدار هژیر مارکت")

        password_response = self.client.post(
            reverse("core:dashboard"),
            {
                "form_type": "password",
                "old_password": "safe-dashboard-password",
                "new_password1": "updated-dashboard-password-2026!",
                "new_password2": "updated-dashboard-password-2026!",
            },
        )
        self.assertRedirects(
            password_response,
            f"{reverse('core:dashboard')}#account-detail",
        )
        self.assertTrue(self.client.session.get("_auth_user_id"))
        self.user.refresh_from_db()
        self.assertTrue(
            self.user.check_password("updated-dashboard-password-2026!")
        )

    def test_dashboard_creates_first_default_address_and_changes_it_safely(self):
        create_response = self.client.post(
            reverse("core:dashboard"),
            {
                "form_type": "address",
                "address": "تهران، خیابان نمونه، پلاک ۱۰",
                "mobile": "09120000001",
            },
        )
        self.assertRedirects(create_response, f"{reverse('core:dashboard')}#address")
        first_address = Address.objects.get(user=self.user)
        self.assertTrue(first_address.status)

        second_address = Address.objects.create(
            user=self.user,
            address="تهران، نشانی دوم",
            mobile="09120000002",
        )
        default_response = self.client.post(
            reverse("core:make-default-address"),
            {"id": second_address.id},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertJSONEqual(default_response.content, {"boolean": True})
        first_address.refresh_from_db()
        second_address.refresh_from_db()
        self.assertFalse(first_address.status)
        self.assertTrue(second_address.status)

        another_user = get_user_model().objects.create_user(
            username="address-owner",
            email="address-owner@example.com",
            password="safe-dashboard-password",
        )
        foreign_address = Address.objects.create(
            user=another_user,
            address="نشانی خصوصی",
            mobile="09120000003",
        )
        forbidden_response = self.client.post(
            reverse("core:make-default-address"),
            {"id": foreign_address.id},
        )
        self.assertEqual(forbidden_response.status_code, 404)
        second_address.refresh_from_db()
        self.assertTrue(second_address.status)

    def test_dashboard_tracking_panel_shows_telegram_and_instagram_contacts(self):
        response = self.client.get(reverse("core:dashboard"))

        self.assertContains(
            response,
            "جهت پیگیری سفارشات به",
        )
        self.assertContains(response, "09186555100")
        self.assertContains(response, "hazhir.market")
        self.assertContains(response, 'href="https://t.me/+989186555100"')
        self.assertContains(
            response,
            'href="https://www.instagram.com/hazhir.market/"',
        )
        self.assertContains(
            response,
            'class="customer-dashboard__tracking-label">جهت پیگیری سفارشات به تلگرام ما (09186555100) و یا به اینستاگرام hazhir.market مراجعه فرمائید.</span>',
        )
        self.assertContains(response, 'id="track-title"')
        self.assertNotContains(response, "پیگیری آسان")
        self.assertNotContains(response, "> پیگیری سفارش</a>")
        self.assertContains(
            response,
            f'href="{reverse("core:dashboard")}#track-orders"',
        )
        self.assertNotContains(response, 'name="order_id"')

    def test_order_detail_is_private_to_the_order_owner(self):
        other_user = get_user_model().objects.create_user(
            username="private-order-owner",
            email="private-order-owner@example.com",
            password="safe-dashboard-password",
        )
        order = CartOrder.objects.create(user=other_user, price=1250000)

        response = self.client.get(
            reverse("core:order-detail", args=[order.id]),
        )

        self.assertEqual(response.status_code, 404)

    def test_robots_and_sitemap_resolve_public_urls(self):
        product = Product.objects.create(
            title="سشوار حرفه‌ای برای نقشه",
            product_status="published",
            status=True,
        )

        robots_response = self.client.get(reverse("robots-txt"))
        self.assertEqual(robots_response.status_code, 200)
        self.assertTrue(robots_response["Content-Type"].startswith("text/plain"))
        self.assertIn("User-agent: *", robots_response.content.decode())
        self.assertIn("Sitemap: http://testserver/sitemap.xml", robots_response.content.decode())

        sitemap_response = self.client.get(
            reverse("sitemap"),
            {"section": "products"},
        )
        self.assertEqual(sitemap_response.status_code, 200)
        self.assertContains(
            sitemap_response,
            reverse("core:product-detail", args=[product.pid]),
        )

    def test_product_detail_has_product_schema_and_canonical_url(self):
        product = Product.objects.create(
            title="سشوار حرفه‌ای سئو",
            description="توضیح محصول برای دادهٔ ساختاریافته",
            price=250000,
            product_status="published",
            status=True,
        )

        response = self.client.get(
            reverse("core:product-detail", args=[product.pid]),
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '"@type":"Product"')
        self.assertContains(response, '"priceCurrency":"IRR"')
        self.assertContains(
            response,
            f'<link rel="canonical" href="http://testserver{reverse("core:product-detail", args=[product.pid])}">',
            html=True,
        )

    def test_unapproved_reviews_are_hidden_until_approved(self):
        user = get_user_model().objects.create_user(username="reviewer")
        product = Product.objects.create(
            title="ریش‌تراش قابل بررسی",
            product_status="published",
            status=True,
        )
        review = ProductReview.objects.create(
            user=user,
            product=product,
            review="نظر در انتظار بررسی",
            rating=5,
        )

        detail_url = reverse("core:product-detail", args=[product.pid])
        self.assertNotContains(self.client.get(detail_url), "نظر در انتظار بررسی")
        self.assertNotContains(self.client.get(reverse("core:index")), "نظر در انتظار بررسی")

        review.is_approved = True
        review.save(update_fields=["is_approved"])
        self.assertContains(self.client.get(detail_url), "نظر در انتظار بررسی")
        self.assertContains(self.client.get(reverse("core:index")), "نظر در انتظار بررسی")

    def test_checkout_does_not_call_zarinpal_without_merchant_id(self):
        user = get_user_model().objects.create_user(username="merchant-not-configured")
        order = CartOrder.objects.create(user=user, price=1250000)
        self.client.force_login(user)

        with override_settings(ZARINPAL_MERCHANT_ID=""), patch(
            "core.views.create_payment"
        ) as create_payment:
            response = self.client.post(
                reverse("core:checkout", args=[order.oid]),
                {"action": "pay"},
            )

        self.assertEqual(response.status_code, 302)
        self.assertFalse(create_payment.called)
        self.assertFalse(PaymentAttempt.objects.filter(order=order).exists())

    def test_checkout_creates_payment_attempt_with_rial_amount(self):
        user = get_user_model().objects.create_user(username="merchant-configured")
        order = CartOrder.objects.create(user=user, price=1250000)
        self.client.force_login(user)

        with override_settings(ZARINPAL_MERCHANT_ID="merchant-id"), patch(
            "core.views.create_payment",
            return_value={
                "authority": "A00000000000000000000000000123456789",
                "payment_url": "https://sandbox.zarinpal.com/pg/StartPay/A00000000000000000000000000123456789",
            },
        ) as create_payment:
            response = self.client.post(
                reverse("core:checkout", args=[order.oid]),
                {"action": "pay"},
            )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response["Location"],
            "https://sandbox.zarinpal.com/pg/StartPay/A00000000000000000000000000123456789",
        )
        create_payment.assert_called_once()
        attempt = PaymentAttempt.objects.get(order=order)
        self.assertEqual(attempt.amount_rial, 12500000)
        self.assertEqual(attempt.status, "pending")

    def test_zarinpal_callback_verifies_and_marks_order_paid(self):
        user = get_user_model().objects.create_user(username="verified-customer")
        order = CartOrder.objects.create(user=user, price=1250000)
        attempt = PaymentAttempt.objects.create(
            order=order,
            authority="A00000000000000000000000000987654321",
            amount_rial=12500000,
        )

        with override_settings(
            ZARINPAL_MERCHANT_ID="merchant-id",
            ZARINPAL_SANDBOX=True,
        ), patch(
            "core.views.verify_payment",
            return_value={"ref_id": "123456", "already_verified": False},
        ) as verify_payment:
            response = self.client.get(
                reverse("core:zarinpal-callback", args=[order.oid]),
                {
                    "Authority": attempt.authority,
                    "Status": "OK",
                },
            )

        self.assertRedirects(
            response,
            reverse("core:payment-completed", args=[order.oid]),
            fetch_redirect_response=False,
        )
        verify_payment.assert_called_once()
        order.refresh_from_db()
        attempt.refresh_from_db()
        self.assertTrue(order.paid_status)
        self.assertEqual(attempt.status, "paid")
        self.assertEqual(attempt.ref_id, "123456")

    def test_zarinpal_cancel_callback_fails_attempt_without_verification(self):
        user = get_user_model().objects.create_user(username="canceled-customer")
        order = CartOrder.objects.create(user=user, price=1250000)
        attempt = PaymentAttempt.objects.create(
            order=order,
            authority="A00000000000000000000000000123400001",
            amount_rial=12500000,
        )

        with patch("core.views.verify_payment") as verify_payment:
            response = self.client.get(
                reverse("core:zarinpal-callback", args=[order.oid]),
                {
                    "Authority": attempt.authority,
                    "Status": "NOK",
                },
            )

        self.assertEqual(response.status_code, 200)
        verify_payment.assert_not_called()
        attempt.refresh_from_db()
        order.refresh_from_db()
        self.assertEqual(attempt.status, "failed")
        self.assertFalse(order.paid_status)


class ProgressiveWebAppTests(TestCase):
    def test_service_worker_uses_root_scope_and_keeps_private_pages_uncached(self):
        response = self.client.get(reverse("core:service-worker"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/javascript; charset=utf-8")
        self.assertEqual(response["Service-Worker-Allowed"], "/")
        worker = response.content.decode()
        self.assertIn('request.mode === "navigate"', worker)
        self.assertIn("caches.match(OFFLINE_PAGE)", worker)
        navigation_handler = worker.split('if (request.mode === "navigate") {', 1)[1]
        navigation_handler = navigation_handler.split("const isStaticAsset", 1)[0]
        self.assertNotIn("cache.put", navigation_handler)

    def test_zarinpal_verification_error_does_not_mark_order_paid(self):
        user = get_user_model().objects.create_user(username="unverified-customer")
        order = CartOrder.objects.create(user=user, price=1250000)
        attempt = PaymentAttempt.objects.create(
            order=order,
            authority="A00000000000000000000000000123400002",
            amount_rial=12500000,
        )

        with override_settings(ZARINPAL_MERCHANT_ID="merchant-id"), patch(
            "core.views.verify_payment",
            side_effect=ZarinpalError("درگاه پرداخت در دسترس نیست."),
        ):
            response = self.client.get(
                reverse("core:zarinpal-callback", args=[order.oid]),
                {
                    "Authority": attempt.authority,
                    "Status": "OK",
                },
            )

        self.assertEqual(response.status_code, 502)
        attempt.refresh_from_db()
        order.refresh_from_db()
        self.assertEqual(attempt.status, "pending")
        self.assertFalse(order.paid_status)

    def test_paid_zarinpal_callback_is_idempotent(self):
        user = get_user_model().objects.create_user(username="already-paid-customer")
        order = CartOrder.objects.create(
            user=user,
            price=1250000,
            paid_status=True,
        )
        attempt = PaymentAttempt.objects.create(
            order=order,
            authority="A00000000000000000000000000123400003",
            amount_rial=12500000,
            ref_id="123456",
            status="paid",
        )

        with patch("core.views.verify_payment") as verify_payment:
            response = self.client.get(
                reverse("core:zarinpal-callback", args=[order.oid]),
                {
                    "Authority": attempt.authority,
                    "Status": "OK",
                },
            )

        self.assertRedirects(
            response,
            reverse("core:payment-completed", args=[order.oid]),
            fetch_redirect_response=False,
        )
        verify_payment.assert_not_called()
