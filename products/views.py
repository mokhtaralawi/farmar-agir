"""
Products Views - إدارة الأصناف
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Product, Category, Unit, ProductPrice


@login_required
def products_list(request):
    products = Product.objects.filter(status='ACTIVE').order_by('name')
    return render(request, 'products/products.html', {'products': products})


@login_required
def create_product(request):
    if request.method == 'POST':
        Product.objects.create(
            code=Product.generate_code(),
            name=request.POST.get('name'),
            category_id=request.POST.get('category'),
            unit_id=request.POST.get('unit'),
            status='ACTIVE',
        )
        messages.success(request, 'تم إنشاء الصنف بنجاح')
        return redirect('products:products')
    return render(request, 'products/create.html', {
        'categories': Category.objects.filter(is_active=True),
        'units': Unit.objects.filter(is_active=True),
        'generated_code': Product.generate_code(),
    })


@login_required
def product_prices(request, pk):
    product = get_object_or_404(Product, id=pk)
    prices = ProductPrice.objects.filter(product=product).order_by('-date')
    return render(request, 'products/prices.html', {
        'product': product,
        'prices': prices,
    })
