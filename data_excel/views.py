import pandas as pd
from django.http import HttpResponse
from django.contrib.admin.views.decorators import staff_member_required
from .services import get_attendance_for_date

@staff_member_required
def export_custom_date_view(request):
    selected_date = request.GET.get('date')
    
    # Call the service
    data = get_attendance_for_date(selected_date)
    
    # If no data, handle it
    if not data:
        return HttpResponse("No records found for this date.")

    # Convert to DataFrame
    df = pd.DataFrame(data)

    # Generate Excel response
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename="Attendance_{selected_date}.xlsx"'
    
    with pd.ExcelWriter(response, engine='openpyxl') as writer:
        df.to_excel(writer, index=False)
        
    return response