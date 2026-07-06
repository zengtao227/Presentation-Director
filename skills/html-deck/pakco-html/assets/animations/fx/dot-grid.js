(function(){
  window.HPX = window.HPX || {};
  window.HPX['dot-grid'] = function(el){
    const U = window.HPX._u;
    const k = U.canvas(el), ctx = k.ctx;
    const ac = U.accent(el, '#3b6cff');
    const SPACING = 28, DOT_R = 1.5;
    const RIPPLE_SPEED = 2.2, RIPPLE_SCALE = 80;

    const stop = U.loop((t) => {
      ctx.clearRect(0, 0, k.w, k.h);
      const cols = Math.ceil(k.w / SPACING) + 1;
      const rows = Math.ceil(k.h / SPACING) + 1;
      const cx = k.w * 0.5, cy = k.h * 0.5;

      for (let r = 0; r <= rows; r++) {
        for (let c = 0; c <= cols; c++) {
          const x = c * SPACING, y = r * SPACING;
          const dist  = Math.sqrt((x - cx) ** 2 + (y - cy) ** 2);
          const wave  = Math.sin(dist / RIPPLE_SCALE - t * RIPPLE_SPEED);
          ctx.globalAlpha = 0.15 + 0.35 * ((wave + 1) / 2);
          ctx.fillStyle = ac;
          ctx.beginPath();
          ctx.arc(x, y, DOT_R, 0, Math.PI * 2);
          ctx.fill();
        }
      }
      ctx.globalAlpha = 1;
    });

    return { stop(){ stop(); k.destroy(); } };
  };
})();
