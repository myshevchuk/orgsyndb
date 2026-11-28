"""Tests for the Stimulus-based lab.js controllers, vendored Stimulus,
CSS Anchor Positioning, and template wiring (web-app: Page shell,
Scripts; modular-lab-script).
"""

import json
import re
import shutil
import subprocess
from pathlib import Path
from unittest import skipUnless
from urllib.parse import parse_qs, urlsplit

from django.test import SimpleTestCase, TestCase

from . import (REPO, make_batch, make_item, make_substance, make_task,
               make_user, make_vessel, page, shell_scripts, test_shell)
from .inventory_support import NEW_ITEM, NEW_NOTE
from .main_lists_support import must_outer_split
from .planning_support import PLAN, PlanningCase

NODE = shutil.which("node")
STATIC = REPO / "webapp" / "orgsyndb_web" / "static"
STIMULUS_DIR = STATIC / "stimulus"
STIMULUS_JS = STIMULUS_DIR / "stimulus.umd.js"
STIMULUS_LICENSE = STIMULUS_DIR / "LICENSE"
LAB_JS = STATIC / "lab.js"
LAB_CSS = STATIC / "lab.css"

EXPECTED_CONTROLLERS = [
    "master-detail",
    "split",
    "sortable-table",
    "dialog",
    "popover-anchor",
    "batch-narrow",
]

