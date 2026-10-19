from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from core.models import CartOrder, Category, Product


class AdminDashboardTests(TestCase):
    def setUp(self):
        self.admin = get_user_model().objects.create_user(
            username="dashboard-admin",
            email="dashboard-admin@example.com",
            password="test-only-password",
            is_staff=True,
            is_superuser=True,
        )
        self.category = Category.objects.create(title="سلامت")
        self.client.force_login(self.admin)

    def create_product(self, title, status="published", price=120000, stock="4"):
        return Product.objects.create(
            user=self.admin,
            category=self.category,
            title=title,
            product_status=status,
            price=price,
            stock_count=stock,
        )

    def test_dashboard_shows_database_backed_summary_and_persian_navigation(self):
        customer = get_user_model().objects.create_user(
            username="dashboard-customer",
            password="test-only-password",
        )
        Product.objects.create(
            user=self.admin,
            category=self.category,
            title="ماشین اصلاح",
            product_status="in_review",
        )
        CartOrder.objects.create(user=customer, price=230000, paid_status=True)
        CartOrder.objects.create(user=customer, price=90000, paid_status=False)

        response = self.client.get(reverse("useradmin:dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["product_count"], 1)
        self.assertEqual(response.context["orders_count"], 2)
        self.assertEqual(response.context["customer_count"], 1)
        self.assertEqual(response.context["revenue"]["price"], 230000)
        self.assertEqual(response.context["unpaid_orders_count"], 1)
        for label in (
            "داشبورد",
            "محصولات",
            "دسته‌بندی‌ها",
            "سفارش‌ها",
            "مشتریان",
            "تخفیف‌ها",
            "تنظیمات",
        ):
            with self.subTest(label=label):
                self.assertContains(response, label)
        self.assertContains(response, "آمار بر پایهٔ سفارش‌ها")

    def test_product_list_searches_filters_sorts_and_paginates(self):
        self.create_product("ماشین اصلاح سبز", status="published", price=300000, stock="2")
        self.create_product("سشوار کرم", status="draft", price=100000, stock="11")

        response = self.client.get(
            reverse("useradmin:dashboard-products"),
            {"q": "سبز", "category": str(self.category.pk), "status": "published", "sort": "price"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["total_products"], 1)
        self.assertContains(response, "ماشین اصلاح سبز")
        self.assertNotContains(response, "سشوار کرم")

        for index in range(13):
            self.create_product(f"محصول صفحه‌بندی {index:02d}")
        page_two = self.client.get(
            reverse("useradmin:dashboard-products"),
            {"page": "2", "sort": "-date"},
        )
        self.assertEqual(page_two.status_code, 200)
        self.assertEqual(page_two.context["page_obj"].number, 2)
        self.assertEqual(len(page_two.context["products"]), 3)

    def test_empty_filtered_product_list_has_a_clear_state(self):
        response = self.client.get(
            reverse("useradmin:dashboard-products"),
            {"q": "موردی که وجود ندارد"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "محصولی با این فیلترها پیدا نشد")

    def test_edit_product_form_uses_persian_labels_and_existing_product_fields(self):
        product = self.create_product("محصول برای ویرایش")

        response = self.client.get(
            reverse("useradmin:dashboard-edit-products", args=[product.pid])
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "ویرایش محصول")
        self.assertContains(response, "قیمت (تومان)")
        self.assertContains(response, "دسته‌بندی")
        self.assertContains(response, "وضعیت انتشار")
        self.assertContains(response, "ذخیره تغییرات")
        self.assertNotContains(response, "Add New Product")
        self.assertNotContains(response, "Product title")

    def test_product_delete_requires_post_and_deletes_after_confirmation(self):
        product = self.create_product("محصول برای حذف")
        delete_url = reverse("useradmin:dashboard-delete-products", args=[product.pid])

        self.assertEqual(self.client.get(delete_url).status_code, 405)
        response = self.client.post(delete_url)

        self.assertRedirects(response, reverse("useradmin:dashboard-products"))
        self.assertFalse(Product.objects.filter(pk=product.pk).exists())

    def test_bulk_delete_only_deletes_explicitly_selected_products(self):
        selected = self.create_product("حذف انتخاب‌شده")
        retained = self.create_product("محصول نگه‌داشته‌شده")

        response = self.client.post(
            reverse("useradmin:bulk-delete-products"),
            {"selected_products": [selected.pid]},
        )

        self.assertRedirects(response, reverse("useradmin:dashboard-products"))
        self.assertFalse(Product.objects.filter(pk=selected.pk).exists())
        self.assertTrue(Product.objects.filter(pk=retained.pk).exists())
