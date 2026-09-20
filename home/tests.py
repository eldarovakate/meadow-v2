import datetime
import json

from django.test import TestCase, override_settings
from wagtail.models import Page, Site

from home.models import HomePage


@override_settings(SALES_OPEN_DATE=datetime.date(2026, 10, 1))
class PrelaunchSectionTests(TestCase):
    """TASK 2: the homepage prelaunch section, gated on SALES_MODE."""

    def setUp(self):
        root = Page.objects.get(id=1)
        body = json.dumps([{"type": "hero", "value": {"headline": "Test Hero"}}])
        self.home = HomePage(title="Home", slug="home-test", body=body)
        root.add_child(instance=self.home)

        site = Site.objects.filter(is_default_site=True).first()
        if site:
            site.root_page = self.home
            site.save()
        else:
            Site.objects.create(hostname="testserver", root_page=self.home, is_default_site=True)

    @override_settings(SALES_MODE="preorder")
    def test_preorder_shows_prelaunch_section_after_hero(self):
        response = self.client.get("/")

        self.assertContains(response, 'class="prelaunch">')
        self.assertContains(response, "Открытие продаж — 1 октября")
        self.assertNotContains(response, "предзаказ")
        self.assertNotContains(response, "Смотреть коллекцию")

        content = response.content.decode()
        self.assertLess(content.index("Test Hero"), content.index("prelaunch"))

    @override_settings(SALES_MODE="sales")
    def test_sales_hides_prelaunch_section(self):
        response = self.client.get("/")

        self.assertNotContains(response, "prelaunch")
