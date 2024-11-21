import base64
import calendar
import json
import os
import re
import tempfile
import uuid
import logging

from datetime import datetime, timedelta

from axes.models import AccessAttempt

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from django.core.files.storage import default_storage
from django.core.mail import send_mail
from django.core.paginator import Paginator
from django.core.signing import TimestampSigner, BadSignature, SignatureExpired
from django.db.models import Count, F, Q, Sum
from django.db.models.functions import ExtractMonth
from django.http import JsonResponse, HttpResponseNotAllowed
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.safestring import mark_safe
from django.views.decorators.csrf import csrf_exempt

from . import college_data
from .college_data import college_abbr_to_full, college_departments
from .forms import FirstLoginForm
from .models import Profile, ScannedImage, UnrecognizedImages, Users
from .utils import upload_image_to_drive, get_images_by_category
# from .utils import get_access_token



# Create your views here.

def college_dept_data(request):
    selected_college = request.GET.get('college', '')
    context = {
        'college_departments': college_data.college_departments,
        'selected_college': selected_college
    }
    return render(request, 'myapp/dashboard.html', context)


def index(request):
    if request.method == 'POST':
        identifier = request.POST.get('username')
        password = request.POST.get('password')

        print("Identifier:", identifier)
        print("Password:", password)

        if not identifier or not password:
            messages.error(request, 'Username or Email and Password are required')
            return render(request, 'myapp/index.html')

        if identifier:
            if re.match(r"[^@]+@[^@]+\.[^@]+", identifier):
                try:
                    user_obj = User.objects.get(email=identifier)
                    username = user_obj.username
                except User.DoesNotExist:
                    username = None
            else:
                username = identifier

            user = authenticate(request, username=username, password=password) if username else None

            if user is not None and user.is_staff:

                Profile.objects.get_or_create(user=user)
               
                if not user.email:
                    login(request, user)
                    return redirect('profiles')
                
                login(request, user)
                return redirect('dashboard')
            else:
                messages.error(request, 'Invalid credentials or unauthorized access')
        else:
            messages.error(request, 'Username or Email is required')

    return render(request, 'myapp/index.html')


def logout_view(request):
    storage = messages.get_messages(request)
    storage.used = True  
    
    request.session.flush()

    logout(request)
    return redirect('index')


@login_required(login_url='/index')
def dashboard(request):
    selected_college = request.GET.get('college', 'All Colleges')
    if selected_college not in college_departments and selected_college != 'All Colleges':
        selected_college = 'All Colleges'

    def get_category_counts(model, college=None):
        query = model.objects.filter(isArchived=False, email_address__isArchived=False)
        if college and college != 'All Colleges':
            query = query.filter(email_address__college_department=college)
        return query.values('category').annotate(count=Count('id'))

    total_users = Users.objects.filter(isArchived=False).count()
    filtered_users = (
        Users.objects.filter(college_department=selected_college, isArchived=False).count()
        if selected_college != 'All Colleges' else total_users
    )

    scanned_counts = get_category_counts(ScannedImage, selected_college)
    registered_counts = get_category_counts(UnrecognizedImages, selected_college)

    categories = ['Plastic', 'Metal', 'Glass']
    scanned_counts_dict = {category: 0 for category in categories}
    registered_counts_dict = {category: 0 for category in categories}

    for item in scanned_counts:
        scanned_counts_dict[item['category']] = item['count']

    for item in registered_counts:
        registered_counts_dict[item['category']] = item['count']

    total_counts = {
        category: scanned_counts_dict[category] + registered_counts_dict[category]
        for category in categories
    }

    total_registered_counts = {
        category: registered_counts_dict[category]
        for category in categories
    }


    total_scanned = sum(scanned_counts_dict.values())
    scanned_percentages = {
        category: round((scanned_counts_dict[category] / total_scanned) * 100, 2)
        if total_scanned > 0 else 0
        for category in categories
    }

    context = {
        'college_departments': college_departments, 
        'selected_college': selected_college,
        'total_users': total_users,
        'filtered_users': filtered_users,
        'total_solid_wastes_registered': sum(total_registered_counts.values()),
        'scanned_counts': scanned_counts_dict,
        'registered_counts': registered_counts_dict,
        'total_counts': total_counts,
        'scanned_percentages': json.dumps(scanned_percentages),
    }

    return render(request, 'myapp/dashboard.html', context)

