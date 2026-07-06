(function(){
  window.HPX = window.HPX || {};
  window.HPX['light-rays'] = function(el){
    const U = window.HPX._u;
    const k = U.canvas(el), ctx = k.ctx;
    const ac = U.accent(el, '#3b6cff');

    const h2r = (h) => {
      const m = h.replace('#','').match(/.{2}/g);
      return m ? m.map(x => parseInt(x, 16)) : [59, 108, 255];
    };
    const [R, G, B] = h2r(ac);

    const N = 9;
    const rays = Array.from({length: N}, (_, i) => ({
      angle: -80 + (160 / (N - 1)) * i, // spread -80° to +80° from vertical
      width: U.rand(18, 55),
      alpha: U.rand(0.04, 0.13),
      sp:    U.rand(0.25, 0.6),
      ph:    Math.random() * Math.PI * 2,
    }));

    const stop = U.loop((t) => {
      ctx.clearRect(0, 0, k.w, k.h);
      const ox = k.w * 0.5;
      const oy = k.h * -0.05; // focal point slightly above top edge

      for (const ray of rays) {
        const fa  = (ray.angle * Math.PI) / 180 + Math.sin(t * ray.sp + ray.ph) * 0.04;
        const len = k.w * 1.5;
        const ex  = ox + Math.sin(fa) * len;
        const ey  = oy + Math.cos(fa) * len;
        const a   = ray.alpha * (0.7 + 0.3 * Math.sin(t * ray.sp * 1.3 + ray.ph));
        const w   = ray.width;
        const wx  = w * (1 + len / (k.w * 0.5));

        const grad = ctx.createLinearGradient(ox, oy, ex, ey);
        grad.addColorStop(0,   `rgba(${R},${G},${B},${(a * 4).toFixed(3)})`);
        grad.addColorStop(0.2, `rgba(${R},${G},${B},${a.toFixed(3)})`);
        grad.addColorStop(1,   `rgba(${R},${G},${B},0)`);

        // Perpendicular direction for trapezoid width
        const perp = fa - Math.PI / 2;
        const px = Math.sin(perp), py = Math.cos(perp);

        ctx.save();
        ctx.beginPath();
        ctx.moveTo(ox + px * (w / 2),  oy + py * (w / 2));
        ctx.lineTo(ex + px * (wx / 2), ey + py * (wx / 2));
        ctx.lineTo(ex - px * (wx / 2), ey - py * (wx / 2));
        ctx.lineTo(ox - px * (w / 2),  oy - py * (w / 2));
        ctx.closePath();
        ctx.fillStyle = grad;
        ctx.fill();
        ctx.restore();
      }
    });

    return { stop(){ stop(); k.destroy(); } };
  };
})();
