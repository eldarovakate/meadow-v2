"""По умолчанию внизу страницы товара — блок «По дороге» с главной (копия, дальше
редактируется независимо в Настройках). Заполняем только пустое поле, ничего не затираем."""

import json
import uuid

from django.db import migrations


def copy_statement_block(apps, schema_editor):
    HomePage = apps.get_model("home", "HomePage")
    SiteSettings = apps.get_model("website", "SiteSettings")
    Site = apps.get_model("wagtailcore", "Site")

    statement = None
    for home in HomePage.objects.all():
        for item in home.body.raw_data:
            if item.get("type") == "collection_statement":
                statement = dict(item)
                break
        if statement:
            break
    if not statement:
        return

    statement["id"] = str(uuid.uuid4())
    for site in Site.objects.all():
        settings_obj, _ = SiteSettings.objects.get_or_create(site=site)
        if len(settings_obj.product_page_blocks.raw_data) == 0:
            settings_obj.product_page_blocks = json.dumps([statement])
            settings_obj.save(update_fields=["product_page_blocks"])


class Migration(migrations.Migration):

    dependencies = [
        ("website", "0018_product_page_blocks"),
        ("home", "0020_alter_homepage_body"),
        ("wagtailcore", "0089_log_entry_data_json_null_to_object"),
    ]

    operations = [
        migrations.RunPython(copy_statement_block, migrations.RunPython.noop),
    ]
