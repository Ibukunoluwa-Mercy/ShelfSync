document.addEventListener("DOMContentLoaded", () => {
  const forgotForm = document.getElementById("forgot-form");
  const emailInput = document.getElementById("email");
  const submitButton = document.getElementById("forgot-submit");

  // Client-side validation on submit
  if (forgotForm) {
    forgotForm.addEventListener("submit", (event) => {
      const emailValue = (emailInput?.value || "").trim();
      const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

      // Clean existing errors
      document.querySelectorAll(".client-invalid-feedback").forEach((el) => el.remove());
      emailInput?.classList.remove("is-invalid");

      let hasError = false;
      if (!emailValue) {
        showError(emailInput, "Please enter your email address.");
        hasError = true;
      } else if (!emailRegex.test(emailValue) || emailValue.length > 254) {
        showError(emailInput, "Please enter a valid email address.");
        hasError = true;
      }

      if (hasError) {
        event.preventDefault();
        emailInput?.focus();
        return;
      }

      // Prevent duplicate submits & show progress spinner
      if (submitButton) {
        submitButton.disabled = true;
        submitButton.innerHTML = '<i class="fa-solid fa-spinner fa-spin me-2"></i>Sending...';
      }
    });
  }

  function showError(inputElement, message) {
    if (!inputElement) return;
    inputElement.classList.add("is-invalid");
    const parentField = inputElement.closest(".forgot-field");
    if (parentField) {
      const errorDiv = document.createElement("div");
      errorDiv.className = "invalid-feedback d-block client-invalid-feedback";
      errorDiv.textContent = message;
      parentField.appendChild(errorDiv);
    }
  }

  // Autofocus email input
  emailInput?.focus();

  // Auto-dismiss success/info alerts after 6 seconds; keep danger and warning
  const alerts = document.querySelectorAll(".alert-success, .alert-info");
  alerts.forEach((alertElement) => {
    setTimeout(() => {
      alertElement.classList.remove("show");
      setTimeout(() => alertElement.remove(), 250);
    }, 6000);
  });
});