@login_required(login_url='/index')
def profiles(request):
    if request.method == 'POST':
        user = request.user
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        
        if first_name and last_name:
            user.first_name = first_name
            user.last_name = last_name
            user.save()
            messages.success(request, "Profile updated successfully.")
        else:
            messages.error(request, "Both first name and last name are required.")

        first_login = not request.user.email
        return render(request, 'myapp/profiles.html', {'first_login': first_login, 'user': user})

    first_login = not request.user.email
    return render(request, 'myapp/profiles.html', {'first_login': first_login, 'user': request.user})


def clear_messages(request):
    messages.get_messages(request).used = True 
    return JsonResponse({'status': 'success'})  


@login_required(login_url='/index')
def user_list(request):
    search_term = request.GET.get('search', '')
    sort_order = request.GET.get('sort', 'asc')

    query = Q(first_name__icontains=search_term) | Q(last_name__icontains=search_term) | \
            Q(email_address__icontains=search_term) | Q(college_department__icontains=search_term)

    wrusers = Users.objects.filter(query, isArchived=False)

    if sort_order == 'asc':
        wrusers = wrusers.order_by('last_name')
    else:
        wrusers = wrusers.order_by('-last_name')

    context = {
        'wrusers': wrusers,
        'search_term': search_term,
        'sort_order': sort_order,
    }
    return render(request, 'myapp/users.html', context)


@login_required(login_url='/index')
def user_activity_list(request, email_address):
    user = get_object_or_404(Users, email_address=email_address)

    profile_pic_url = None
    if user.profile_picture:
        profile_pic_url = save_image_to_file(user.profile_picture, "profile")

    scanned_categories = ScannedImage.objects.values_list('category', flat=True).distinct()
    unrecognized_categories = UnrecognizedImages.objects.values_list('category', flat=True).distinct()
    all_categories = sorted(set(scanned_categories) | set(unrecognized_categories))

    selected_category = request.GET.get('category', '')
    selected_action = request.GET.get('action', '')

    activities = []

    scanned_activities = ScannedImage.objects.filter(email_address=user.email_address)
    if selected_category:
        scanned_activities = scanned_activities.filter(category=selected_category)
    if selected_action == 'Scanned':
        scanned_activities = scanned_activities 
    for activity in scanned_activities:
        image_url = save_image_to_file(activity.image, 'scanned')
        activities.append({
            'waste_action': 'Scanned',
            'category': activity.category,
            'location': activity.location,
            'activity_date': activity.scan_date,
            'image_url': image_url
        })

    registered_activities = UnrecognizedImages.objects.filter(email_address=user.email_address)
    if selected_category:
        registered_activities = registered_activities.filter(category=selected_category)
    if selected_action == 'Registered':
        registered_activities = registered_activities 
    for activity in registered_activities:
        image_url = save_image_to_file(activity.image, 'unrecognized')
        activities.append({
            'waste_action': 'Registered',
            'category': activity.category,
            'location': None,
            'activity_date': activity.date_registered,
            'image_url': image_url
        })

    activities = sorted(activities, key=lambda x: x['activity_date'], reverse=True)

    context = {
        'user': user,
        'profile_pic_url': profile_pic_url,
        'activities': activities,
        'selected_category': selected_category,
        'selected_action': selected_action,
        'all_categories': all_categories,  
    }
    return render(request, 'myapp/userinfo.html', context)


def save_image_to_file(binary_data, prefix):
    """Save binary image data to a temporary file and return the URL."""
    filename = f"{prefix}_{uuid.uuid4().hex}.jpg"  
    file_path = os.path.join(settings.MEDIA_ROOT, 'temporary', filename)

    os.makedirs(os.path.dirname(file_path), exist_ok=True)

    with open(file_path, 'wb') as file:
        file.write(binary_data)

    return f"{settings.MEDIA_URL}temporary/{filename}"


@csrf_exempt
def set_violation_notice(request, user_email):
    if request.method == 'POST':
        try:
            user = Users.objects.get(email_address=user_email)
            user.isWarned = True
            user.save(update_fields=['isWarned'])
            return JsonResponse({"success": True})
        except Users.DoesNotExist:
            return JsonResponse({"success": False, "error": "User not found"})
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)})
    return JsonResponse({"success": False, "error": "Invalid request method"})


