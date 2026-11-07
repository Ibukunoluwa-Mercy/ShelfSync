document.addEventListener("DOMContentLoaded", () => {
  const resetForm = document.getElementById("reset-form");
  const newPasswordInput = document.getElementById("new_password");
  const confirmPasswordInput = document.getElementById("confirm_password");
  const submitButton = document.getElementById("reset-submit");
  const strengthProgress = document.getElementById("strength-progress");
  const strengthLabel = document.getElementById("strength-label");

  // Show/Hide password toggles
  document.querySelectorAll(".password-toggle").forEach((button) => {
    button.addEventListener("click", () => {
      const targetId = button.dataset.target;
      const input = document.getElementById(targetId);
      if (!input) return;
      const isPassword = input.type === "password";
      input.type = isPassword ? "text" : "password";
      button.setAttribute("aria-label", isPassword ? "Hide password" : "Show password");
      const icon = button.querySelector("i");
      if (icon) {
        icon.classList.toggle("fa-eye", !isPassword);
        icon.classList.toggle("fa-eye-slash", isPassword);
      }
    });
  });

  // Password strength meter
  if (newPasswordInput && strengthProgress && strengthLabel) {
    newPasswordInput.addEventListener("input", () => {
      const val = newPasswordInput.value;
      if (!val) {
        strengthProgress.style.width = "0%";
        strengthProgress.className = "";
        strengthLabel.textContent = "";
        strengthLabel.className = "";
        return;
      }

      let score = 0;
      if (val.length >= 8) score++;
      if (/[A-Za-z]/.test(val) && /\d/.test(val)) score++;
      if (val.length >= 12 && /[^A-Za-z0-9]/.test(val)) score++;

      if (score === 0 || val.length < 8) {
        strengthProgress.style.width = "33%";
        strengthProgress.className = "strength-weak";
        strengthLabel.textContent = "Weak";
        strengthLabel.className = "strength-weak";
      } else if (score === 1 || score === 2) {
        strengthProgress.style.width = "66%";
        strengthProgress.className = "strength-fair";
        strengthLabel.textContent = "Fair";
        strengthLabel.className = "strength-fair";
      } else {
        strengthProgress.style.width = "100%";
        strengthProgress.className = "strength-strong";
        strengthLabel.textContent = "Strong";
        strengthLabel.className = "strength-strong";
      }
    });
  }

  // Form submit validation & locking
  if (resetForm) {
    resetForm.addEventListener("submit", (event) => {
      const pw = newPasswordInput?.value || "";
      const confirmPw = confirmPasswordInput?.value || "";

      document.querySelectorAll(".client-invalid-feedback").forEach((el) => el.remove());
      newPasswordInput?.classList.remove("is-invalid");
      confirmPasswordInput?.classList.remove("is-invalid");

      let hasError = false;
      if (!pw) {
        showError(newPasswordInput, "Please enter a new password.");
        hasError = true;
      } else if (pw.length < 8 || pw.length > 128) {
        showError(newPasswordInput, "Password must be between 8 and 128 characters.");
        hasError = true;
      } else if (!/[A-Za-z]/.test(pw) || !/\d/.test(pw)) {
        showError(newPasswordInput, "Password must include at least one letter and one number.");
        hasError = true;
      }

      if (!confirmPw) {
        showError(confirmPasswordInput, "Please confirm your new password.");
        hasError = true;
      } else if (pw !== confirmPw) {
        showError(confirmPasswordInput, "Passwords do not match.");
        hasError = true;
      }

      if (hasError) {
        event.preventDefault();
        const first = resetForm.querySelector(".is-invalid");
        if (first) first.focus();
        return;
      }

      if (submitButton) {
        submitButton.disabled = true;
        submitButton.innerHTML = '<i class="fa-solid fa-spinner fa-spin me-2"></i>Resetting...';
      }
    });
  }

  function showError(inputElement, message) {
    if (!inputElement) return;
    inputElement.classList.add("is-invalid");
    const parentField = inputElement.closest(".reset-field");
    if (parentField) {
      const errorDiv = document.createElement("div");
      errorDiv.className = "invalid-feedback d-block client-invalid-feedback";
      errorDiv.textContent = message;
      parentField.appendChild(errorDiv);
    }
  }

  // Auto-dismiss alerts
  const alerts = document.querySelectorAll(".alert-success, .alert-info");
  alerts.forEach((alertElement) => {
    setTimeout(() => {
      alertElement.classList.remove("show");
      setTimeout(() => alertElement.remove(), 250);
    }, 6000);
  });
});