# Minimal DOM, selector, MutationObserver, DOMParser, and Idiomorph harness
# for loading real stimulus.umd.js and lab.js inside Node vm.
DOM_HARNESS = r"""
const fs = require("fs");
const vm = require("vm");

function createHarness(options = {}) {
  const observers = new Set();
  let flushScheduled = false;

  function scheduleFlush() {
    if (flushScheduled) return;
    flushScheduled = true;
    queueMicrotask(() => {
      flushScheduled = false;
      for (const obs of observers) obs._deliver();
    });
  }

  function recordMutation(target, record) {
    for (const obs of observers) {
      if (obs._matches(target, record)) {
        obs._queue.push(record);
        scheduleFlush();
      }
    }
  }

  function toKebab(name) {
    return name.replace(/[A-Z]/g, (m) => `-${m.toLowerCase()}`);
  }

  function toCamel(name) {
    return name.replace(/-([a-z0-9])/g, (_, ch) => ch.toUpperCase());
  }

  function splitTopLevel(text, sep) {
    const parts = [];
    let depth = 0;
    let quote = null;
    let start = 0;
    for (let i = 0; i < text.length; i += 1) {
      const ch = text[i];
      if (quote) {
        if (ch === quote) quote = null;
      } else if (ch === '"' || ch === "'") {
        quote = ch;
      } else if (ch === "(" || ch === "[") {
        depth += 1;
      } else if (ch === ")" || ch === "]") {
        depth -= 1;
      } else if (depth === 0 && ch === sep) {
        parts.push(text.slice(start, i).trim());
        start = i + 1;
      }
    }
    parts.push(text.slice(start).trim());
    return parts.filter(Boolean);
  }

  function tokenizeComplex(selector) {
    const tokens = [];
    let cur = "";
    let depth = 0;
    let quote = null;
    const pushCur = () => {
      if (cur) { tokens.push(cur); cur = ""; }
    };
    for (let i = 0; i < selector.length; i += 1) {
      const ch = selector[i];
      if (quote) {
        cur += ch;
        if (ch === quote) quote = null;
        continue;
      }
      if (ch === '"' || ch === "'") {
        quote = ch;
        cur += ch;
      } else if (ch === "(" || ch === "[") {
        depth += 1;
        cur += ch;
      } else if (ch === ")" || ch === "]") {
        depth -= 1;
        cur += ch;
      } else if (depth === 0 && (ch === " " || ch === ">")) {
        pushCur();
        if (ch === ">") {
          tokens.push(">");
        } else if (tokens[tokens.length - 1] !== " "
                   && tokens[tokens.length - 1] !== ">") {
          tokens.push(" ");
        }
      } else {
        cur += ch;
      }
    }
    pushCur();
    while (tokens[tokens.length - 1] === " ") tokens.pop();
    const cleaned = [];
    for (let i = 0; i < tokens.length; i += 1) {
      if (tokens[i] === " " && (tokens[i - 1] === ">"
          || tokens[i + 1] === ">")) {
        continue;
      }
      cleaned.push(tokens[i]);
    }
    return cleaned;
  }

  function matchCompound(el, compound, scopeEl) {
    if (!el || el.nodeType !== 1) return false;
    let i = 0;
    while (i < compound.length) {
      const ch = compound[i];
      if (ch === "#") {
        const rest = compound.slice(i + 1).match(/^[A-Za-z0-9_-]+/)[0];
        if (el.id !== rest) return false;
        i += 1 + rest.length;
      } else if (ch === ".") {
        const rest = compound.slice(i + 1).match(/^[A-Za-z0-9_-]+/)[0];
        if (!el.classList.contains(rest)) return false;
        i += 1 + rest.length;
      } else if (ch === "[") {
        const end = compound.indexOf("]", i);
        const body = compound.slice(i + 1, end);
        const eq = body.indexOf("=");
        if (eq < 0) {
          if (!el.hasAttribute(body.trim())) return false;
        } else {
          const name = body.slice(0, eq).trim();
          let want = body.slice(eq + 1).trim();
          if ((want.startsWith('"') && want.endsWith('"'))
              || (want.startsWith("'") && want.endsWith("'"))) {
            want = want.slice(1, -1);
          }
          if (el.getAttribute(name) !== want) return false;
        }
        i = end + 1;
      } else if (ch === ":") {
        const rest = compound.slice(i + 1);
        if (rest.startsWith("scope")) {
          if (el !== scopeEl) return false;
          i += 6;
        } else if (rest.startsWith("checked")) {
          if (!el.checked) return false;
          i += 8;
        } else if (rest.startsWith("disabled")) {
          if (!el.disabled) return false;
          i += 9;
        } else if (rest.startsWith("popover-open")) {
          if (!el.hasAttribute("popover") || !el._popoverOpen) return false;
          i += 13;
        } else if (rest.startsWith("not(") || rest.startsWith("is(")) {
          const isNot = rest.startsWith("not(");
          let depth = 0;
          let end = -1;
          for (let j = isNot ? 3 : 2; j < rest.length; j += 1) {
            if (rest[j] === "(") depth += 1;
            else if (rest[j] === ")") {
              depth -= 1;
              if (depth === 0) { end = j; break; }
            }
          }
          const inner = rest.slice(isNot ? 4 : 3, end);
          const matched = matchSelector(el, inner, scopeEl);
          if (isNot ? matched : !matched) return false;
          i += 1 + end + 1;
        } else {
          return false;
        }
      } else if (ch === "*") {
        i += 1;
      } else {
        const tag = compound.slice(i).match(/^[A-Za-z0-9_-]+/)[0];
        if (el.tagName !== tag.toUpperCase()) return false;
        i += tag.length;
      }
    }
    return true;
  }

  function matchComplex(el, tokens, idx, scopeEl) {
    if (!matchCompound(el, tokens[idx], scopeEl)) return false;
    if (idx === 0) return true;
    const comb = tokens[idx - 1];
    if (comb === ">") {
      return el.parentElement
        && matchComplex(el.parentElement, tokens, idx - 2, scopeEl);
    }
    for (let p = el.parentElement; p; p = p.parentElement) {
      if (matchComplex(p, tokens, idx - 2, scopeEl)) return true;
    }
    return false;
  }

  function matchSelector(el, selector, scopeEl = null) {
    if (!el || el.nodeType !== 1) return false;
    for (const part of splitTopLevel(selector, ",")) {
      const tokens = tokenizeComplex(part);
      if (tokens.length && matchComplex(el, tokens, tokens.length - 1,
                                        scopeEl)) {
        return true;
      }
    }
    return false;
  }

  class Event {
    constructor(type, init = {}) {
      this.type = type;
      this.bubbles = Boolean(init.bubbles);
      this.cancelable = Boolean(init.cancelable);
      this.defaultPrevented = false;
      this.target = null;
      this.currentTarget = null;
      this.eventPhase = 0;
      this._stopped = false;
      this._immediateStopped = false;
    }
    preventDefault() {
      if (this.cancelable) this.defaultPrevented = true;
    }
    stopPropagation() { this._stopped = true; }
    stopImmediatePropagation() {
      this._stopped = true;
      this._immediateStopped = true;
    }
  }

  class CustomEvent extends Event {
    constructor(type, init = {}) {
      super(type, init);
      this.detail = init.detail !== undefined ? init.detail : null;
    }
  }

  class Node {
    constructor(nodeType, ownerDocument) {
      this.nodeType = nodeType;
      this.ownerDocument = ownerDocument;
      this.parentNode = null;
      this._children = [];
      this._listeners = new Map();
    }
    get parentElement() {
      return this.parentNode && this.parentNode.nodeType === 1
        ? this.parentNode : null;
    }
    get childNodes() { return [...this._children]; }
    get children() { return this._children.filter((c) => c.nodeType === 1); }
    get firstChild() { return this._children[0] || null; }
    get nextSibling() {
      if (!this.parentNode) return null;
      const list = this.parentNode._children;
      const idx = list.indexOf(this);
      return idx >= 0 && idx + 1 < list.length ? list[idx + 1] : null;
    }
    get isConnected() {
      for (let n = this; n; n = n.parentNode) {
        if (n === this.ownerDocument) return true;
      }
      return false;
    }
    contains(other) {
      for (let n = other; n; n = n.parentNode) {
        if (n === this) return true;
      }
      return false;
    }
    _insertNode(node, ref = null) {
      if (node.parentNode) node.parentNode.removeChild(node);
      node.parentNode = this;
      if (ref && this._children.includes(ref)) {
        this._children.splice(this._children.indexOf(ref), 0, node);
      } else {
        this._children.push(node);
      }
      if (this.isConnected) {
        recordMutation(this, {
          type: "childList", target: this,
          addedNodes: [node], removedNodes: [],
        });
      }
      return node;
    }
    appendChild(node) { return this._insertNode(node, null); }
    insertBefore(node, ref) { return this._insertNode(node, ref); }
    removeChild(node) {
      const idx = this._children.indexOf(node);
      if (idx < 0) return node;
      const wasConnected = this.isConnected;
      this._children.splice(idx, 1);
      node.parentNode = null;
      if (wasConnected) {
        recordMutation(this, {
          type: "childList", target: this,
          addedNodes: [], removedNodes: [node],
        });
      }
      return node;
    }
    append(...nodes) {
      for (const n of nodes) {
        this.appendChild(typeof n === "string"
          ? new Text(n, this.ownerDocument) : n);
      }
    }
    prepend(...nodes) {
      const first = this._children[0] || null;
      for (const n of nodes) {
        this.insertBefore(typeof n === "string"
          ? new Text(n, this.ownerDocument) : n, first);
      }
    }
    remove() {
      if (this.parentNode) this.parentNode.removeChild(this);
    }
    replaceWith(...nodes) {
      const parent = this.parentNode;
      if (!parent) return;
      const ref = this.nextSibling;
      parent.removeChild(this);
      for (const n of nodes) {
        parent.insertBefore(typeof n === "string"
          ? new Text(n, this.ownerDocument) : n, ref);
      }
    }
    replaceChildren(...nodes) {
      for (const child of [...this._children]) this.removeChild(child);
      this.append(...nodes);
    }
    after(...nodes) {
      const parent = this.parentNode;
      if (!parent) return;
      const ref = this.nextSibling;
      for (const n of nodes) {
        parent.insertBefore(typeof n === "string"
          ? new Text(n, this.ownerDocument) : n, ref);
      }
    }
    addEventListener(type, fn, opts = false) {
      const capture = typeof opts === "boolean"
        ? opts : Boolean(opts && opts.capture);
      const once = typeof opts === "object" && Boolean(opts && opts.once);
      if (!this._listeners.has(type)) this._listeners.set(type, []);
      const list = this._listeners.get(type);
      if (!list.some((e) => e.fn === fn && e.capture === capture)) {
        list.push({ fn, capture, once });
      }
    }
    removeEventListener(type, fn, opts = false) {
      const capture = typeof opts === "boolean"
        ? opts : Boolean(opts && opts.capture);
      const list = this._listeners.get(type);
      if (!list) return;
      const idx = list.findIndex(
        (e) => e.fn === fn && e.capture === capture);
      if (idx >= 0) list.splice(idx, 1);
    }
    _invokeListeners(event, capturePhase) {
      const list = [...(this._listeners.get(event.type) || [])];
      for (const entry of list) {
        if (event._immediateStopped) break;
        if (entry.capture !== capturePhase) continue;
        if (entry.once) {
          this.removeEventListener(event.type, entry.fn, entry.capture);
        }
        if (typeof entry.fn === "function") {
          entry.fn.call(this, event);
        } else if (entry.fn && typeof entry.fn.handleEvent === "function") {
          entry.fn.handleEvent(event);
        }
      }
    }
    dispatchEvent(event) {
      event.target = this;
      const path = [];
      for (let n = this.parentNode; n; n = n.parentNode) path.push(n);
      if (this.ownerDocument && this.ownerDocument.defaultView) {
        path.push(this.ownerDocument.defaultView);
      }
      event.eventPhase = 1;
      for (let i = path.length - 1; i >= 0 && !event._stopped; i -= 1) {
        event.currentTarget = path[i];
        path[i]._invokeListeners(event, true);
      }
      if (!event._stopped) {
        event.eventPhase = 2;
        event.currentTarget = this;
        this._invokeListeners(event, true);
        if (!event._immediateStopped) this._invokeListeners(event, false);
      }
      if (event.bubbles && !event._stopped) {
        event.eventPhase = 3;
        for (let i = 0; i < path.length && !event._stopped; i += 1) {
          event.currentTarget = path[i];
          path[i]._invokeListeners(event, false);
        }
      }
      event.currentTarget = null;
      event.eventPhase = 0;
      return !event.defaultPrevented;
    }
    cloneNode(deep = false) {
      if (this.nodeType === 3) {
        return new Text(this.nodeValue, this.ownerDocument);
      }
      const copy = new HTMLElement(this.tagName, this.ownerDocument);
      for (const [k, v] of this._attrs) copy._attrs.set(k, v);
      copy._checked = this._checked;
      copy._selected = this._selected;
      copy.disabled = this.disabled;
      copy.hidden = this.hidden;
      if (deep) {
        for (const ch of this._children) copy.appendChild(ch.cloneNode(true));
      }
      return copy;
    }
  }
  Node.ELEMENT_NODE = 1;
  Node.TEXT_NODE = 3;
  Node.DOCUMENT_NODE = 9;

  class Text extends Node {
    constructor(data, ownerDocument) {
      super(3, ownerDocument);
      this.nodeValue = String(data);
    }
    get textContent() { return this.nodeValue; }
    set textContent(v) { this.nodeValue = String(v); }
  }

  class Element extends Node {
    constructor(tagName, ownerDocument) {
      super(1, ownerDocument);
      this.tagName = tagName.toUpperCase();
      this.localName = tagName.toLowerCase();
      this._attrs = new Map();
      this.style = {};
      this.inert = false;
      this.tabIndex = -1;
      this._checked = false;
      this._selected = undefined;
      this._value = undefined;
      this.disabled = false;
      this._form = null;
      this.offsetWidth = 200;
      this.offsetHeight = 160;
      this._rect = { left: 20, top: 20, right: 80, bottom: 44 };
      this.scrollTop = 0;
      this.scrollLeft = 0;
      this.popoverHiddenCount = 0;
      this._popoverOpen = false;
      const el = this;
      this.classList = {
        contains(name) {
          return (el.getAttribute("class") || "").split(/\s+/)
            .filter(Boolean).includes(name);
        },
        add(...names) {
          const cur = (el.getAttribute("class") || "").split(/\s+/)
            .filter(Boolean);
          for (const n of names) {
            if (!cur.includes(n)) cur.push(n);
          }
          el.setAttribute("class", cur.join(" "));
        },
        remove(...names) {
          const cur = (el.getAttribute("class") || "").split(/\s+/)
            .filter((n) => n && !names.includes(n));
          el.setAttribute("class", cur.join(" "));
        },
        toggle(name, force) {
          const has = this.contains(name);
          const want = force === undefined ? !has : Boolean(force);
          if (want && !has) this.add(name);
          if (!want && has) this.remove(name);
          return want;
        },
      };
      this.dataset = new Proxy({}, {
        get(_, prop) {
          if (typeof prop !== "string") return undefined;
          const attr = `data-${toKebab(prop)}`;
          return el._attrs.has(attr) ? el._attrs.get(attr) : undefined;
        },
        set(_, prop, val) {
          el.setAttribute(`data-${toKebab(prop)}`, String(val));
          return true;
        },
        deleteProperty(_, prop) {
          el.removeAttribute(`data-${toKebab(prop)}`);
          return true;
        },
        has(_, prop) {
          return el._attrs.has(`data-${toKebab(prop)}`);
        },
        ownKeys() {
          return [...el._attrs.keys()]
            .filter((k) => k.startsWith("data-"))
            .map((k) => toCamel(k.slice(5)));
        },
        getOwnPropertyDescriptor(_, prop) {
          const attr = `data-${toKebab(prop)}`;
          if (!el._attrs.has(attr)) return undefined;
          return {
            enumerable: true, configurable: true,
            value: el._attrs.get(attr),
          };
        },
      });
    }
    get id() { return this.getAttribute("id") || ""; }
    set id(v) { this.setAttribute("id", String(v)); }
    get className() { return this.getAttribute("class") || ""; }
    set className(v) { this.setAttribute("class", String(v)); }
    get name() { return this.getAttribute("name") || ""; }
    set name(v) { this.setAttribute("name", String(v)); }
    get type() {
      if (this.hasAttribute("type")) return this.getAttribute("type");
      if (this.tagName === "SELECT") return "select-one";
      if (this.tagName === "TEXTAREA") return "textarea";
      return "text";
    }
    set type(v) { this.setAttribute("type", String(v)); }
    get hidden() { return this.hasAttribute("hidden"); }
    set hidden(v) {
      if (v) this.setAttribute("hidden", "");
      else this.removeAttribute("hidden");
    }
    get open() { return this.hasAttribute("open"); }
    set open(v) {
      if (v) this.setAttribute("open", "");
      else this.removeAttribute("open");
    }
    get checked() { return this._checked; }
    set checked(v) { this._checked = Boolean(v); }
    get selected() {
      return this._selected !== undefined
        ? this._selected : this.hasAttribute("selected");
    }
    set selected(v) { this._selected = Boolean(v); }
    get options() { return this.querySelectorAll("option"); }
    get selectedOptions() {
      if (this.tagName !== "SELECT") return [];
      const opts = this.options;
      const chosen = opts.filter((o) => o.selected);
      if (chosen.length) return chosen;
      return opts[0] ? [opts[0]] : [];
    }
    get value() {
      if (this.tagName === "SELECT") {
        const chosen = this.selectedOptions[0];
        return chosen ? chosen.value : "";
      }
      if (this.tagName === "OPTION") {
        return this.hasAttribute("value")
          ? this.getAttribute("value") : this.textContent;
      }
      if (this._value !== undefined) return this._value;
      return this.getAttribute("value") || "";
    }
    set value(v) {
      const str = String(v);
      if (this.tagName === "SELECT") {
        for (const opt of this.options) {
          opt.selected = opt.value === str;
        }
        return;
      }
      this._value = str;
    }
    get form() {
      if (this._form) return this._form;
      if (this.hasAttribute("form")) {
        return this.ownerDocument.getElementById(this.getAttribute("form"));
      }
      return this.closest("form");
    }
    get elements() {
      if (this.tagName !== "FORM") return undefined;
      const controls = [
        ...this.querySelectorAll("input, select, textarea, button"),
      ];
      if (this.id) {
        for (const c of this.ownerDocument.querySelectorAll(
          `[form="${this.id}"]`)) {
          if (!controls.includes(c)) controls.push(c);
        }
      }
      controls.namedItem = (name) => controls.find(
        (c) => c.name === name) || null;
      return controls;
    }
    get href() {
      if (!this.hasAttribute("href")) return "";
      return new URL(
        this.getAttribute("href"), this.ownerDocument._location.href).href;
    }
    get tHead() {
      return this.children.find((c) => c.tagName === "THEAD") || null;
    }
    get tBodies() {
      return this.children.filter((c) => c.tagName === "TBODY");
    }
    get rows() {
      if (this.tagName === "TABLE") {
        const list = [];
        if (this.tHead) list.push(...this.tHead.rows);
        for (const tb of this.tBodies) list.push(...tb.rows);
        return list;
      }
      return this.children.filter((c) => c.tagName === "TR");
    }
    get cells() {
      return this.children.filter(
        (c) => c.tagName === "TH" || c.tagName === "TD");
    }
    get textContent() {
      return this._children.map((c) => c.textContent).join("");
    }
    set textContent(v) {
      for (const child of [...this._children]) this.removeChild(child);
      if (v !== "") this.appendChild(new Text(String(v), this.ownerDocument));
    }
    get attributes() {
      return [...this._attrs.entries()].map(([name, value]) => ({
        name, value,
      }));
    }
    getAttribute(name) {
      return this._attrs.has(name) ? this._attrs.get(name) : null;
    }
    hasAttribute(name) { return this._attrs.has(name); }
    getAttributeNames() { return [...this._attrs.keys()]; }
    setAttribute(name, value) {
      const oldValue = this._attrs.has(name) ? this._attrs.get(name) : null;
      const next = String(value);
      this._attrs.set(name, next);
      if (name === "checked") this._checked = true;
      if (this.isConnected && oldValue !== next) {
        recordMutation(this, {
          type: "attributes", target: this,
          attributeName: name, oldValue,
        });
      }
    }
    removeAttribute(name) {
      if (!this._attrs.has(name)) return;
      const oldValue = this._attrs.get(name);
      this._attrs.delete(name);
      if (name === "checked") this._checked = false;
      if (this.isConnected) {
        recordMutation(this, {
          type: "attributes", target: this,
          attributeName: name, oldValue,
        });
      }
    }
    matches(selector) { return matchSelector(this, selector, this); }
    closest(selector) {
      for (let el = this; el; el = el.parentElement) {
        if (matchSelector(el, selector, this)) return el;
      }
      return null;
    }
    querySelectorAll(selector) {
      const out = [];
      const walk = (node) => {
        for (const child of node.children) {
          if (matchSelector(child, selector, this)) out.push(child);
          walk(child);
        }
      };
      walk(this);
      return out;
    }
    querySelector(selector) {
      return this.querySelectorAll(selector)[0] || null;
    }
    focus() { this.ownerDocument.activeElement = this; }
    showModal() { this.open = true; }
    close() {
      if (!this.open) return;
      this.open = false;
      this.dispatchEvent(new Event("close"));
    }
    showPopover() { this._popoverOpen = true; }
    hidePopover() {
      this.popoverHiddenCount += 1;
      this._popoverOpen = false;
    }
    getBoundingClientRect() { return { ...this._rect }; }
  }

  class HTMLElement extends Element {}

  class Document extends Node {
    constructor(locationObj) {
      super(9, null);
      this.ownerDocument = this;
      this._location = locationObj;
      this.defaultView = null;
      this.title = "";
      this.cookie = "";
      this.activeElement = null;
      this.documentElement = new HTMLElement("html", this);
      this.documentElement.clientWidth = 1000;
      this.documentElement.clientHeight = 800;
      this.head = new HTMLElement("head", this);
      this.body = new HTMLElement("body", this);
      this._children.push(this.documentElement);
      this.documentElement.parentNode = this;
      this.documentElement.appendChild(this.head);
      this.documentElement.appendChild(this.body);
      this.activeElement = this.body;
    }
    createElement(tag) { return new HTMLElement(tag, this); }
    adoptNode(node) {
      if (node.parentNode) node.parentNode.removeChild(node);
      const fixDoc = (n) => {
        n.ownerDocument = this;
        for (const ch of n._children) fixDoc(ch);
      };
      fixDoc(node);
      return node;
    }
    querySelectorAll(selector) {
      return this.documentElement.querySelectorAll(selector);
    }
    querySelector(selector) {
      return this.documentElement.querySelector(selector);
    }
    getElementById(id) {
      const walk = (node) => {
        for (const child of node.children) {
          if (child.id === id) return child;
          const found = walk(child);
          if (found) return found;
        }
        return null;
      };
      return walk(this.documentElement);
    }
  }

  class MutationObserver {
    constructor(callback) {
      this._callback = callback;
      this._targets = [];
      this._queue = [];
    }
    observe(target, options = {}) {
      this._targets.push({ target, options });
      observers.add(this);
    }
    disconnect() {
      this._targets = [];
      this._queue = [];
      observers.delete(this);
    }
    takeRecords() { return this._queue.splice(0); }
    _matches(target, record) {
      return this._targets.some(({ target: root, options }) => {
        if (target !== root && !(options.subtree && root.contains(target))) {
          return false;
        }
        if (record.type === "childList") return Boolean(options.childList);
        if (record.type === "attributes") {
          if (!options.attributes) return false;
          if (options.attributeFilter
              && !options.attributeFilter.includes(record.attributeName)) {
            return false;
          }
          return true;
        }
        return false;
      });
    }
    _deliver() {
      const records = this.takeRecords();
      if (records.length) this._callback(records, this);
    }
  }

  const VOID = new Set([
    "area", "base", "br", "col", "embed", "hr", "img", "input",
    "link", "meta", "source", "track", "wbr",
  ]);

  function decodeEntities(text) {
    return text
      .replace(/&amp;/g, "&")
      .replace(/&lt;/g, "<")
      .replace(/&gt;/g, ">")
      .replace(/&quot;/g, '"')
      .replace(/&#39;/g, "'");
  }

  function parseHTMLInto(html, doc, container) {
    const stack = [container];
    const tokenRe = /<(\/?)([a-zA-Z0-9-]+)((?:"[^"]*"|'[^']*'|[^>"'])*)>|([^<]+)/g;
    let match;
    while ((match = tokenRe.exec(html)) !== null) {
      if (match[4] !== undefined) {
        stack[stack.length - 1].appendChild(
          new Text(decodeEntities(match[4]), doc));
        continue;
      }
      const closing = match[1] === "/";
      const tag = match[2].toLowerCase();
      const rawAttrs = match[3];
      if (closing) {
        for (let i = stack.length - 1; i > 0; i -= 1) {
          if (stack[i].localName === tag) {
            stack.length = i;
            break;
          }
        }
        continue;
      }
      const el = doc.createElement(tag);
      const attrRe =
        /([^\s=/>]+)(?:\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s>]+)))?/g;
      let am;
      while ((am = attrRe.exec(rawAttrs)) !== null) {
        if (am[1] === "/") continue;
        const val = am[2] ?? am[3] ?? am[4] ?? "";
        el.setAttribute(am[1], decodeEntities(val));
      }
      stack[stack.length - 1].appendChild(el);
      if (!VOID.has(tag) && !rawAttrs.trim().endsWith("/")) {
        stack.push(el);
      }
    }
  }

  class DOMParser {
    parseFromString(html, _type) {
      const doc = new Document(locationObj);
      const titleMatch = /<title>([^<]*)<\/title>/i.exec(html);
      if (titleMatch) doc.title = decodeEntities(titleMatch[1]);
      const bodyMatch = /<body[^>]*>([\s\S]*)<\/body>/i.exec(html);
      parseHTMLInto(bodyMatch ? bodyMatch[1] : html, doc, doc.body);
      return doc;
    }
  }

  function morphNode(oldNode, newNode, callbacks) {
    const beforeAttr = callbacks && callbacks.beforeAttributeUpdated;
    for (const { name, value } of newNode.attributes) {
      if (oldNode.getAttribute(name) === value) continue;
      if (beforeAttr && beforeAttr(name, oldNode, "update") === false) {
        continue;
      }
      oldNode.setAttribute(name, value);
    }
    for (const { name } of oldNode.attributes) {
      if (!newNode.hasAttribute(name)) {
        if (beforeAttr && beforeAttr(name, oldNode, "remove") === false) {
          continue;
        }
        oldNode.removeAttribute(name);
      }
    }
    const oldKids = [...oldNode.childNodes];
    const newKids = [...newNode.childNodes];
    const max = Math.max(oldKids.length, newKids.length);
    for (let i = 0; i < newKids.length; i += 1) {
      const next = newKids[i];
      const prev = oldKids[i];
      if (!prev) {
        oldNode.appendChild(oldNode.ownerDocument.adoptNode(
          next.cloneNode(true)));
      } else if (prev.nodeType === 3 && next.nodeType === 3) {
        prev.nodeValue = next.nodeValue;
      } else if (prev.nodeType === 1 && next.nodeType === 1
                 && prev.tagName === next.tagName
                 && (!prev.id || prev.id === next.id)) {
        morphNode(prev, next, callbacks);
      } else {
        const clone = oldNode.ownerDocument.adoptNode(next.cloneNode(true));
        prev.replaceWith(clone);
      }
    }
    for (let i = newKids.length; i < oldKids.length; i += 1) {
      oldKids[i].remove();
    }
    return oldNode;
  }

  const locationObj = {
    pathname: options.pathname || "/lab/inventory/",
    search: options.search || "",
    hash: options.hash || "",
    get href() {
      return `http://testserver${this.pathname}${this.search}${this.hash}`;
    },
  };
  const store = new Map(Object.entries(options.storage || {}));
  const localStorageObj = {
    getItem(k) { return store.has(k) ? store.get(k) : null; },
    setItem(k, v) { store.set(k, String(v)); },
    removeItem(k) { store.delete(k); },
  };
  const historyObj = {
    state: null,
    replaceCalls: [],
    replaceState(state, title, url) {
      this.state = state;
      this.replaceCalls.push(url);
      const parsed = new URL(url, locationObj.href);
      locationObj.pathname = parsed.pathname;
      locationObj.search = parsed.search;
      locationObj.hash = parsed.hash;
    },
  };
  const doc = new Document(locationObj);
  doc.documentElement.lang = options.lang || "de";
  if (options.bodyHtml) parseHTMLInto(options.bodyHtml, doc, doc.body);

  const htmxCalls = [];
  const htmxObj = {
    defineExtension() {},
    process() {},
    trigger(el, name) { htmxCalls.push({ kind: "trigger", el, name }); },
    ajax(method, url, opts) {
      htmxCalls.push({ kind: "ajax", method, url, opts });
    },
  };
  const morphCalls = [];
  const idiomorphObj = {
    morph(oldNode, newNode, opts = {}) {
      morphCalls.push({ oldId: oldNode.id, newId: newNode.id });
      return morphNode(oldNode, newNode, opts.callbacks);
    },
  };
  const cssObj = {
    supports: options.cssSupports || (() => false),
  };
  const win = new Node(0, doc);
  win.document = doc;
  win.Element = Element;
  win.HTMLElement = HTMLElement;
  win.Node = Node;
  win.Event = Event;
  win.CustomEvent = CustomEvent;
  win.MutationObserver = MutationObserver;
  win.DOMParser = DOMParser;
  win.localStorage = localStorageObj;
  win.location = locationObj;
  win.history = historyObj;
  win.innerHeight = options.innerHeight || 800;
  win.CSS = cssObj;
  win.matchMedia = () => ({ matches: Boolean(options.reducedMotion) });
  doc.defaultView = win;

  const context = {
    window: win,
    self: win,
    document: doc,
    Element,
    HTMLElement,
    Node,
    Event,
    CustomEvent,
    KeyboardEvent: class KeyboardEvent extends Event {},
    MouseEvent: class MouseEvent extends Event {},
    PointerEvent: class PointerEvent extends Event {},
    MutationObserver,
    DOMParser,
    CSS: cssObj,
    localStorage: localStorageObj,
    location: locationObj,
    history: historyObj,
    htmx: htmxObj,
    Idiomorph: idiomorphObj,
    fetch: options.fetch || (() => Promise.reject(new Error("no fetch"))),
    URL,
    URLSearchParams,
    Set,
    Map,
    Intl,
    Promise,
    Error,
    console,
    setTimeout,
    clearTimeout,
    queueMicrotask,
    requestAnimationFrame: (fn) => setTimeout(fn, 0),
    cancelAnimationFrame: (id) => clearTimeout(id),
  };
  context.globalThis = context;
  win.globalThis = context;
  vm.createContext(context);

  vm.runInContext(
    fs.readFileSync(process.argv[1], "utf8"), context,
    { filename: process.argv[1] });
  const startedApps = [];
  const origStart = context.Stimulus.Application.start;
  context.Stimulus.Application.start = function (...args) {
    const app = origStart.apply(this, args);
    startedApps.push(app);
    return app;
  };
  vm.runInContext(
    fs.readFileSync(process.argv[2], "utf8"), context,
    { filename: process.argv[2] });

  function fire(target, type, init = {}) {
    const ev = new Event(type, { bubbles: true, cancelable: true, ...init });
    for (const [k, v] of Object.entries(init)) {
      if (!(k in ev)) ev[k] = v;
    }
    target.dispatchEvent(ev);
    return ev;
  }

  function fireCustom(target, type, detail = {}, init = {}) {
    const ev = new CustomEvent(type, {
      bubbles: true, cancelable: true, detail, ...init,
    });
    target.dispatchEvent(ev);
    return ev;
  }

  const flush = () => new Promise((resolve) => setTimeout(resolve, 0));

  return {
    context, doc, win, startedApps, htmxCalls, morphCalls,
    historyObj, locationObj, localStorageObj, fire, fireCustom, flush,
  };
}
"""


