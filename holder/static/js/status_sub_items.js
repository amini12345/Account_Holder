/**
 * JavaScript برای مدیریت پویای زیر مجموعه‌های وضعیت کالا
 */

document.addEventListener('DOMContentLoaded', function() {
    const statusItemSelect = document.getElementById('id_status_item');
    const statusSubItemSelect = document.getElementById('id_status_sub_item');
    
    if (statusItemSelect && statusSubItemSelect) {
        // رویداد تغییر وضعیت اصلی کالا
        statusItemSelect.addEventListener('change', function() {
            const statusItem = this.value;
            
            // پاک کردن گزینه‌های قبلی
            statusSubItemSelect.innerHTML = '<option value="">---------</option>';
            
            if (statusItem) {
                // ارسال درخواست Ajax به سرور
                fetch(`/get-status-sub-items/?status_item=${statusItem}`)
                    .then(response => {
                        if (!response.ok) {
                            throw new Error('Network response was not ok');
                        }
                        return response.json();
                    })
                    .then(data => {
                        // افزودن گزینه‌های جدید
                        data.forEach(option => {
                            const opt = document.createElement('option');
                            opt.value = option.value;
                            opt.textContent = option.label;
                            statusSubItemSelect.appendChild(opt);
                        });
                        
                        // فعال کردن فیلد زیر مجموعه
                        statusSubItemSelect.disabled = false;
                    })
                    .catch(error => {
                        console.error('خطا در دریافت زیر مجموعه‌های وضعیت:', error);
                        statusSubItemSelect.disabled = true;
                    });
            } else {
                // غیرفعال کردن فیلد زیر مجموعه اگر وضعیت اصلی انتخاب نشده
                statusSubItemSelect.disabled = true;
            }
        });
        
        // در ابتدا فیلد زیر مجموعه را غیرفعال کن اگر وضعیت اصلی انتخاب نشده
        if (!statusItemSelect.value) {
            statusSubItemSelect.disabled = true;
        }
    }
});

/**
 * تابع کمکی برای بارگذاری زیر مجموعه‌ها در صورت ویرایش فرم
 */
function loadSubItemsForEdit(statusItem, selectedSubItem) {
    const statusSubItemSelect = document.getElementById('id_status_sub_item');
    
    if (statusItem && statusSubItemSelect) {
        fetch(`/get-status-sub-items/?status_item=${statusItem}`)
            .then(response => response.json())
            .then(data => {
                statusSubItemSelect.innerHTML = '<option value="">---------</option>';
                
                data.forEach(option => {
                    const opt = document.createElement('option');
                    opt.value = option.value;
                    opt.textContent = option.label;
                    
                    // انتخاب گزینه مورد نظر در صورت ویرایش
                    if (option.value === selectedSubItem) {
                        opt.selected = true;
                    }
                    
                    statusSubItemSelect.appendChild(opt);
                });
                
                statusSubItemSelect.disabled = false;
            })
            .catch(error => {
                console.error('خطا در بارگذاری زیر مجموعه‌ها:', error);
            });
    }
}