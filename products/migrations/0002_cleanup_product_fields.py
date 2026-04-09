import uuid

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("products", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="ColorVariant",
            fields=[
                ("uid", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now=True)),
                ("updated_at", models.DateTimeField(auto_now_add=True)),
                ("color_name", models.CharField(max_length=100)),
                ("price", models.IntegerField(default=0)),
            ],
            options={
                "abstract": False,
            },
        ),
        migrations.CreateModel(
            name="SizeVariant",
            fields=[
                ("uid", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now=True)),
                ("updated_at", models.DateTimeField(auto_now_add=True)),
                ("size_name", models.CharField(max_length=100)),
                ("price", models.IntegerField(default=0)),
            ],
            options={
                "abstract": False,
            },
        ),
        migrations.RemoveField(
            model_name="product",
            name="ription",
        ),
        migrations.AddField(
            model_name="product",
            name="color_variant",
            field=models.ManyToManyField(blank=True, to="products.colorvariant"),
        ),
        migrations.AddField(
            model_name="product",
            name="size_variant",
            field=models.ManyToManyField(blank=True, to="products.sizevariant"),
        ),
        migrations.AlterField(
            model_name="category",
            name="category_image",
            field=models.ImageField(upload_to="catgories"),
        ),
        migrations.AlterField(
            model_name="product",
            name="category",
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="products", to="products.category"),
        ),
        migrations.RenameField(
            model_name="productimage",
            old_name="Product",
            new_name="product",
        ),
        migrations.AlterField(
            model_name="productimage",
            name="image",
            field=models.ImageField(upload_to="product"),
        ),
    ]
