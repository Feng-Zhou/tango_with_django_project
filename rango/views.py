from django.shortcuts import render
from django.http import HttpResponse, HttpResponseRedirect
from django.template import RequestContext
from django.shortcuts import render_to_response
from rango.models import Category
from rango.models import Page, UserProfile
from rango.forms import CategoryForm, PageForm
from rango.forms import UserForm, UserProfileForm
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from datetime import datetime
from rango.bing_search import run_query
from django.contrib.auth.models import User
from django.shortcuts import redirect

def index(request):
    context = RequestContext(request)
    category_list = Category.objects.order_by('-likes')[:5]
    page_list = Page.objects.order_by('-views')[:5]

    cat_list = get_category_list()
    context_dict = {'categories': category_list, 'pages': page_list}
    context_dict['cat_list'] = cat_list

    for category in category_list:
        category.url = encode_url(category.name)

    if request.session.get('last_visit'):
        last_visit_time = request.session.get('last_visit')
        visits = request.session.get('visits', 0)

        if (datetime.now() - datetime.strptime(last_visit_time[:-7], "%Y-%m-%d %H:%M:%S")).days > 0:
            request.session['visits'] = visits + 1
            request.session['last_visit'] = str(datetime.now())
    else:
        request.session['last_visit'] = str(datetime.now())
        request.session['visit'] = 1

    return render_to_response('rango/index.html', context_dict, context)

    # response = render_to_response('rango/index.html', context_dict, context)

    # visits = int(request.COOKIES.get('visits', '0'))

    # if 'last_visit' in request.COOKIES:
    #     last_visit = request.COOKIES['last_visit']
    #     last_visit_time = datetime.strptime(last_visit[:-7], "%Y-%m-%d %H:%M:%S")
    #
    #     if (datetime.now() - last_visit_time).seconds > 5:
    #         response.set_cookie('visits', visits + 1)
    #         response.set_cookie('last_visit', datetime.now())
    # else:
    #     response.set_cookie('visits', 1)
    #     response.set_cookie('last_visit', datetime.now())
    #
    # return response

def category(request, category_name_url):
    context = RequestContext(request)
    category_name = decode_url(category_name_url)
    context_dict = {'category_name': category_name,
                    'category_name_url': category_name_url}
    cat_list = get_category_list()
    context_dict['cat_list'] = cat_list

    try:
        category = Category.objects.get(name=category_name)
        pages = Page.objects.filter(category=category).order_by('-views')
        context_dict['pages'] = pages
        context_dict['category'] = category
    except Category.DoesNotExist:
        pass
        # return HttpResponse("This category doesn't exist")

    if request.method == 'POST':
        query = request.POST['query'].strip()
        if query:
            result_list = run_query(query)
            context_dict['result_list'] = result_list
    return render_to_response('rango/category.html', context_dict, context)

def about(request):
    context = RequestContext(request)

    if request.session.get('visits'):
        count = request.session.get('visits')
    else:
        count = 0
    context_dict = {'italicmsg': "about page", 'visits': count}
    cat_list = get_category_list()
    context_dict['cat_list'] = cat_list
    return render_to_response('rango/about.html', context_dict, context)

def add_category(request):
    context = RequestContext(request)

    if request.method == 'POST':
        form = CategoryForm(request.POST)

        if form.is_valid():
            form.save(commit=True)
            return index(request)
        else:
            print(form.errors)
    else:
        form = CategoryForm

    cat_list = get_category_list()
    context_dict = {'cat_list': cat_list, 'form': form}

    return render_to_response('rango/add_category.html', context_dict, context)

def add_page(request, category_name_url):
    context = RequestContext(request)

    category_name = decode_url(category_name_url)

    if request.method == 'POST':
        form = PageForm(data=request.POST)

        if form.is_valid():
            page = form.save(commit=False)

            try:
                cat = Category.objects.get(name=category_name)
                page.category = cat
            except Category.DoesNotExist:
                return render_to_response('rango/add_catetory.html', {}, context)

            page.views = 0

            page.save()

            return category(request, category_name_url)
        else:
            print(form.errors)
    else:
        form = PageForm()

    cat_list = get_category_list()
    context_dict = {'category_name_url': category_name_url,
         'category_name': category_name, 'form': form, 'cat_list': cat_list}
    return render_to_response('rango/add_page.html',context_dict, context)

