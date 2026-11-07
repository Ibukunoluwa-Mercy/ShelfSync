document.addEventListener("DOMContentLoaded", () => {
  const loginForm = document.getElementById("login-form");
  const emailInput = document.getElementById("email");
  const passwordInput = document.getElementById("password");
  const submitButton = document.getElementById("login-submit");
  const passwordToggle = document.getElementById("password-toggle");
  const capsLockWarning = document.getElementById("caps-lock-warning");

  // 1. Password show/hide toggle
  if (passwordToggle && passwordInput) {
    passwordToggle.addEventListener("click", () => {
      const isPassword = passwordInput.getAttribute("type") === "password";
      passwordInput.setAttribute("type", isPassword ? "text" : "password");
      passwordToggle.setAttribute(
        "aria-label",
        isPassword ? "Hide password" : "Show password"
      );
      const icon = passwordToggle.querySelector("i");
      if (icon) {
        icon.classList.toggle("fa-eye", !isPassword);
        icon.classList.toggle("fa-eye-slash", isPassword);
      }
    });
  }

  // 2. Caps Lock detection on password field
  const checkCapsLock = (event) => {
    if (!capsLockWarning) return;
    if (event.getModifierState && event.getModifierState("CapsLock")) {
      capsLockWarning.classList.remove("d-none");
    } else {
      capsLockWarning.classList.add("d-none");
    }
  };

  if (passwordInput) {
    passwordInput.addEventListener("keydown", checkCapsLock);
    passwordInput.addEventListener("keyup", checkCapsLock);
    passwordInput.addEventListener("blur", () => {
      if (capsLockWarning) {
        capsLockWarning.classList.add("d-none");
      }
    });
  }

  // 3. Client-side validation & submit lock
  if (loginForm) {
    loginForm.addEventListener("submit", (event) => {
      let hasError = false;
      const emailValue = (emailInput?.value || "").trim();
      const passwordValue = passwordInput?.value || "";

      // Clear existing client errors
      document.querySelectorAll(".client-invalid-feedback").forEach((el) => el.remove());
      emailInput?.classList.remove("is-invalid");
      passwordInput?.classList.remove("is-invalid");

      const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
      if (!emailValue) {
        showError(emailInput, "Please enter your email address.");
        hasError = true;
      } else if (!emailRegex.test(emailValue) || emailValue.length > 254) {
        showError(emailInput, "Please enter a valid email address.");
        hasError = true;
      }

      if (!passwordValue) {
        showError(passwordInput, "Please enter your password.");
        hasError = true;
      }

      if (hasError) {
        event.preventDefault();
        const firstInvalid = loginForm.querySelector(".is-invalid");
        if (firstInvalid) {
          firstInvalid.focus();
        }
        return;
      }

      // Valid: disable button & show spinner
      if (submitButton) {
        submitButton.disabled = true;
        submitButton.innerHTML = '<i class="fa-solid fa-spinner fa-spin me-2"></i>Signing in...';
      }
    });
  }

  function showError(inputElement, message) {
    if (!inputElement) return;
    inputElement.classList.add("is-invalid");
    const parentField = inputElement.closest(".login-field");
    if (parentField) {
      const errorDiv = document.createElement("div");
      errorDiv.className = "invalid-feedback d-block client-invalid-feedback";
      errorDiv.textContent = message;
      parentField.appendChild(errorDiv);
    }
  }

  // 4. Autofocus helper: focus email, or password if email already filled
  if (emailInput && emailInput.value.trim() !== "") {
    passwordInput?.focus();
  } else if (emailInput) {
    emailInput.focus();
  }

  // 5. Auto-dismiss success and info alerts after 6 seconds; keep danger and warning
  const alerts = document.querySelectorAll(".alert-success, .alert-info");
  alerts.forEach((alertElement) => {
    setTimeout(() => {
      alertElement.classList.remove("show");
      setTimeout(() => alertElement.remove(), 250);
    }, 6000);
  });
});

