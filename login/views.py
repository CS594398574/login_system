from django.shortcuts import render
from django.shortcuts import redirect
from login.models import User
from . import forms
import hashlib
import datetime
from login import models
from django.conf import settings

# Create your views here.

def hash_code(s,salt='login_system'):
    h = hashlib.sha256()
    s += salt
    h.update(s.encode())
    return h.hexdigest()

def make_confirm_string(user):
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    code = hash_code(user.name,now)
    models.ConfirmString.objects.create(code=code,user=user,)
    return code

def user_confirm(request):
    code = request.GET.get('code',None)  #从请求中得到请求码
    message = ''
    try:
        confirm = models.ConfirmString.objects.get(code=code)   #与数据库中的确认码进行对比
    except:
        message = '无效确认请求'
        return render(request,'login/confirm.html',locals())

    c_time = confirm.c_time
    now = datetime.datetime.now()
    if now > c_time + datetime.timedelta(settings.CONFIRM_DAYS):
        confirm.user.delete()
        message = "邮件确认码已过期，请重新登录！"
        return render(request,'login/confirm.html',locals())
    else:
        confirm.user.has_confirmed = True
        confirm.user.save()
        confirm.delete()
        message = "感谢确认，请使用账号登录"
        return render(request,'login/confirm.html',locals())


def send_email(email,code):
    from django.core.mail import EmailMultiAlternatives

    subject = "来自zolhuangjinlong@163.com的注册确认邮件"
    text_content = '''感谢注册zolhuangjinlong，这里是黄金龙的测试网站，专注于Python、Django和机器学习、计算机视觉技术的分享！\
                       如果你看到这条消息，说明你的邮箱服务器不提供HTML链接功能，请联系管理员！'''

    html_content = '''
                       <p>感谢注册<a href="http://{}/confirm/?code={}" target=blank>点击代码确认</a>，\
                       这里是黄金龙Web网站测试站点，专注于计算机视觉、Python、Django和机器学习技术的分享！</p>
                       <p>请点击站点链接完成注册确认！</p>
                       <p>此链接有效期为{}天！</p>
                       '''.format('127.0.0.1:8000', code, settings.CONFIRM_DAYS)
    msg = EmailMultiAlternatives(subject, text_content, settings.EMAIL_HOST_USER, [email])
    msg.attach_alternative(html_content, "text/html")
    msg.send()


def index(request):
    if not request.session.get('is_login',None):
        return redirect('/login/')
    return render(request,'login/index.html')

# def login(request):
#     if request.method =='POST':
#         username = request.POST.get('username')
#         password = request.POST.get('password')
#         # print(username,password)
#         message ="请检查填写的内容"
#         if username.strip() and password:
#             try:
#                 user = User.objects.get(name=username)
#                 # print("用户密码：",user.password)
#             except:
#                 message ="用户不存在!"
#                 return render(request,'login/login.html',{'message':message})
#
#             if user.password ==password:
#                 # print(username,password)
#                 # print("查找到用户名和密码！")
#                 return redirect('/index/')
#             else:
#                 message = '密码不正确！'
#                 return render(request,'login/login.html',{'message':message})
#
#         else:
#             return render(request,'login/login.html',{'message':message})
#     return render(request, 'login/login.html')

def login(request):
    if request.session.get('is_login',None):  #不允许重复登录
        return redirect('/index/')

    if request.method =='POST':
        login_form = forms.UserForm(request.POST)
        message = "请检查填写的内容！"
        if login_form.is_valid():
            username = login_form.cleaned_data.get('username')
            password = login_form.cleaned_data.get('password')

            try:
                user = User.objects.get(name = username)
            except:
                message = "用户不存在！"
                return render(request,'login/login.html',locals())
            if not user.has_confirmed:
                message = '该用户还未经过邮件确认！'
                return render(request,'login/login.html',locals())

            if user.password == hash_code(password):
                request.session['is_login'] = True
                request.session['user_id'] = user.id
                request.session['user_name'] = user.name
                return redirect('/index/')
            else:
                message = '密码不正确！'
                return render(request,'login/login.html',locals())

        else:
            return render(request,'login/login.html',locals())  #locals()返回当前所有的本地变量字典。
    login_form = forms.UserForm()    #返回一个之前填写的表单，方便用户修改。
    return render(request,'login/login.html',locals())

def register(request):
    if request.session.get('is_login',None):
        return redirect('/index/')

    if request.method=='POST':
        register_form = forms.RegisterForm(request.POST)
        message= '请检查填写内容！'
        if register_form.is_valid():
            username = register_form.cleaned_data.get('username')
            password1 = register_form.cleaned_data.get('password1')
            password2 = register_form.cleaned_data.get('password2')
            email = register_form.cleaned_data.get('email')
            sex = register_form.cleaned_data.get('sex')

            if password1 != password2:
                message = '两次输入密码不同！'
                return render(request,'login/register.html',locals())
            else:
                same_name_user = User.objects.filter(name=username)
                print(same_name_user)
                if same_name_user:
                    message = "用户已经存在"
                    return render(request,'login/register.html',locals())
                same_email_user = User.objects.filter(email=email)
                if same_email_user:
                    message = '该邮箱已经被注册！'
                    return render(request,'login/register.html',locals())

                new_user = User()
                new_user.name = username
                new_user.password = hash_code(password1)
                # new_user.password = password1
                new_user.email = email
                new_user.sex = sex
                new_user.save()

                code = make_confirm_string( new_user)
                send_email(email,code)

                return redirect('/login/')
        else:
            return render(request,'login/register.html',locals())
    register_form = forms.RegisterForm()
    return render(request,'login/register.html',locals())


def logout(request):
    if not request.session.get('is_login',None):# 判断是否登录，登录则清空，未登录则进入login页面
        return redirect('/login/')
    request.session.flush()  #一次性将session中的所有内容全部清空
    return redirect("/login/")