/**
 * Smart Kirana Enterprise - Universal Offline Purchase Order PDF Generator
 * Generates a clean A4 printable purchase order with ZERO historical or predicted prices.
 * Designed for offline physical store visits and shopkeeper verification.
 */

(function (window) {
    'use strict';

    function formatDateDisplay(d) {
        if (!d) return new Date().toLocaleDateString('mr-IN');
        if (typeof d === 'string' && d.includes('-')) {
            const parts = d.split('-');
            if (parts.length === 3 && parts[0].length === 4) {
                return `${parts[2]}/${parts[1]}/${parts[0]}`;
            }
        }
        return d;
    }

    function generatePurchaseOrderHTML(data) {
        const title = data.title || "किराणा खरेदी यादी";
        const dateStr = formatDateDisplay(data.date);
        const customerName = data.customerName || "स्मार्ट किराणा ग्राहक";
        const occasionType = data.occasionType || "नियमित";
        const items = data.items || [];

        let rowsHtml = '';
        items.forEach((item, index) => {
            const name = item.commodity_name || item.name || item.raw_input || `वस्तू #${index + 1}`;
            const qty = item.quantity || item.qty || 1;
            const unit = item.unit || "किलो";

            rowsHtml += `
                <tr>
                    <td style="text-align: center; font-weight: 600;">${index + 1}</td>
                    <td style="font-weight: 500; font-size: 14px;">${name}</td>
                    <td style="text-align: center; font-size: 14px;">${qty} ${unit}</td>
                    <td style="text-align: center;">
                        <div style="border: 1px dashed #718096; width: 85%; height: 26px; margin: 0 auto; background: #fff;"></div>
                    </td>
                    <td style="text-align: center;">
                        <div style="border: 1.5px solid #4a5568; width: 20px; height: 20px; margin: 0 auto; border-radius: 3px;"></div>
                    </td>
                </tr>
            `;
        });

        return `<!DOCTYPE html>
<html lang="mr">
<head>
    <meta charset="UTF-8">
    <title>${title} - खरेदी पावती (Offline PDF)</title>
    <style>
        @page {
            size: A4 portrait;
            margin: 12mm 15mm;
        }
        * {
            box-sizing: border-box;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Mukta", Roboto, "Noto Sans Devanagari", sans-serif;
        }
        body {
            margin: 0;
            padding: 10px;
            color: #1a202c;
            background: #ffffff;
            -webkit-print-color-adjust: exact;
            print-color-adjust: exact;
        }
        .header-card {
            border-bottom: 2.5px solid #2b6cb0;
            padding-bottom: 12px;
            margin-bottom: 15px;
            display: flex;
            justify-content: space-between;
            align-items: flex-end;
        }
        .brand-title {
            font-size: 22px;
            font-weight: 800;
            color: #2b6cb0;
            margin: 0 0 4px 0;
        }
        .list-title {
            font-size: 17px;
            font-weight: 700;
            color: #2d3748;
            margin: 0;
        }
        .meta-box {
            text-align: right;
            font-size: 13px;
            color: #4a5568;
            line-height: 1.5;
        }
        .po-table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 10px;
        }
        .po-table th {
            background-color: #edf2f7;
            color: #2d3748;
            border: 1px solid #cbd5e0;
            padding: 8px 10px;
            font-size: 13px;
            font-weight: 700;
            text-align: left;
        }
        .po-table td {
            border: 1px solid #e2e8f0;
            padding: 7px 10px;
            font-size: 13px;
        }
        .po-table tr:nth-child(even) {
            background-color: #f7fafc;
        }
        .footer-note {
            margin-top: 25px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-top: 1px solid #e2e8f0;
            padding-top: 12px;
            font-size: 12px;
            color: #718096;
        }
        .sign-box {
            text-align: right;
            font-size: 13px;
            color: #4a5568;
            padding-top: 15px;
        }
        @media print {
            body { padding: 0; }
            .no-print { display: none !important; }
        }
    </style>
</head>
<body>
    <div class="header-card">
        <div>
            <div class="brand-title">🛒 स्मार्ट किराणा खरेदी पावती (Store Purchase Order)</div>
            <div class="list-title">यादीचे शीर्षक: ${title} (${occasionType})</div>
        </div>
        <div class="meta-box">
            <div><strong>दिनांक:</strong> ${dateStr}</div>
            <div><strong>ग्राहक:</strong> ${customerName}</div>
            <div><strong>एकूण वस्तू:</strong> ${items.length}</div>
        </div>
    </div>

    <table class="po-table">
        <thead>
            <tr>
                <th style="width: 7%; text-align: center;">अ.क्र.</th>
                <th style="width: 48%;">वस्तूचे नाव व तपशील</th>
                <th style="width: 17%; text-align: center;">प्रमाण व एकक</th>
                <th style="width: 18%; text-align: center;">दुकानदार दर / रक्कम</th>
                <th style="width: 10%; text-align: center;">खूण [✓]</th>
            </tr>
        </thead>
        <tbody>
            ${rowsHtml}
        </tbody>
    </table>

    <div class="footer-note">
        <div>
            ℹ️ <em>टीप: ही यादी दुकानात खरेदी करताना प्रत्यक्षात भरण्यासाठी आहे. ऐतिहासिक किंवा अंदाजित दर छापलेले नाहीत.</em>
        </div>
        <div class="sign-box">
            दुकानदाराची स्वाक्षरी / शिक्का: _______________________
        </div>
    </div>
</body>
</html>`;
    }

    function downloadStorePurchaseOrderPDF(data) {
        const htmlContent = generatePurchaseOrderHTML(data);
        
        // Universal offline technique: Render inside a hidden iframe and trigger print/save
        let printFrame = document.getElementById('offline-po-print-iframe');
        if (!printFrame) {
            printFrame = document.createElement('iframe');
            printFrame.id = 'offline-po-print-iframe';
            printFrame.style.position = 'fixed';
            printFrame.style.right = '0';
            printFrame.style.bottom = '0';
            printFrame.style.width = '0';
            printFrame.style.height = '0';
            printFrame.style.border = '0';
            document.body.appendChild(printFrame);
        }

        const frameDoc = printFrame.contentWindow || printFrame.contentDocument;
        const doc = printFrame.contentDocument || printFrame.contentWindow.document;

        doc.open();
        doc.write(htmlContent);
        doc.close();

        setTimeout(() => {
            try {
                if (frameDoc.focus) frameDoc.focus();
                if (frameDoc.print) frameDoc.print();
            } catch (err) {
                console.error("Print frame trigger failed, falling back to popup window:", err);
                const win = window.open('', '_blank');
                win.document.write(htmlContent);
                win.document.close();
                win.focus();
                setTimeout(() => { win.print(); }, 250);
            }
        }, 300);
    }

    // Attach to window
    window.downloadStorePurchaseOrderPDF = downloadStorePurchaseOrderPDF;
    window.generatePurchaseOrderHTML = generatePurchaseOrderHTML;

})(window);
