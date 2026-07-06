(function(){
  window.HPX = window.HPX || {};
  window.HPX['dot-field'] = function(el){
    const U = window.HPX._u;
    const k = U.canvas(el), ctx = k.ctx;
    const ac = U.accent(el, '#3b6cff');
    const N = 120;
    const dots = Array.from({length: N}, () => ({
      x:  Math.random(),
      y:  Math.random(),
      r:  U.rand(0.8, 3.5),
      a:  U.rand(0.15, 0.7),
      sp: U.rand(0.3, 1.2),
      ph: Math.random() * Math.PI * 2,
    }));

    const stop = U.loop((t) => {
      ctx.clearRect(0, 0, k.w, k.h);
      for (const d of dots) {
        ctx.globalAlpha = d.a * (0.6 + 0.4 * Math.sin(t * d.sp + d.ph));
        ctx.fillStyle = ac;
        ctx.beginPath();
        ctx.arc(d.x * k.w, d.y * k.h, d.r, 0, Math.PI * 2);
        ctx.fill();
      }
      ctx.globalAlpha = 1;
    });

    return { stop(){ stop(); k.destroy(); } };
  };
})();