@csrf_exempt
def suspend_user(request):
    if request.method == 'POST':
        email_address = request.POST.get('email_address')
        try:
            user = Users.objects.get(email_address=email_address)
            user.isSuspended = True
            user.save(update_fields=['isSuspended'])
            return JsonResponse({'message': 'User suspended successfully'})
        except Users.DoesNotExist:
            return JsonResponse({'message': 'User not found'}, status=404)
    return JsonResponse({'message': 'Invalid request'}, status=400)


@csrf_exempt
def delete_user(request):
    if request.method == 'POST':
        email_address = request.POST.get('email_address')
        try:
            user = Users.objects.get(email_address=email_address)
            user.isArchived = True
            user.save(update_fields=['isArchived'])
            return JsonResponse({'message': 'User deleted successfully'})
        except Users.DoesNotExist:
            return JsonResponse({'message': 'User not found'}, status=404)
    return JsonResponse({'message': 'Invalid request'}, status=400)


@csrf_exempt
def update_user_status(request, email_address):
    if request.method == "POST":
        data = json.loads(request.body)
        is_suspended = data.get("isSuspended", False)
        is_archived = data.get("isArchived", False)

        is_warned = False if not is_suspended else data.get("isWarned")

        try:
            user = Users.objects.get(email_address=email_address)
            user.isSuspended = is_suspended
            user.isArchived = is_archived
            if is_warned is not None:
                user.isWarned = is_warned 
            user.save()
            return JsonResponse({"success": True})
        except Users.DoesNotExist:
            return JsonResponse({"success": False, "error": "User not found"})
    return JsonResponse({"success": False, "error": "Invalid request"})



@login_required(login_url='/index')
def filtering(request):
    unrecognized_images = UnrecognizedImages.objects.filter(
        isRecognized=False,
        isArchived=False,
        isFlagged=False,
        isAddedToDataset=False,
        email_address__isArchived=False  
    ).order_by('-date_registered')

    for image in unrecognized_images:
        image.image_url = save_image_to_file(image.image, 'unrecognized')

    context = {
        'unrecognized_images': unrecognized_images
    }
    return render(request, 'myapp/filtering.html', context)



@login_required(login_url='/index')
def changepass(request):
    return render(request, 'myapp/changepass.html', {})

@login_required(login_url='/index')
def verifypass(request):
    return render(request, 'myapp/verifypass.html', {})  

@login_required(login_url='/index')
def registerwaste(request):
    return render(request, 'myapp/registerwaste.html', {})

@login_required(login_url='/index')
def successfulreg(request):
    return render(request, 'myapp/successfulreg.html', {})

@login_required(login_url='/index')
def successfuladd(request):
    return render(request, 'myapp/successfuladd.html', {})


def lockout_view(request):
    lockout_duration = timedelta(seconds=180)
    username = request.POST.get('username')

    try:
        access_attempt, created = AccessAttempt.objects.get_or_create(username=username)
        
        if created or access_attempt.failures_since_start < 3:
            access_attempt.attempt_time = timezone.now()  
            access_attempt.failures_since_start += 1  
            access_attempt.save()

        elapsed_time = timezone.now() - access_attempt.attempt_time
        remaining_time = lockout_duration - elapsed_time
        remaining_seconds = max(0, int(remaining_time.total_seconds())) 

    except AccessAttempt.DoesNotExist:
        remaining_seconds = 180

    return render(request, 'lockout.html', {'remaining_seconds': remaining_seconds})


@login_required(login_url='/index')
def temp(request):
    return render(request, 'myapp/temp.html', {})  


signer = TimestampSigner()

def send_verification_email(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        user = request.user

        storage = messages.get_messages(request)
        storage.used = True

        if not email:
            messages.error(request, "Please enter an email address.")
            return redirect('changepass')

        token = default_token_generator.make_token(user)
        uid = urlsafe_base64_encode(force_bytes(user.pk))

        verification_url = request.build_absolute_uri(
            reverse('verify_email', kwargs={'uidb64': uid, 'token': token})
        )

        subject = "Verify Your Email Address"
        message = render_to_string('myapp/verification_email.html', {
            'user': user,
            'verification_url': verification_url,
        })
        send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [email])

        messages.success(request, "Verification email sent. Check your inbox.")
        return redirect('changepass')


