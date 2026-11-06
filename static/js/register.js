document.addEventListener("DOMContentLoaded", () => {
  const form = document.querySelector("#register-form");
  const password = document.querySelector("#password");
  const confirmation = document.querySelector("#confirm_password");
  const strengthProgress = document.querySelector("#strength-progress");
  const strengthLabel = document.querySelector("#strength-label");
  const matchHint = document.querySelector("#match-hint");

  document.querySelectorAll(".password-toggle").forEach((button) => {
    button.addEventListener("click", () => {
      const input = document.getElementById(button.dataset.target);
      const icon = button.querySelector("i");
      const showing = input.type === "text";
      input.type = showing ? "password" : "text";
      icon.classList.toggle("fa-eye", showing);
      icon.classList.toggle("fa-eye-slash", !showing);
      button.setAttribute("aria-label", showing ? "Show password" : "Hide password");
    });
  });

  function updateStrength() {
    const value = password.value;
    let score = 0;
    if (value.length >= 8) score += 1;
    if (/[A-Za-z]/.test(value)) score += 1;
    if (/\d/.test(value)) score += 1;
    if (/[^A-Za-z\d]/.test(value)) score += 1;
    const widths = ["0%", "25%", "50%", "75%", "100%"];
    const labels = ["", "Weak", "Weak", "Fair", "Strong"];
    strengthProgress.style.width = widths[score];
    strengthLabel.textContent = labels[score];
    strengthProgress.style.background = score >= 4 ? "var(--green)" : score >= 3 ? "var(--amber)" : "var(--danger)";
    strengthLabel.style.color = score >= 4 ? "var(--green)" : score >= 3 ? "var(--amber)" : "var(--danger)";
  }

  function updateMatch() {
    if (!confirmation.value) {
      matchHint.textContent = "";
      return;
    }
    matchHint.textContent = password.value === confirmation.value ? "Passwords match." : "Passwords do not match.";
    matchHint.style.color = password.value === confirmation.value ? "var(--green)" : "var(--danger)";
  }

  password.addEventListener("input", updateStrength);
  password.addEventListener("input", updateMatch);
  confirmation.addEventListener("input", updateMatch);

  form.addEventListener("submit", (event) => {
    const values = {
      full_name: document.querySelector("#full_name").value.trim().replace(/\s+/g, " "),
      email: document.querySelector("#email").value.trim().toLowerCase(),
    };
    const errors = [];
    if (!values.full_name) errors.push(["full_name", "Please enter your full name."]);
    else if (values.full_name.length < 2 || values.full_name.length > 100) errors.push(["full_name", "Full name must be between 2 and 100 characters."]);
    if (!values.email || values.email.length > 254 || !/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(values.email)) errors.push(["email", "Please enter a valid email address."]);
    if (!password.value) errors.push(["password", "Please enter a password."]);
    else if (password.value.length < 8 || password.value.length > 128) errors.push(["password", "Password must be between 8 and 128 characters."]);
    else if (!/[A-Za-z]/.test(password.value) || !/\d/.test(password.value)) errors.push(["password", "Password must include at least one letter and one number."]);
    else if (password.value.toLowerCase() === values.email) errors.push(["password", "Password cannot be the same as your email."]);
    if (password.value !== confirmation.value) errors.push(["confirm_password", "Passwords do not match."]);
    if (errors.length) {
      event.preventDefault();
      const firstInvalid = document.getElementById(errors[0][0]);
      errors.forEach(([field, message]) => {
        const input = document.getElementById(field);
        input.classList.add("is-invalid");
        let feedback = input.closest(".register-field").querySelector(".client-feedback");
        if (!feedback) {
          feedback = document.createElement("div");
          feedback.className = "invalid-feedback d-block client-feedback";
          input.closest(".register-field").append(feedback);
        }
        feedback.textContent = message;
      });
      firstInvalid.focus();
      return;
    }
    const submit = document.querySelector("#register-submit");
    submit.disabled = true;
    submit.innerHTML = '<i class="fa-solid fa-spinner fa-spin me-2"></i>Creating account...';
  });

  document.querySelectorAll(".alert:not(.alert-danger)").forEach((alert) => {
    window.setTimeout(() => alert.remove(), 6000);
  });
});
