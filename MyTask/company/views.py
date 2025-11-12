from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from rest_framework import authentication
from django.conf import settings
from authentication.models import User
from .models import Company, Department
import jwt
import json


def get_user_payload(request):
    try:
        auth_header = authentication.get_authorization_header(request).split()
        if len(auth_header) != 2:
            return None, JsonResponse({'error': 'Authorization header '
                                                'missing or malformed'},
                                      status=401)

        token = auth_header[1].decode('utf-8')
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])

        return payload, None

    except jwt.ExpiredSignatureError:
        return None, JsonResponse({'error': 'Token expired'}, status=401)
    except jwt.InvalidTokenError:
        return None, JsonResponse({'error': 'Invalid token'}, status=401)
    except Exception as e:
        return None, JsonResponse({'error': str(e)}, status=500)


def parse_json_body(request):
    try:
        return json.loads(request.body), None
    except json.JSONDecodeError:
        return {}, JsonResponse({'error': 'Invalid JSON'}, status=400)


def company_profile_page(request):
    """Возвращает HTML-страницу профиля компании"""
    return render(request, 'profile.html')


def lict_departments(request):
    return render(request, 'departments.html')


@csrf_exempt
@require_http_methods(["POST"])
def get_departments(request):
    payload, error = get_user_payload(request)
    if error:
        return error

    try:
        user = User.objects.get(id=payload['user_id'])
    except User.DoesNotExist:
        return JsonResponse({'error': 'User not found'}, status=404)

    all_departments = Department.objects.filter(
        company__in=Department.objects.filter(personnel=user).values('company')
    ).select_related('company').distinct()

    data = [
        {
            'id': dept.id,
            'name': dept.name,
            'company_name': dept.company.name
        }
        for dept in all_departments
    ]

    return JsonResponse({'departments': data}, status=200)


@csrf_exempt
@require_http_methods(["POST"])
def create_department(request):
    payload, error = get_user_payload(request)
    try:
        user = User.objects.get(id=payload['user_id'])
    except User.DoesNotExist:
        return JsonResponse({'error': 'User not found'}, status=404)

    data, error = parse_json_body(request)
    if error:
        return error

    name = data.get('name')

    company_id = Department.objects.filter(personnel=user).values_list(
        'company_id', flat=True).first()
    if not company_id:
        return JsonResponse({'error': 'User is not assigned to any company'},
                            status=403)

    try:
        department = Department.objects.create(
            name=name,
            company_id=company_id
        )
    except Exception as e:
        return JsonResponse({'error': f'Failed to create department:'
                                      f' {str(e)}'}, status=400)

    return JsonResponse({
        'department': {
            'id': department.id,
            'name': department.name,
            'company_name': department.company.name
        }
    }, status=201)


@csrf_exempt
@require_http_methods(["POST"])
def view_department(request):
    payload, error = get_user_payload(request)

    if error:
        return error

    try:
        user = User.objects.get(id=payload['user_id'])
    except User.DoesNotExist:
        return JsonResponse({'error': 'User not found'}, status=404)

    data, error = parse_json_body(request)

    if error:
        return error

    department_id = data.get('department_id')

    if not department_id:
        return JsonResponse({'error': 'Department ID is required'}, status=400)

    try:
        department = Department.objects.get(id=department_id)

    except Department.DoesNotExist:
        return JsonResponse({'error': 'Department not found'}, status=404)

    user_company_id = Department.objects.filter(personnel=user).values_list(
        'company_id', flat=True).first()

    if not user_company_id or department.company_id != user_company_id:
        return JsonResponse({'error': 'Permission denied'}, status=403)

    users = department.personnel.all().values('id', 'username', 'email')

    return JsonResponse({'users': list(users)}, status=200)


@csrf_exempt
@require_http_methods(["POST"])
def company_profile(request):
    payload, error = get_user_payload(request)
    if error:
        return error

    try:
        user = User.objects.get(id=payload['user_id'])
    except User.DoesNotExist:
        return JsonResponse({'error': 'User not found'}, status=404)

    company_id = Department.objects.filter(personnel=user).values_list(
        'company_id', flat=True).first()

    if company_id:
        company = Company.objects.get(id=company_id)
        return JsonResponse({
            'company': {
                'name': company.name,
                'owner': company.owner.username
            }
        }, status=200)

    else:
        return JsonResponse({
            'company': None
        }, status=200)


@csrf_exempt
@require_http_methods(["POST"])
def create_company(request):
    payload, error = get_user_payload(request)
    if error:
        return error

    try:
        user = User.objects.get(id=payload['user_id'])
    except User.DoesNotExist:
        return JsonResponse({'error': 'User not found'}, status=404)

    data, error = parse_json_body(request)
    if error:
        return error

    company_name = data.get('name')
    if not company_name:
        return JsonResponse({'error': 'Company name is required'},
                            status=400)

    existing_company = Department.objects.filter(personnel=user).exists()
    if existing_company:
        return JsonResponse({'error': 'You are already in a company'},
                            status=400)

    company = Company.objects.create(name=company_name, owner=user)

    department = Department.objects.create(name="Аппарат управления",
                                           company=company)
    department.personnel.add(user)

    return JsonResponse({
        'company': {
            'id': company.id,
            'name': company.name,
            'owner': user.username
        }
    }, status=201)