def run_node_test(body: str) -> dict:
    """Execute a Node vm test script with DOM_HARNESS and return JSON."""
    script = (
        f"{DOM_HARNESS}\n(async () => {{\n{body}\n}})().catch((e) => {{\n"
        "  console.error(e && e.stack ? e.stack : e);\n"
        "  process.exit(1);\n});\n"
    )
    done = subprocess.run(
        [NODE, "-e", script, str(STIMULUS_JS), str(LAB_JS)],
        capture_output=True, text=True, check=True)
    return json.loads(done.stdout)


# A category list's page in the details view: an outer split of the
# substances and the pane of the selected substance `a`, which holds an
# inner split of its lots and the details of the selected lot `2`. The
# page names both selections in its address and its filter form.
NESTED_HTML = r"""
    <p id="list-summary"><a id="reset-link"
       href="/lab/inventory/intermediates/?selected=a&lot=2"
       hx-get="/lab/inventory/intermediates/?selected=a&lot=2">Reset</a></p>
    <form id="filters" class="lab-filters"
          hx-get="/lab/inventory/intermediates/">
      <span id="filter-selected">
        <input type="hidden" name="selected" value="a">
        <input type="hidden" name="lot" value="2">
      </span>
    </form>
    <div id="view-bar">
      <input type="radio" id="view-table" name="view" value="table">
      <input type="radio" id="view-details" name="view" value="details"
             checked>
      <button type="button" id="toggle"
              data-lab-action="click->split#toggle">Larger</button>
      <a id="outside-link" href="/lab/inventory/batches/new/"
         data-dialog>New batch</a>
    </div>
    <div id="outer" class="split split--outer split--rows"
         data-major="first" data-controller="split master-detail"
         data-view="details" data-cookie="intermediate-list-view"
         data-split-cookie-value="intermediate-list-split"
         data-master-detail-level-value="outer"
         data-master-detail-rows-value="item-rows"
         data-master-detail-pane-value="item-detail"
         data-master-detail-param-value="selected">
      <div class="split__pane">
        <div class="table-scroll table-sticky">
          <table class="main-table">
            <thead id="item-head"><tr><th><a id="sort-link"
              href="/lab/inventory/intermediates/?sort=amount&selected=a&lot=2"
              hx-get="/lab/inventory/intermediates/?sort=amount&selected=a&lot=2"
              >Amount</a></th></tr></thead>
            <tbody id="item-rows" data-refresh>
              <tr id="o1" data-item="a" aria-current="true"
                  hx-get="/lab/inventory/intermediates/a/"><td id="oc1">A</td>
              </tr>
              <tr id="o2" data-item="b"
                  hx-get="/lab/inventory/intermediates/b/"><td id="oc2">B</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
      <div class="split__pane">
        <aside id="item-detail" data-item="a" data-refresh>
          <header class="pane-head">
            <h2 id="item-detail-title">A</h2>
            <button type="button" popovertarget="item-actions">Actions
            </button>
            <div id="item-actions" popover><a id="item-edit"
              href="/lab/inventory/batches/new/?substance=a"
              data-dialog>New batch</a></div>
          </header>
          <div id="inner" class="split split--columns" data-major="first"
               data-controller="master-detail"
               data-master-detail-level-value="inner"
               data-master-detail-rows-value="lot-rows"
               data-master-detail-pane-value="lot-detail"
               data-master-detail-param-value="lot">
            <div class="split__pane">
              <table id="category-lots" class="main-table">
                <thead><tr><th>Vessel</th></tr></thead>
                <tbody id="lot-rows">
                  <tr id="l1" data-item="1"
                      hx-get="/lab/inventory/intermediates/a/lots/1/">
                    <td id="lc1">1</td></tr>
                  <tr id="l2" data-item="2" aria-current="true"
                      hx-get="/lab/inventory/intermediates/a/lots/2/">
                    <td id="lc2">2</td></tr>
                  <tr id="l3" data-item="3"
                      hx-get="/lab/inventory/intermediates/a/lots/3/">
                    <td id="lc3">3</td></tr>
                </tbody>
              </table>
            </div>
            <div class="split__pane">
              <aside id="lot-detail" data-item="2">
                <header class="pane-head">
                  <h2 id="lot-detail-title">#2</h2>
                  <button type="button" popovertarget="lot-actions">Actions
                  </button>
                  <div id="lot-actions" popover><a id="lot-edit"
                    href="/lab/inventory/vessels/2/edit/"
                    data-dialog>Edit</a></div>
                </header>
              </aside>
            </div>
          </div>
        </aside>
      </div>
    </div>
    <dialog id="lab-dialog" class="lab-dialog" data-controller="dialog">
      <div id="lab-dialog-body"></div>
      <button type="button" class="lab-dialog-close">Close</button>
    </dialog>
"""

