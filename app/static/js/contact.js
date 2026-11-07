/**
 * Smart Kirana Enterprise - Contact Page Controller (contact.html)
 * Form Validation, AJAX Ticket Generation, and Feedback Toasts
 */

document.addEventListener('DOMContentLoaded', () => {
  const form = document.getElementById('contact-support-form');
  const submitBtn = document.getElementById('contact-submit-btn');
  const feedbackBox = document.getElementById('contact-ticket-feedback');

  if (!form) return;

  form.addEventListener('submit', async (e) => {
    e.preventDefault();

    const name = document.getElementById('contact-name').value.trim();
    const mobile = document.getElementById('contact-mobile').value.trim();
    const category = document.getElementById('contact-category').value;
    const message = document.getElementById('contact-message').value.trim();

    // Client Validation
    if (name.length < 2) {
      showToast("कृपया आपले पूर्ण नाव टाका.", "error");
      return;
    }

    const digitsOnly = mobile.replace(/\D/g, '');
    if (digitsOnly.length < 10) {
      showToast("कृपया वैध १० अंकी मोबाईल नंबर टाका.", "error");
      return;
    }

    if (!category) {
      showToast("कृपया समस्येचा प्रकार निवडा.", "error");
      return;
    }

    if (message.length < 5) {
      showToast("कृपया संदेश किमान ५ अक्षरांचा लिहा.", "error");
      return;
    }

    submitBtn.disabled = true;
    submitBtn.innerHTML = `⏳ पाठवले जात आहे...`;

    try {
      const resp = await fetch('/api/v1/contact', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: name,
          mobile: digitsOnly,
          category: category,
          message: message
        })
      });

      const data = await resp.json();

      if (!resp.ok) {
        throw new Error(data.detail || "तक्रार पाठवण्यात अडचण आली.");
      }

      showToast("आपली चौकशी यशस्वीरित्या नोंदवली गेली!", "success");
      form.reset();

      if (feedbackBox) {
        feedbackBox.style.display = 'block';
        feedbackBox.innerHTML = `
          <div style="background:#F0FDF4;border:1px solid #86EFAC;border-radius:12px;padding:20px;text-align:center;">
            <div style="font-size:2rem;margin-bottom:8px;">✅</div>
            <h3 style="font-size:1.3rem;font-weight:700;color:#166534;margin-bottom:6px;">नोंदणी यशस्वी झाली!</h3>
            <p style="font-size:0.95rem;color:#1E293B;margin-bottom:12px;">${data.message_mr}</p>
            <div style="display:inline-block;background:#FFFFFF;border:1.5px dashed #16A34A;padding:8px 16px;border-radius:8px;font-weight:800;color:#166534;">
              तिकीट क्रमांक: ${data.ticket_number}
            </div>
          </div>
        `;
      }

    } catch (err) {
      showToast(err.message || "सर्व्हर एरर. कृपया पुन्हा प्रयत्न करा.", "error");
    } finally {
      submitBtn.disabled = false;
      submitBtn.innerHTML = `📩 संदेश पाठवा`;
    }
  });
});
