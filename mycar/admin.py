
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import Category, Customer, Product, Order, Profile
from django.contrib.auth.models import User

admin.site.register(Category)
admin.site.register(Customer)
admin.site.register(Product)
admin.site.register(Order)
admin.site.register(Profile)

# Mix profile info and user info
# --- Inline profile with User ---
class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False


# --- Extend the default Django UserAdmin ---
class UserAdmin(BaseUserAdmin):
    inlines = [ProfileInline]


# --- Replace default User admin ---
try:
    admin.site.unregister(User)
except admin.sites.NotRegistered:
    pass

admin.site.register(User, UserAdmin)





# class ProfileInline(admin.StackedInline):
#     model = Profile

# # Extend user model
# class UserAdmin(admin.ModelAdmin):
#     model = User
#     field = ["username", "first_name", "last_name", "email"]
#     inlines = [ProfileInline]

# # Unregister the old way
# admin.site.unregister(User)

# # Re register the new way
# admin.site.register(User, UserAdmin)