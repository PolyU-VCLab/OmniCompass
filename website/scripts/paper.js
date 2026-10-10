export function arxivPdfUrl(value) {
  if (typeof value !== "string" || !value.trim()) return "";
  try {
    const url = new URL(value);
    if (url.protocol !== "https:" || !["arxiv.org", "www.arxiv.org"].includes(url.hostname)) return "";
    if (url.username || url.password || url.port) return "";
    const match = url.pathname.match(/^\/(?:abs|pdf)\/(\d{4}\.\d{4,5}(?:v\d+)?)(?:\.pdf)?$/);
    return match ? `https://arxiv.org/pdf/${match[1]}` : "";
  } catch {
    return "";
  }
}

export function configurePaperLink(link, arxivUrl) {
  const pdfUrl = arxivPdfUrl(arxivUrl);
  if (pdfUrl) {
    link.setAttribute("href", pdfUrl);
    link.setAttribute("target", "_blank");
    link.setAttribute("rel", "noopener noreferrer");
    link.removeAttribute("aria-disabled");
    link.removeAttribute("tabindex");
  } else {
    for (const name of ["href", "target", "rel"]) link.removeAttribute(name);
    link.setAttribute("aria-disabled", "true");
    link.setAttribute("tabindex", "-1");
  }
  return pdfUrl;
}
