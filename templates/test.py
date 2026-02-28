import win32print

def print_and_cut_final():
    # البحث عن الطابعة
    all_printers = win32print.EnumPrinters(win32print.PRINTER_ENUM_LOCAL)
    target_printer = next((p[2] for p in all_printers if "Xprinter" in p[2] or "Generic" in p[2]), None)

    if not target_printer:
        print("Printer not found!")
        return

    try:
        hPrinter = win32print.OpenPrinter(target_printer)
        pd = ("CMS_Final_Receipt", None, "RAW")
        win32print.StartDocPrinter(hPrinter, 1, pd)
        win32print.StartPagePrinter(hPrinter)

        # 1. تهيئة الطابعة (Reset)
        raw_data = b"\x1b\x40" 
        
        # 2. نص الفاتورة (Center Align)
        raw_data += b"\x1b\x61\x01" 
        raw_data += b"NEXUS CODE SYSTEMS\n"
        raw_data += b"--------------------------------\n"
        raw_data += b"Order Completed Successfully\n"
        raw_data += b"Developer: Fady Ashraf\n"
        raw_data += b"--------------------------------\n"

        # 3. دفع الورقة + القص (هنا السر)
        # \x1b\x64\x06 : تدفع الورقة 6 سطور للأمام
        # \x1d\x56\x01 : أمر القص الجزئي (Partial Cut) أو \x1d\x56\x00 للقص الكامل
        raw_data += b"\x1b\x64\x06" 
        raw_data += b"\x1d\x56\x01"

        win32print.WritePrinter(hPrinter, raw_data)
        
        win32print.EndPagePrinter(hPrinter)
        win32print.EndDocPrinter(hPrinter)
        win32print.ClosePrinter(hPrinter)
        print("Check the printer now!")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    print_and_cut_final()