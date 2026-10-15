import { app } from "../../scripts/app.js";

const NODE_NAME = "AdvancedEmptyLatentImage";
const API = "/advanced-empty-latent/presets";
let presetCache = [];
let hiddenBuiltinCache = new Set();
let builtinPresetCache = [];

function gcd(a, b) {
  a = Math.abs(a);
  b = Math.abs(b);
  while (b) [a, b] = [b, a % b];
  return a || 1;
}

function aspectRatio(width, height) {
  const divisor = gcd(width, height);
  return `${width / divisor}:${height / divisor}`;
}

function nearestMultiple(value, multiple) {
  return Math.floor(value / multiple + 0.5) * multiple;
}

function widget(node, name) {
  return node.widgets?.find((item) => item.name === name);
}

function selectedPreset(node) {
  return presetCache.find((item) => item.name === widget(node, "preset")?.value);
}

function resolution(node) {
  const preset = selectedPreset(node);
  const width = Number(preset?.width ?? widget(node, "final_width")?.value);
  const height = Number(preset?.height ?? widget(node, "final_height")?.value);
  const scale = Number(widget(node, "scale")?.value);
  const multiple = Number(widget(node, "multiple")?.value);
  if (![width, height, scale, multiple].every(Number.isFinite) || width <= 0 || height <= 0 || scale <= 0 || multiple <= 0) return null;
  return {
    finalWidth: width,
    finalHeight: height,
    initialWidth: nearestMultiple(width / scale, multiple),
    initialHeight: nearestMultiple(height / scale, multiple),
  };
}

function updateNode(node) {
  const preset = widget(node, "preset")?.value;
  const isCustom = preset === "Custom";
  for (const name of ["final_width", "final_height"]) {
    const item = widget(node, name);
    if (item) item.disabled = !isCustom;
  }
  node.setDirtyCanvas?.(true, true);
}

function reserveFooter(node) {
  const minimum = node.computeSize?.() ?? node.size;
  const width = Math.max(node.size[0], minimum[0], 320);
  const height = Math.max(node.size[1], minimum[1] + 82);
  node.setSize?.([width, height]);
  node._advancedEmptyLatentManageBounds = [width - 126, height - 76, 116, 24];
}

async function fetchPresets() {
  const response = await fetch(API);
  if (!response.ok) throw new Error("Could not load resolution presets");
  const data = await response.json();
  presetCache = Array.isArray(data.presets) ? data.presets : [];
  builtinPresetCache = Array.isArray(data.builtin_presets) ? data.builtin_presets : [];
  hiddenBuiltinCache = new Set(
    Array.isArray(data.hidden_builtin_presets) ? data.hidden_builtin_presets : []
  );
  return presetCache;
}

function refreshCombo(node) {
  const combo = widget(node, "preset");
  if (!combo) return;
  const values = [...presetCache.map((item) => item.name), "Custom"];
  combo.options.values = values;
  if (!values.includes(combo.value)) combo.value = "Custom";
  updateNode(node);
}

function openDialog(title, body, zIndex = 10000) {
  const overlay = document.createElement("div");
  overlay.style.cssText = `position:fixed;inset:0;z-index:${zIndex};background:rgb(0 0 0 / 62%);display:grid;place-items:center;padding:24px;box-sizing:border-box`;
  const dialog = document.createElement("div");
  dialog.style.cssText = "background:linear-gradient(145deg,#30343b,#1d2026);color:#eef1f6;width:min(680px,100%);max-height:min(760px,90vh);overflow:auto;padding:24px;border:1px solid #596171;border-radius:12px;box-shadow:0 24px 70px #000c;font:14px system-ui,sans-serif";
  const heading = document.createElement("h2");
  heading.textContent = title;
  heading.style.cssText = "margin:0 0 6px;font-size:20px;letter-spacing:.01em";
  dialog.append(heading);
  dialog.append(body);
  overlay.append(dialog);
  overlay.addEventListener("click", (event) => { if (event.target === overlay) overlay.remove(); });
  document.body.append(overlay);
  return { overlay, dialog };
}