def decode_url(category_name_url):
    category_name = category_name_url.replace('_', ' ')
    return category_name

def encode_url(category_name):
    category_name_url = category_name.replace(' ', '_')
    return category_name_url

def register(request):
    context = RequestContext(request)

    registered = False

    if request.method == 'POST':
        user_form = UserForm(data=request.POST)
        profile_form = UserProfileForm(data=request.POST)

        if user_form.is_valid() and profile_form.is_valid():
            user = user_form.save()

            user.set_password(user.password)
            user.save()

            profile = profile_form.save(commit=False)
            profile.user = user

            if 'picture' in request.FILES:
                profile.picture = request.FILES['picture']

            profile.save()
            registered = True
        else:
            print(user_form.errors, profile_form.errors)
    else:
        user_form = UserForm()
        profile_form = UserProfileForm()

    cat_list = get_category_list()
    context_dict = {'user_form': user_form, 'profile_form': profile_form,
                    'registered': registered, 'cat_list': cat_list}

    return render_to_response('rango/register.html', context_dict,context)

def user_login(request):
    context = RequestContext(request)
    cat_list = get_category_list()

    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']

        user = authenticate(username=username, password=password)
        bad_details = False
        disabled_account = False
        if user:
            if user.is_active:
                login(request, user)
                return HttpResponseRedirect('/rango/')
            else:
                disabled_account = True
                return render_to_response('rango/login.html',
                                          {'disabled_account': disabled_account,'cat_list': cat_list}, context)
        else:
            print("hhhhhhhh")
            bad_details = True
            return render_to_response('rango/login.html', {'bad_details': bad_details,'cat_list': cat_list}, context)
    else:
        return render_to_response('rango/login.html', {'cat_list': cat_list}, context)


@login_required
def restricted(request):
    context = RequestContext(request)
    cat_list = get_category_list()
    return render_to_response('rango/restricted.html', {'cat_list': cat_list}, context)
    #return HttpResponse("Since you'are logged in, you can see this text!")

@login_required
def user_logout(request):
    logout(request)
    return HttpResponseRedirect('/rango/')

@login_required
def profile(request):
    context = RequestContext(request)
    cat_list = get_category_list()
    context_dict = {'cat_list': cat_list}
    u = User.objects.get(username=request.user)

    try:
        up = UserProfile.objects.get(user=u)
    except:
        up = None

    context_dict['user'] = u
    context_dict['userprofile'] = up
    return render_to_response('rango/profile.html', context_dict, context)

from django.contrib.auth.decorators import login_required

@login_required
def like_category(request):
    context = RequestContext(request)
    cat_id = None
    if request.method == 'GET':
        cat_id = request.GET['category_id']

    likes = 0
    if cat_id:
        category = Category.objects.get(id=int(cat_id))
        if category:
            likes = category.likes + 1
            category.likes =  likes
            category.save()

    return HttpResponse(likes)

def search(request):
    context = RequestContext(request)
    cat_list = get_category_list()
    result_list = []

    if request.method == 'POST':
        query = request.POST['query'].strip()

        if query:
            result_list = run_query(query)

    return render_to_response('rango/search.html', {'result_list': result_list, 'cat_list': cat_list}, context)

def get_category_list():
    cat_list = Category.objects.all()

    for cat in cat_list:
        cat.url = encode_url(cat.name)

    return cat_list

def track_url(request):
    context = RequestContext(request)
    page_id = None
    url = '/rango/'
    if request.method == 'GET':
        if 'page_id' in request.GET:
            page_id = request.GET['page_id']
            try:
                page = Page.objects.get(id=page_id)
                page.views = page.views + 1
                page.save()
                url = page.url
            except:
                pass

    return redirect(url)

def get_category_list(max_results=0, starts_with=''):
    cat_list = []
    if starts_with:
        cat_list = Category.objects.filter(name__istartswith=starts_with)
    else:
        cat_list = Category.objects.all()

    if max_results > 0:
        if len(cat_list) > max_results:
            cat_list = cat_list[:max_results]

    for cat in cat_list:
        cat.url = encode_url(cat.name)

    return cat_list

def suggest_category(request):
    context = RequestContext(request)
    cat_list = []
    starts_with = ''
    if request.method == 'GET':
        starts_with = request.GET['suggestion']

    cat_list = get_category_list(8, starts_with)

    return render_to_response('rango/category_list.html', {'cat_list': cat_list }, context)