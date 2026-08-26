from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('website', '0008_order_payment_id'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='payment_idempotence_key',
            field=models.CharField(blank=True, max_length=64, verbose_name='Idempotence-Key платежа'),
        ),
    ]