def verify_email(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)

        if default_token_generator.check_token(user, token):
            user.email = user.email
            user.save()
            messages.success(request, "Email verified successfully.")
        else:
            messages.error(request, "Invalid or expired verification link.")
    
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        messages.error(request, "Invalid verification link.")
    
    return redirect('changepass')



def analytics_view(request):
    college_departments = Users.objects.values_list('college_department', flat=True).distinct()
    selected_college = request.GET.get('college', '')
    selected_type = request.GET.get('type', 'scanned')

    model = ScannedImage if selected_type == 'scanned' else UnrecognizedImages
    images = get_images_by_category(model, college=selected_college)

    analytics_data = images.values('email_address__college_department', 'category').annotate(total=Count('id'))

    table_data = {}
    for item in analytics_data:
        college = item['email_address__college_department']
        category = item['category']
        count = item['total']
        if college not in table_data:
            table_data[college] = {'Plastic': 0, 'Metal': 0, 'Glass': 0}
        table_data[college][category] = count

    one_year_ago = timezone.now() - timedelta(days=365)
    monthly_data = (
        images.filter(scan_date__gte=one_year_ago)
        .annotate(month=F('scan_date__month'))
        .values('month')
        .annotate(count=Count('id'))
        .order_by('month')
    )

    context = {
        'college_departments': college_departments,
        'table_data': table_data,
        'monthly_data': mark_safe(json.dumps(list(monthly_data))),
        'selected_college': selected_college,
        'selected_type': selected_type,
    }
    return render(request, 'myapp/dashboard.html', context)


def get_scanned_data():
    scanned_data = (
        ScannedImage.objects
        .filter(isArchived=False, email_address__isArchived=False) 
        .values('email_address__college_department', 'category')
        .annotate(count=Count('id'))
    )

    college_data = {}
    for entry in scanned_data:
        college = entry['email_address__college_department']
        category = entry['category']
        count = entry['count']
        
        if college not in college_data:
            college_data[college] = {'Plastic': 0, 'Metal': 0, 'Glass': 0}
        
        college_data[college][category] = count

    colleges = list(college_data.keys())
    plastic_data = [college_data[college]['Plastic'] for college in colleges]
    metal_data = [college_data[college]['Metal'] for college in colleges]
    glass_data = [college_data[college]['Glass'] for college in colleges]

    return colleges, plastic_data, metal_data, glass_data


def get_scanned_percentages(request):
    college_filter = request.GET.get('college')

    if college_filter:
        scanned_images = ScannedImage.objects.filter(isArchived=False, email_address__isArchived=False, email_address__college_department=college_filter)
    else:
        scanned_images = ScannedImage.objects.filter(isArchived=False, email_address__isArchived=False)

    total_scanned = scanned_images.count()

    plastic_count = scanned_images.filter(category="Plastic").count()
    metal_count = scanned_images.filter(category="Metal").count()
    glass_count = scanned_images.filter(category="Glass").count()

    scanned_percentages = {
        'Plastic': round((plastic_count / total_scanned) * 100, 2) if total_scanned > 0 else 0,
        'Metal': round((metal_count / total_scanned) * 100, 2) if total_scanned > 0 else 0,
        'Glass': round((glass_count / total_scanned) * 100, 2) if total_scanned > 0 else 0
    }

    return JsonResponse(scanned_percentages)


