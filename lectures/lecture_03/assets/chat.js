// Fallback for Enter submission if Dash's native n_submit event is unavailable.
document.addEventListener("keydown", (event) => {
  const input = event.target;
  if (input.id !== "prompt" || event.key !== "Enter") return;
  event.preventDefault();
  const send = document.getElementById("send");
  if (send && !send.disabled) send.click();
});