# The same page after a booking: the lot `2` is gone, the pane names the
# lot `1`, and no row is marked, so that the script has to mark them.
NESTED_AFTER_SAVE = (
    "<!DOCTYPE html><html><head><title>Updated</title></head><body>"
    '<main id="main">' + NESTED_HTML
    .replace('<tr id="o1" data-item="a" aria-current="true"',
             '<tr id="o1" data-item="a"')
    .replace('<tr id="l2" data-item="2" aria-current="true"',
             '<tr id="l2" data-item="2"')
    .replace('<aside id="lot-detail" data-item="2">',
             '<aside id="lot-detail" data-item="1">')
    + "</main></body></html>")

# Swaps in the pane of the substance `b`, whose first lot is `11`.
NEXT_ITEM_PANE = r"""
const nextItemPane = () => {
  const parsed = new h.context.DOMParser().parseFromString(`
    <aside id="item-detail" data-item="b" data-refresh>
      <div id="inner" class="split split--columns" data-major="first"
           data-controller="master-detail"
           data-master-detail-level-value="inner"
           data-master-detail-rows-value="lot-rows"
           data-master-detail-pane-value="lot-detail"
           data-master-detail-param-value="lot">
        <div class="split__pane">
          <table id="category-lots" class="main-table"><tbody id="lot-rows">
            <tr id="m11" data-item="11"
                hx-get="/lab/inventory/intermediates/b/lots/11/">
              <td>11</td></tr>
          </tbody></table>
        </div>
        <div class="split__pane">
          <aside id="lot-detail" data-item="11"></aside>
        </div>
      </div>
    </aside>`, "text/html");
  return h.doc.adoptNode(parsed.body.children[0]);
};
"""


def nested_script(body: str, **options: str) -> str:
    """The Node script BODY on a harness holding ``NESTED_HTML``, with
    helpers: ``triggers()``, ``clicked(id)``, ``fields()``, ``flow(row,
    pane)`` and ``nextItemPane()``."""
    setup = (
        "const fetched = [];\n"
        "const h = createHarness({\n"
        '  pathname: "/lab/inventory/intermediates/",\n'
        '  search: "?selected=a&lot=2",\n'
        "  fetch: async (url) => {\n"
        "    fetched.push(String(url));\n"
        "    return { ok: true, status: 200, redirected: false,\n"
        "             async text() { return REFRESHED; } };\n"
        "  },\n"
        "  bodyHtml: `__NESTED__`,\n"
        "});\n"
        "await h.flush();\n"
        "const REFRESHED = `__AFTER__`;\n")
    helpers = r"""
const triggers = () => h.htmxCalls.filter((c) => c.kind === "trigger");
// The ids of the rows that one click on ID makes htmx trigger.
const clicked = (id) => {
  const before = triggers().length;
  h.fire(h.doc.getElementById(id), "click", { button: 0 });
  return triggers().slice(before).map((c) => c.el.id);
};
const stepped = (id, key) => {
  const before = triggers().length;
  h.fire(h.doc.getElementById(id), "keydown", { key });
  return triggers().slice(before).map((c) => c.el.id);
};
const field = (name) => {
  const found = h.doc.querySelector(`#filter-selected input[name=${name}]`);
  return found ? found.value : null;
};
const search = () => new URLSearchParams(h.locationObj.search);
// What htmx does once the row ROW has asked for PANE: the request, the
// swap of the pane and the end of the request.
const flow = (row, pane, old) => {
  h.fireCustom(row, "htmx:beforeRequest", { elt: row });
  old.replaceWith(pane);
  h.fireCustom(pane, "htmx:afterSwap", {
    target: pane, requestConfig: { elt: row } });
  h.fireCustom(row, "htmx:afterRequest", { elt: row });
};
const paneLike = (id, item) => {
  const found = h.doc.createElement("aside");
  found.id = id;
  found.setAttribute("data-item", item);
  return found;
};
"""
    after = NESTED_AFTER_SAVE.replace("`", "")
    return (setup.replace("__NESTED__", NESTED_HTML)
            .replace("__AFTER__", after)
            + helpers + NEXT_ITEM_PANE + body)


class VendoredStimulusTests(SimpleTestCase):
    """Static and CSP compliance checks for vendored Stimulus."""

    def test_vendored_stimulus_and_license_exist(self) -> None:
        self.assertTrue(STIMULUS_JS.is_file(), f"missing {STIMULUS_JS}")
        self.assertTrue(STIMULUS_LICENSE.is_file(),
                        f"missing {STIMULUS_LICENSE}")

    def test_vendored_stimulus_contains_no_eval_or_function_calls(
            self) -> None:
        source = STIMULUS_JS.read_text(encoding="utf-8")
        self.assertIsNone(
            re.search(r"\beval\s*\(|\bnew\s+Function\b|\bFunction\s*\(",
                      source))

    @skipUnless(NODE, "node is not installed")
    def test_vendored_stimulus_loads_with_code_generation_disabled(
            self) -> None:
        runner = (
            'const fs = require("fs");\n'
            'const vm = require("vm");\n'
            'const ctx = { window: {}, document: {}, Element: class {} };\n'
            'ctx.window = ctx;\n'
            'ctx.self = ctx;\n'
            'ctx.globalThis = ctx;\n'
            'vm.createContext(ctx, { codeGeneration: { strings: false } });\n'
            'vm.runInContext(fs.readFileSync(process.argv[1], "utf8"), ctx,\n'
            '                { filename: process.argv[1] });\n'
            'const s = ctx.Stimulus;\n'
            'process.stdout.write(JSON.stringify({\n'
            '  hasApp: typeof (s && s.Application) === "function",\n'
            '  hasCtrl: typeof (s && s.Controller) === "function",\n'
            '  hasSchema: Boolean(s && s.defaultSchema),\n'
            '}));\n'
        )
        done = subprocess.run(
            [NODE, "-e", runner, str(STIMULUS_JS)],
            capture_output=True, text=True, check=True)
        self.assertEqual(
            json.loads(done.stdout),
            {"hasApp": True, "hasCtrl": True, "hasSchema": True})


class AnchorPositioningCSSTests(SimpleTestCase):
    """CSS Anchor Positioning rules in lab.css."""

    def test_anchor_positioning_rules_present(self) -> None:
        css = LAB_CSS.read_text(encoding="utf-8")
        supports = re.search(
            r"@supports\s*\(anchor-name:\s*--a\)\s+and\s+"
            r"\(position-anchor:\s*--a\)\s+and\s+"
            r"\(top:\s*anchor\(bottom\)\)\s+and\s+"
            r"\(position-try-fallbacks:\s*flip-block\)",
            css)
        self.assertIsNotNone(supports, "missing @supports anchor check")
        self.assertRegex(
            css,
            r"@position-try\s+--popover-below-inset\s*\{[^}]*left:\s*16px")
        self.assertRegex(
            css,
            r"@position-try\s+--popover-above-inset\s*\{[^}]*left:\s*16px")
        self.assertRegex(
            css,
            r"@position-try\s+--popover-fit\s*\{[^}]*"
            r"bottom:\s*16px[^}]*left:\s*16px")
        self.assertRegex(
            css,
            r"position-try-fallbacks:[^;]*flip-block[^;]*"
            r"--popover-below-inset[^;]*--popover-above-inset[^;]*"
            r"--popover-fit")
        for popover_id in ("#stock-menu", "#more-filters"):
            with self.subTest(popover=popover_id):
                self.assertIn(popover_id, css)
                self.assertRegex(
                    css,
                    rf"{re.escape(popover_id)}[^{{]*\{{[^}}]*"
                    r"position-anchor:\s*--")
                target = popover_id.lstrip("#")
                self.assertRegex(
                    css,
                    rf'popovertarget="{re.escape(target)}"[^{{]*\{{[^}}]*'
                    r"anchor-name:\s*--")