@csrf_exempt
@require_http_methods(["POST"])
def edit_company(request):
    payload, error = get_user_payload(request)
    if error:
        return error

    try:
        user = User.objects.get(id=payload['user_id'])
    except User.DoesNotExist:
        return JsonResponse({'error': 'User not found'}, status=404)

    data, error = parse_json_body(request)
    if error:
        return error

    company_id = Department.objects.filter(personnel=user).values_list(
        'company_id', flat=True).first()

    if not company_id:
        return JsonResponse({'error': 'No company found'}, status=404)

    try:
        company = Company.objects.get(id=company_id)
    except Company.DoesNotExist:
        return JsonResponse({'error': 'Company not found'}, status=404)

    if company.owner != user:
        return JsonResponse({'error': 'Permission denied'}, status=403)

    new_name = data.get('name')
    new_owner = data.get('owner')
    if not new_name:
        return JsonResponse({'error': 'Name is required'}, status=400)

    company.name = new_name
    if new_owner:
        company.owner = new_owner
    company.save()

    return JsonResponse({
        'company': {
            'id': company.id,
            'name': company.name,
            'owner': company.owner.username
        }
    }, status=200)


@csrf_exempt
@require_http_methods(["POST"])
def edit_department(request):
    payload, error = get_user_payload(request)
    if error:
        return error

    try:
        user = User.objects.get(id=payload['user_id'])
    except User.DoesNotExist:
        return JsonResponse({'error': 'User not found'}, status=404)

    data, error = parse_json_body(request)
    if error:
        return error

    dept_id = data.get('department_id')
    new_name = data.get('name')

    try:
        department = Department.objects.get(id=dept_id)
    except Department.DoesNotExist:
        return JsonResponse({'error': 'Department not found'}, status=404)

    company_id = Department.objects.filter(personnel=user).values_list(
        'company_id', flat=True).first()
    if not company_id or company_id != department.company.id:
        return JsonResponse({'error': 'Permission denied'}, status=403)

    department.name = new_name
    department.save()

    return JsonResponse({
        'department': {
            'id': department.id,
            'name': department.name,
            'company_name': department.company.name
        }
    }, status=200)


@csrf_exempt
@require_http_methods(["POST"])
def add_personnel(request):
    payload, error = get_user_payload(request)
    if error:
        return error

    try:
        user = User.objects.get(id=payload['user_id'])

    except User.DoesNotExist:
        return JsonResponse({'error': 'User not found'}, status=404)

    data, error = parse_json_body(request)
    if error:
        return error

    department_id = data.get('department_id')
    email = data.get('email')

    if not department_id or not email:
        return JsonResponse(
            {'error': 'Department ID and email are required'},
            status=400)

    try:
        department = Department.objects.get(id=department_id)
        print(department)
    except Department.DoesNotExist:
        return JsonResponse({'error': 'Department not found'}, status=404)

    user_company_id = Department.objects.filter(personnel=user).values_list(
        'company_id', flat=True).first()
    print(user_company_id)
    if not user_company_id or department.company_id != user_company_id:
        return JsonResponse({'error': 'Permission denied'}, status=403)

    try:
        new_personnel = User.objects.get(email=email)
        print(new_personnel)
    except User.DoesNotExist:
        return JsonResponse(
            {'error': 'User with this email does not exist'}, status=404)

    department.personnel.add(new_personnel)

    return JsonResponse({
        'success': True,
        'message': f'User {new_personnel.username} added to {department.name}'
    }, status=200)


@csrf_exempt
@require_http_methods(["POST"])
def remove_personnel(request):
    payload, error = get_user_payload(request)
    if error:
        return error

    try:
        user = User.objects.get(id=payload['user_id'])
    except User.DoesNotExist:
        return JsonResponse({'error': 'User not found'}, status=404)

    data = json.loads(request.body)
    department_id = data.get('department_id')
    user_id = data.get('user_id')

    if not department_id:
        return JsonResponse({'error': 'Department ID is required'},
                            status=400)

    if not user_id:
        return JsonResponse({'error': 'User ID is required'}, status=400)

    try:
        department = Department.objects.get(id=department_id)
    except Department.DoesNotExist:
        return JsonResponse({'error': 'Department not found'}, status=404)

    company_id = (Department.objects.filter(personnel=user).values_list
                  ('company_id', flat=True).first())
    if not company_id or department.company_id != company_id:
        return JsonResponse({'error': 'Permission denied'}, status=403)

    try:
        department.personnel.remove(user_id)
    except Exception as e:
        return JsonResponse(
            {'error': 'User not in department or invalid ID'}, status=400)

    return JsonResponse({
        'success': True,
        'message': 'User removed successfully'
    }, status=200)


@csrf_exempt
@require_http_methods(["POST"])
def delete_department(request):
    payload, error = get_user_payload(request)
    if error:
        return error

    try:
        user = User.objects.get(id=payload['user_id'])
    except User.DoesNotExist:
        return JsonResponse({'error': 'User not found'}, status=404)

    data = json.loads(request.body)
    department_id = data.get('department_id')

    if not department_id:
        return JsonResponse({'error': 'Department ID is required'}, status=400)

    try:
        department = Department.objects.get(id=department_id)
    except Department.DoesNotExist:
        return JsonResponse({'error': 'Department not found'}, status=404)

    company_id = Department.objects.filter(personnel=user).values_list(
        'company_id', flat=True).first()
    owner_company = Company.objects.get(id=company_id).owner
    if owner_company != user:
        return JsonResponse({'error': 'Permission denied'}, status=403)

    department.personnel.clear()

    department.delete()

    return JsonResponse({
        'success': True,
        'message': 'Department deleted successfully'
    }, status=200)
