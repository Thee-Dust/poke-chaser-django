from django.contrib import admin

from pokechaser.binders.models import Binder, BinderPage, BinderSlot


class BinderPageInline(admin.TabularInline):
    model = BinderPage
    extra = 0


class BinderSlotInline(admin.TabularInline):
    model = BinderSlot
    extra = 0


@admin.register(Binder)
class BinderAdmin(admin.ModelAdmin):
    list_display = ["name", "user", "created_at"]
    inlines = [BinderPageInline]


@admin.register(BinderPage)
class BinderPageAdmin(admin.ModelAdmin):
    list_display = ["__str__", "order", "rows", "cols"]
    inlines = [BinderSlotInline]
