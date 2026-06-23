from django.contrib import admin
from django.http import HttpResponse
import pandas as pd
from openpyxl.styles import PatternFill, Font, Alignment

from .models import Teammates, AttendanceLog


class TeammatesAdmin(admin.ModelAdmin):
    list_display = ('name', 'rfid_number', 'branch', 'email', 'phone_number', 'is_fully_registered', 'date_posted')
    list_filter = ('is_fully_registered', 'branch', 'date_posted')
    search_fields = ('name', 'rfid_number', 'email', 'phone_number')
    readonly_fields = ('date_posted', 'author')
    
    fieldsets = (
        ('Personal Information', {
            'fields': ('name', 'email', 'phone_number', 'about')
        }),
        ('Academic Info', {
            'fields': ('branch', 'division', 'year', 'domain')
        }),
        ('RFID & System', {
            'fields': ('rfid_number', 'is_fully_registered', 'author', 'date_posted')
        }),
    )


class AttendanceLogAdmin(admin.ModelAdmin):
    list_display = ('id', 'teammate_name', 'timestamp_display', 'status')
    list_filter = ('status', 'timestamp', 'teammate__branch')
    search_fields = ('teammate__name', 'teammate__rfid_number')
    readonly_fields = ('timestamp',)
    actions = ['export_to_excel']
    
    def teammate_name(self, obj):
        return obj.teammate.name if obj.teammate else "Unknown"
    teammate_name.short_description = "Teammate"
    
    def timestamp_display(self, obj):
        return obj.timestamp.strftime("%Y-%m-%d %H:%M:%S")
    timestamp_display.short_description = "Scanned At"
    
    def export_to_excel(self, request, queryset):
        """Custom action to export selected attendance logs to Excel."""
        data = []
        for log in queryset:
            data.append({
                'ID': log.id,
                'Name': log.teammate.name if log.teammate else 'Unknown',
                'RFID': log.teammate.rfid_number if log.teammate else 'N/A',
                'Branch': log.teammate.branch if log.teammate else 'N/A',
                'Timestamp': log.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                'Status': log.status,
            })
        
        df = pd.DataFrame(data)
        
        response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = 'attachment; filename="Attendance_Export.xlsx"'
        
        with pd.ExcelWriter(response, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Attendance')
            
            # Style the header row
            worksheet = writer.sheets['Attendance']
            header_fill = PatternFill(start_color='4472C4', end_color='4472C4', fill_type='solid')
            header_font = Font(bold=True, color='FFFFFF')
            
            for cell in worksheet[1]:
                cell.fill = header_fill
                cell.font = header_font
                cell.alignment = Alignment(horizontal='center')
        
        return response
    export_to_excel.short_description = "Export selected attendance logs to Excel"


admin.site.register(Teammates, TeammatesAdmin)
admin.site.register(AttendanceLog, AttendanceLogAdmin)