@skipUnless(NODE, "node is not installed")
class StimulusControllerTests(SimpleTestCase):
    """Unit and lifecycle checks for Stimulus controllers in lab.js."""

    def test_custom_schema_and_all_controllers_registered(self) -> None:
        result = run_node_test(r"""
const h = createHarness({
  bodyHtml: `
    <div id="probe-lab" data-controller="probe"
         data-lab-action="click->probe#hit"></div>
    <div id="probe-std" data-controller="probe"
         data-action="click->probe#hit"></div>
  `,
});
await h.flush();
const app = h.startedApps[0];
const registered = [...app.router.modulesByIdentifier.keys()].sort();
const hits = [];
app.register("probe", class extends h.context.Stimulus.Controller {
  hit() { hits.push(this.element.id); }
});
await h.flush();
h.fire(h.doc.getElementById("probe-std"), "click", { button: 0 });
h.fire(h.doc.getElementById("probe-lab"), "click", { button: 0 });
process.stdout.write(JSON.stringify({
  started: h.startedApps.length,
  actionAttribute: app.schema.actionAttribute,
  registered,
  hits,
}));
""")
        self.assertEqual(result["started"], 1)
        self.assertEqual(result["actionAttribute"], "data-lab-action")
        self.assertEqual(result["registered"], sorted(EXPECTED_CONTROLLERS))
        self.assertEqual(result["hits"], ["probe-lab"])

    def test_popover_anchor_native_vs_fallback(self) -> None:
        body_html = r"""
<button type="button" id="btn" popovertarget="stock-menu">Stock</button>
<div id="stock-menu" class="lab-popup" popover
     data-controller="popover-anchor"></div>
"""
        native = run_node_test(
            f"const h = createHarness({{\n"
            f"  bodyHtml: `{body_html}`,\n"
            f"  cssSupports: () => true,\n"
            f"}});\n"
            r"""
await h.flush();
const pop = h.doc.getElementById("stock-menu");
h.fire(pop, "toggle", { newState: "open", bubbles: false });
process.stdout.write(JSON.stringify({
  placed: pop.hasAttribute("data-placed"),
  left: pop.style.left || null,
  top: pop.style.top || null,
}));
""")
        self.assertEqual(
            native, {"placed": False, "left": None, "top": None})

        for mode in ("all-false", "partial-true"):
            with self.subTest(mode=mode):
                supports_fn = (
                    "() => false" if mode == "all-false"
                    else '(p, v) => !(p === "position-try-fallbacks" '
                         '&& v === "flip-block")'
                )
                fallback = run_node_test(
                    f"const h = createHarness({{\n"
                    f"  bodyHtml: `{body_html}`,\n"
                    f"  innerHeight: 300,\n"
                    f"  cssSupports: {supports_fn},\n"
                    f"}});\n"
                    r"""
await h.flush();
const btn = h.doc.getElementById("btn");
btn._rect = { left: 100, top: 150, right: 160, bottom: 174 };
const pop = h.doc.getElementById("stock-menu");
pop.offsetWidth = 200;
pop.offsetHeight = 200;
h.fire(pop, "toggle", { newState: "open", bubbles: false });
const openPos = {
  placed: pop.getAttribute("data-placed"),
  left: pop.style.left,
  top: pop.style.top,
};
btn._rect = { left: 120, top: 20, right: 180, bottom: 44 };
h.fire(h.win, "resize");
const resizedTop = pop.style.top;
h.fire(pop, "toggle", { newState: "closed", bubbles: false });
btn._rect = { left: 120, top: 80, right: 180, bottom: 104 };
h.fire(h.win, "resize");
process.stdout.write(JSON.stringify({
  openPos, resizedTop, afterCloseTop: pop.style.top,
}));
""")
                self.assertEqual(
                    fallback["openPos"],
                    {"placed": "", "left": "100px", "top": "84px"})
                self.assertEqual(fallback["resizedTop"], "52px")
                self.assertEqual(fallback["afterCloseTop"], "52px")

    def test_master_detail_htmx_timing_abort_swap_and_reconnect(self) -> None:
        result = run_node_test(r"""
const h = createHarness({
  pathname: "/lab/inventory/end-products/",
  search: "?selected=1",
  bodyHtml: `
    <p id="list-summary"><a id="reset-link"
       href="/lab/inventory/end-products/?selected=1"
       hx-get="/lab/inventory/end-products/?selected=1">Reset</a></p>
    <div id="stock-entries"><a id="stock-link"
       href="/lab/inventory/end-products/?stock=low&selected=1"
       hx-get="/lab/inventory/end-products/?stock=low&selected=1">Low</a></div>
    <form id="filters" class="lab-filters"
          hx-get="/lab/inventory/end-products/">
      <span id="filter-selected">
        <input type="hidden" name="selected" value="1">
      </span>
    </form>
    <div id="view-bar">
      <input type="radio" id="view-table" name="view" value="table" checked>
      <input type="radio" id="view-details" name="view" value="details">
      <button type="button" id="stray-btn"
              popovertarget="columns-menu">Columns</button>
    </div>
    <div id="layout" class="split split--outer split--rows"
         data-major="first" data-controller="split master-detail"
         data-view="table" data-cookie="item-list-view"
         data-split-cookie-value="item-list-split"
         data-master-detail-level-value="outer"
         data-master-detail-rows-value="item-rows"
         data-master-detail-pane-value="item-detail"
         data-master-detail-param-value="selected">
      <div class="split__pane">
      <div class="table-scroll">
        <table class="main-table">
          <thead><tr><th><a id="sort-link"
            href="/lab/inventory/end-products/?sort=name&selected=1"
            hx-get="/lab/inventory/end-products/?sort=name&selected=1">Name</a>
          </th></tr></thead>
          <tbody id="item-rows">
            <tr id="row-1" data-item="1" aria-current="true"
                hx-get="/lab/inventory/items/1/detail/"><td>Item 1</td></tr>
            <tr id="row-2" data-item="2"
                hx-get="/lab/inventory/items/2/detail/"><td>Item 2</td></tr>
          </tbody>
        </table>
      </div>
      </div>
      <div class="split__pane">
      <aside id="item-detail" data-item="1">Detail 1</aside>
      </div>
    </div>
  `,
});
await h.flush();
const layout = h.doc.getElementById("layout");
const row1 = h.doc.getElementById("row-1");
const row2 = h.doc.getElementById("row-2");
const detail = h.doc.getElementById("item-detail");
const selInput = () => h.doc.querySelector(
  "#filter-selected input[name=selected]");

// 1. Click row 2 -> triggers item-select; beforeRequest makes pane inert
// without mutating mark, URL, hidden input, or OWN_LINKS while pending.
h.fire(row2, "click", { button: 0 });
h.fireCustom(row2, "htmx:beforeRequest", { elt: row2 });
const whilePending = {
  triggers: h.htmxCalls.filter((c) => c.kind === "trigger").length,
  inert: detail.inert,
  row1Current: row1.getAttribute("aria-current"),
  row2Current: row2.getAttribute("aria-current"),
  search: h.locationObj.search,
  hiddenVal: selInput().value,
  sortHref: h.doc.getElementById("sort-link").getAttribute("href"),
};

// 2. Failed/aborted request: afterRequest fires without afterSwap.
h.fireCustom(row2, "htmx:afterRequest", { elt: row2 });
const afterAbort = {
  inert: detail.inert,
  row1Current: row1.getAttribute("aria-current"),
  row2Current: row2.getAttribute("aria-current"),
  search: h.locationObj.search,
  hiddenVal: selInput().value,
  sortHref: h.doc.getElementById("sort-link").getAttribute("href"),
};

// 3. Successful swap with updated #item-detail[data-item="2"].
h.fire(row2, "click", { button: 0 });
h.fireCustom(row2, "htmx:beforeRequest", { elt: row2 });
const nextDetail = h.doc.createElement("aside");
nextDetail.id = "item-detail";
nextDetail.setAttribute("data-item", "2");
detail.replaceWith(nextDetail);
h.fireCustom(nextDetail, "htmx:afterSwap", {
  target: nextDetail, requestConfig: { elt: row2 },
});
h.fireCustom(row2, "htmx:afterRequest", { elt: row2 });
const afterSuccess = {
  inert: nextDetail.inert,
  row1Current: row1.getAttribute("aria-current"),
  row2Current: row2.getAttribute("aria-current"),
  search: h.locationObj.search,
  hiddenVal: selInput().value,
  sortHref: h.doc.getElementById("sort-link").getAttribute("href"),
  sortHxGet: h.doc.getElementById("sort-link").getAttribute("hx-get"),
  stockHref: h.doc.getElementById("stock-link").getAttribute("href"),
  resetHxGet: h.doc.getElementById("reset-link").getAttribute("hx-get"),
};

// 4. Disconnect and reconnect: outside radio change + click handled once.
const detailsRadio = h.doc.getElementById("view-details");
const tableRadio = h.doc.getElementById("view-table");
layout.remove();
await h.flush();
tableRadio.checked = false;
detailsRadio.checked = true;
h.fire(detailsRadio, "change");
const viewWhileDisconnected = layout.getAttribute("data-view");
h.fire(row1, "click", { button: 0 });
const triggersWhileDisconnected = h.htmxCalls.length;

h.doc.body.appendChild(layout);
await h.flush();
let viewTransitions = 0;
const origSetAttr = layout.setAttribute.bind(layout);
layout.setAttribute = function (k, v) {
  if (k === "data-view") viewTransitions += 1;
  return origSetAttr(k, v);
};
detailsRadio.checked = false;
tableRadio.checked = true;
h.fire(tableRadio, "change");
const beforeReconnectClick = h.htmxCalls.length;
h.fire(row1, "click", { button: 0 });
const reconnected = {
  viewAfterReconnect: layout.getAttribute("data-view"),
  viewTransitions,
  triggersAddedOnReconnectClick: h.htmxCalls.length - beforeReconnectClick,
};

// 5. A button of a menu that is no longer here stays as it is.
const strayButton = h.doc.getElementById("stray-btn");
tableRadio.checked = false;
detailsRadio.checked = true;
h.fire(detailsRadio, "change");
const strayDisabledInDetails = strayButton.disabled;

process.stdout.write(JSON.stringify({
  whilePending, afterAbort, afterSuccess,
  viewWhileDisconnected, triggersWhileDisconnected,
  ...reconnected, strayDisabledInDetails,
}));
""")
        self.assertEqual(result["whilePending"], {
            "triggers": 1,
            "inert": True,
            "row1Current": "true",
            "row2Current": None,
            "search": "?selected=1",
            "hiddenVal": "1",
            "sortHref": "/lab/inventory/end-products/?sort=name&selected=1",
        })
        self.assertEqual(result["afterAbort"], {
            "inert": False,
            "row1Current": "true",
            "row2Current": None,
            "search": "?selected=1",
            "hiddenVal": "1",
            "sortHref": "/lab/inventory/end-products/?sort=name&selected=1",
        })
        self.assertEqual(result["afterSuccess"], {
            "inert": False,
            "row1Current": None,
            "row2Current": "true",
            "search": "?selected=2",
            "hiddenVal": "2",
            "sortHref": "/lab/inventory/end-products/?sort=name&selected=2",
            "sortHxGet": "/lab/inventory/end-products/?sort=name&selected=2",
            "stockHref": "/lab/inventory/end-products/?stock=low&selected=2",
            "resetHxGet": "/lab/inventory/end-products/?selected=2",
        })
        self.assertEqual(result["viewWhileDisconnected"], "table")
        self.assertEqual(result["triggersWhileDisconnected"], 2)
        self.assertEqual(result["viewAfterReconnect"], "table")
        self.assertEqual(result["viewTransitions"], 1)
        self.assertEqual(result["triggersAddedOnReconnectClick"], 1)
        self.assertIs(result["strayDisabledInDetails"], False)

    def test_master_detail_selects_the_rows_of_its_own_tbody(self) -> None:
        result = run_node_test(r"""
const h = createHarness({
  pathname: "/lab/tasks/",
  bodyHtml: `
    <div id="layout" class="split split--outer split--rows"
         data-major="first" data-controller="split master-detail"
         data-view="details" data-cookie="task-list-view"
         data-split-cookie-value="task-list-split"
         data-master-detail-level-value="outer"
         data-master-detail-rows-value="item-rows"
         data-master-detail-pane-value="item-detail"
         data-master-detail-param-value="selected">
      <div class="split__pane">
      <div class="table-scroll">
        <table class="main-table" id="main">
          <thead><tr><th><a id="sort-link"
            href="/lab/tasks/?sort=number&selected=T-1"
            hx-get="/lab/tasks/?sort=number&selected=T-1">No.</a>
          </th></tr></thead>
          <tbody id="item-rows">
            <tr id="r1" data-item="T-1" aria-current="true"
                hx-get="/lab/tasks/T-1/detail/">
              <td id="c1">One</td></tr>
            <tr id="r2" data-item="T-2" hx-get="/lab/tasks/T-2/detail/">
              <td id="c2">Two</td>
              <td><a id="l2" href="/lab/tasks/T-2/">link</a></td>
              <td><button id="b2" type="button">button</button></td>
              <td><label id="lab2">label</label></td>
              <td><input id="i2" type="checkbox"></td>
              <td><select id="s2"></select></td>
              <td><textarea id="t2"></textarea></td></tr>
            <tr id="r3" data-item="T-3" hx-get="/lab/tasks/T-3/detail/">
              <td id="c3">Three</td></tr>
          </tbody>
        </table>
        <table class="item-table">
          <tbody>
            <tr id="old" data-item="X-1" hx-get="/lab/inventory/x/">
              <td id="oldc">Old</td></tr>
          </tbody>
        </table>
      </div>
      </div>
      <div class="split__pane">
      <aside id="item-detail" data-item="T-1">Detail 1</aside>
      </div>
    </div>
  `,
});
await h.flush();
const triggers = () => h.htmxCalls.filter((c) => c.kind === "trigger");
const clicked = (id) => {
  const before = triggers().length;
  h.fire(h.doc.getElementById(id), "click", { button: 0 });
  const found = triggers();
  return found.length - before === 1
    ? found[found.length - 1].el.id : null;
};
const clicks = {};
for (const id of ["c2", "l2", "b2", "lab2", "i2", "s2", "t2", "oldc"]) {
  clicks[id] = clicked(id);
}
const before = triggers().length;
h.fire(h.doc.getElementById("r1"), "keydown", { key: "ArrowDown" });
const afterDown = triggers().slice(before).map((c) => [c.el.id, c.name]);
h.fire(h.doc.getElementById("old"), "keydown", { key: "ArrowDown" });
const afterOld = triggers().length - before - afterDown.length;
process.stdout.write(JSON.stringify({
  clicks, afterDown, afterOld,
  focused: h.doc.activeElement && h.doc.activeElement.id,
}));
""")
        self.assertEqual(result["clicks"], {
            "c2": "r2", "l2": None, "b2": None, "lab2": None, "i2": None,
            "s2": None, "t2": None, "oldc": None})
        self.assertEqual(result["afterDown"], [["r2", "item-select"]])
        self.assertEqual(result["afterOld"], 0)
        self.assertEqual(result["focused"], "r2")

    def test_dialog_and_sortable_table_morph_and_reconnect(self) -> None:
        result = run_node_test(r"""
const refreshedHtml = `<!DOCTYPE html><html><head><title>Updated</title>
</head><body><main id="main">
  <div id="item-refresh" data-refresh>
    <h1 id="page-h1">Item 1</h1>
    <a id="edit-link" href="/lab/inventory/items/1/changed/"
       data-dialog>Edit</a>
    <div class="table-scroll">
      <table id="movements" data-sortable data-controller="sortable-table">
        <thead><tr>
          <th scope="col">Date</th>
          <th scope="col">Count</th>
          <th scope="col"><span class="visually-hidden">Actions</span></th>
        </tr></thead>
        <tbody>
          <tr id="m-1"><td data-sort="2026-01-02">02.01</td>
              <td data-sort="20">20</td><td></td></tr>
          <tr id="m-2"><td data-sort="2026-01-01">01.01</td>
              <td data-sort="3">3</td><td></td></tr>
          <tr id="m-3"><td data-sort="2026-01-03">03.01</td>
              <td data-sort="12">12</td><td></td></tr>
        </tbody>
      </table>
    </div>
  </div>
</main></body></html>`;

let releaseFetch;
const fetchGate = new Promise((resolve) => { releaseFetch = resolve; });
const h = createHarness({
  pathname: "/lab/inventory/items/1/",
  fetch: async () => {
    await fetchGate;
    return {
      ok: true,
      status: 200,
      redirected: false,
      async text() { return refreshedHtml; },
    };
  },
  bodyHtml: `
    <main id="main">
      <div id="item-refresh" data-refresh>
        <h1 id="page-h1">Item 1</h1>
        <a id="edit-link" href="/lab/inventory/items/1/edit/"
           data-dialog>Edit</a>
        <div class="table-scroll">
          <table id="movements" data-sortable
                 data-controller="sortable-table">
            <thead><tr>
              <th scope="col">Date</th>
              <th scope="col">Count</th>
              <th scope="col"><span class="visually-hidden">Actions</span></th>
            </tr></thead>
            <tbody>
              <tr id="m-1"><td data-sort="2026-01-02">02.01</td>
                  <td data-sort="10">10</td><td></td></tr>
              <tr id="m-2"><td data-sort="2026-01-01">01.01</td>
                  <td data-sort="2">2</td><td></td></tr>
            </tbody>
          </table>
        </div>
      </div>
    </main>
    <dialog id="lab-dialog" class="lab-dialog" data-controller="dialog">
      <div id="lab-dialog-body"></div>
      <button type="button" class="lab-dialog-close">Close</button>
    </dialog>
  `,
});
await h.flush();

const movements = h.doc.getElementById("movements");
const dialog = h.doc.getElementById("lab-dialog");
const dialogBody = h.doc.getElementById("lab-dialog-body");
const editLink = h.doc.getElementById("edit-link");

const countBtn = () => movements.tHead.rows[0].cells[1].querySelector(
  "button.sort-header");
const initialButtons = movements.querySelectorAll("button.sort-header").length;
h.fire(countBtn(), "click", { button: 0 });
const initialSortedIds = [...movements.tBodies[0].rows].map((r) => r.id);
const initialAriaSort = movements.tHead.rows[0].cells[1].getAttribute(
  "aria-sort");

// Open dialog from sibling <main>
const openEv = h.fire(editLink, "click", { button: 0 });
const ajaxCall = h.htmxCalls.find((c) => c.kind === "ajax");
const form = h.doc.createElement("form");
const saveBtn = h.doc.createElement("button");
saveBtn.type = "submit";
form.appendChild(saveBtn);
dialogBody.appendChild(form);
h.fireCustom(dialogBody, "htmx:afterSwap", { target: dialogBody });
const openAfterSwap = dialog.open;

// Posting makes body inert and blocks cancel
h.fireCustom(dialog, "htmx:beforeRequest", {
  requestConfig: { verb: "post" },
});
const inertWhilePosting = dialogBody.inert;
const cancelWhilePosting = h.fire(dialog, "cancel", { cancelable: true });

// Saving locks dialog and guards inert/cancel while refresh is pending
h.fireCustom(dialog, "htmx:afterRequest");
h.fireCustom(form, "lab-saved");
await h.flush();
const cancelWhileSaving = h.fire(dialog, "cancel", { cancelable: true });
const closeBtn = dialog.querySelector(".lab-dialog-close");
const whileSaving = {
  dialogOpen: dialog.open,
  inert: dialogBody.inert,
  cancelPrevented: cancelWhileSaving.defaultPrevented,
  closeDisabled: Boolean(closeBtn && closeBtn.disabled),
};
releaseFetch();
await new Promise((r) => setTimeout(r, 20));
await h.flush();

const afterSave = {
  morphCount: h.morphCalls.length,
  sameTableNode: h.doc.getElementById("movements") === movements,
  headerButtonCounts: [...movements.tHead.rows[0].cells].map(
    (th) => th.querySelectorAll("button.sort-header").length),
  ariaSort: movements.tHead.rows[0].cells[1].getAttribute("aria-sort"),
  rowIds: [...movements.tBodies[0].rows].map((r) => r.id),
  dialogOpen: dialog.open,
  bodyEmpty: dialogBody.childNodes.length === 0,
  focusedId: h.doc.activeElement ? h.doc.activeElement.id : null,
};

// Click sort header after morph -> toggles once to descending
h.fire(countBtn(), "click", { button: 0 });
const afterPostMorphClick = {
  ariaSort: movements.tHead.rows[0].cells[1].getAttribute("aria-sort"),
  rowIds: [...movements.tBodies[0].rows].map((r) => r.id),
};

// Disconnect and reconnect both dialog and sortable-table
const tableParent = movements.parentNode;
const dialogParent = dialog.parentNode;
movements.remove();
dialog.remove();
await h.flush();

const ajaxBeforeDisc = h.htmxCalls.length;
h.fire(h.doc.getElementById("edit-link"), "click", { button: 0 });
h.fire(countBtn(), "click", { button: 0 });
const whileDisconnected = {
  ajaxAdded: h.htmxCalls.length - ajaxBeforeDisc,
  ariaSort: movements.tHead.rows[0].cells[1].getAttribute("aria-sort"),
};

tableParent.appendChild(movements);
dialogParent.appendChild(dialog);
await h.flush();

const ajaxBeforeReconn = h.htmxCalls.length;
h.fire(h.doc.getElementById("edit-link"), "click", { button: 0 });
h.fire(countBtn(), "click", { button: 0 });
const afterReconnect = {
  ajaxAdded: h.htmxCalls.length - ajaxBeforeReconn,
  ariaSort: movements.tHead.rows[0].cells[1].getAttribute("aria-sort"),
};

process.stdout.write(JSON.stringify({
  initialButtons,
  initialSortedIds,
  initialAriaSort,
  openPrevented: openEv.defaultPrevented,
  ajaxMethod: ajaxCall ? ajaxCall.method : null,
  ajaxTargetId: ajaxCall && ajaxCall.opts ? ajaxCall.opts.target.id : null,
  openAfterSwap,
  inertWhilePosting,
  cancelPreventedWhilePosting: cancelWhilePosting.defaultPrevented,
  whileSaving,
  afterSave,
  afterPostMorphClick,
  whileDisconnected,
  afterReconnect,
}));
""")
        self.assertEqual(result["initialButtons"], 2)
        self.assertEqual(result["initialSortedIds"], ["m-2", "m-1"])
        self.assertEqual(result["initialAriaSort"], "ascending")
        self.assertTrue(result["openPrevented"])
        self.assertEqual(result["ajaxMethod"], "GET")
        self.assertEqual(result["ajaxTargetId"], "lab-dialog-body")
        self.assertTrue(result["openAfterSwap"])
        self.assertTrue(result["inertWhilePosting"])
        self.assertTrue(result["cancelPreventedWhilePosting"])
        self.assertEqual(result["whileSaving"], {
            "dialogOpen": True,
            "inert": True,
            "cancelPrevented": True,
            "closeDisabled": True,
        })
        self.assertEqual(result["afterSave"], {
            "morphCount": 1,
            "sameTableNode": True,
            "headerButtonCounts": [1, 1, 0],
            "ariaSort": "ascending",
            "rowIds": ["m-2", "m-3", "m-1"],
            "dialogOpen": False,
            "bodyEmpty": True,
            "focusedId": "page-h1",
        })
        self.assertEqual(result["afterPostMorphClick"], {
            "ariaSort": "descending",
            "rowIds": ["m-1", "m-3", "m-2"],
        })
        self.assertEqual(result["whileDisconnected"], {
            "ajaxAdded": 0,
            "ariaSort": "descending",
        })
        self.assertEqual(result["afterReconnect"], {
            "ajaxAdded": 1,
            "ariaSort": "ascending",
        })

    def test_batch_narrow_both_drivers(self) -> None:
        result = run_node_test(r"""
const h = createHarness({
  bodyHtml: `
    <form id="new-item-form">
      <input type="text" id="sub-in" name="substance" value="cinnamic-acid">
      <select id="batch-new" name="batch" data-controller="batch-narrow"
              data-batch-for="substance">
        <option value="">unknown</option>
        <optgroup label="Acetophenone" data-substance="acetophenone">
          <option value="b-ap">AP1</option>
        </optgroup>
        <optgroup label="Cinnamic" data-substance="cinnamic-acid">
          <option value="b-ca" selected>CA1</option>
        </optgroup>
      </select>
    </form>
    <form id="note-form">
      <select id="item-0" name="item_0">
        <option value="">--</option>
        <option value="i-ca" data-substance="cinnamic-acid"
                selected>CA</option>
        <option value="i-ap" data-substance="acetophenone">AP</option>
      </select>
      <select id="batch-0" name="batch_0" data-controller="batch-narrow"
              data-batch-for="item_0">
        <option value="">--</option>
        <optgroup label="Acetophenone" data-substance="acetophenone">
          <option value="b0-ap">AP1</option>
        </optgroup>
        <optgroup label="Cinnamic" data-substance="cinnamic-acid">
          <option value="b0-ca" selected>CA1</option>
        </optgroup>
      </select>
      <select id="item-1" name="item_1">
        <option value="">--</option>
        <option value="i1-ca" data-substance="cinnamic-acid">CA</option>
        <option value="i1-ap" data-substance="acetophenone"
                selected>AP</option>
      </select>
      <select id="batch-1" name="batch_1" data-controller="batch-narrow"
              data-batch-for="item_1">
        <option value="">--</option>
        <optgroup label="Acetophenone" data-substance="acetophenone">
          <option value="b1-ap" selected>AP1</option>
        </optgroup>
        <optgroup label="Cinnamic" data-substance="cinnamic-acid">
          <option value="b1-ca">CA1</option>
        </optgroup>
      </select>
    </form>
  `,
});
await h.flush();

const groupsState = (sel) => sel.querySelectorAll("optgroup").map((g) => ({
  key: g.dataset.substance, hidden: g.hidden, disabled: g.disabled,
}));

const batchNew = h.doc.getElementById("batch-new");
const subIn = h.doc.getElementById("sub-in");
const initialNew = {
  value: batchNew.value,
  groups: groupsState(batchNew),
};
subIn.value = "acetophenone";
h.fire(subIn, "input");
const afterTextInput = {
  value: batchNew.value,
  groups: groupsState(batchNew),
};

const item0 = h.doc.getElementById("item-0");
const batch0 = h.doc.getElementById("batch-0");
const batch1 = h.doc.getElementById("batch-1");
const initialNote = {
  batch0: batch0.value,
  batch1: batch1.value,
  groups0: groupsState(batch0),
  groups1: groupsState(batch1),
};
item0.value = "i-ap";
h.fire(item0, "change");
const afterRow0Change = {
  batch0: batch0.value,
  batch1: batch1.value,
  groups0: groupsState(batch0),
  groups1: groupsState(batch1),
};

process.stdout.write(JSON.stringify({
  initialNew, afterTextInput, initialNote, afterRow0Change,
}));
""")
        self.assertEqual(result["initialNew"], {
            "value": "b-ca",
            "groups": [
                {"key": "acetophenone", "hidden": True, "disabled": True},
                {"key": "cinnamic-acid", "hidden": False, "disabled": False},
            ],
        })
        self.assertEqual(result["afterTextInput"], {
            "value": "",
            "groups": [
                {"key": "acetophenone", "hidden": False, "disabled": False},
                {"key": "cinnamic-acid", "hidden": True, "disabled": True},
            ],
        })
        self.assertEqual(result["initialNote"], {
            "batch0": "b0-ca",
            "batch1": "b1-ap",
            "groups0": [
                {"key": "acetophenone", "hidden": True, "disabled": True},
                {"key": "cinnamic-acid", "hidden": False, "disabled": False},
            ],
            "groups1": [
                {"key": "acetophenone", "hidden": False, "disabled": False},
                {"key": "cinnamic-acid", "hidden": True, "disabled": True},
            ],
        })
        self.assertEqual(result["afterRow0Change"], {
            "batch0": "",
            "batch1": "b1-ap",
            "groups0": [
                {"key": "acetophenone", "hidden": False, "disabled": False},
                {"key": "cinnamic-acid", "hidden": True, "disabled": True},
            ],
            "groups1": [
                {"key": "acetophenone", "hidden": False, "disabled": False},
                {"key": "cinnamic-acid", "hidden": True, "disabled": True},
            ],
        })


