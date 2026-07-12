"""
Partners Views - الرعويون والمقاوته
"""

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Farmer, Buyer


@login_required
def farmers_list(request):
    farmers = Farmer.objects.all().order_by('-created_at')
    return render(request, 'partners/farmers.html', {'farmers': farmers})


@login_required
def create_farmer(request):
    if request.method == 'POST':
        Farmer.objects.create(
            code=Farmer.generate_code(),
            name=request.POST.get('name'),
            phone=request.POST.get('phone', ''),
            id_number=request.POST.get('id_number', ''),
            city=request.POST.get('city', ''),
            address=request.POST.get('address', ''),
            notes=request.POST.get('notes', ''),
        )
        messages.success(request, 'تم إنشاء الرعوي بنجاح')
        return redirect('partners:farmers')
    return render(request, 'partners/create_farmer.html', {'generated_code': Farmer.generate_code()})


@login_required
def buyers_list(request):
    buyers = Buyer.objects.all().order_by('-created_at')
    return render(request, 'partners/buyers.html', {'buyers': buyers})


@login_required
def create_buyer(request):
    if request.method == 'POST':
        code = request.POST.get('code')
        if not code:
            code = Buyer.generate_code()
        Buyer.objects.create(
            code=code,
            name=request.POST.get('name'),
            phone=request.POST.get('phone', ''),
            city=request.POST.get('city', ''),
            address=request.POST.get('address', ''),
            credit_limit=request.POST.get('credit_limit') or 0,
            notes=request.POST.get('notes', ''),
        )
        messages.success(request, 'تم إنشاء الرعوي بنجاح')
        return redirect('partners:buyers')
    return render(request, 'partners/create_buyer.html', {'generated_code': Buyer.generate_code()})


@login_required
def edit_farmer(request, pk):
    from django.shortcuts import get_object_or_404
    farmer = get_object_or_404(Farmer, id=pk)
    if request.method == 'POST':
        farmer.name = request.POST.get('name', farmer.name)
        farmer.phone = request.POST.get('phone', farmer.phone)
        farmer.id_number = request.POST.get('id_number', farmer.id_number)
        farmer.city = request.POST.get('city', farmer.city)
        farmer.address = request.POST.get('address', farmer.address)
        farmer.notes = request.POST.get('notes', farmer.notes)
        farmer.status = request.POST.get('status', farmer.status)
        farmer.save()
        messages.success(request, f'تم تعديل بيانات {farmer.name} بنجاح')
        return redirect('partners:farmers')
    return render(request, 'partners/edit_farmer.html', {'farmer': farmer})


@login_required
def edit_buyer(request, pk):
    from django.shortcuts import get_object_or_404
    buyer = get_object_or_404(Buyer, id=pk)
    if request.method == 'POST':
        buyer.name = request.POST.get('name', buyer.name)
        buyer.phone = request.POST.get('phone', buyer.phone)
        buyer.city = request.POST.get('city', buyer.city)
        buyer.address = request.POST.get('address', buyer.address)
        buyer.credit_limit = request.POST.get('credit_limit') or buyer.credit_limit
        buyer.notes = request.POST.get('notes', buyer.notes)
        buyer.status = request.POST.get('status', buyer.status)
        buyer.save()
        messages.success(request, f'تم تعديل بيانات {buyer.name} بنجاح')
        return redirect('partners:buyers')
    return render(request, 'partners/edit_buyer.html', {'buyer': buyer})
