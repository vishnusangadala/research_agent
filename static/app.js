const form = document.querySelector("#researchForm");
const input = document.querySelector("#topicInput");
const messages = document.querySelector("#messages");
const statusPill = document.querySelector("#statusPill");
const submitButton = document.querySelector("#submitButton");
const resetButton = document.querySelector("#resetButton");

const initialMessage = messages.innerHTML;

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function setStatus(text, tone = "ready") {
  statusPill.textContent = text;
  statusPill.classList.toggle("busy", tone === "busy");
  statusPill.classList.toggle("error", tone === "error");
}

function scrollToBottom() {
  messages.scrollTop = messages.scrollHeight;
}

function addMessage(role, html) {
  const article = document.createElement("article");
  article.className = `message ${role}`;
  article.innerHTML = `
    <div class="avatar">${role === "user" ? "YOU" : "AI"}</div>
    <div class="bubble">${html}</div>
  `;
  messages.appendChild(article);
  scrollToBottom();
  return article;
}

function addTyping() {
  return addMessage(
    "assistant",
    `<div class="typing" aria-label="Research in progress">
      <span></span><span></span><span></span>
      <p>Running web, arXiv, and GitHub branches...</p>
    </div>`
  );
}

function listItems(items) {
  if (!items?.length) return "<p>No items returned.</p>";
  return `<ul>${items.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>`;
}

function sourceTags(sources) {
  return `<span class="source-tags">${(sources || [])
    .map((source) => `<span class="tag">${escapeHtml(source)}</span>`)
    .join("")}</span>`;
}

function renderClaims(claims) {
  if (!claims?.length) return "<p>No key claims returned.</p>";
  return `
    <ul class="claim-list">
      ${claims
        .map(
          (claim) => `
            <li>
              ${sourceTags(claim.sources)}
              ${escapeHtml(claim.claim)}
            </li>
          `
        )
        .join("")}
    </ul>
  `;
}

function renderBrief(data) {
  const brief = data.brief;
  const timings = data.timings || {};

  return `
    <div class="brief">
      <div class="meta-grid">
        <div class="metric">
          <strong>${Number(timings.total || 0).toFixed(1)}s</strong>
          <span>Total runtime</span>
        </div>
        <div class="metric">
          <strong>${Number(timings.fanout || 0).toFixed(1)}s</strong>
          <span>Parallel fan-out</span>
        </div>
        <div class="metric">
          <strong>${Number(timings.merge || 0).toFixed(1)}s</strong>
          <span>Merge</span>
        </div>
      </div>

      <section class="brief-section">
        <h3>Executive Summary</h3>
        <p>${escapeHtml(brief.executive_summary)}</p>
      </section>

      <section class="brief-section">
        <h3>Key Claims</h3>
        ${renderClaims(brief.key_claims)}
      </section>

      <section class="brief-section">
        <h3>State of Research</h3>
        <p>${escapeHtml(brief.state_of_research)}</p>
      </section>

      <section class="brief-section">
        <h3>State of Practice</h3>
        <p>${escapeHtml(brief.state_of_practice)}</p>
      </section>

      <section class="brief-section">
        <h3>State of Discourse</h3>
        <p>${escapeHtml(brief.state_of_discourse)}</p>
      </section>

      <section class="brief-section">
        <h3>Contradictions and Gaps</h3>
        <p>${escapeHtml(brief.contradictions_or_gaps)}</p>
      </section>

      <section class="brief-section">
        <h3>Recommended Next Steps</h3>
        ${listItems(brief.recommended_next_steps)}
      </section>

      <section class="brief-section">
        <h3>Top Resources</h3>
        ${listItems(brief.top_resources)}
      </section>
    </div>
  `;
}

function autoResize() {
  input.style.height = "auto";
  input.style.height = `${input.scrollHeight}px`;
}

async function runResearch(topic) {
  setStatus("Working", "busy");
  submitButton.disabled = true;
  resetButton.disabled = true;

  addMessage("user", `<p>${escapeHtml(topic)}</p>`);
  const typing = addTyping();

  try {
    const response = await fetch("/api/research", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ topic }),
    });
    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.error || "The research pipeline failed.");
    }

    typing.remove();
    addMessage("assistant", renderBrief(data));
    setStatus("Ready");
  } catch (error) {
    typing.remove();
    addMessage(
      "assistant",
      `<p><strong>Something stopped the pipeline.</strong></p>
       <p>${escapeHtml(error.message)}</p>`
    );
    setStatus("Error", "error");
  } finally {
    submitButton.disabled = false;
    resetButton.disabled = false;
    input.focus();
  }
}

form.addEventListener("submit", (event) => {
  event.preventDefault();
  const topic = input.value.trim();
  if (!topic || submitButton.disabled) return;
  input.value = "";
  autoResize();
  runResearch(topic);
});

input.addEventListener("input", autoResize);

input.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    form.requestSubmit();
  }
});

resetButton.addEventListener("click", () => {
  messages.innerHTML = initialMessage;
  input.value = "";
  autoResize();
  setStatus("Ready");
  input.focus();
});

autoResize();
