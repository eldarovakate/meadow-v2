import json

from django.db import migrations


def clear_featured_products(apps, schema_editor):
    with schema_editor.connection.cursor() as cursor:
        cursor.execute("SELECT page_ptr_id, body FROM home_homepage")
        rows = cursor.fetchall()
        for page_id, raw in rows:
            if not raw:
                continue
            data = json.loads(raw)
            changed = False
            for block in data:
                if block.get('type') == 'featured_products':
                    products = block.get('value', {}).get('products')
                    if isinstance(products, list) and any(
                        isinstance(item.get('value'), dict) for item in products
                    ):
                        block['value']['products'] = []
                        changed = True
            if changed:
                cursor.execute(
                    "UPDATE home_homepage SET body = %s WHERE page_ptr_id = %s",
                    [json.dumps(data), page_id],
                )


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('home', '0003_alter_homepage_body'),
    ]

    operations = [
        migrations.RunPython(clear_featured_products, noop),
    ]
