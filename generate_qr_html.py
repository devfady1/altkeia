import os
import django
import qrcode
import base64
from io import BytesIO

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from tables.models import Table
from django.conf import settings

def generate_html_report():
    tables = Table.objects.all().order_by('floor', 'number')
    
    base_url = "http://127.0.0.1:8000"
    
    html_content = """
    <!DOCTYPE html>
    <html lang="ar" dir="rtl">
    <head>
        <meta charset="UTF-8">
        <title>باركود الترابيزات - كافيه التكية</title>
        <link href="https://fonts.googleapis.com/css2?family=Amiri:wght@400;700&family=Cairo:wght@400;700&display=swap" rel="stylesheet">
        <!-- إضافة FontAwesome للأيقونات -->
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
        <style>
            body {
                font-family: 'Cairo', sans-serif;
                background-color: #f4ece1;
                margin: 0;
            }
            .page {
                display: flex;
                flex-wrap: wrap;
                gap: 15px; /* مسافة أصغر بين الكروت */
                justify-content: center;
                align-content: flex-start;
                padding: 10px 10px;
                page-break-after: always;
                height: 297mm; /* ارتفاع ورقة A4 التقريبي */
                box-sizing: border-box;
            }
            .header {
                width: 100%;
                text-align: center;
                margin-bottom: 10px;
                color: #5c3a21;
                font-family: 'Amiri', serif;
            }
            .card {
                background: linear-gradient(135deg, #fdfbf7 0%, #f4e8d8 100%);
                border: 2px dashed #8b5a2b;
                border-radius: 12px;
                padding: 12px;
                text-align: center;
                width: 31%; /* لضمان ظهور 3 كروت في الصف */
                box-shadow: 0 4px 8px rgba(92, 58, 33, 0.15);
                page-break-inside: avoid;
                box-sizing: border-box;
                position: relative;
                /* تحديد أقصى ارتفاع للكارت لتجنب النزول لصفحة أخرى */
                max-height: 45%; 
            }
            .card::before {
                content: '';
                position: absolute;
                top: 4px; left: 4px; right: 4px; bottom: 4px;
                border: 1px solid rgba(139, 90, 43, 0.3);
                border-radius: 8px;
                pointer-events: none;
            }
            .welcome-text {
                font-family: 'Amiri', serif;
                font-size: 18px; /* تصغير الخط */
                font-weight: bold;
                color: #5c3a21;
                margin-bottom: 5px;
            }
            .qr-code {
                width: 100%;
                max-width: 140px; /* تصغير الباركود */
                height: auto;
                margin-bottom: 10px;
                border: 3px solid #fff;
                border-radius: 8px;
                box-shadow: 0 2px 5px rgba(0,0,0,0.1);
            }
            .table-name {
                font-size: 20px; /* تصغير الخط */
                font-weight: bold;
                color: #8b5a2b;
                margin-bottom: 2px;
                text-shadow: 1px 1px 0px rgba(255,255,255,0.7);
            }
            .table-floor {
                font-size: 14px; /* تصغير الخط */
                color: #6d4c41;
                margin-bottom: 8px;
                font-weight: bold;
            }
            .friendly-text {
                font-size: 12px; /* تصغير الخط */
                color: #4e342e;
                line-height: 1.4;
                background: rgba(255, 255, 255, 0.6);
                padding: 6px;
                border-radius: 6px;
                font-weight: 600;
            }
            .friendly-text i {
                color: #8b5a2b;
                margin: 0 3px;
            }
            
            @media print {
                body {
                    background-color: white;
                    -webkit-print-color-adjust: exact; 
                    print-color-adjust: exact; 
                }
                .card {
                    box-shadow: none;
                }
                .page {
                    padding: 0;
                    margin: 0;
                    height: 100vh;
                }
                @page {
                    margin: 10mm; /* تقليل هوامش الطباعة */
                    size: A4 portrait;
                }
            }
        </style>
    </head>
    <body>
    """
    
    for i in range(0, len(tables), 6):
        chunk = tables[i:i+6]
        
        html_content += '\\n        <div class="page">'
        
        if i == 0:
            html_content += """
            <div class="header">
                <h1 style="font-size: 28px; margin: 0;"><i class="fas fa-scroll"></i> قائمة باركود طاولات التكية <i class="fas fa-scroll"></i></h1>
            </div>
            """
            
        for table in chunk:
            url = f"{base_url}/qr/{table.uuid}/"
            
            qr_maker = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_H,
                box_size=10,
                border=2,
            )
            qr_maker.add_data(url)
            qr_maker.make(fit=True)
            
            qr_img = qr_maker.make_image(fill_color="#5c3a21", back_color="#fdfbf7")
            
            buf = BytesIO()
            qr_img.save(buf, format='PNG')
            img_str = base64.b64encode(buf.getvalue()).decode('utf-8')
            
            name = table.name or f"ترابيزة {table.number}"
            floor_name = table.floor.name if table.floor else ""
            
            html_content += f"""
                <div class="card">
                    <div class="welcome-text"><i class="fas fa-star" style="font-size: 12px; color:#d4af37;"></i> كافيه التكية يرحب بكم <i class="fas fa-star" style="font-size: 12px; color:#d4af37;"></i></div>
                    <img src="data:image/png;base64,{img_str}" alt="QR Code" class="qr-code">
                    <div class="table-name"><i class="fas fa-coffee" style="font-size:16px;"></i> {name} </div>
                    <div class="table-floor">{floor_name}</div>
                    <div class="friendly-text">
                        <i class="fas fa-wifi"></i> اتصل بشبكة المكان <br>
                        <i class="fas fa-bolt"></i> واطلب طلبك يجيلك أسرع!
                    </div>
                </div>
            """
            
        html_content += '\\n        </div>'
        
    html_content += """
    </body>
    </html>
    """
    
    with open("Tables_QR_Codes.html", "w", encoding="utf-8") as f:
        f.write(html_content)
        
    print("Done! Created Tables_QR_Codes.html with classic style and icons")

if __name__ == "__main__":
    generate_html_report()
