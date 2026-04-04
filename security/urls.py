from django.urls import path
from . import views

app_name = 'security'

urlpatterns = [
    # Dashboard
    path('security/', views.dashboard, name='dashboard'),

    # Analytics
    path('security/analytics/', views.analytics, name='analytics'),

    # Custody
    path('security/custody/', views.custody_list, name='custody_list'),
    path('security/custody/<int:pk>/', views.custody_detail, name='custody_detail'),
    path('security/custody/<int:pk>/transfer/', views.transfer_custody, name='transfer_custody'),
    path('security/items/<int:pk>/receive/', views.receive_item, name='receive_item'),

    # Claims
    path('security/claims/', views.all_claims, name='all_claims'),
    path('security/claims/<int:pk>/', views.claim_detail, name='claim_detail'),
    path('security/claims/<int:pk>/review/', views.review_claim, name='review_claim'),
    path('security/claims/<int:pk>/handover/', views.process_handover, name='process_handover'),

    # Student claim submission & QR collection
    path('items/<int:pk>/claim/', views.submit_claim, name='submit_claim'),
    path('security/handover-qr/<uuid:token>/', views.my_handover_qr, name='handover_qr'),

    # Item status override
    path('security/items/<int:pk>/status/', views.update_item_status, name='update_item_status'),

    # Staff management (superuser only)
    path('security/staff/', views.staff_list, name='staff_list'),
    path('security/staff/<int:pk>/deactivate/', views.deactivate_staff, name='deactivate_staff'),
    path('security/staff/<int:pk>/reactivate/', views.reactivate_staff, name='reactivate_staff'),

    # Incidents
    path('security/incidents/', views.incident_list, name='incident_list'),
    path('security/incidents/log/', views.log_incident, name='log_incident'),
    path('security/incidents/log/item/<int:item_pk>/', views.log_incident, name='log_incident_item'),
    path('security/incidents/log/claim/<int:claim_pk>/', views.log_incident, name='log_incident_claim'),
]