function editPreset(preset, onSave) {
  const form = document.createElement("form");
  form.innerHTML = `
    <p style="margin:0 0 18px;color:#b9c1cd">Final resolution used by this preset.</p>
    <label style="display:block;margin:14px 0 6px;font-weight:600">Preset Name<input required maxlength="128" name="name" style="display:block;width:100%;box-sizing:border-box;margin-top:6px;padding:9px;border-radius:6px"></label>
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px"><label style="font-weight:600">Width<input required min="1" step="1" type="number" name="width" style="display:block;width:100%;box-sizing:border-box;margin-top:6px;padding:9px;border-radius:6px"></label><label style="font-weight:600">Height<input required min="1" step="1" type="number" name="height" style="display:block;width:100%;box-sizing:border-box;margin-top:6px;padding:9px;border-radius:6px"></label></div>
    <p class="ratio" style="margin:16px 0;color:#9fd0ff"></p><div style="display:flex;justify-content:flex-end;gap:8px;margin-top:22px"><button type="button" class="cancel">Cancel</button> <button>Save Preset</button></div>`;
  const { overlay } = openDialog(preset ? "Edit Preset" : "Add Preset", form, 10001);
  form.elements.name.value = preset?.name ?? "";
  form.elements.width.value = preset?.width ?? 1440;
  form.elements.height.value = preset?.height ?? 3200;
  const updateRatio = () => {
    const width = Number(form.elements.width.value), height = Number(form.elements.height.value);
    form.querySelector(".ratio").textContent = width > 0 && height > 0 ? `Aspect Ratio: ${aspectRatio(width, height)}` : "Aspect Ratio: —";
  };
  form.elements.width.addEventListener("input", updateRatio);
  form.elements.height.addEventListener("input", updateRatio);
  updateRatio();
  form.querySelector(".cancel").onclick = () => overlay.remove();
  form.onsubmit = (event) => {
    event.preventDefault();
    onSave({ name: form.elements.name.value.trim(), width: Number(form.elements.width.value), height: Number(form.elements.height.value) });
    overlay.remove();
  };
}

async function managePresets(node) {
  try { await fetchPresets(); } catch (error) { alert(error.message); return; }
  const state = presetCache.map((item) => ({ ...item }));
  const hiddenBuiltins = new Set(hiddenBuiltinCache);
  const content = document.createElement("div");
  let selection = widget(node, "preset")?.value;
  if (!state.some((item) => item.name === selection)) selection = state[0]?.name;
  const render = () => {
    content.innerHTML = "";
    const help = document.createElement("p");
    help.textContent = "Built-in presets can be removed from this list. They can be restored later.";
    help.style.cssText = "margin:0 0 16px;color:#b9c1cd";
    content.append(help);
    const list = document.createElement("div");
    list.style.cssText = "display:grid;gap:8px;max-height:310px;overflow:auto;padding:2px";
    state.forEach((item) => {
      const row = document.createElement("button");
      row.type = "button";
      const active = item.name === selection;
      row.style.cssText = `display:grid;grid-template-columns:1fr auto;gap:4px 14px;text-align:left;padding:12px 14px;border-radius:8px;border:1px solid ${active ? "#68a9e6" : "#4a5260"};background:${active ? "#274865" : "#252a32"};color:#f4f7fb;cursor:pointer`;
      const name = document.createElement("strong"); name.textContent = item.name;
      const size = document.createElement("span"); size.textContent = `${item.width} × ${item.height}`; size.style.cssText = "font-weight:650;color:#b9ddff";
      const metadata = document.createElement("span"); metadata.textContent = item.builtin ? "Built-in · removable" : `Custom · ${aspectRatio(item.width, item.height)}`; metadata.style.cssText = "grid-column:1 / -1;color:#b7beca;font-size:12px";
      row.append(name, size, metadata);
      row.onclick = () => { selection = item.name; render(); };
      row.ondblclick = () => { if (!item.builtin) editPreset(item, (updated) => { Object.assign(item, updated); selection = updated.name; render(); }); };
      list.append(row);
    });
    content.append(list);
    const chosen = state.find((item) => item.name === selection);
    const actions = document.createElement("div");
    actions.style.cssText = "display:flex;gap:8px;flex-wrap:wrap;margin:18px 0";
    const button = (text, handler, disabled = false, title = "") => { const item = document.createElement("button"); item.type = "button"; item.textContent = text; item.disabled = disabled; item.title = title; item.style.cssText = disabled ? "opacity:.45;cursor:not-allowed" : ""; item.onclick = handler; actions.append(item); };
    button("Add", () => editPreset(null, (newPreset) => { state.push({ ...newPreset, builtin: false }); selection = newPreset.name; render(); }));
    button("Duplicate", () => { const item = state.find((preset) => preset.name === selection); if (item) editPreset({ ...item, name: `${item.name} Copy` }, (copy) => { state.push({ ...copy, builtin: false }); selection = copy.name; render(); }); });
    button("Edit", () => { const item = state.find((preset) => preset.name === selection); if (item) editPreset(item, (updated) => { Object.assign(item, updated); selection = updated.name; render(); }); }, !chosen || chosen.builtin, "Built-in presets cannot be edited. Duplicate one first.");
    button("Delete", () => { const item = state.find((preset) => preset.name === selection); if (item && confirm(`Remove '${item.name}' from the preset list?`)) { if (item.builtin) hiddenBuiltins.add(item.name); state.splice(state.indexOf(item), 1); selection = state[0]?.name; render(); } }, !chosen, "Remove the selected preset from the list.");
    if (hiddenBuiltins.size) button("Restore Built-ins", () => { hiddenBuiltins.clear(); const users = state.filter((item) => !item.builtin); state.splice(0, state.length, ...builtinPresetCache.map((item) => ({ ...item })), ...users); selection = state[0]?.name; render(); }, false, "Put all removed built-in presets back into the list.");
    content.append(actions);
    const footer = document.createElement("div"); footer.style.cssText = "display:flex;justify-content:flex-end;gap:8px;padding-top:14px;border-top:1px solid #48515f";
    const close = document.createElement("button"); close.type = "button"; close.textContent = "Close"; close.onclick = () => overlay.remove();
    const save = document.createElement("button"); save.type = "button"; save.textContent = "Save Changes"; save.onclick = async () => {
      const response = await fetch(API, { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ presets: state.filter((item) => !item.builtin), hidden_builtin_presets: [...hiddenBuiltins] }) });
      const data = await response.json(); if (!response.ok) { alert(data.error || "Unable to save presets"); return; }
      presetCache = Array.isArray(data.presets) ? data.presets : [];
      builtinPresetCache = Array.isArray(data.builtin_presets) ? data.builtin_presets : builtinPresetCache;
      hiddenBuiltinCache = new Set(data.hidden_builtin_presets ?? []);
      refreshCombo(node); overlay.remove();
    };
    footer.append(close, save); content.append(footer);
  };
  const { overlay } = openDialog("Resolution Presets", content);
  render();
}

