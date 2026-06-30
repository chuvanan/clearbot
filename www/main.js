document.addEventListener('click', (event) => {
  const target = event.target.closest('[data-snapshot-index]');
  if (!target) return;
  
  event.preventDefault();
  
  const traceInput = document.querySelector('#trace_num');
  const traceOffcanvas = document.querySelector('#trace');
  
  traceInput.value = target.dataset.snapshotIndex;
  traceInput.dispatchEvent(new Event('change'));
  
  bootstrap.Offcanvas.getOrCreateInstance(traceOffcanvas).show();
});

// Press Esc to interrupt an in-flight response. The Stop button only exists in
// the DOM while streaming, so this is a no-op otherwise.
document.addEventListener('keydown', (event) => {
  if (event.key !== 'Escape') return;
  const stopBtn = document.querySelector('#stop_stream');
  if (stopBtn) {
    event.preventDefault();
    stopBtn.click();
  }
});