def get_waste_data_by_college(request):
    start_date = request.GET.get('startDate')
    end_date = request.GET.get('endDate')

    start_date = parse_date(start_date) if start_date else None
    end_date = parse_date(end_date) if end_date else None

    waste_data_by_college = {
        "colleges": list(college_abbr_to_full.keys()),
        "Plastic": [],
        "Metal": [],
        "Glass": []
    }

    date_filter = Q()
    if start_date:
        date_filter &= Q(scan_date__gte=start_date)
    if end_date:
        date_filter &= Q(scan_date__lte=end_date)

    for abbr in waste_data_by_college["colleges"]:
        plastic_count = ScannedImage.objects.filter(
            email_address__college_department=abbr,
            category="Plastic",
            isArchived=False,
            email_address__isArchived=False  
        ).filter(date_filter).count()

        metal_count = ScannedImage.objects.filter(
            email_address__college_department=abbr,
            category="Metal",
            isArchived=False,
            email_address__isArchived=False 
        ).filter(date_filter).count()

        glass_count = ScannedImage.objects.filter(
            email_address__college_department=abbr,
            category="Glass",
            isArchived=False,
            email_address__isArchived=False 
        ).filter(date_filter).count()

        waste_data_by_college["Plastic"].append(plastic_count)
        waste_data_by_college["Metal"].append(metal_count)
        waste_data_by_college["Glass"].append(glass_count)

    return JsonResponse(waste_data_by_college)


def get_user_activity_data(request):
    try:
        year = int(request.GET.get('year', timezone.now().year)) 
    except ValueError:
        return JsonResponse({"error": "Invalid year format."}, status=400)

    colleges = list(college_abbr_to_full.keys())
    activity_data = {college: [0] * 12 for college in colleges}

    for college in colleges:
        user_emails = Users.objects.filter(college_department=college, isArchived=False).values_list('email_address', flat=True)

        scanned_counts = ScannedImage.objects.filter(email_address__in=user_emails, isArchived=False)
        if year:
            scanned_counts = scanned_counts.filter(scan_date__year=year)
        scanned_counts = scanned_counts.extra({'month': "EXTRACT(month FROM scan_date)"}).values('month').annotate(count=Count('id'))
        
        for entry in scanned_counts:
            month_index = int(entry['month']) - 1
            activity_data[college][month_index] += entry['count']
        
        unrecognized_counts = UnrecognizedImages.objects.filter(email_address__in=user_emails, isArchived=False)
        if year:
            unrecognized_counts = unrecognized_counts.filter(date_registered__year=year)
        unrecognized_counts = unrecognized_counts.extra({'month': "EXTRACT(month FROM date_registered)"}).values('month').annotate(count=Count('id'))
        
        for entry in unrecognized_counts:
            month_index = int(entry['month']) - 1
            activity_data[college][month_index] += entry['count']

    return JsonResponse({"activity_data": activity_data, "colleges": colleges})



@login_required(login_url='/index')
def filteredimages(request):
    def process_image(image, prefix):
        if image.image:
            image.image_url = save_image_to_file(image.image, prefix)
        return image

    plastic_images = [
        process_image(img, 'plastic') for img in get_images_by_category(
            UnrecognizedImages, category='Plastic'
        ).filter(isFlagged=False, isRecognized=True, isAddedToDataset=False)
    ]
    metal_images = [
        process_image(img, 'metal') for img in get_images_by_category(
            UnrecognizedImages, category='Metal'
        ).filter(isFlagged=False, isRecognized=True, isAddedToDataset=False)
    ]
    glass_images = [
        process_image(img, 'glass') for img in get_images_by_category(
            UnrecognizedImages, category='Glass'
        ).filter(isFlagged=False, isRecognized=True, isAddedToDataset=False)
    ]
    flagged_images = [
        process_image(img, 'flagged') for img in get_images_by_category(
            UnrecognizedImages
        ).filter(isFlagged=True)
    ]

    context = {
        'plastic_images': plastic_images,
        'metal_images': metal_images,
        'glass_images': glass_images,
        'flagged_images': flagged_images,
    }
    return render(request, 'myapp/filteredimages.html', context)


