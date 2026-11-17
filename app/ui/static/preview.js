/** Rebuild a small passive HTML vocabulary from inert template content. */
export function inertPreview(html, title) {
  const template = document.createElement("template");
  template.innerHTML = html;
  const allowed = new Set([
    "P",
    "DIV",
    "SPAN",
    "H1",
    "H2",
    "H3",
    "H4",
    "H5",
    "H6",
    "UL",
    "OL",
    "LI",
    "STRONG",
    "EM",
    "B",
    "I",
    "BR",
    "HR",
    "BLOCKQUOTE",
    "PRE",
    "CODE",
    "TABLE",
    "THEAD",
    "TBODY",
    "TR",
    "TH",
    "TD",
  ]);
  const output = document.createElement("div");
  function copy(from, to, depth = 0) {
    if (depth > 100) return;
    for (const node of from.childNodes) {
      if (node.nodeType === Node.TEXT_NODE)
        to.append(document.createTextNode(node.textContent));
      else if (
        node.nodeType === Node.ELEMENT_NODE &&
        allowed.has(node.tagName)
      ) {
        const child = document.createElement(node.tagName.toLowerCase());
        copy(node, child, depth + 1);
        to.append(child);
      }
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