@skipUnless(NODE, "node is not installed")
class NestedSplitTests(SimpleTestCase):
    """Two levels of ``master-detail`` on one page, and the ``split``
    controller (web-app: Main lists, Views, Live lists; end-product-
    inventory: Lists by substance)."""

    def test_each_level_ignores_the_rows_of_the_other(self) -> None:
        result = run_node_test(nested_script(r"""
const outerClick = clicked("oc2");
const lotClick = clicked("lc3");
const outerKey = stepped("o1", "ArrowDown");
const lotDown = stepped("l2", "ArrowDown");
const lotUp = stepped("l2", "ArrowUp");
const lotLast = stepped("l3", "ArrowDown");
const lotFirst = stepped("l1", "ArrowUp");
const outerLast = stepped("o2", "ArrowDown");
const withLink = clicked("lot-edit");
process.stdout.write(JSON.stringify({
  outerClick, lotClick, outerKey, lotDown, lotUp, lotLast, lotFirst,
  outerLast, withLink,
}));
"""))
        self.assertEqual(result, {
            "outerClick": ["o2"], "lotClick": ["l3"],
            "outerKey": ["o2"], "lotDown": ["l3"], "lotUp": ["l1"],
            "lotLast": [], "lotFirst": [], "outerLast": [],
            "withLink": []})

    def test_the_arrow_keys_focus_the_row_they_move_to(self) -> None:
        result = run_node_test(nested_script(r"""
stepped("l2", "ArrowDown");
const lotFocus = h.doc.activeElement && h.doc.activeElement.id;
stepped("o1", "ArrowDown");
const outerFocus = h.doc.activeElement && h.doc.activeElement.id;
process.stdout.write(JSON.stringify({ lotFocus, outerFocus }));
"""))
        self.assertEqual(result, {"lotFocus": "l3", "outerFocus": "o2"})

    def test_a_lot_click_writes_the_lot_and_keeps_the_selection(
            self) -> None:
        result = run_node_test(nested_script(r"""
const row = h.doc.getElementById("l3");
const lotPane = h.doc.getElementById("lot-detail");
const outerPane = h.doc.getElementById("item-detail");
h.fire(h.doc.getElementById("lc3"), "click", { button: 0 });
h.fireCustom(row, "htmx:beforeRequest", { elt: row });
const pending = {
  current: ["o1", "l1", "l2", "l3"].map(
    (id) => h.doc.getElementById(id).getAttribute("aria-current")),
  search: h.locationObj.search,
  lot: field("lot"),
};
h.fireCustom(row, "htmx:afterRequest", { elt: row });
const aborted = { search: h.locationObj.search, lot: field("lot") };
h.fire(h.doc.getElementById("lc3"), "click", { button: 0 });
flow(row, paneLike("lot-detail", "3"), lotPane);
const after = {
  current: ["o1", "o2", "l1", "l2", "l3"].map(
    (id) => h.doc.getElementById(id).getAttribute("aria-current")),
  search: h.locationObj.search,
  selected: field("selected"),
  lot: field("lot"),
  sort: h.doc.getElementById("sort-link").getAttribute("href"),
  sortHx: h.doc.getElementById("sort-link").getAttribute("hx-get"),
  reset: h.doc.getElementById("reset-link").getAttribute("href"),
  outerPane: h.doc.getElementById("item-detail") === outerPane,
};
process.stdout.write(JSON.stringify({ pending, aborted, after }));
"""))
        self.assertEqual(result["pending"], {
            "current": ["true", None, "true", None],
            "search": "?selected=a&lot=2", "lot": "2"})
        self.assertEqual(result["aborted"],
                         {"search": "?selected=a&lot=2", "lot": "2"})
        base = "/lab/inventory/intermediates/"
        self.assertEqual(result["after"], {
            "current": ["true", None, None, None, "true"],
            "search": "?selected=a&lot=3", "selected": "a", "lot": "3",
            "sort": f"{base}?sort=amount&selected=a&lot=3",
            "sortHx": f"{base}?sort=amount&selected=a&lot=3",
            "reset": f"{base}?selected=a&lot=3",
            "outerPane": True})

    def test_an_outer_selection_drops_the_lot(self) -> None:
        result = run_node_test(nested_script(r"""
const row = h.doc.getElementById("o2");
h.fire(h.doc.getElementById("oc2"), "click", { button: 0 });
flow(row, nextItemPane(), h.doc.getElementById("item-detail"));
await h.flush();
const lotField = field("lot");
process.stdout.write(JSON.stringify({
  current: ["o1", "o2"].map(
    (id) => h.doc.getElementById(id).getAttribute("aria-current")),
  selected: search().get("selected"),
  lot: search().get("lot"),
  selectedField: field("selected"),
  lotField,
  sort: h.doc.getElementById("sort-link").getAttribute("href"),
}));
"""))
        self.assertEqual(result["current"], [None, "true"])
        self.assertEqual(result["selected"], "b")
        self.assertEqual(result["selectedField"], "b")
        # Neither the address, nor the field, nor a link names the lot of
        # the substance `a`; the new pane may bring its own.
        self.assertIn(result["lot"], (None, "11"))
        self.assertIn(result["lotField"], (None, "", "11"))
        self.assertNotIn("lot=2", result["sort"])
        self.assertIn("selected=b", result["sort"])

    def test_the_lot_level_marks_its_rows_from_the_pane_after_a_swap(
            self) -> None:
        result = run_node_test(nested_script(r"""
const lotPane = h.doc.getElementById("lot-detail");
const next = paneLike("lot-detail", "1");
lotPane.replaceWith(next);
h.fireCustom(next, "htmx:afterSwap", {
  target: next, requestConfig: { elt: h.doc.getElementById("l1") } });
process.stdout.write(JSON.stringify({
  current: ["l1", "l2", "l3"].map(
    (id) => h.doc.getElementById(id).getAttribute("aria-current")),
  lot: search().get("lot"), selected: search().get("selected"),
}));
"""))
        self.assertEqual(result, {"current": ["true", None, None],
                                  "lot": "1", "selected": "a"})

    def test_lot_rows_are_focusable_again_after_their_body_is_morphed(
            self) -> None:
        result = run_node_test(nested_script(r"""
const body = h.doc.getElementById("lot-rows");
for (const row of [...body.children]) row.remove();
const fresh = [];
for (const id of ["n1", "n2"]) {
  const row = h.doc.createElement("tr");
  row.id = id;
  row.setAttribute("data-item", id);
  row.setAttribute("hx-get", `/lab/inventory/intermediates/a/lots/${id}/`);
  row.tabIndex = 99;
  body.appendChild(row);
  fresh.push(row);
}
await h.flush();
const pane = h.doc.getElementById("item-detail");
for (const name of ["htmx:oobAfterSwap", "htmx:afterSwap",
                    "htmx:afterSettle"]) {
  h.fireCustom(pane, name, { target: pane, elt: pane });
}
await h.flush();
const lotClick = clicked("n2");
process.stdout.write(JSON.stringify({
  tabIndex: fresh.map((row) => row.tabIndex), lotClick,
}));
"""))
        self.assertEqual(result["tabIndex"], [-1, -1])
        self.assertEqual(result["lotClick"], ["n2"])

    def test_only_the_outer_level_handles_the_view_switch(self) -> None:
        result = run_node_test(nested_script(r"""
const writes = [];
let jar = "";
Object.defineProperty(h.doc, "cookie", {
  get: () => jar, set: (value) => { writes.push(value); jar = value; },
});
const outer = h.doc.getElementById("outer");
const inner = h.doc.getElementById("inner");
const before = outer.getAttribute("data-view");
h.doc.getElementById("view-details").checked = false;
h.doc.getElementById("view-table").checked = true;
h.fire(h.doc.getElementById("view-table"), "change");
await h.flush();
process.stdout.write(JSON.stringify({
  before, after: outer.getAttribute("data-view"), writes,
  outerScripted: outer.hasAttribute("data-scripted"),
  innerScripted: inner.hasAttribute("data-scripted"),
  innerView: inner.hasAttribute("data-view"),
}));
"""))
        self.assertEqual(result["before"], "details")
        self.assertEqual(result["after"], "table")
        self.assertEqual(len(result["writes"]), 1, result["writes"])
        self.assertTrue(
            result["writes"][0].startswith("intermediate-list-view=table"))
        self.assertTrue(result["outerScripted"])
        self.assertFalse(result["innerScripted"])
        self.assertFalse(result["innerView"])

    def test_the_toggle_swaps_the_larger_side_and_remembers_it(
            self) -> None:
        result = run_node_test(nested_script(r"""
const writes = [];
let jar = "";
Object.defineProperty(h.doc, "cookie", {
  get: () => jar, set: (value) => { writes.push(value); jar = value; },
});
const outer = h.doc.getElementById("outer");
const inner = h.doc.getElementById("inner");
const majors = [outer.getAttribute("data-major")];
h.fire(h.doc.getElementById("toggle"), "click", { button: 0 });
majors.push(outer.getAttribute("data-major"));
h.fire(h.doc.getElementById("toggle"), "click", { button: 0 });
majors.push(outer.getAttribute("data-major"));
process.stdout.write(JSON.stringify({
  majors, writes, inner: inner.getAttribute("data-major"),
  view: outer.getAttribute("data-view"),
  triggers: triggers().length,
}));
"""))
        self.assertEqual(result["majors"], ["first", "second", "first"])
        self.assertEqual(result["inner"], "first")
        self.assertEqual(result["view"], "details")
        self.assertEqual(result["triggers"], 0)
        self.assertEqual(len(result["writes"]), 2, result["writes"])
        for write, side in zip(result["writes"], ("second", "first")):
            parts = [part.strip() for part in write.split(";")]
            self.assertEqual(parts[0], f"intermediate-list-split={side}")
            self.assertIn("path=/lab/inventory/intermediates/", parts)
            self.assertIn("SameSite=Lax", parts)
            self.assertIn("max-age=31536000", [p.lower() for p in parts])

    def test_a_dialog_hides_the_popover_that_holds_its_link(self) -> None:
        result = run_node_test(nested_script(r"""
const order = [];
const realAjax = h.context.htmx.ajax;
h.context.htmx.ajax = (...args) => {
  order.push("ajax");
  realAjax(...args);
};
const popovers = {};
for (const id of ["item-actions", "lot-actions"]) {
  const popover = h.doc.getElementById(id);
  popover._popoverOpen = true;
  const hide = popover.hidePopover.bind(popover);
  popover.hidePopover = () => { order.push(`hide ${id}`); hide(); };
  popovers[id] = popover;
}
h.fire(h.doc.getElementById("lot-edit"), "click", { button: 0 });
const afterLot = [...order];
const lotLeft = popovers["item-actions"]._popoverOpen;
const dialog = h.doc.getElementById("lab-dialog");
// Close the dialog again and open another from the outer pane.
const body = h.doc.getElementById("lab-dialog-body");
h.fireCustom(body, "htmx:afterSwap", { target: body });
dialog.close();
order.length = 0;
popovers["item-actions"]._popoverOpen = true;
h.fire(h.doc.getElementById("item-edit"), "click", { button: 0 });
const afterItem = [...order];
h.fireCustom(body, "htmx:afterSwap", { target: body });
dialog.close();
order.length = 0;
h.fire(h.doc.getElementById("outside-link"), "click", { button: 0 });
process.stdout.write(JSON.stringify({
  afterLot, lotLeft, afterItem, afterOutside: [...order],
}));
"""))
        self.assertEqual(result["afterLot"], ["hide lot-actions", "ajax"])
        self.assertTrue(result["lotLeft"])
        self.assertEqual(result["afterItem"], ["hide item-actions", "ajax"])
        self.assertEqual(result["afterOutside"], ["ajax"])

    def refresh_flow(self, opener: str) -> dict:
        """Open the dialog from the link OPENER, save, and read the page
        after its refresh."""
        return run_node_test(nested_script(r"""
const body = h.doc.getElementById("lab-dialog-body");
const dialog = h.doc.getElementById("lab-dialog");
const rowsOf = (ids) => ids.map((id) => h.doc.getElementById(id));
// What a morph leaves: rows the script has not made focusable yet.
for (const row of rowsOf(["o1", "o2", "l1", "l2", "l3"])) {
  row.tabIndex = 99;
}
h.fire(h.doc.getElementById("__OPENER__"), "click", { button: 0 });
const form = h.doc.createElement("form");
body.appendChild(form);
h.fireCustom(body, "htmx:afterSwap", { target: body });
h.fireCustom(form, "lab-saved");
await new Promise((resolve) => setTimeout(resolve, 20));
await h.flush();
process.stdout.write(JSON.stringify({
  fetched,
  open: dialog.open,
  current: ["o1", "o2", "l1", "l2", "l3"].map(
    (id) => h.doc.getElementById(id).getAttribute("aria-current")),
  tabIndex: rowsOf(["o1", "o2", "l1", "l2", "l3"]).map(
    (row) => row.tabIndex),
  search: h.locationObj.search,
  selected: field("selected"),
  lot: field("lot"),
  focused: h.doc.activeElement && h.doc.activeElement.id,
}));
""".replace("__OPENER__", opener)))

    def test_a_save_restores_both_levels(self) -> None:
        result = self.refresh_flow("lot-edit")
        self.assertFalse(result["open"])
        self.assertEqual(len(result["fetched"]), 1)
        asked = urlsplit(result["fetched"][0])
        self.assertEqual(asked.path, "/lab/inventory/intermediates/")
        self.assertEqual(parse_qs(asked.query),
                         {"selected": ["a"], "lot": ["2"]})
        # The pane now names the lot 1: both levels mark their rows from
        # their panes, and the lot is in the field and the address.
        self.assertEqual(result["current"], ["true", None, "true", None,
                                             None])
        self.assertEqual(result["tabIndex"], [-1] * 5)
        self.assertEqual(result["selected"], "a")
        self.assertEqual(result["lot"], "1")
        self.assertEqual(parse_qs(result["search"][1:]),
                         {"selected": ["a"], "lot": ["1"]})

    def test_a_save_focuses_the_title_of_the_pane_of_the_opener(
            self) -> None:
        for opener, title in (("lot-edit", "lot-detail-title"),
                              ("item-edit", "item-detail-title")):
            with self.subTest(opener=opener):
                self.assertEqual(self.refresh_flow(opener)["focused"],
                                 title)

    def test_a_save_focuses_an_opener_that_is_in_no_popover(self) -> None:
        self.assertEqual(self.refresh_flow("outside-link")["focused"],
                         "outside-link")


