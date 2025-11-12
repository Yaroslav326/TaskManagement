from django.urls import path
from . import views

app_name = 'company'
urlpatterns = [
    path('', views.lict_departments, name='list_departments'),
    path('profile/', views.company_profile_page, name='company_profile_page'),
    path('api/profile/', views.company_profile, name='company_profile'),
    path('api/create/', views.create_company, name='create_company'),
    path('api/update/', views.edit_company, name='update_company'),
    path('api/get-departments/', views.get_departments,
         name='get_departments'),
    path('api/create-department/', views.create_department,
         name='create_department'),
    path('api/edit-department/', views.edit_department,
         name='edit_department'),
    path('api/add-personnel/', views.add_personnel,
         name='add_personnel'),
    path('api/view-department/', views.view_department,
         name='view_department'),
    path('api/delete-department/', views.delete_department,
         name='delete_department'),
    path('api/remove-personnel/', views.remove_personnel,
         name='remove_personnel'),

]