app.registerExtension({
  name: "advanced-empty-latent-image.ui",
  async beforeRegisterNodeDef(nodeType, nodeData) {
    if (nodeData.name !== NODE_NAME) return;
    const originalCreated = nodeType.prototype.onNodeCreated;
    const originalDraw = nodeType.prototype.onDrawForeground;
    const originalMouseDown = nodeType.prototype.onMouseDown;
    nodeType.prototype.onNodeCreated = function () {
      originalCreated?.apply(this, arguments);
      for (const name of ["preset", "final_width", "final_height", "scale", "multiple"]) {
        const item = widget(this, name); const callback = item?.callback;
        if (item) item.callback = (...args) => { callback?.apply(item, args); updateNode(this); };
      }
      reserveFooter(this);
      fetchPresets().then(() => refreshCombo(this)).catch(() => updateNode(this));
      updateNode(this);
    };
    nodeType.prototype.onDrawForeground = function (ctx) {
      originalDraw?.apply(this, arguments);
      const result = resolution(this);
      if (!result || this.flags?.collapsed) return;
      const [x, y, width, height] = this._advancedEmptyLatentManageBounds ?? [this.size[0] - 126, this.size[1] - 76, 116, 24];
      ctx.save();
      ctx.fillStyle = "#263b4d"; ctx.strokeStyle = "#78b9ef"; ctx.lineWidth = 1;
      ctx.fillRect(x, y, width, height); ctx.strokeRect(x + 0.5, y + 0.5, width - 1, height - 1);
      ctx.fillStyle = "#d8efff"; ctx.font = "12px sans-serif"; ctx.textAlign = "center";
      ctx.fillText("Manage Presets", x + width / 2, y + 16);
      ctx.textAlign = "left"; ctx.fillStyle = "#a8d8ff";
      ctx.fillText(`Initial: ${result.initialWidth} × ${result.initialHeight}`, 10, this.size[1] - 38);
      ctx.fillText(`Final: ${result.finalWidth} × ${result.finalHeight}`, 10, this.size[1] - 20);
      ctx.restore();
    };
    nodeType.prototype.onMouseDown = function (event, pos) {
      const [x, y, width, height] = this._advancedEmptyLatentManageBounds ?? [];
      if (x !== undefined && pos[0] >= x && pos[0] <= x + width && pos[1] >= y && pos[1] <= y + height) {
        managePresets(this);
        return true;
      }
      return originalMouseDown?.apply(this, arguments);
    };
  },
});