@csrf_exempt
def update_flagged_status(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        image_ids = data.get('image_ids', [])

        images = UnrecognizedImages.objects.filter(id__in=image_ids)

        for image in images:
            image.isFlagged = not image.isFlagged
            if image.isFlagged:
                image.isRecognized = False 
            image.save()

        return JsonResponse({'status': 'success'})


@csrf_exempt
def update_recognized_status(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        image_ids = data.get('image_ids', [])
        tab = data.get('tab', '')

        images = UnrecognizedImages.objects.filter(id__in=image_ids)

        if tab == 'flaggedTab':
            images.update(isFlagged=False)
        else:
            for image in images:
                image.isRecognized = not image.isRecognized
                if image.isRecognized:
                    image.isFlagged = False
                image.save()

        return JsonResponse({'status': 'success'})


@csrf_exempt
def add_to_dataset(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        image_ids = data.get('image_ids', [])
        category = data.get('category')

        if not image_ids or not category:
            return JsonResponse({'status': 'failed', 'message': 'Image IDs or category missing.'})

        images = UnrecognizedImages.objects.filter(id__in=image_ids)

        for image in images:
            with tempfile.NamedTemporaryFile(delete=False) as temp_file:
                file_name = f"{image.id}.jpg"
                
                temp_file.write(image.image)  
                temp_file.close()

                upload_result = upload_image_to_drive(temp_file.name, file_name, category)
                os.remove(temp_file.name)

                if upload_result:
                    image.isAddedToDataset = True 
                    image.save()
                else:
                    return JsonResponse({'status': 'failed', 'message': 'Failed to upload some images.'})

        return JsonResponse({'status': 'success', 'message': 'Images successfully added to dataset.'})
    
    return HttpResponseNotAllowed(['POST'])
    

def custom_bad_request(request, exception=None):
    return render(request, '400.html', status=400)

def custom_permission_denied(request, exception=None):
    return render(request, '403.html', status=403)

def custom_page_not_found(request, exception=None):
    return render(request, '404.html', status=404)

def custom_server_error(request):
    return render(request, '500.html', status=500)


def get_table_data(request):
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    college = request.GET.get('college', 'All Colleges')

    date_range_text = "All Dates"
    if start_date and end_date:
        date_range_text = f"{start_date} to {end_date}"

    filters = Q(isArchived=False)
    if start_date and end_date:
        filters &= Q(scan_date__range=[start_date, end_date])
    if college != 'All Colleges':
        filters &= Q(email_address__college_department=college)

    users_query = Users.objects.filter(isArchived=False)
    if college != 'All Colleges':
        users_query = users_query.filter(college_department=college)
    total_users = users_query.count()

    scanned_query = ScannedImage.objects.filter(filters)
    scanned_data = scanned_query.values('category').annotate(count=Count('id'))
    total_scanned = scanned_query.count()

    bsu_scanned_query = scanned_query.filter(location="Bulacan State University")
    bsu_scanned_data = bsu_scanned_query.values('category').annotate(count=Count('id'))
    total_bsu_scanned = bsu_scanned_query.count()

    registered_query = UnrecognizedImages.objects.filter(isArchived=False)
    if start_date and end_date:
        registered_query = registered_query.filter(date_registered__range=[start_date, end_date])
    if college != 'All Colleges':
        registered_query = registered_query.filter(email_address__college_department=college)
    registered_data = registered_query.values('category').annotate(count=Count('id'))
    total_registered = registered_query.count()

    total_solid_wastes_registered = total_registered

    categories = ['Plastic', 'Metal', 'Glass']
    table_data = []
    total_scanned_count = 0
    total_registered_count = 0

    for category in categories:
        scanned_count = next((item['count'] for item in scanned_data if item['category'] == category), 0)
        registered_count = next((item['count'] for item in registered_data if item['category'] == category), 0)
        table_data.append({
            'category': category,
            'scanned': scanned_count,
            'registered': registered_count,
            'total': scanned_count + registered_count,
        })
        total_scanned_count += scanned_count
        total_registered_count += registered_count

    table_data.append({
        'category': 'Total',
        'scanned': total_scanned_count,
        'registered': total_registered_count,
        'total': total_scanned_count + total_registered_count,
    })

    percentages = {
        category: round((next((item['count'] for item in scanned_data if item['category'] == category), 0) / total_scanned) * 100, 2)
        if total_scanned > 0 else 0
        for category in categories
    }

    bsu_percentages = {
        category: round((next((item['count'] for item in bsu_scanned_data if item['category'] == category), 0) / total_bsu_scanned) * 100, 2)
        if total_bsu_scanned > 0 else 0
        for category in categories
    }

    has_data = any(item['count'] > 0 for item in scanned_data) or any(item['count'] > 0 for item in registered_data)

    return JsonResponse({
        'table_data': table_data,
        'totals': {
            'total_users': total_users,
            'total_solid_wastes_registered': total_solid_wastes_registered,
            'percentages': percentages,
            'bsu_percentages': bsu_percentages,
        },
        'date_range_text': date_range_text,
        'has_data': has_data
    })



logger = logging.getLogger(__name__)

def export_filtered_college_data(request):
    try:
        logger.info("Received request to export filtered data.")

        college = request.GET.get("college", "All Colleges")
        start_date_raw = request.GET.get("start_date")
        end_date_raw = request.GET.get("end_date")

        logger.info(f"Filters - College: {college}, Start Date: {start_date_raw}, End Date: {end_date_raw}")

        start_date = parse_date(start_date_raw) if start_date_raw else None
        end_date = parse_date(end_date_raw) if end_date_raw else None

        users = Users.objects.filter(isArchived=False)
        if college != "All Colleges":
            users = users.filter(college_department=college)

        if not users.exists():
            logger.warning("No users found for the specified criteria.")
            return JsonResponse({"message": "No users found for the specified criteria."}, status=404)

        logger.info(f"Number of users fetched: {users.count()}")

        unrecognized_images = UnrecognizedImages.objects.filter(email_address__in=users, isArchived=False)
        scanned_images = ScannedImage.objects.filter(email_address__in=users, isArchived=False)

        if start_date:
            unrecognized_images = unrecognized_images.filter(date_registered__gte=start_date)
            scanned_images = scanned_images.filter(scan_date__gte=start_date)
        if end_date:
            unrecognized_images = unrecognized_images.filter(date_registered__lte=end_date)
            scanned_images = scanned_images.filter(scan_date__lte=end_date)

        logger.info(f"Filtered Unrecognized Images: {unrecognized_images.count()}")
        logger.info(f"Filtered Scanned Images: {scanned_images.count()}")

        user_activities = {}
        for activity in unrecognized_images:
            user_email = activity.email_address.email_address
            user_activities.setdefault(user_email, []).append({
                "type": "Unrecognized",
                "category": activity.category,
                "image_url": convert_image_to_base64(activity.image),
                "date": activity.date_registered.strftime("%Y-%m-%d"),
                "isRecognized": activity.isRecognized,
                "isFlagged": activity.isFlagged,
            })

        for activity in scanned_images:
            user_email = activity.email_address.email_address
            user_activities.setdefault(user_email, []).append({
                "type": "Scanned",
                "category": activity.category,
                "image_url": convert_image_to_base64(activity.image),
                "location": activity.location,
                "date": activity.scan_date.strftime("%Y-%m-%d"),
                "isRecognized": None,
                "isFlagged": None,
            })

        logger.info("Mapped user activities successfully.")

        data = []
        for user in users:
            activities = user_activities.get(user.email_address, [])
            data.append({
                "first_name": user.first_name,
                "last_name": user.last_name,
                "email_address": user.email_address,
                "college_department": user.college_department,
                "status": "Suspended" if user.isSuspended else "Warned" if user.isWarned else "Good",
                "profile_picture": convert_image_to_base64(user.profile_picture),
                "activities": activities,
            })

        logger.info("Data prepared successfully for export.")
        return JsonResponse(data, safe=False)

    except Exception as e:
        logger.error(f"Error in export_filtered_college_data: {e}", exc_info=True)
        return JsonResponse({"error": str(e)}, status=500)

    

def convert_image_to_base64(image_binary):
    """
    Converts binary image data to a base64-encoded string.
    """
    if not image_binary:
        return None
    return f"data:image/png;base64,{base64.b64encode(image_binary).decode('utf-8')}"



def get_summary_table_data(request):
    college = request.GET.get('college', 'All Colleges')
    start_date = request.GET.get('start_date', None)
    end_date = request.GET.get('end_date', None)

    query = Q()

    if college != 'All Colleges':
        query &= Q(email_address__college_department=college) 

    if start_date and end_date:
        query &= Q(scan_date__range=[start_date, end_date])

    data = (
        ScannedImage.objects.filter(query)
        .values('category')
        .annotate(
            scanned=Sum('isArchived', filter=Q(isArchived=False)),  
            registered=Sum('isArchived', filter=Q(isArchived=True)),
            total=Sum('isArchived'), 
        )
    )

    return JsonResponse({'table_data': list(data)})