/**
 * Smart Kirana Enterprise - WebRTC QR Scanner & UPI Decoder Engine
 * Hardware camera video stream, continuous canvas decoding loop,
 * BarcodeDetector with offline jsQR fallback, and automatic UPI intent dispatch.
 */

if (typeof window.KiranaQRScanner === 'undefined') {
  class KiranaQRScanner {
    constructor(options = {}) {
    this.videoElement = options.videoElement;
    this.onSuccess = options.onSuccess || (() => {});
    this.onError = options.onError || (() => {});
    this.onDecodedPayload = options.onDecodedPayload || null;
    this.getGrandTotal = options.getGrandTotal || (() => 0.0);

    this.stream = null;
    this.animationFrameId = null;
    this.scannerActive = false;

    // Dedicated in-memory canvas for continuous frame extraction
    this.canvas = document.createElement('canvas');
    this.ctx = this.canvas.getContext('2d', { willReadFrequently: true });

    // Initialize BarcodeDetector if natively supported
    this.barcodeDetector = null;
    if ('BarcodeDetector' in window) {
      try {
        this.barcodeDetector = new BarcodeDetector({ formats: ['qr_code'] });
      } catch (e) {
        console.warn('[QR Scanner] BarcodeDetector format qr_code not supported, using jsQR fallback');
        this.barcodeDetector = null;
      }
    }
  }

  /**
   * Initializes hardware media stream and activates the continuous decoding loop.
   */
  async startCamera() {
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      this.onError("आपल्या ब्राउझरमध्ये कॅमेरा सपोर्ट उपलब्ध नाही. कृपया मॅन्युअल VPA पर्याय वापरा.");
      return false;
    }

    // Stop any existing stream
    this.stopCamera();

    try {
      this.stream = await navigator.mediaDevices.getUserMedia({
        video: {
          facingMode: { ideal: 'environment' },
          width: { ideal: 1280 },
          height: { ideal: 720 }
        },
        audio: false
      });

      if (this.videoElement) {
        this.videoElement.srcObject = this.stream;
        this.videoElement.setAttribute('playsinline', 'true');
        this.videoElement.setAttribute('webkit-playsinline', 'true');
        this.videoElement.muted = true;
        await this.videoElement.play();
        this.scannerActive = true;
        this.scanTick();
      }
      return true;
    } catch (err) {
      console.error("[QR Scanner] Camera access failed:", err);
      this.onError("कॅमेरा सुरू करता आला नाही किंवा परवानगी नाकारली आहे. कृपया कॅमेरा परवानगी द्या किंवा इमेज अपलोड करा.");
      return false;
    }
  }

  /**
   * Safely halts active video tracks and cancels decoding animation frames.
   */
  stopCamera() {
    this.scannerActive = false;
    if (this.animationFrameId) {
      cancelAnimationFrame(this.animationFrameId);
      this.animationFrameId = null;
    }
    if (this.stream) {
      this.stream.getTracks().forEach(track => {
        try {
          track.stop();
        } catch (e) {
          console.warn('[QR Scanner] Error stopping media track:', e);
        }
      });
      this.stream = null;
    }
    if (this.videoElement) {
      this.videoElement.srcObject = null;
    }
  }

  /**
   * Continuous frame-by-frame analysis loop using requestAnimationFrame.
   * Extracts frames onto in-memory canvas and decodes using BarcodeDetector / jsQR.
   */
  scanTick() {
    if (!this.scannerActive || !this.videoElement) return;

    if (this.videoElement.readyState === this.videoElement.HAVE_ENOUGH_DATA) {
      const vWidth = this.videoElement.videoWidth;
      const vHeight = this.videoElement.videoHeight;

      if (vWidth > 0 && vHeight > 0) {
        this.canvas.width = vWidth;
        this.canvas.height = vHeight;
        this.ctx.drawImage(this.videoElement, 0, 0, vWidth, vHeight);

        // 1. Primary: Native BarcodeDetector if available
        if (this.barcodeDetector) {
          this.barcodeDetector.detect(this.canvas)
            .then(barcodes => {
              if (!this.scannerActive) return;
              if (barcodes && barcodes.length > 0 && barcodes[0].rawValue) {
                this.handleDecodedPayload(barcodes[0].rawValue);
                return;
              }
              this.fallbackJsQR(vWidth, vHeight);
            })
            .catch(() => {
              if (this.scannerActive) {
                this.fallbackJsQR(vWidth, vHeight);
              }
            });
          return;
        }

        // 2. Fallback: Offline jsQR engine
        if (this.fallbackJsQR(vWidth, vHeight)) {
          return;
        }
      }
    }

    if (this.scannerActive) {
      this.animationFrameId = requestAnimationFrame(() => this.scanTick());
    }
  }

  /**
   * Performs pixel analysis with offline jsQR engine.
   */
  fallbackJsQR(vWidth, vHeight) {
    if (window.jsQR) {
      try {
        const imageData = this.ctx.getImageData(0, 0, vWidth, vHeight);
        const code = window.jsQR(imageData.data, imageData.width, imageData.height, {
          inversionAttempts: "dontInvert"
        });
        if (code && code.data) {
          this.handleDecodedPayload(code.data);
          return true;
        }
      } catch (err) {
        console.warn("[QR Scanner] jsQR frame error:", err);
      }
    }
    if (this.scannerActive) {
      this.animationFrameId = requestAnimationFrame(() => this.scanTick());
    }
    return false;
  }

  /**
   * Static File Decode Handler: Decodes QR codes from uploaded images using the same canvas pipeline.
   */
  decodeFromImageFile(file) {
    if (!file) return;

    const img = new Image();
    const reader = new FileReader();

    reader.onload = (e) => {
      img.onload = async () => {
        try {
          this.canvas.width = img.width;
          this.canvas.height = img.height;
          this.ctx.drawImage(img, 0, 0, img.width, img.height);

          // 1. Try BarcodeDetector first
          if (this.barcodeDetector) {
            try {
              const barcodes = await this.barcodeDetector.detect(this.canvas);
              if (barcodes && barcodes.length > 0 && barcodes[0].rawValue) {
                this.handleDecodedPayload(barcodes[0].rawValue);
                return;
              }
            } catch (err) {
              console.warn("[QR Scanner] BarcodeDetector file scan failed, trying jsQR", err);
            }
          }

          // 2. Offline jsQR engine with high-contrast attempts
          if (window.jsQR) {
            const imageData = this.ctx.getImageData(0, 0, img.width, img.height);
            let code = window.jsQR(imageData.data, imageData.width, imageData.height, {
              inversionAttempts: "dontInvert"
            });
            if (!code || !code.data) {
              code = window.jsQR(imageData.data, imageData.width, imageData.height, {
                inversionAttempts: "attemptBoth"
              });
            }
            if (code && code.data) {
              this.handleDecodedPayload(code.data);
              return;
            }
          }

          this.onError("या फोटोमधून QR कोड वाचता आला नाही. कृपया स्पष्ट फोटो टाका किंवा थेट UPI आयडी भरा.");
        } catch (err) {
          console.error("[QR Scanner] File decode exception:", err);
          this.onError("इमेज वाचताना त्रुटी आली. कृपया मॅन्युअल VPA पर्याय वापरा.");
        }
      };
      img.src = e.target.result;
    };
    reader.readAsDataURL(file);
  }

  /**
   * Processes successfully decoded payload string, parses UPI query parameters,
   * auto-populates merchant fields, stops hardware tracks, and dispatches UPI intent.
   */
  handleDecodedPayload(rawPayload) {
    if (!rawPayload) return;

    // Immediately terminate camera tracks
    this.stopCamera();

    // Dismiss scanner modal
    const qrModal = document.getElementById('qr-modal');
    if (qrModal) qrModal.classList.remove('active');

    // Parse UPI payload
    const parsed = KiranaQRScanner.parseUPIString(rawPayload);

    // Auto-populate the merchant info fields on the interface
    const vpaInput = document.getElementById('merchant-vpa-input');
    const nameInput = document.getElementById('merchant-name-input');
    if (vpaInput && parsed.vpa) vpaInput.value = parsed.vpa;
    if (nameInput && parsed.pn) nameInput.value = parsed.pn;

    // Notify callback
    this.onSuccess(rawPayload, parsed);
  }

  /**
   * Helper to parse upi://pay URI or standard payment strings
   */
  static parseUPIString(text) {
    let vpa = "patil.kirana@upi";
    let pn = "पाटील किराणा स्टोअर्स";

    if (!text || typeof text !== 'string') return { vpa, pn, raw: text };

    const clean = text.trim();

    if (clean.startsWith('upi://pay') || clean.includes('pa=')) {
      try {
        const fakeUrl = clean.startsWith('http') ? clean : clean.replace(/^upi:\/\/pay\??/, 'http://upi.org/?');
        const url = new URL(fakeUrl);
        vpa = url.searchParams.get('pa') || vpa;
        pn = url.searchParams.get('pn') || pn;
      } catch (e) {
        // Fallback regex extraction
        const paMatch = clean.match(/[?&]pa=([^&]+)/);
        const pnMatch = clean.match(/[?&]pn=([^&]+)/);
        if (paMatch) vpa = decodeURIComponent(paMatch[1]);
        if (pnMatch) pn = decodeURIComponent(pnMatch[1]);
      }
    } else if (clean.includes('@')) {
      vpa = clean;
    }

    return { vpa, pn, raw: clean };
  }

  /**
   * Builds the official NPCI compliant UPI transaction URI with exact Grand Total override.
   */
  static buildUPIIntentUri(vpa, pn, grandTotal) {
    const totalVal = (typeof grandTotal === 'number' && grandTotal > 0) ? grandTotal.toFixed(2) : "0.00";
    const note = "किराणा बिल";
    return `upi://pay?pa=${encodeURIComponent(vpa)}&pn=${encodeURIComponent(pn)}&am=${totalVal}&cu=INR&tn=${encodeURIComponent(note)}`;
  }
  }
  // Global exposure
  window.KiranaQRScanner = KiranaQRScanner;
}
