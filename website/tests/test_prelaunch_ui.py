"""
Prelaunch announcement bar tests (TASK 2).

The bar is rendered from templates/base.html for every page in the shared
layout, so it's enough to check it through one already-fixtured page
(the catalog page from PaymentTestBase) rather than every single URL.
"""

import datetime

from django.test import override_settings
from wagtail.models import Site

from website.tests.test_payments import PaymentTestBase


@override_settings(SALES_OPEN_DATE=datetime.date(2026, 10, 1))
class AnnouncementBarTests(PaymentTestBase):
    """Checked through the catalog page: the bar itself lives in the shared
    base.html layout, so any page proves it renders site-wide."""

    def setUp(self):
        super().setUp()
        site = Site.objects.filter(is_default_site=True).first()
        if site:
            site.root_page = self.catalog.get_parent()
            site.save()
        else:
            Site.objects.create(
                hostname="testserver", root_page=self.catalog.get_parent(), is_default_site=True
            )

    @override_settings(SALES_MODE="preorder")
    def test_preorder_shows_announcement_bar_with_date(self):
        response = self.client.get(self.catalog.url)

        self.assertContains(response, 'class="announcement-bar"')
        self.assertContains(response, "Открытие продаж — 1 октября 2026 года")
        self.assertContains(response, "До открытия можно оформить предзаказ")

    @override_settings(SALES_MODE="sales")
    def test_sales_hides_announcement_bar(self):
        response = self.client.get(self.catalog.url)

        self.assertNotContains(response, "announcement-bar")
        self.assertNotContains(response, "has-announcement")
