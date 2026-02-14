from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("products", "0012_orderitem_size_label_productsizevariant_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="ProductImage",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("image", models.ImageField(upload_to="products/extra/")),
                ("display_order", models.PositiveIntegerField(default=0)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("product", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="images", to="products.product")),
            ],
            options={
                "ordering": ["display_order", "id"],
            },
        ),
    ]
