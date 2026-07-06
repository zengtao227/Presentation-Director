(function(){
  window.HPX = window.HPX || {};
  window.HPX['aurora'] = function(el){
    const U = window.HPX._u;
    const k = U.canvas(el), ctx = k.ctx;

    const BANDS = [
      { y:0.25, col:[59,108,255],  a:0.28, sp:0.50, amp:0.07, ph:0.0 },
      { y:0.38, col:[122,92,255],  a:0.32, sp:0.35, amp:0.09, ph:1.2 },
      { y:0.50, col:[26,175,108],  a:0.22, sp:0.65, amp:0.06, ph:2.4 },
      { y:0.30, col:[255,92,138],  a:0.18, sp:0.45, amp:0.11, ph:0.7 },
      { y:0.55, col:[14,165,233],  a:0.20, sp:0.55, amp:0.08, ph:1.8 },
    ];

    const stop = U.loop((t) => {
      ctx.clearRect(0, 0, k.w, k.h);
      ctx.save();
      if (typeof ctx.filter !== 'undefined') ctx.filter = 'blur(38px)';

      for (const b of BANDS) {
        const cy = (b.y + Math.sin(t * b.sp + b.ph) * b.amp) * k.h;
        const bh = k.h * 0.22;
        const grad = ctx.createLinearGradient(0, cy - bh, 0, cy + bh);
        const [R,G,B] = b.col;
        grad.addColorStop(0,   `rgba(${R},${G},${B},0)`);
        grad.addColorStop(0.5, `rgba(${R},${G},${B},${b.a})`);
        grad.addColorStop(1,   `rgba(${R},${G},${B},0)`);

        ctx.beginPath();
        const pts = 10;
        ctx.moveTo(0, cy - bh);
        for (let i = 0; i <= pts; i++) {
          const x  = (i / pts) * k.w;
          const dy = Math.sin(t * b.sp * 1.4 + i * 0.9 + b.ph) * 18;
          ctx.lineTo(x, cy + dy);
        }
        ctx.lineTo(k.w, cy + bh);
        ctx.lineTo(0,   cy + bh);
        ctx.closePath();
        ctx.fillStyle = grad;
        ctx.fill();
      }
      ctx.restore();
    });

    return { stop(){ stop(); k.destroy(); } };
  };
})();
