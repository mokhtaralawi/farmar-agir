"""
Payroll Views - إدارة الرواتب
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.http import HttpResponse
from django.utils import timezone
from decimal import Decimal
from .models import Employee, Attendance, Leave, SalaryAdvance, Payroll, PayrollLine


@login_required
def employees_list(request):
    """قائمة الموظفين"""
    employees = Employee.objects.filter(status='ACTIVE')
    return render(request, 'payroll/employees.html', {'employees': employees})


@login_required
def create_employee(request):
    """إنشاء موظف"""
    if request.method == 'POST':
        Employee.objects.create(
            code=request.POST.get('code'),
            name=request.POST.get('name'),
            phone=request.POST.get('phone', ''),
            position=request.POST.get('position', ''),
            basic_salary=request.POST.get('basic_salary', 0),
            allowances=request.POST.get('allowances', 0),
            deductions=request.POST.get('deductions', 0),
            hire_date=request.POST.get('hire_date'),
        )
        messages.success(request, 'تم إنشاء الموظف بنجاح')
        return redirect('payroll:employees')
    return render(request, 'payroll/create_employee.html')


@login_required
def attendance_list(request):
    """سجل الحضور"""
    employee_id = request.GET.get('employee')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    
    attendance = Attendance.objects.all()
    if employee_id:
        attendance = attendance.filter(employee_id=employee_id)
    if date_from:
        attendance = attendance.filter(date__gte=date_from)
    if date_to:
        attendance = attendance.filter(date__lte=date_to)
    attendance = attendance.order_by('-date')
    
    return render(request, 'payroll/attendance.html', {
        'attendance': attendance,
        'employees': Employee.objects.filter(status='ACTIVE'),
        'date_from': date_from,
        'date_to': date_to,
    })


@login_required
def create_payroll(request):
    """إنشاء مسير رواتب"""
    if request.method == 'POST':
        period_start = request.POST.get('period_start')
        period_end = request.POST.get('period_end')
        
        last_payroll = Payroll.objects.order_by('-id').first()
        num = (int(last_payroll.payroll_number.split('-')[-1]) + 1) if last_payroll else 1
        
        payroll = Payroll.objects.create(
            payroll_number=f"SAL-{num:06d}",
            period_start=period_start, period_end=period_end,
            created_by=request.user, status='APPROVED',
        )
        
        total_salary = Decimal('0')
        total_deductions = Decimal('0')
        total_bonuses = Decimal('0')
        
        for emp in Employee.objects.filter(status='ACTIVE'):
            # Calculate advances for this employee in this period
            advances = SalaryAdvance.objects.filter(
                employee=emp, date__gte=period_start, date__lte=period_end
            ).aggregate(total=Sum('amount'))['total'] or 0
            
            bonuses = Decimal('0')
            deductions = emp.deductions
            
            line = PayrollLine.objects.create(
                payroll=payroll, employee=emp,
                basic_salary=emp.basic_salary, allowances=emp.allowances,
                bonuses=bonuses, deductions=deductions, advances=advances,
            )
            
            total_salary += emp.basic_salary
            total_deductions += deductions + advances
            total_bonuses += emp.allowances + bonuses
        
        payroll.total_salary = total_salary
        payroll.total_deductions = total_deductions
        payroll.total_bonuses = total_bonuses
        payroll.net_amount = total_salary + total_bonuses - total_deductions
        payroll.save()
        
        messages.success(request, f'تم إنشاء مسير رواتب {payroll.payroll_number} بنجاح')
        return redirect('payroll:payrolls')
    
    return render(request, 'payroll/create_payroll.html', {
        'employees': Employee.objects.filter(status='ACTIVE'),
    })


@login_required
def payrolls_list(request):
    """قائمة مسيرات الرواتب"""
    payrolls = Payroll.objects.all().order_by('-created_at')
    return render(request, 'payroll/payrolls.html', {'payrolls': payrolls})


@login_required
def advances_list(request):
    """قائمة السلف"""
    advances = SalaryAdvance.objects.all().order_by('-created_at')
    return render(request, 'payroll/advances.html', {'advances': advances})


@login_required
@transaction.atomic
def create_advance(request):
    """إنشاء سلفة"""
    if request.method == 'POST':
        employee_id = request.POST.get('employee')
        amount = Decimal(request.POST.get('amount', 0))
        try:
            employee = Employee.objects.get(id=employee_id)
        except:
            messages.error(request, 'بيانات غير صحيحة')
            return redirect('payroll:advances')
        
        SalaryAdvance.objects.create(
            employee=employee, amount=amount, date=timezone.now().date(),
            remaining=amount, created_by=request.user,
        )
        
        messages.success(request, 'تم إنشاء السلفة بنجاح')
        return redirect('payroll:advances')
    
    return render(request, 'payroll/create_advance.html', {
        'employees': Employee.objects.filter(status='ACTIVE'),
    })
