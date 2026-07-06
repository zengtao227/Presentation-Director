(function(){
  window.HPX = window.HPX || {};
  window.HPX['side-rays'] = function(el){
    const U = window.HPX._u;
    const k = U.canvas(el), ctx = k.ctx;
    const ac = U.accent(el, '#3b6cff');

    const h2r = (h) => {
      const m = h.replace('#','').match(/.{2}/g);
      return m ? m.map(x => parseInt(x, 16)) : [59, 108, 255];
    };
    const [R, G, B] = h2r(ac);

    // Five rays fanning from the left edge at mid-height
    const ANGLES = [-25, -10, 0, 12, 22]; // degrees

    const stop = U.loop((t) => {
      ctx.clearRect(0, 0, k.w, k.h);
      const oy = k.h * 0.5;

      for (let i = 0; i < ANGLES.length; i++) {
        const baseA = (ANGLES[i] * Math.PI) / 180;
        const angle = baseA + Math.sin(t * 0.4 + i * 0.8) * 0.03;
        const len   = k.w * 1.2;
        const alpha = 0.06 + 0.04 * Math.sin(t * 0.5 + i * 1.1);
        const w0    = 12 + i * 8;
        const wx    = w0 * (1 + (len / k.w) * 3);

        const grad = ctx.createLinearGradient(0, oy, Math.cos(angle) * len, oy + Math.sin(angle) * len);
        grad.addColorStop(0,   `rgba(${R},${G},${B},${(alpha * 6).toFixed(3)})`);
        grad.addColorStop(0.3, `rgba(${R},${G},${B},${(alpha * 2).toFixed(3)})`);
        grad.addColorStop(1,   `rgba(${R},${G},${B},0)`);

        ctx.save();
        ctx.translate(0, oy);
        ctx.rotate(angle);
        ctx.beginPath();
        ctx.moveTo(0,   -w0 / 2);
        ctx.lineTo(len, -wx / 2);
        ctx.lineTo(len,  wx / 2);
        ctx.lineTo(0,    w0 / 2);
        ctx.closePath();
        ctx.fillStyle = grad;
        ctx.fill();
        ctx.restore();
      }
    });

    return { stop(){ stop(); k.destroy(); } };
  };
})();
