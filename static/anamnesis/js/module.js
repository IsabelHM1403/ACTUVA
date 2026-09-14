/* eslint-env browser */
/*
 * EduMed module front-end.
 *
 * Vanilla ES2020 — no framework, no build step.
 * Bootstraps from a JSON `<script id="module-data">` tag rendered by Django,
 * then renders the module page (step nav, patient card, step content,
 * flip cards, irrelevant items, dx feedback, summary, combos) from a single
 * `state` object via re-renders into `#module-root` and `#step-nav`.
 *
 * Mirrors the behaviour of the original Preact reference:
 * EduMed_UVa_completo/Anamnesis_Cefalea_v1.html
 *
 * TODO(phase-3): progressive reveal animation. Currently every section of an
 * active step renders at once (no "Reveal" gating). Functional parity, with
 * slightly more eager presentation than the Preact original.
 */

(function () {
  'use strict';

  // ─── State ──────────────────────────────────────────────────────────────────

  const dataEl = document.getElementById('module-data');
  if (!dataEl) {
    console.error('module.js: missing #module-data element');
    return;
  }
  const data = JSON.parse(dataEl.textContent);

  const state = {
    data: data,         // raw module payload (slug, steps, patient, progress…)
    activeStepIdx: 0,
    completedSteps: new Set(),
    flippedCards: {},   // { "stepIdx_cardIdx": true }
    knownCards: {},     // { "stepIdx_cardIdx": "knew" | "unknown" }
    openIrr: {},        // { "stepIdx_irrIdx": true }
    quizAnswers: {},
    quizAttempt: null,  // {answers, score, total, perQuestion} after submission
    view: 'steps',      // 'steps' | 'summary'
  };

  // ─── Helpers ────────────────────────────────────────────────────────────────

  /** Escape user-supplied text for safe interpolation into HTML. */
  function esc(s) {
    if (s == null) return '';
    return String(s)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  /** Read Django's CSRF token from the `csrftoken` cookie. */
  function getCsrfToken() {
    // Django's csrftoken cookie is set on any GET that uses CsrfViewMiddleware.
    const m = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/);
    return m ? m[1] : '';
  }

  // Convention: every event payload that involves the user's current step
  // location includes a 1-based `step` field (field name standardized as
  // `step`; do not introduce 0-based `stepIdx` keys).
  /**
   * Fire-and-forget POST to the event tracking endpoint. Never blocks the UI;
   * tracking failures are swallowed so the user experience is unaffected.
   * `keepalive: true` lets the request survive page navigation (e.g. the
   * virtual-patient CTA).
   */
  function postEvent(type, payload) {
    const slug = state.data.slug;
    fetch(`/anamnesis/${encodeURIComponent(slug)}/event/`, {
      method: 'POST',
      credentials: 'same-origin',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCsrfToken(),
      },
      body: JSON.stringify({ event_type: type, payload: payload || {} }),
      keepalive: true,
    }).catch(err => {
      // Tracking failure must not break user interaction.
      console.warn('Event tracking failed:', err);
    });
  }

  /** True if we should show the patient card / per-step content for `idx`. */
  function isStepIndex(idx) {
    return idx >= 0 && idx < data.steps.length;
  }

  /** Total entries in the step nav, including the synthetic "Resumen" pill. */
  function totalNavEntries() {
    return data.steps.length + 1; // + summary
  }

  /** Quote for the patient at the current step (clamped to available quotes). */
  function quoteForStep(idx) {
    if (!data.patient || !data.patient.quotes || data.patient.quotes.length === 0) return '';
    const i = Math.min(idx, data.patient.quotes.length - 1);
    return data.patient.quotes[i] || '';
  }

  // ─── Step nav ───────────────────────────────────────────────────────────────

  function renderStepNav() {
    const nav = document.getElementById('step-nav');
    if (!nav) return;

    const parts = [];
    data.steps.forEach((s, i) => {
      const active = state.view === 'steps' && state.activeStepIdx === i;
      const done = state.completedSteps.has(i) && !active;
      let cls = 'step-pill';
      if (active) cls += ' active';
      if (done) cls += ' done';
      const label = stepNavLabel(s);
      parts.push(
        `<button type="button" class="${cls}" data-action="goto-step" data-step="${i}">` +
          `<span>${esc(label)}</span>` +
        `</button>`
      );
    });

    // Synthetic summary pill
    const summaryActive = state.view === 'summary';
    let sumCls = 'step-pill summary';
    if (summaryActive) sumCls += ' active';
    parts.push(
      `<button type="button" class="${sumCls}" data-action="goto-summary">` +
        `<span>Resumen</span>` +
      `</button>`
    );

    nav.innerHTML = parts.join('');
  }

  /** Pick a short navigation label for a step. */
  function stepNavLabel(step) {
    // Try to grab the part before "—" / "-" / ":" if the title is long.
    const t = step.title || `Paso ${step.n}`;
    const match = t.match(/^([^—\-:]+)/);
    const head = (match ? match[1] : t).trim();
    if (head.length <= 18) return head;
    return head.slice(0, 16) + '…';
  }

  // ─── Patient card ───────────────────────────────────────────────────────────

  function renderPatientCard(idx) {
    if (!data.patient) return '';
    const quote = quoteForStep(idx);
    return `
      <div class="patient-card">
        <div class="patient-stripe"></div>
        <div class="patient-inner">
          <div class="patient-meta">
            <div class="patient-name-tag">${esc(data.patient.name)}</div>
            <div class="patient-age">${esc(data.patient.age)} años</div>
            <div class="patient-case">CASO CLÍNICO</div>
          </div>
          <div class="patient-quote-area">
            <div class="patient-quote-label">Dice el paciente</div>
            <div class="patient-quote">${esc(quote)}</div>
          </div>
        </div>
      </div>`;
  }

  // ─── Active step card ───────────────────────────────────────────────────────

  function renderActiveStep(idx) {
    const step = data.steps[idx];
    if (!step) return '<p>Paso no disponible.</p>';

    const numLabel = `Paso ${step.n} de ${data.steps.length}`;
    const deco = String(step.n).padStart(2, '0');

    const sections = [];

    // Think box
    if (step.think_box) {
      sections.push(`
        <div class="think-box">
          <div class="lbl">Piensa antes de continuar</div>
          <p>${esc(step.think_box)}</p>
        </div>`);
    }

    // TODO(phase-3): progressive reveal. For now everything below renders together.

    // Example question
    if (step.example_question) {
      sections.push(`
        <div class="example-q">
          <div class="lbl">Cómo preguntarlo</div>
          <p>${esc(step.example_question)}</p>
        </div>`);
    }

    // Tip box
    if (step.tip_box) {
      const paragraphs = step.tip_box
        .split(/\n\n+/)
        .map(p => `<p>${esc(p).replace(/\n/g, '<br>')}</p>`)
        .join('');
      sections.push(`
        <div class="tip-box">
          <div class="lbl">Pista</div>
          ${paragraphs}
        </div>`);
    }

    // Flip cards / irrelevant items / dx feedback are added in later commits.
    sections.push(renderFlipCards(idx, step));
    sections.push(renderIrrelevantItems(idx, step));
    sections.push(renderDxFeedback(idx, step));

    // Next step / summary CTA
    const lastStep = idx === data.steps.length - 1;
    const ctaLabel = lastStep ? 'Ver ficha resumen →' : 'Siguiente paso →';
    sections.push(`
      <button type="button" class="btn-next" data-action="next-step">${esc(ctaLabel)}</button>
    `);

    return `
      <div class="card">
        <div class="card-head">
          <div class="card-num">${esc(numLabel)}</div>
          <div class="card-title">${esc(step.title || '')}</div>
          <span class="card-head-deco" aria-hidden="true">${esc(deco)}</span>
        </div>
        <div class="card-body">
          ${renderPatientCard(idx)}
          ${sections.join('\n')}
        </div>
      </div>`;
  }

  // ─── Flip cards ─────────────────────────────────────────────────────────────

  function renderFlipCards(stepIdx, step) {
    if (!step.flip_cards || step.flip_cards.length === 0) return '';
    const cards = step.flip_cards.map((fc, i) => {
      const key = `${stepIdx}_${i}`;
      const flipped = state.flippedCards[key] === true;
      const known = state.knownCards[key]; // 'knew' | 'unknown' | undefined
      let frontCls = 'fc-front';
      if (known === 'knew') frontCls += ' knew-state';
      else if (known === 'unknown') frontCls += ' unknown-state';

      const stateBadge =
        known === 'knew'
          ? `<div class="fc-state-badge knew">✓ Dominada</div>`
          : known === 'unknown'
            ? `<div class="fc-state-badge unknown">↩ Para repasar</div>`
            : `<div class="fc-tap">tocar para ver</div>`;

      const knowledgeBtns = !known
        ? `
          <div class="knowledge-btns">
            <button type="button" class="btn-knew" data-action="knew" data-card-key="${esc(key)}">✓ Ya lo sabía</button>
            <button type="button" class="btn-unknown" data-action="unknown" data-card-key="${esc(key)}">↩ Repasar</button>
          </div>`
        : '';

      return `
        <div class="fc${flipped ? ' flipped' : ''}" data-action="flip-card" data-card-key="${esc(key)}">
          <div class="fc-inner">
            <div class="${frontCls}">
              <div class="fc-label">${esc(fc.label || '')}</div>
              ${fc.badge ? `<div class="fc-badge">${esc(fc.badge)}</div>` : ''}
              ${stateBadge}
            </div>
            <div class="fc-back">
              <div class="fc-back-header">
                <div class="fc-back-label">${esc(fc.label || '')}</div>
                <button type="button" class="fc-back-close" data-action="unflip-card" data-card-key="${esc(key)}">← Volver</button>
              </div>
              ${fc.badge ? `<span class="fc-back-badge">${esc(fc.badge)}</span>` : ''}
              <p>${esc(fc.back || '')}</p>
              ${knowledgeBtns}
            </div>
          </div>
        </div>`;
    });

    return `
      <div class="sec-label">¿Qué nos dice cada hallazgo? — Evalúa lo que sabes</div>
      <p class="fc-hint">Toca cada tarjeta para ver la orientación diagnóstica, luego indica si ya lo sabías</p>
      <div class="fc-grid">${cards.join('')}</div>`;
  }

  // ─── Irrelevant items (accordion) ───────────────────────────────────────────

  function renderIrrelevantItems(stepIdx, step) {
    if (!step.irrelevant || step.irrelevant.length === 0) return '';
    const rows = step.irrelevant.map((it, i) => {
      const key = `${stepIdx}_${i}`;
      const open = state.openIrr[key] === true;
      return `
        <div class="irr-item${open ? ' open' : ''}">
          <button type="button" class="irr-trigger" data-action="toggle-irr" data-irr-key="${esc(key)}">
            <span class="irr-name">${esc(it.name || '')}</span>
            ${it.badge ? `<span class="irr-badge">${esc(it.badge)}</span>` : ''}
            <span class="irr-arrow">▼</span>
          </button>
          <div class="irr-body">
            <div class="irr-text">${esc(it.body || '')}</div>
          </div>
        </div>`;
    });
    return `
      <div class="sec-label">Datos que no orientan el diagnóstico</div>
      <div class="irr-list">${rows.join('')}</div>`;
  }

  // ─── Dx feedback (per-step diagnostic clue analysis) ────────────────────────

  function renderDxFeedback(stepIdx, step) {
    if (!step.dx_feedback || step.dx_feedback.length === 0) return '';

    const blocks = step.dx_feedback.map((dx) => {
      const compat = ['neutral', 'positive', 'strong'].includes(dx.compat) ? dx.compat : 'neutral';
      const compatLabel =
        compat === 'strong' ? 'Evidencia fuerte' :
        compat === 'positive' ? 'Dato orientativo' :
        'Sin orientación';

      const quoteIdx = typeof dx.quote_idx === 'number' ? dx.quote_idx : stepIdx;
      const quote = data.patient && data.patient.quotes ? (data.patient.quotes[quoteIdx] || '') : '';
      const fits = (dx.fits_for || []).map(t => `<span class="dx-tag fits">${esc(t)}</span>`).join('');
      const rules = (dx.rules_out || []).map(t => `<span class="dx-tag rules">${esc(t)}</span>`).join('');

      const fitsBlock = fits
        ? `<div><div class="dx-tags-label fits">Apunta hacia</div><div class="dx-tags">${fits}</div></div>`
        : '';
      const rulesBlock = rules
        ? `<div><div class="dx-tags-label rules">Hace menos probable</div><div class="dx-tags">${rules}</div></div>`
        : '';

      const patientName = data.patient ? data.patient.name : 'el paciente';
      const quoteBox = quote ? `
        <div class="dx-quote-box">
          <div class="dx-quote-who">${esc(patientName)} dice</div>
          <div class="dx-quote-text">${esc(quote)}</div>
        </div>` : '';

      return `
        <div class="dx-fb">
          <div class="dx-fb-head">
            <div>
              <div class="dx-fb-eyebrow">Diagnóstico en construcción</div>
              <div class="dx-fb-title">¿Qué nos dice este dato?</div>
            </div>
            <div class="dx-compat ${compat}">${esc(compatLabel)}</div>
          </div>
          <div class="dx-fb-body">
            ${quoteBox}
            <p class="dx-interp">${esc(dx.interpretation || '')}</p>
            <div class="dx-tags-row">
              ${fitsBlock}
              ${rulesBlock}
            </div>
          </div>
        </div>`;
    });

    return blocks.join('\n');
  }

  // ─── Summary view ───────────────────────────────────────────────────────────

  function renderSummary() {
    const patient = data.patient;

    const dxName = patient ? patient.diagnosis : '';
    const dxKey = patient && Array.isArray(patient.diagnosis_key) ? patient.diagnosis_key : [];

    const dxReveal = dxName ? `
      <div class="dx-reveal">
        <div class="dx-reveal-top">
          <div class="dx-eyebrow">Diagnóstico del caso</div>
          <div class="dx-name">${esc(dxName)}</div>
        </div>
        ${dxKey.length ? `
          <div class="dx-evidence">
            <h4>Claves de la anamnesis que lo orientaban</h4>
            ${dxKey.map(c => `
              <div class="dx-clue"><div class="dx-clue-dot"></div><p>${esc(c)}</p></div>
            `).join('')}
          </div>` : ''}
      </div>` : '';

    const finalCard = `
      <div class="final-card">
        <div style="font-size:1.4rem;margin-bottom:.4rem;">✓</div>
        <h2 style="font-size:1rem;margin-bottom:.3rem;">Anamnesis completada</h2>
        <p style="font-size:.84rem;color:var(--ink-2);line-height:1.6;">
          La anamnesis estructurada es el primer paso del razonamiento clínico. Repasa las preguntas y los datos
          clave abajo, y prueba ahora con un paciente virtual.
        </p>
      </div>`;

    const summaryRows = data.steps.map(s => `
      <div class="q-row">
        <div class="q-num">${esc(String(s.n))}</div>
        <div>
          <div class="q-title">${esc(s.title || '')}</div>
          ${s.example_question ? `<div class="q-ex">${esc(s.example_question)}</div>` : ''}
        </div>
      </div>
    `).join('');

    const summaryCard = `
      <div class="summary-card">
        <div class="sc-head">Las ${data.steps.length} preguntas clave de la anamnesis</div>
        <div class="sc-body">${summaryRows}</div>
      </div>`;

    const combosBlock = renderCombos();

    const quizBlock = renderQuiz();

    const vpBlock = renderVirtualPatients();

    return `${dxReveal}${finalCard}${summaryCard}${combosBlock}${quizBlock}${vpBlock}`;
  }

  // ─── Quiz (summary view) ────────────────────────────────────────────────────

  function renderQuiz() {
    const quiz = data.quiz || [];
    if (quiz.length === 0) return '';
    const attempt = state.quizAttempt;

    const fieldsets = quiz.map((q, qIdx) => {
      const choices = (q.choices || []).map(c => {
        const isSelected = attempt && Number(attempt.answers[q.id]) === c.id;
        const fb = attempt && attempt.perQuestion ? attempt.perQuestion[q.id] : null;
        const isCorrectChoice = fb && fb.correctChoiceId === c.id;
        let cls = '';
        if (attempt) {
          if (isCorrectChoice) cls = ' is-correct';
          else if (isSelected && fb && !fb.correct) cls = ' is-wrong';
        }
        return `
          <label class="quiz-choice${cls}">
            <input type="radio" name="q-${esc(String(q.id))}" value="${esc(String(c.id))}"
              ${isSelected ? 'checked' : ''} ${attempt ? 'disabled' : ''}>
            <span>${esc(c.text)}</span>
          </label>`;
      }).join('');

      const fb = attempt && attempt.perQuestion ? attempt.perQuestion[q.id] : null;
      const explanationBlock = (attempt && fb && fb.explanation)
        ? `<div class="quiz-explanation">${esc(fb.explanation)}</div>`
        : '';

      return `
        <fieldset class="quiz-q">
          <legend class="quiz-q-text">${qIdx + 1}. ${esc(q.text)}</legend>
          ${choices}
          ${explanationBlock}
        </fieldset>`;
    }).join('');

    const footer = !attempt
      ? `<button type="submit" class="quiz-submit-btn">Comprobar respuestas</button>`
      : `<div class="quiz-result">Resultado: ${attempt.score}/${attempt.total}</div>`;

    return `
      <section class="quiz-section">
        <h3 class="quiz-section-title">Test rápido</h3>
        <p class="quiz-section-sub">Responde estas preguntas para comprobar lo que has aprendido.</p>
        <form class="quiz-form" data-action-form="quiz-submit">
          ${fieldsets}
          ${footer}
        </form>
      </section>`;
  }

  function submitQuiz(form) {
    const slug = state.data.slug;
    const answers = {};
    for (const q of (state.data.quiz || [])) {
      const sel = form.querySelector(`input[name="q-${q.id}"]:checked`);
      answers[q.id] = sel ? Number(sel.value) : null;
    }
    fetch(`/anamnesis/${encodeURIComponent(slug)}/quiz/`, {
      method: 'POST',
      credentials: 'same-origin',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCsrfToken(),
      },
      body: JSON.stringify({ answers: answers }),
    }).then(r => r.json()).then(result => {
      if (result && typeof result.score === 'number') {
        state.quizAttempt = result;
        render();
        postEvent('quiz_answer', { score: result.score, total: result.total });
      } else {
        console.warn('Quiz submit returned unexpected payload:', result);
      }
    }).catch(err => {
      console.warn('Quiz submit failed:', err);
    });
  }

  // ─── Virtual patient cards (summary view) ───────────────────────────────────

  function renderVirtualPatients() {
    const vps = data.virtual_patients || [];
    if (vps.length === 0) return '';
    return `
      <section class="vp-section">
        <h3 class="vp-section-title">Pacientes virtuales</h3>
        <p class="vp-section-sub">Practica la entrevista con un paciente simulado.</p>
        <div class="vp-grid">
          ${vps.map(vp => `
            <article class="vp-card${vp.available ? '' : ' vp-card-disabled'}">
              <div class="vp-card-name">${esc(vp.display_name)}</div>
              <div class="vp-card-age">${esc(String(vp.age))} años</div>
              <p class="vp-card-summary">${esc(vp.card_blurb)}</p>
              ${vp.available
                ? `<button type="button" class="vp-card-cta" data-action="open-vp" data-vp-id="${esc(String(vp.id))}">Hablar con ${esc(vp.display_name)}</button>`
                : `<div class="vp-card-unavailable">No disponible (ajusta las credenciales OpenAI)</div>`}
            </article>
          `).join('')}
        </div>
      </section>
    `;
  }

  function renderCombos() {
    if (!data.combos || data.combos.length === 0) return '';
    const cards = data.combos.map(c => {
      const compat = ['neutral', 'positive', 'strong'].includes(c.compat) ? c.compat : 'positive';
      const tagLabel =
        compat === 'strong' ? 'Alta especificidad' :
        compat === 'neutral' ? 'Diferencial' :
        'Orientativo';
      const syms = (c.symptoms || []).map(s => `<span class="combo-card-sym">${esc(s)}</span>`).join('');
      return `
        <div class="combo-card ${compat}">
          <div class="combo-card-head">
            <div class="combo-card-dx">${esc(c.dx || '')}</div>
            <div class="combo-card-tag">${esc(tagLabel)}</div>
          </div>
          <div class="combo-card-body">
            <div class="combo-card-symlbl">Características típicas</div>
            <div class="combo-card-syms">${syms}</div>
            ${c.key ? `<div class="combo-card-key">${esc(c.key)}</div>` : ''}
          </div>
        </div>`;
    }).join('');
    return `
      <div class="sec-label" style="margin-top:1.4rem;">Combinaciones clave → diagnóstico diferencial</div>
      <p class="fc-hint">La combinación de características es lo que permite el diagnóstico diferencial.</p>
      <div class="combo-grid">${cards}</div>`;
  }

  // ─── Top-level render ───────────────────────────────────────────────────────

  function renderProgress() {
    const fill = document.getElementById('progress-fill');
    if (!fill) return;
    const total = data.steps.length;
    let pct = 0;
    if (state.view === 'summary') {
      pct = 100;
    } else if (total > 0) {
      pct = (state.completedSteps.size / total) * 100;
    }
    fill.style.width = `${pct}%`;
  }

  function render() {
    renderStepNav();
    renderProgress();
    const root = document.getElementById('module-root');
    if (!root) return;
    if (state.view === 'summary') {
      root.innerHTML = `
        <div class="card">
          <div class="card-head">
            <div class="card-num">Resumen del caso</div>
            <div class="card-title">${esc(data.name || '')}</div>
          </div>
          <div class="card-body">
            ${renderSummary()}
          </div>
        </div>`;
    } else {
      root.innerHTML = renderActiveStep(state.activeStepIdx);
    }
  }

  // ─── Event delegation ───────────────────────────────────────────────────────

  function findActionTarget(e) {
    let node = e.target;
    while (node && node !== document.body) {
      if (node.dataset && node.dataset.action) return node;
      node = node.parentNode;
    }
    return null;
  }

  function onRootClick(e) {
    const target = findActionTarget(e);
    if (!target) return;
    const action = target.dataset.action;
    switch (action) {
      case 'flip-card': {
        const key = target.dataset.cardKey;
        state.flippedCards[key] = !state.flippedCards[key];
        postEvent('flip', { step: state.activeStepIdx + 1, card_key: key });
        render();
        break;
      }
      case 'unflip-card': {
        e.stopPropagation();
        const key = target.dataset.cardKey;
        state.flippedCards[key] = false;
        postEvent('flip', { step: state.activeStepIdx + 1, card_key: key, direction: 'unflip' });
        render();
        break;
      }
      case 'knew':
      case 'unknown': {
        e.stopPropagation();
        const key = target.dataset.cardKey;
        state.knownCards[key] = action;
        postEvent(action, { step: state.activeStepIdx + 1, card_key: key });
        render();
        break;
      }
      case 'toggle-irr': {
        const key = target.dataset.irrKey;
        const opened = !state.openIrr[key];
        state.openIrr[key] = opened;
        postEvent('dx_view', { step: state.activeStepIdx + 1, irr_key: key, opened: opened });
        render();
        break;
      }
      case 'next-step': {
        const cur = state.activeStepIdx;
        state.completedSteps.add(cur);
        if (cur < data.steps.length - 1) {
          state.activeStepIdx = cur + 1;
          // step is 1-based; the backend uses it to advance ModuleProgress.last_step.
          postEvent('step_open', { step: state.activeStepIdx + 1 });
        } else {
          state.view = 'summary';
          postEvent('complete', {});
        }
        window.scrollTo({ top: 0, behavior: 'smooth' });
        render();
        break;
      }
      case 'open-vp': {
        const vpId = target.dataset.vpId;
        if (!vpId) break;
        postEvent('vp_open', { vp_id: Number(vpId) });
        // Server picks up here: routes to chat start with the linked Assistant slug.
        window.location.href = `/anamnesis/vp/${encodeURIComponent(vpId)}/start/`;
        break;
      }
      default:
        break;
    }
  }

  function onNavClick(e) {
    const target = findActionTarget(e);
    if (!target) return;
    const action = target.dataset.action;
    if (action === 'goto-step') {
      const idx = parseInt(target.dataset.step, 10);
      if (isStepIndex(idx)) {
        state.view = 'steps';
        state.activeStepIdx = idx;
        // step is 1-based; idx is 0-based.
        postEvent('step_open', { step: idx + 1 });
        window.scrollTo({ top: 0, behavior: 'smooth' });
        render();
      }
    } else if (action === 'goto-summary') {
      state.view = 'summary';
      postEvent('complete', { source: 'summary_pill' });
      window.scrollTo({ top: 0, behavior: 'smooth' });
      render();
    }
  }

  // ─── Bootstrap ──────────────────────────────────────────────────────────────

  function init() {
    // Honor the server-side resume hint: if the student has already opened
    // a later step in a previous session, jump straight to it. last_step is
    // 1-based; activeStepIdx is 0-based — hence the -1. Capped to the last
    // step for defence against stale data.
    const progress = state.data.progress;
    if (progress && Number.isInteger(progress.last_step) && progress.last_step > 0) {
      state.activeStepIdx = Math.min(progress.last_step - 1, state.data.steps.length - 1);
    }

    const root = document.getElementById('module-root');
    const nav = document.getElementById('step-nav');
    if (root) {
      root.addEventListener('click', onRootClick);
      // The quiz form lives inside #module-root and is re-rendered on every
      // state change — so we listen on the parent (which is stable) instead
      // of the form node itself.
      root.addEventListener('submit', (e) => {
        const form = e.target.closest('form[data-action-form="quiz-submit"]');
        if (!form) return;
        e.preventDefault();
        submitQuiz(form);
      });
    }
    if (nav) nav.addEventListener('click', onNavClick);
    render();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
