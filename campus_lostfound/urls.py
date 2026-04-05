from django.contrib import admin
from django.contrib.auth.views import PasswordResetView
from accounts.password_reset_utils import BrevoPasswordResetForm

_password_reset_view = PasswordResetView.as_view(
    form_class=BrevoPasswordResetForm,
    template_name='registration/password_reset_form.html',
    email_template_name='registration/password_reset_email.html',
    subject_template_name='registration/password_reset_subject.txt',
)
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import TemplateView

admin.site.site_header = "Campus Lost & Found Admin"
admin.site.site_title = "Campus Lost & Found"
admin.site.index_title = "Administration"

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('accounts.urls')),
    # Override password reset view to use Brevo API instead of SMTP
    path('accounts/password_reset/', _password_reset_view, name='password_reset'),
    path('accounts/', include('django.contrib.auth.urls')),
    path('', include('security.urls')),
    path('', include('items.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

handler404 = 'items.views.custom_404'
handler500 = 'items.views.custom_500'
