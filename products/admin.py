from django.contrib import admin
from django.utils.html import format_html
from .models import Category, Product


# ========================
# ADMIN BRANDING
# ========================
admin.site.site_header = "vMall – Internal Admin"
admin.site.site_title = "vMall Admin"
admin.site.index_title = "Developer Control Panel"


# ========================
# CATEGORY ADMIN
# ========================
@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "is_active", "created_at")
    list_editable = ("is_active",)
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ("name",)
    list_filter = ("is_active",)
    ordering = ("name",)


# ========================
# PRODUCT ADMIN
# ========================
@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):

    # ---- VISUAL HELPERS ----
    def image_preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="width:60px;height:60px;object-fit:cover;border-radius:6px;" />',
                obj.image.url
            )
        return "—"
    image_preview.short_description = "Image"

    def stock_badge(self, obj):
       if obj.stock <= 5:
            return format_html(
                '<b style="color:{};">{}</b>',
               '#ef4444',
                'LOW'
        )
       elif obj.stock <= 20:
            return format_html(
               '<b style="color:{};">{}</b>',
              '#f97316',
              'MEDIUM'
        )
       else:
           return format_html(
              '<b style="color:{};">{}</b>',
             '#22c55e',
              'HIGH'
        )



    stock_badge.short_description = "Stock Level"

    def featured_badge(self, obj):
        if obj.featured:
           return format_html(
              '<span style="color:{};">⭐ {}</span>',
             '#ca8a04',
              'Featured'
        )
        return '—'

    # featured_badge.short_description = "Featured"

    def status_badge(self, obj):
      if obj.is_active:
        return format_html(
            '<span style="color:{};">{}</span>',
            '#16a34a',
            'Active'
        )
      return format_html(
        '<span style="color:{};">{}</span>',
        '#dc2626',
        'Inactive'
    )

    status_badge.short_description = "Status"


    def save_model(self, request, obj, form, change):
        if obj.offer_price and obj.offer_price >= obj.original_price:
           obj.offer_price = None
        super().save_model(request, obj, form, change)
 

    readonly_fields = ("created_at", "updated_at")

    # ---- LIST VIEW ----
    list_display = (
        "image_preview",
        "name",
        "category",
        "original_price",
        "offer_price",
        "stock",
        "stock_badge",
        "featured_badge",
        "status_badge",
    )

    list_editable = (
        "original_price",
        "offer_price",
    )

    list_filter = (
        "is_active",
        "featured",
        "category",
    )

    search_fields = ("name",)
    prepopulated_fields = {"slug": ("name",)}
    ordering = ("-created_at",)

    # ---- FORM VIEW ----
    fieldsets = (
        ("Basic Info", {
            "fields": (
                "name",
                "slug",
                "category",
                "image",
            )
        }),
        ("Pricing & Stock", {
            "fields": (
                "original_price",
                "offer_price",
                "stock",
            )
        }),
        ("Visibility", {
            "fields": (
                "featured",
                "is_active",
            )
        }),
        ("Description", {
            "fields": ("description",)
        }),
        ("System Info", {
           "fields": ("created_at", "updated_at")
        }),

    )

    # ---- SAFETY ----
    actions = None  # disables bulk delete