class TemplateWiringTests(PlanningCase):
    """Rendered pages attach the Stimulus data-controller attributes."""

    def controllers(self, element) -> set[str]:
        return set((element.get("data-controller") or "").split())

    def check_page(self, path: str, signed_in: bool = False):
        if signed_in:
            self.client.force_login(self.kl)
        response = self.client.get(path)
        self.assertEqual(response.status_code, 200, path)
        test_shell.ShellTests.assert_scripts(self, response)
        root = page(response)
        shell_scripts(root)
        return root

    def test_end_products_list_wiring(self) -> None:
        make_item(self.kl, "CH-0012", quantity=5)
        root = self.check_page("/lab/inventory/end-products/")
        self.assertIn("dialog",
                      self.controllers(root.find("dialog", id="lab-dialog")))
        layout = must_outer_split(root)
        self.assertEqual(self.controllers(layout),
                         {"split", "master-detail"})
        for pop_id in ("stock-menu", "more-filters"):
            with self.subTest(popover=pop_id):
                self.assertIn("popover-anchor",
                              self.controllers(root.find("div", id=pop_id)))
        self.assertIsNone(root.find("details", cls="lab-view-menu"))
        self.assertEqual(root.find_all(attrs={"data-remember": True}), [])
        used = set().union(*(self.controllers(node)
                             for node in root.walk()))
        self.assertFalse(used & {"view-menu", "remember"}, used)

    def test_item_page_movements_wiring(self) -> None:
        item = make_item(self.kl, "CH-0012", quantity=5)
        root = self.check_page(f"/lab/inventory/items/{item.pk}/")
        self.assertIn(
            "sortable-table",
            self.controllers(root.find("table", id="movements")))

    def test_planning_page_wiring(self) -> None:
        self.planned_item("NV-10", quantity=10)
        root = self.check_page(PLAN)
        layout = must_outer_split(root)
        self.assertEqual(self.controllers(layout),
                         {"split", "master-detail"})
        self.assertIn("planning-list-view", layout.attrs.values())
        grid = root.find("table", cls="main-table")
        self.assertIsNotNone(grid)
        self.assertNotIn("sortable-table", self.controllers(grid))
        self.assertEqual(root.find_all("div", cls="planning-grid"), [])
        rows = root.find_all("tr", attrs={"data-item": True})
        self.assertTrue(rows)
        for row in rows:
            self.assertTrue(row.get("hx-get"))
            self.assertEqual(row.get("hx-trigger"), "item-select")
        self.assertEqual(root.find_all("tr", attrs={"data-article": True}),
                         [])

    def test_every_main_list_wires_master_detail_and_split(self) -> None:
        self.planned_item("NV-10", quantity=10)
        make_task(self.kl, "NV-10")
        make_vessel(self.kl, article="NV-10", unit="mg", amount="5")
        for path in ("/lab/inventory/end-products/",
                     "/lab/inventory/end-products/bulk/",
                     "/lab/inventory/deliveries/",
                     "/lab/inventory/intermediates/",
                     "/lab/inventory/chemicals/",
                     "/lab/inventory/batches/",
                     "/lab/inventory/vessels/",
                     "/lab/tasks/", "/lab/registry/", PLAN):
            with self.subTest(path=path):
                root = self.check_page(path)
                layout = must_outer_split(root)
                self.assertEqual(self.controllers(layout),
                                 {"split", "master-detail"})
                self.assertEqual(
                    {name: value for name, value in layout.attrs.items()
                     if name.startswith("data-master-detail-")},
                    {"data-master-detail-level-value": "outer",
                     "data-master-detail-rows-value": "item-rows",
                     "data-master-detail-pane-value": "item-detail",
                     "data-master-detail-param-value": "selected"})
                self.assertRegex(layout.get("data-split-cookie-value"),
                                 r"^[a-z]+-list-split$")
                self.assertTrue([value for value in layout.attrs.values()
                                 if value.endswith("-list-view")])
                self.assertIsNotNone(root.find("table", cls="main-table"))
                self.assertEqual(
                    [node.tag for node in root.walk()
                     if "split-list" in self.controllers(node)], [])

    def test_batch_narrow_wiring_on_item_and_delivery_forms(self) -> None:
        make_substance("cinnamic-acid", "Cinnamic acid")
        make_batch(self.kl, "CH-0012", number="KL0412")
        for path in (NEW_ITEM, NEW_NOTE):
            with self.subTest(path=path):
                root = self.check_page(path, signed_in=True)
                selects = root.find_all(
                    "select", attrs={"data-batch-for": True})
                self.assertTrue(selects)
                for select in selects:
                    self.assertIn("batch-narrow", self.controllers(select))
