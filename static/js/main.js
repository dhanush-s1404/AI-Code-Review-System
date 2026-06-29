// ─── AI Code Review System - Main JavaScript ────────────────────────────────

document.addEventListener("DOMContentLoaded", function () {
    // Auto-dismiss alerts after 5 seconds
    const alerts = document.querySelectorAll(".alert");
    alerts.forEach(function (alert) {
        setTimeout(function () {
            alert.style.opacity = "0";
            alert.style.transform = "translateY(-10px)";
            setTimeout(function () {
                alert.remove();
            }, 300);
        }, 5000);
    });

    // Tab key support in textarea (insert spaces instead of moving focus)
    const codeTextarea = document.getElementById("code");
    if (codeTextarea) {
        codeTextarea.addEventListener("keydown", function (e) {
            if (e.key === "Tab") {
                e.preventDefault();
                const start = this.selectionStart;
                const end = this.selectionEnd;
                this.value =
                    this.value.substring(0, start) +
                    "    " +
                    this.value.substring(end);
                this.selectionStart = this.selectionEnd = start + 4;
            }
        });

        // Line count indicator
        codeTextarea.addEventListener("input", updateLineCount);
        updateLineCount.call(codeTextarea);
    }

    function updateLineCount() {
        const textarea = document.getElementById("code");
        if (!textarea) return;
        const lines = textarea.value.split("\n").length;
        let counter = document.getElementById("line-counter");
        if (!counter) {
            counter = document.createElement("div");
            counter.id = "line-counter";
            counter.style.cssText =
                "font-size:0.8rem; color:#718096; margin-top:0.3rem;";
            textarea.parentNode.appendChild(counter);
        }
        counter.textContent = lines + " line" + (lines !== 1 ? "s" : "");
    }
});
