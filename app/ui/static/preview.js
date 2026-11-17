/** Rebuild a small passive HTML vocabulary from inert template content.
 *
 * Nothing from the artifact is copied except text and a fixed set of element names,
 * all without attributes. Active or embedding elements are dropped with everything
 * inside them; other unknown elements (links, for example) are flattened to their
 * text. The frame is sandboxed with no permissions and a deny-all policy; styling is
 * intentionally not reproduced (this is a content preview, not a renderer).
 */
const PASSIVE = new Set([
  "P", "DIV", "SPAN", "H1", "H2", "H3", "H4", "H5", "H6", "UL", "OL", "LI", "STRONG", "EM",
  "B", "I", "BR", "HR", "BLOCKQUOTE", "PRE", "CODE", "TABLE", "THEAD", "TBODY", "TR", "TH", "TD",
  // Structural elements carry no behaviour; the Builder's landing page uses them.
  "MAIN", "SECTION", "ARTICLE", "ASIDE", "HEADER", "FOOTER", "NAV",
]);
const DROP = new Set([
  "SCRIPT", "STYLE", "IFRAME", "FRAME", "OBJECT", "EMBED", "FORM", "INPUT", "BUTTON", "SELECT",
  "TEXTAREA", "OPTION", "SVG", "MATH", "TEMPLATE", "NOSCRIPT", "LINK", "META", "TITLE", "BASE",
  "IMG", "VIDEO", "AUDIO", "SOURCE", "PICTURE", "CANVAS", "DIALOG", "PORTAL", "APPLET",
]);
export function inertPreview(html, title) {
  const template = document.createElement("template");
  template.innerHTML = html;
  const output = document.createElement("div");
  function copy(from, to, depth = 0) {
    if (depth > 100) return;
    for (const node of from.childNodes) {
      if (node.nodeType === Node.TEXT_NODE)
        to.append(document.createTextNode(node.textContent));
      else if (node.nodeType !== Node.ELEMENT_NODE || DROP.has(node.tagName)) continue;
      else if (PASSIVE.has(node.tagName)) {
        const child = document.createElement(node.tagName.toLowerCase());
        copy(node, child, depth + 1);
        to.append(child);
      } else copy(node, to, depth + 1); // flatten unknown elements to their text
    }
  }
  copy(template.content, output);
  const frame = document.createElement("iframe");
  frame.setAttribute("sandbox", "");
  frame.referrerPolicy = "no-referrer";
  frame.title = title + " — inert preview";
  frame.srcdoc =
    '<meta http-equiv="Content-Security-Policy" content="default-src &#39;none&#39;; form-action &#39;none&#39;; base-uri &#39;none&#39;">' +
    output.innerHTML;
  return frame;
}
